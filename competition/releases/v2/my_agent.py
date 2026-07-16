from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from collections import Counter, deque
import hashlib, json, math, random, time
try:
    from arcengine import FrameData, GameAction, GameState
    from agents.agent import Agent
except Exception:
    FrameData = Any
    class GameState:
        WIN="WIN"; GAME_OVER="GAME_OVER"; NOT_PLAYED="NOT_PLAYED"
    class _FallbackAction:
        def __init__(self, name): self.name=name; self.data=None; self.reasoning=""
        def __repr__(self): return self.name
        def __str__(self): return self.name
        def is_complex(self): return self.name.endswith("XY")
        def set_data(self, data): self.data=data
    class _GameAction:
        RESET=_FallbackAction("RESET"); ACTION1=_FallbackAction("ACTION1"); ACTION2=_FallbackAction("ACTION2"); ACTION3=_FallbackAction("ACTION3"); ACTION4=_FallbackAction("ACTION4"); ACTIONXY=_FallbackAction("ACTIONXY")
        def __iter__(self): return iter([self.RESET,self.ACTION1,self.ACTION2,self.ACTION3,self.ACTION4,self.ACTIONXY])
    GameAction=_GameAction()
    class Agent:
        def __init__(self,*args:Any,**kwargs:Any): self.game_id=kwargs.get("game_id","local")

Grid = tuple[tuple[int, ...], ...]
Action = Any
class EnvironmentStatus(str, Enum): ACTIVE="active"; WIN="win"; GAME_OVER="game_over"
def as_grid(frame: Any) -> Grid:
    if isinstance(frame, tuple): return tuple(tuple(int(x) for x in r) for r in frame)
    if hasattr(frame, "tolist"): frame = frame.tolist()
    if isinstance(frame, list) and frame and not isinstance(frame[0], (list, tuple)): return (tuple(int(x) for x in frame),)
    return tuple(tuple(int(x) for x in row) for row in frame)
def grid_shape(grid: Grid) -> tuple[int,int]: return (len(grid), len(grid[0]) if grid else 0)
def grid_hash(grid: Grid) -> str: return hashlib.sha256(json.dumps(grid,separators=(",",":")).encode()).hexdigest()[:16]
@dataclass(frozen=True)
class Observation: grid: Grid; legal_actions: tuple[Action,...]; status: EnvironmentStatus=EnvironmentStatus.ACTIVE; frame_index:int=0; metadata:dict[str,Any]=field(default_factory=dict)
@dataclass(frozen=True)
class Component: id:str; value:int; cells:tuple[tuple[int,int],...]; bbox:tuple[int,int,int,int]; centroid:tuple[float,float]; area:int; signature:str; border:tuple[str,...]=()
@dataclass(frozen=True)
class Scene: grid:Grid; components:tuple[Component,...]; relations:tuple[tuple[str,str,str],...]; features:dict[str,Any]
@dataclass(frozen=True)
class Transition: previous:Scene; action:Action; result:Scene; mapping:dict[str,str]; changed_cells:tuple[tuple[int,int],...]; created:tuple[str,...]; deleted:tuple[str,...]; terminal:EnvironmentStatus
@dataclass(frozen=True)
class Operation: name:str; args:tuple[Any,...]=()
@dataclass(frozen=True)
class Rule: action:Action|None; operations:tuple[Operation,...]; conditions:tuple[str,...]=(); complexity:float=1.0; evidence:int=0
@dataclass(frozen=True)
class Hypothesis: rule:Rule; log_weight:float; loss:float=0.0; contradictions:int=0; provenance:str="prior"
@dataclass(frozen=True)
class Goal: name:str; probability:float; target:Any=None; evidence:tuple[str,...]=()
@dataclass
class Episode: observations:list[Observation]=field(default_factory=list); transitions:list[Transition]=field(default_factory=list); actions:list[Action]=field(default_factory=list); timeline:list[dict[str,Any]]=field(default_factory=list)
@dataclass
class StateNode:
    state_hash: str; first_grid: Grid; visits: int = 0; terminal: str = 'active'
@dataclass
class StateActionEdge:
    source: str; action: str; target: str; count: int = 1; changed: int = 0; reversible: bool = False; ineffective: bool = False
@dataclass
class StateActionGraph:
    nodes: dict[str, StateNode] = field(default_factory=dict); edges: dict[tuple[str,str], StateActionEdge] = field(default_factory=dict); action_attempts: dict[tuple[str,str], int] = field(default_factory=dict)
    def observe_state(self, grid:Grid, terminal='active'):
        h=grid_hash(grid); node=self.nodes.setdefault(h, StateNode(h, grid, 0, terminal)); node.visits += 1; node.terminal=terminal; return h
    def record(self, source, action, target, changed):
        key=(source,str(action)); self.action_attempts[key]=self.action_attempts.get(key,0)+1; edge=self.edges.get(key)
        if edge is None: self.edges[key]=StateActionEdge(source,str(action),target,1,changed,False,changed==0)
        else: edge.target=target; edge.count+=1; edge.changed=changed; edge.ineffective=edge.ineffective and changed==0
    def tried(self, state_hash, action): return self.action_attempts.get((state_hash,str(action)),0)
    def frontier_actions(self, state_hash, legal): return [a for a in legal if self.tried(state_hash,a)==0]
    def repeated_ineffective(self, state_hash, action):
        edge=self.edges.get((state_hash,str(action))); return bool(edge and edge.ineffective and edge.count>=1)

@dataclass(frozen=True)
class AxiomConfig:
    seed:int=0; particle_count:int=64; max_hypotheses:int=96; max_mutations:int=32; max_history:int=256; planning_depth:int=18; coordinate_candidate_limit:int=64; per_action_ms:int=35; global_seconds:int=660
    w_information:float=1.0; w_progress:float=.8; w_novelty:float=.75; w_reversibility:float=.35; w_risk:float=1.2; w_repeat:float=.8; w_cost:float=.02; neural_proposer_enabled:bool=False

def infer_background(grid:Grid)->int: return Counter(x for r in grid for x in r).most_common(1)[0][0] if grid else 0
def _signature(cells):
    ys=[y for y,_ in cells]; xs=[x for _,x in cells]; my,mx=min(ys),min(xs); return hashlib.sha1(repr(tuple(sorted((y-my,x-mx) for y,x in cells))).encode()).hexdigest()[:12]
def connected_components(grid:Grid, connectivity:int=4, include_background:bool=False, background:int|None=None)->tuple[Component,...]:
    h,w=grid_shape(grid); bg=infer_background(grid) if background is None else background; seen=set(); nbr4=((1,0),(-1,0),(0,1),(0,-1)); nbr8=nbr4+((1,1),(1,-1),(-1,1),(-1,-1)); nbrs=nbr8 if connectivity==8 else nbr4; comps=[]; idx=0
    for y in range(h):
      for x in range(w):
        if (y,x) in seen or (not include_background and grid[y][x]==bg): continue
        val=grid[y][x]; q=deque([(y,x)]); seen.add((y,x)); cells=[]
        while q:
          cy,cx=q.popleft(); cells.append((cy,cx))
          for dy,dx in nbrs:
            ny,nx=cy+dy,cx+dx
            if 0<=ny<h and 0<=nx<w and (ny,nx) not in seen and grid[ny][nx]==val:
              seen.add((ny,nx)); q.append((ny,nx))
        ys=[c[0] for c in cells]; xs=[c[1] for c in cells]; bbox=(min(ys),min(xs),max(ys)+1,max(xs)+1); border=tuple(n for n,b in (("top",bbox[0]==0),("left",bbox[1]==0),("bottom",bbox[2]==h),("right",bbox[3]==w)) if b); sig=_signature(cells); comps.append(Component(f"v{val}_{idx}_{sig}",val,tuple(sorted(cells)),bbox,(sum(ys)/len(cells),sum(xs)/len(cells)),len(cells),sig,border)); idx+=1
    return tuple(comps)
def build_scene(grid:Grid)->Scene:
    comps=connected_components(grid); rel=[]
    for i,a in enumerate(comps):
      for b in comps[i+1:]:
        if a.value==b.value: rel.append((a.id,"same_value",b.id))
        if a.signature==b.signature: rel.append((a.id,"same_shape",b.id))
        if any(abs(y1-y2)+abs(x1-x2)==1 for y1,x1 in a.cells for y2,x2 in b.cells): rel.append((a.id,"touching",b.id))
    return Scene(grid, comps, tuple(rel), {"hash":grid_hash(grid),"shape":grid_shape(grid),"background":infer_background(grid),"values":tuple(sorted({x for r in grid for x in r}))})
def diff_cells(a:Grid,b:Grid)->tuple[tuple[int,int],...]:
    h,w=grid_shape(b); return tuple((y,x) for y in range(h) for x in range(w) if y>=len(a) or x>=len(a[y]) or a[y][x]!=b[y][x])
def track(prev, nxt):
    out={}; used=set()
    for a in prev.components:
      best=None; score=10**9; aset=set(a.cells)
      for b in nxt.components:
        if b.id in used: continue
        overlap=len(aset & set(b.cells)); dist=abs(a.centroid[0]-b.centroid[0])+abs(a.centroid[1]-b.centroid[1]); s=(a.value!=b.value)*4+(a.signature!=b.signature)*2+dist-overlap
        if s<score: score=s; best=b
      if best and score<7: out[a.id]=best.id; used.add(best.id)
    return out

@dataclass
class ActionSemanticsPosterior:
    meanings: dict[str, dict[str,float]] = field(default_factory=dict)
    def ensure(self, actions):
        prior={"no_op":.18,"move_up":.14,"move_down":.14,"move_left":.14,"move_right":.14,"select":.08,"toggle":.08,"interact":.1}
        for a in actions: self.meanings.setdefault(str(a), dict(prior))
    def update_from_delta(self, action, moved_delta, changed):
        self.ensure([action]); dist=self.meanings[str(action)]
        if moved_delta:
            label={(-1,0):"move_up",(1,0):"move_down",(0,-1):"move_left",(0,1):"move_right"}.get(moved_delta,"interact"); dist[label]=dist.get(label,0)+1.0
        elif changed==0: dist["no_op"]=dist.get("no_op",0)+.7
        else: dist["interact"]=dist.get("interact",0)+.6
        s=sum(dist.values()) or 1.0
        for k in list(dist): dist[k]/=s
    def best(self, action):
        d=self.meanings.get(str(action),{}); return max(d.items(), key=lambda kv:kv[1]) if d else ("unknown",0.0)

MOVE={"up":(-1,0),"down":(1,0),"left":(0,-1),"right":(0,1),"w":(-1,0),"s":(1,0),"a":(0,-1),"d":(0,1)}
def execute(grid:Grid, rule:Rule, action)->Grid:
    if rule.action is not None and str(rule.action)!=str(action): return grid
    g=[list(r) for r in grid]; bg=max({v:sum(row.count(v) for row in g) for v in {x for r in g for x in r}}.items(), key=lambda kv:kv[1])[0] if g else 0
    for op in rule.operations:
      if op.name=="no_op": continue
      if op.name in ("move","push"):
        val,delta=op.args[0], op.args[1] if len(op.args)>1 else MOVE.get(str(action),(0,0)); cells=[(y,x) for y,row in enumerate(g) for x,v in enumerate(row) if v==val]; dest=[(y+delta[0],x+delta[1]) for y,x in cells]
        if cells and all(0<=y<len(g) and 0<=x<len(g[0]) and (g[y][x] in (bg,val)) for y,x in dest):
          for y,x in cells: g[y][x]=bg
          for y,x in dest: g[y][x]=val
      elif op.name in ("collect","disappear"):
        val=op.args[0]; g=[[bg if v==val else v for v in row] for row in g]
      elif op.name in ("toggle","recolor"):
        a,b=op.args[:2]; g=[[b if v==a else v for v in row] for row in g]
      elif op.name=="appear":
        val,y,x=op.args[:3]
        if 0<=y<len(g) and 0<=x<len(g[0]): g[y][x]=val
      elif op.name=="teleport":
        val,y,x=op.args[:3]; g=[[bg if v==val else v for v in row] for row in g]
        if 0<=y<len(g) and 0<=x<len(g[0]): g[y][x]=val
    return tuple(tuple(r) for r in g)
def prior_hypotheses(actions, n=64):
    base=[Hypothesis(Rule(a,(Operation("no_op"),),(),1.0,0), -1.0, provenance="prior") for a in actions]
    return tuple((base or [Hypothesis(Rule(None,(Operation("no_op"),)),0.0)])[(i%max(1,len(base)))] for i in range(max(1,n)))
def prediction_loss(a,b): return 1.0 if len(a)!=len(b) or (a and len(a[0])!=len(b[0])) else sum(a[y][x]!=b[y][x] for y in range(len(a)) for x in range(len(a[0])))/max(1,len(a)*len(a[0]))
def normalize(parts):
    if not parts: return ()
    m=max(p.log_weight for p in parts); vals=[math.exp(p.log_weight-m) for p in parts]; s=sum(vals) or 1.0
    return tuple(Hypothesis(p.rule, math.log(v/s), p.loss, p.contradictions, p.provenance) for p,v in zip(parts,vals))
def entropy(parts):
    ps=[math.exp(p.log_weight) for p in normalize(parts)]; return -sum(p*math.log(p+1e-12) for p in ps)
def effective_sample_size(parts):
    ps=[math.exp(p.log_weight) for p in normalize(parts)]; return 1.0/sum(p*p for p in ps) if ps else 0.0
def deduplicate(parts):
    seen={}
    for p in parts:
        k=repr((p.rule.action,p.rule.operations,p.rule.conditions))
        if k not in seen or p.log_weight>seen[k].log_weight: seen[k]=p
    return tuple(seen.values())
def update_particles(parts, prev_grid, action, next_grid):
    out=[]
    for p in parts:
      pred=execute(prev_grid,p.rule,action); l=prediction_loss(pred,next_grid); unexplained=0.15 if l>.25 and p.rule.operations[0].name=='no_op' else 0.0; out.append(Hypothesis(p.rule,p.log_weight-8*l-unexplained-.05*p.rule.complexity,l,p.contradictions+(l>.5),p.provenance))
    return normalize(deduplicate(tuple(out)))
def resample(parts, target, seed=0):
    parts=normalize(parts); ps=[math.exp(p.log_weight) for p in parts]; rng=random.Random(seed); out=[]
    for _ in range(target):
        r=rng.random(); acc=0
        for p,prob in zip(parts,ps):
            acc+=prob
            if r<=acc: out.append(Hypothesis(p.rule, -math.log(target), p.loss, p.contradictions, p.provenance)); break
    return tuple(out) or parts
def top(parts,k=5): return sorted(normalize(parts), key=lambda p:p.log_weight, reverse=True)[:k]
def induce_rules(transition, limit=96):
    rules=[Rule(transition.action,(Operation("no_op"),),(),1.0,1)]
    for old,new in transition.mapping.items():
      a=next(c for c in transition.previous.components if c.id==old); b=next(c for c in transition.result.components if c.id==new); dy=round(b.centroid[0]-a.centroid[0]); dx=round(b.centroid[1]-a.centroid[1])
      if (dy,dx)!=(0,0): rules.append(Rule(transition.action,(Operation("move",(a.value,(dy,dx))),),(),2.0,1))
    vals0={c.value for c in transition.previous.components}; vals1={c.value for c in transition.result.components}
    for v in vals0-vals1: rules.append(Rule(transition.action,(Operation("collect",(v,)),),(),2.0,1))
    for v in vals1-vals0:
      c=next(c for c in transition.result.components if c.value==v); y,x=c.cells[0]; rules.append(Rule(transition.action,(Operation("appear",(v,y,x)),),(),3.0,1))
    return tuple(rules[:limit])
def expected_information_gain(parts, action): return max(0.0, entropy(parts)-entropy(tuple(p for p in parts if str(p.rule.action)==str(action)) or parts)*0.9)
def reversibility_score(action, legal):
    inv={"up":"down","down":"up","left":"right","right":"left","w":"s","s":"w","a":"d","d":"a"}; return 1.0 if inv.get(str(action)) in {str(a) for a in legal} else .45
def risk_score(action, predicted_terminal=False): return min(1.0, (.8 if predicted_terminal else 0.0)+(.2 if str(action).lower() in {"reset","quit","delete"} else 0.0))
def novelty_score(state_hash, action, tried): return 0.0 if (state_hash,str(action)) in tried else 1.0
def select_action(config, parts, legal, state_hash, tried, deadline):
    best=legal[0] if legal else None; best_score=-10**9; diag={}
    for a in legal:
      if deadline(): break
      ig=expected_information_gain(parts,a); n=novelty_score(state_hash,a,tried); r=reversibility_score(a,legal); q=risk_score(a); rep=1-n; s=config.w_information*ig+config.w_novelty*n+config.w_reversibility*r-config.w_risk*q-config.w_repeat*rep-config.w_cost
      diag[str(a)]={"score":round(s,3),"information":round(ig,3),"novelty":n,"reversibility":r,"risk":q}
      if s>best_score or (s==best_score and str(a)<str(best)): best_score=s; best=a
    return best, diag
def induce_goals(scene, transition=None):
    vals=scene.features.get("values",()) if scene else (); goals=[]
    for v in vals: goals.append(Goal(f"reach_or_affect_value_{v}",1/max(1,len(vals)),v,("visual_value",)))
    if transition and transition.deleted: goals.append(Goal("remove_or_collect_objects",.7,transition.deleted,("disappearance",)))
    if transition and transition.terminal.value=='win': goals.append(Goal("terminal_success_configuration",.95,scene.features.get('hash'),("win",)))
    if len(vals)>3: goals.append(Goal("match_or_transform_pattern",.35,tuple(vals),("multi_value_scene",)))
    return tuple(sorted(goals, key=lambda g:g.probability, reverse=True))
def update_goals(goals, scene, transition=None): return goals or induce_goals(scene,transition)
def coordinate_candidates(scene, limit=64):
    h,w=scene.features.get('shape',(0,0)); pts={(0,0),(max(0,h-1),0),(0,max(0,w-1)),(max(0,h-1),max(0,w-1)),(h//2 if h else 0,w//2 if w else 0)}
    for c in scene.components:
        cy,cx=c.centroid; pts.add((round(cy),round(cx)))
        y0,x0,y1,x1=c.bbox
        for p in ((y0,x0),(y0,x1-1),(y1-1,x0),(y1-1,x1-1)): pts.add(p)
        for y,x in c.cells[:4]: pts.add((y,x))
    return tuple((y,x) for y,x in sorted(pts) if 0<=y<h and 0<=x<w)[:limit]
class Deadline:
    def __init__(self, seconds): self.end=time.monotonic()+max(0.001,seconds)
    def expired(self): return time.monotonic()>=self.end
class AxiomRuntime:
    def __init__(self, config=None):
        self.config=config or AxiomConfig(); self.rng=random.Random(self.config.seed); self.episode=Episode(); self.hypotheses=(); self.goals=(); self.tried=set(); self.last_scene=None; self.last_action=None; self.loop_counts={}; self.action_semantics=ActionSemanticsPosterior(); self.state_graph=StateActionGraph(); self.mechanics=[]; self.game_grammar={}; self.state_graph=StateActionGraph(); self.mechanics=[]
    def reset_episode(self): self.episode=Episode(); self.hypotheses=(); self.goals=(); self.tried=set(); self.last_scene=None; self.last_action=None; self.loop_counts={}; self.action_semantics=ActionSemanticsPosterior()
    def observe(self, obs, deadline):
        scene=build_scene(obs.grid); self.episode.observations.append(obs); current_hash=self.state_graph.observe_state(obs.grid, obs.status.value); self.action_semantics.ensure(obs.legal_actions)
        if not self.hypotheses: self.hypotheses=prior_hypotheses(obs.legal_actions,self.config.particle_count)
        if self.last_scene is not None and self.last_action is not None and not deadline.expired():
          mapping=track(self.last_scene,scene); trans=Transition(self.last_scene,self.last_action,scene,mapping,diff_cells(self.last_scene.grid,scene.grid),tuple(set(c.id for c in scene.components)-set(mapping.values())),tuple(set(c.id for c in self.last_scene.components)-set(mapping.keys())),obs.status); self.episode.transitions.append(trans); prev_hash=grid_hash(self.last_scene.grid); self.state_graph.record(prev_hash,self.last_action,current_hash,len(trans.changed_cells))
          moved_delta=None
          if mapping:
            old,new=next(iter(mapping.items())); oc=next(c for c in self.last_scene.components if c.id==old); nc=next(c for c in scene.components if c.id==new); moved_delta=(round(nc.centroid[0]-oc.centroid[0]), round(nc.centroid[1]-oc.centroid[1]))
          self.action_semantics.update_from_delta(self.last_action,moved_delta,len(trans.changed_cells)); self.hypotheses=update_particles(self.hypotheses,self.last_scene.grid,self.last_action,scene.grid); rules=induce_rules(trans,self.config.max_hypotheses); additions=tuple(Hypothesis(r,-6.0,provenance="induced") for r in rules[:self.config.max_mutations]); self.hypotheses=normalize((self.hypotheses+additions)[:self.config.particle_count])
          if effective_sample_size(self.hypotheses)<max(2,self.config.particle_count/4): self.hypotheses=resample(self.hypotheses,self.config.particle_count,self.config.seed+len(self.episode.transitions))
          self.goals=update_goals(self.goals,scene,trans)
        else: self.goals=update_goals(self.goals,scene,None)
        self.last_scene=scene; return scene
    def choose_action(self, obs, per_action_ms=None):
        deadline=Deadline((per_action_ms or self.config.per_action_ms)/1000); legal=list(obs.legal_actions)
        if not legal: return None
        try:
          scene=self.observe(obs,deadline); h=grid_hash(obs.grid); frontier=self.state_graph.frontier_actions(h,legal)
          if frontier and len(self.episode.transitions)<max(1,len(legal)*2): action=frontier[0]; diag={'mode':'systematic_frontier'}
          else:
            action,diag=select_action(self.config,self.hypotheses,legal,h,self.tried,deadline.expired)
            if self.state_graph.repeated_ineffective(h, action):
              alternatives=[a for a in legal if not self.state_graph.repeated_ineffective(h,a)]
              if alternatives: action=alternatives[0]
          if action not in legal or deadline.expired(): action=legal[0]
        except Exception:
          action=legal[0]; h=grid_hash(obs.grid)
        self.tried.add((h,str(action))); self.episode.actions.append(action); self.last_action=action; self.loop_counts[h]=self.loop_counts.get(h,0)+1
        if len(self.episode.timeline)>self.config.max_history: self.episode.timeline=self.episode.timeline[-self.config.max_history:]
        return action

def _state_name(value):
    name=getattr(value, 'name', None)
    return str(name if name is not None else value)
def _is_state(value, member): return value is member or _state_name(value).endswith(_state_name(member))
class MyAgent(Agent):
    MAX_ACTIONS=80
    def __init__(self,*args:Any,**kwargs:Any)->None:
        super().__init__(*args,**kwargs); self.runtime=AxiomRuntime(AxiomConfig(seed=abs(hash(getattr(self,"game_id","local")))%1_000_000, per_action_ms=35)); self._actions=0; self._last_level_hash=None
    @property
    def name(self)->str: return f"Axiom.{self.MAX_ACTIONS}"
    def is_done(self, frames:list[FrameData], latest_frame:FrameData)->bool:
        return _is_state(getattr(latest_frame,"state",None), getattr(GameState,"WIN",None))
    def _legal_actions(self):
        raw=None
        for owner in (GameAction,):
            try: raw=[a for a in owner if a is not getattr(GameAction,"RESET",None)]; break
            except Exception: raw=None
        if raw is None: raw=[getattr(GameAction,n) for n in dir(GameAction) if n.startswith("ACTION")]
        return tuple(a for a in raw if a is not getattr(GameAction,"RESET",None))
    def _grid(self, latest_frame):
        for name in ("grid","frame","observation","array","state"):
            if hasattr(latest_frame,name):
                val=getattr(latest_frame,name)
                if not callable(val):
                    try: return as_grid(val)
                    except Exception: continue
        return ((0,),)
    def _obs(self, latest_frame):
        st=getattr(latest_frame,"state",None); status=EnvironmentStatus.WIN if self.is_done([],latest_frame) else EnvironmentStatus.GAME_OVER if _is_state(st,getattr(GameState,"GAME_OVER",None)) else EnvironmentStatus.ACTIVE
        return Observation(self._grid(latest_frame), tuple(self._legal_actions()), status, self._actions)
    def _fallback(self, legal): return legal[0] if legal else getattr(GameAction,"RESET",None)
    def _set_complex_data(self, action, obs):
        if hasattr(action,"is_complex") and action.is_complex():
            h=len(obs.grid); w=len(obs.grid[0]) if h else 1; scene=build_scene(obs.grid); pts=coordinate_candidates(scene, 1); y,x=pts[0] if pts else (min(h-1,h//2), min(w-1,w//2)); action.set_data({"x": int(max(0,min(w-1,x))), "y": int(max(0,min(h-1,y)))})
        return action
    def choose_action(self, frames:list[FrameData], latest_frame:FrameData)->GameAction:
        deadline=Deadline(0.035)
        try:
            st=getattr(latest_frame,"state",None)
            if _is_state(st,getattr(GameState,"NOT_PLAYED",None)) or _is_state(st,getattr(GameState,"GAME_OVER",None)): return getattr(GameAction,"RESET")
            legal=list(self._legal_actions())
            if not legal: return getattr(GameAction,"RESET")
            obs=self._obs(latest_frame)
            h=grid_hash(obs.grid)
            if self._last_level_hash is not None and h!=self._last_level_hash and self.is_done(frames, latest_frame): self.runtime.game_grammar['last_win_hash']=self._last_level_hash
            self._last_level_hash=h
            action=self.runtime.choose_action(obs, per_action_ms=max(1,int((deadline.end-time.monotonic())*1000)))
            if action not in legal or deadline.expired(): action=self._fallback(legal)
            action=self._set_complex_data(action, obs)
            try: action.reasoning="axiom bounded symbolic world-model action"
            except Exception: action=action
            self._actions+=1; return action
        except Exception:
            try:
                legal=list(self._legal_actions()); action=self._fallback(legal); obs=self._obs(latest_frame); return self._set_complex_data(action, obs)
            except Exception:
                return getattr(GameAction,"RESET")

