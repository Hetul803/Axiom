%%writefile /kaggle/working/axiom_core/__init__.py



%%writefile /kaggle/working/axiom_core/causality/__init__.py



%%writefile /kaggle/working/axiom_core/causality/action_semantics.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
DIRECTIONS={"up":(-1,0),"down":(1,0),"left":(0,-1),"right":(0,1),"w":(-1,0),"s":(1,0),"a":(0,-1),"d":(0,1)}
@dataclass
class ActionSemanticsPosterior:
    meanings: dict[str, dict[str,float]] = field(default_factory=dict)
    def ensure(self, actions:list[Any]|tuple[Any,...])->None:
        prior={"no_op":.18,"move_up":.14,"move_down":.14,"move_left":.14,"move_right":.14,"select":.08,"toggle":.08,"interact":.1}
        for a in actions: self.meanings.setdefault(str(a), dict(prior))
    def update_from_delta(self, action:Any, moved_delta:tuple[int,int]|None, changed:int)->None:
        self.ensure([action]); dist=self.meanings[str(action)]
        if moved_delta:
            label={(-1,0):"move_up",(1,0):"move_down",(0,-1):"move_left",(0,1):"move_right"}.get(moved_delta,"interact"); dist[label]=dist.get(label,0)+1.0
        elif changed==0: dist["no_op"]=dist.get("no_op",0)+.7
        else: dist["interact"]=dist.get("interact",0)+.6
        s=sum(dist.values()) or 1.0
        for k in list(dist): dist[k]/=s
    def best(self, action:Any)->tuple[str,float]:
        d=self.meanings.get(str(action),{}); return max(d.items(), key=lambda kv:kv[1]) if d else ("unknown",0.0)


%%writefile /kaggle/working/axiom_core/causality/dsl.py
PREDICATES=("action_is","touching","aligned","at_border","path_exists","selected","terminal","state_variable_equals")
OPERATIONS=("no_op","move","push","collect","appear","disappear","toggle","recolor","teleport","open","close","increment","decrement","sequence_activate")


%%writefile /kaggle/working/axiom_core/causality/hypotheses.py
from axiom_core.types import Hypothesis, Rule, Operation
def prior_hypotheses(actions, n=64):
    base=[Hypothesis(Rule(a,(Operation("no_op"),),(),1.0,0), -1.0, provenance="prior") for a in actions]
    return tuple((base or [Hypothesis(Rule(None,(Operation("no_op"),)),0.0)])[(i%max(1,len(base)))] for i in range(max(1,n)))


%%writefile /kaggle/working/axiom_core/causality/interpreter.py
from axiom_core.types import Grid, Rule
MOVE={"up":(-1,0),"down":(1,0),"left":(0,-1),"right":(0,1),"w":(-1,0),"s":(1,0),"a":(0,-1),"d":(0,1)}
def _set(grid,y,x,v): r=[list(row) for row in grid]; r[y][x]=v; return tuple(tuple(row) for row in r)
def execute(grid:Grid, rule:Rule, action)->Grid:
    if rule.action is not None and str(rule.action)!=str(action): return grid
    g=[list(r) for r in grid]; bg=max({v:sum(row.count(v) for row in g) for v in {x for r in g for x in r}}.items(), key=lambda kv:kv[1])[0]
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


%%writefile /kaggle/working/axiom_core/causality/particles.py
import math, random
from axiom_core.types import Hypothesis
from axiom_core.causality.interpreter import execute
def loss(a,b): return 1.0 if len(a)!=len(b) or (a and len(a[0])!=len(b[0])) else sum(a[y][x]!=b[y][x] for y in range(len(a)) for x in range(len(a[0])))/max(1,len(a)*len(a[0]))
def normalize(parts):
    if not parts: return ()
    m=max(p.log_weight for p in parts); vals=[math.exp(p.log_weight-m) for p in parts]; s=sum(vals) or 1.0
    return tuple(Hypothesis(p.rule, math.log(v/s), p.loss, p.contradictions, p.provenance) for p,v in zip(parts,vals))
def entropy(parts):
    ps=[math.exp(p.log_weight) for p in normalize(parts)]; return -sum(p*math.log(p+1e-12) for p in ps)
def effective_sample_size(parts):
    ps=[math.exp(p.log_weight) for p in normalize(parts)]; return 1.0/sum(p*p for p in ps) if ps else 0.0
def deduplicate(parts):
    seen={};
    for p in parts:
        k=repr((p.rule.action,p.rule.operations,p.rule.conditions))
        if k not in seen or p.log_weight>seen[k].log_weight: seen[k]=p
    return tuple(seen.values())
def update(parts, prev_grid, action, next_grid):
    out=[]
    for p in parts:
      pred=execute(prev_grid,p.rule,action); l=loss(pred,next_grid); unexplained=0.15 if l>.25 and p.rule.operations[0].name=='no_op' else 0.0; out.append(Hypothesis(p.rule,p.log_weight-8*l-unexplained-.05*p.rule.complexity,l,p.contradictions+(l>.5),p.provenance))
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


%%writefile /kaggle/working/axiom_core/causality/rule_induction.py
from axiom_core.types import Rule, Operation
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


%%writefile /kaggle/working/axiom_core/config.py
from dataclasses import dataclass
@dataclass(frozen=True)
class AxiomConfig:
    seed:int=0; particle_count:int=64; max_hypotheses:int=96; max_mutations:int=32; max_history:int=256; planning_depth:int=18; coordinate_candidate_limit:int=64; per_action_ms:int=35; global_seconds:int=11*60
    w_information:float=1.0; w_progress:float=.8; w_novelty:float=.75; w_reversibility:float=.35; w_risk:float=1.2; w_repeat:float=.8; w_cost:float=.02; neural_proposer_enabled:bool=False


%%writefile /kaggle/working/axiom_core/exploration/__init__.py



%%writefile /kaggle/working/axiom_core/exploration/coordinates.py
def coordinate_candidates(scene, limit=64):
    h,w=scene.features.get('shape',(0,0)); pts={(0,0),(max(0,h-1),0),(0,max(0,w-1)),(max(0,h-1),max(0,w-1)),(h//2 if h else 0,w//2 if w else 0)}
    for c in scene.components:
        cy,cx=c.centroid; pts.add((round(cy),round(cx)))
        y0,x0,y1,x1=c.bbox
        for p in ((y0,x0),(y0,x1-1),(y1-1,x0),(y1-1,x1-1)): pts.add(p)
        for y,x in c.cells[:4]: pts.add((y,x))
    return tuple((y,x) for y,x in sorted(pts) if 0<=y<h and 0<=x<w)[:limit]


%%writefile /kaggle/working/axiom_core/exploration/information_gain.py
from axiom_core.causality.particles import entropy
def expected_information_gain(parts, action): return max(0.0, entropy(parts)-entropy(tuple(p for p in parts if str(p.rule.action)==str(action)) or parts)*0.9)


%%writefile /kaggle/working/axiom_core/exploration/novelty.py
def score(state_hash, action, tried): return 0.0 if (state_hash,str(action)) in tried else 1.0


%%writefile /kaggle/working/axiom_core/exploration/reversibility.py
def score(action, legal):
    inv={"up":"down","down":"up","left":"right","right":"left","w":"s","s":"w","a":"d","d":"a"}; return 1.0 if inv.get(str(action)) in {str(a) for a in legal} else .45


%%writefile /kaggle/working/axiom_core/exploration/risk.py
def score(action, predicted_terminal=False): return min(1.0, (.8 if predicted_terminal else 0.0)+(.2 if str(action).lower() in {"reset","quit","delete"} else 0.0))


%%writefile /kaggle/working/axiom_core/exploration/selector.py
from axiom_core.exploration.information_gain import expected_information_gain
from axiom_core.exploration.reversibility import score as rev
from axiom_core.exploration.risk import score as risk
from axiom_core.exploration.novelty import score as nov
def choose(config, parts, legal, state_hash, tried, deadline):
    best=legal[0] if legal else None; best_score=-10**9; diag={}
    for a in legal:
      ig=expected_information_gain(parts,a); n=nov(state_hash,a,tried); r=rev(a,legal); q=risk(a); rep=1-n; s=config.w_information*ig+config.w_novelty*n+config.w_reversibility*r-config.w_risk*q-config.w_repeat*rep-config.w_cost
      diag[str(a)]={"score":s,"information":ig,"novelty":n,"reversibility":r,"risk":q}
      if s>best_score or (s==best_score and str(a)<str(best)): best_score=s; best=a
    return best, diag


%%writefile /kaggle/working/axiom_core/goals/__init__.py



%%writefile /kaggle/working/axiom_core/goals/induction.py
from axiom_core.types import Goal
def induce(scene, transition=None):
    vals=scene.features.get("values",()) if scene else (); goals=[]
    for v in vals: goals.append(Goal(f"reach_or_affect_value_{v}",1/max(1,len(vals)),v,("visual_value",)))
    if transition and transition.deleted: goals.append(Goal("remove_or_collect_objects",.7,transition.deleted,("disappearance",)))
    if transition and transition.terminal.value=='win': goals.append(Goal("terminal_success_configuration",.95,scene.features.get('hash'),("win",)))
    if len(vals)>3: goals.append(Goal("match_or_transform_pattern",.35,tuple(vals),("multi_value_scene",)))
    return tuple(sorted(goals, key=lambda g:g.probability, reverse=True))
def progress(goal, scene):
    vals=set(scene.features.get('values',()))
    if goal.name.startswith('reach_or_affect'): return 1.0 if goal.target in vals else 0.0
    if goal.name.startswith('remove'): return .5
    return 0.0


%%writefile /kaggle/working/axiom_core/goals/posterior.py
def update(goals, scene, transition=None): return goals or __import__('axiom_core.goals.induction',fromlist=['induce']).induce(scene,transition)


%%writefile /kaggle/working/axiom_core/goals/predicates.py
def contains_value(scene,value): return value in scene.features.get('values',())
def removed_value(scene,value): return value not in scene.features.get('values',())


%%writefile /kaggle/working/axiom_core/memory/__init__.py



%%writefile /kaggle/working/axiom_core/memory/consolidation.py
def consolidate(episode): return {"transitions":len(episode.transitions),"actions":len(episode.actions)}


%%writefile /kaggle/working/axiom_core/memory/episode.py
import json
from axiom_core.types import to_jsonable
def dumps_jsonl(episode): return '\n'.join(json.dumps(to_jsonable(x),sort_keys=True) for x in episode.timeline)


%%writefile /kaggle/working/axiom_core/perception/__init__.py



%%writefile /kaggle/working/axiom_core/perception/components.py
from collections import Counter, deque
from axiom_core.types import Component, Grid, grid_shape
import hashlib
def infer_background(grid:Grid)->int: return Counter(x for r in grid for x in r).most_common(1)[0][0] if grid else 0
def signature(cells):
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
        ys=[c[0] for c in cells]; xs=[c[1] for c in cells]; bbox=(min(ys),min(xs),max(ys)+1,max(xs)+1); border=tuple(n for n,b in (("top",bbox[0]==0),("left",bbox[1]==0),("bottom",bbox[2]==h),("right",bbox[3]==w)) if b); sig=signature(cells); comps.append(Component(f"v{val}_{idx}_{sig}",val,tuple(sorted(cells)),bbox,(sum(ys)/len(cells),sum(xs)/len(cells)),len(cells),sig,border)); idx+=1
    return tuple(comps)


%%writefile /kaggle/working/axiom_core/perception/paths.py
from collections import deque
def path_exists(grid,start,goal,blocked_values=frozenset({1})):
    h=len(grid); w=len(grid[0]) if h else 0; q=deque([start]); seen={start}
    while q:
        y,x=q.popleft()
        if (y,x)==goal: return True
        for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
            ny,nx=y+dy,x+dx
            if 0<=ny<h and 0<=nx<w and (ny,nx) not in seen and grid[ny][nx] not in blocked_values:
                seen.add((ny,nx)); q.append((ny,nx))
    return False


%%writefile /kaggle/working/axiom_core/perception/roles.py
def role_candidates(scene, previous=None):
    roles={}
    values=scene.features.get('values',())
    for c in scene.components:
        r={"controllable":0.18,"obstacle":0.16,"target":0.16,"collectible":0.16,"hazard":0.08,"portal":0.08,"key":0.08,"door":0.08,"counter":0.02}
        if c.area==1: r["controllable"]+=.12; r["collectible"]+=.08
        if c.border: r["obstacle"]+=.08
        if len(values)>4: r["counter"]+=.04
        s=sum(r.values()); roles[c.id]={k:v/s for k,v in r.items()}
    return roles


%%writefile /kaggle/working/axiom_core/perception/scene_graph.py
from axiom_core.types import Grid, Scene, grid_hash, grid_shape
from axiom_core.perception.components import connected_components, infer_background
def build_scene(grid:Grid)->Scene:
    comps=connected_components(grid); rel=[]
    for i,a in enumerate(comps):
      for b in comps[i+1:]:
        if a.value==b.value: rel.append((a.id,"same_value",b.id))
        if a.signature==b.signature: rel.append((a.id,"same_shape",b.id))
        if any(abs(y1-y2)+abs(x1-x2)==1 for y1,x1 in a.cells for y2,x2 in b.cells): rel.append((a.id,"touching",b.id))
    return Scene(grid, comps, tuple(rel), {"hash":grid_hash(grid),"shape":grid_shape(grid),"background":infer_background(grid),"values":tuple(sorted({x for r in grid for x in r}))})


%%writefile /kaggle/working/axiom_core/perception/tracking.py
def track(prev, nxt):
    out={}; used=set()
    for a in prev.components:
      best=None; score=10**9
      aset=set(a.cells)
      for b in nxt.components:
        if b.id in used: continue
        overlap=len(aset & set(b.cells)); dist=abs(a.centroid[0]-b.centroid[0])+abs(a.centroid[1]-b.centroid[1]); s=(a.value!=b.value)*4+(a.signature!=b.signature)*2+dist-overlap
        if s<score: score=s; best=b
      if best and score<7: out[a.id]=best.id; used.add(best.id)
    return out


%%writefile /kaggle/working/axiom_core/perception/transitions.py
from axiom_core.types import Grid, grid_shape
def diff_cells(a:Grid,b:Grid)->tuple[tuple[int,int],...]:
    h,w=grid_shape(b); return tuple((y,x) for y in range(h) for x in range(w) if y>=len(a) or x>=len(a[y]) or a[y][x]!=b[y][x])
def changed_regions(a:Grid,b:Grid): return diff_cells(a,b)


%%writefile /kaggle/working/axiom_core/planning/__init__.py



%%writefile /kaggle/working/axiom_core/planning/belief_planner.py
def confident_plan(parts, goals, legal, threshold=.65): return [legal[0]] if legal and parts and goals else []


%%writefile /kaggle/working/axiom_core/planning/search.py
from collections import deque
import heapq
def bfs(start,is_goal,successors,max_depth=18,deadline=lambda:False):
    q=deque([(start,[])]); seen={repr(start)}
    while q and not deadline():
      s,path=q.popleft()
      if is_goal(s): return path
      if len(path)>=max_depth: continue
      for a,n in successors(s):
        k=repr(n)
        if k not in seen: seen.add(k); q.append((n,path+[a]))
    return []
def astar(start,is_goal,successors,heuristic,max_depth=32,deadline=lambda:False):
    heap=[(heuristic(start),0,repr(start),start,[])]; best={repr(start):0}
    while heap and not deadline():
      _,cost,_,state,path=heapq.heappop(heap)
      if is_goal(state): return path
      if len(path)>=max_depth: continue
      for action,nxt in successors(state):
        nc=cost+1; k=repr(nxt)
        if nc<best.get(k,10**9): best[k]=nc; heapq.heappush(heap,(nc+heuristic(nxt),nc,k,nxt,path+[action]))
    return []
def iterative_deepening(start,is_goal,successors,max_depth=32,deadline=lambda:False):
    for d in range(max_depth+1):
        plan=bfs(start,is_goal,successors,d,deadline)
        if plan or deadline(): return plan
    return []


%%writefile /kaggle/working/axiom_core/planning/simulator.py
from axiom_core.causality.interpreter import execute
def simulate(grid,hypothesis,action): return execute(grid,hypothesis.rule,action)


%%writefile /kaggle/working/axiom_core/runtime.py
from __future__ import annotations
import time, random
from axiom_core.config import AxiomConfig
from axiom_core.types import Observation, EnvironmentStatus, Episode, Transition, as_grid, grid_hash
from axiom_core.perception.scene_graph import build_scene
from axiom_core.perception.tracking import track
from axiom_core.perception.transitions import diff_cells
from axiom_core.causality.hypotheses import prior_hypotheses
from axiom_core.causality.particles import update, normalize, top, effective_sample_size, resample
from axiom_core.causality.rule_induction import induce_rules
from axiom_core.types import Hypothesis
from axiom_core.exploration.selector import choose
from axiom_core.goals.posterior import update as update_goals
from axiom_core.causality.action_semantics import ActionSemanticsPosterior
class Deadline:
    def __init__(self, seconds): self.end=time.monotonic()+max(0.001,seconds)
    def expired(self): return time.monotonic()>=self.end
    def remaining(self): return max(0.0,self.end-time.monotonic())
class AxiomRuntime:
    def __init__(self, config:AxiomConfig|None=None):
        self.config=config or AxiomConfig(); self.rng=random.Random(self.config.seed); self.episode=Episode(); self.hypotheses=(); self.goals=(); self.tried=set(); self.last_scene=None; self.last_obs=None; self.last_action=None; self.grammar={}; self.loop_counts={}; self.action_semantics=ActionSemanticsPosterior(); self.game_grammar={}
    def reset_episode(self): self.episode=Episode(); self.hypotheses=(); self.goals=(); self.tried=set(); self.last_scene=None; self.last_obs=None; self.last_action=None; self.loop_counts={}; self.action_semantics=ActionSemanticsPosterior(); self.game_grammar={}
    def observe(self, obs:Observation, deadline:Deadline):
        scene=build_scene(obs.grid); self.episode.observations.append(obs)
        self.action_semantics.ensure(obs.legal_actions)
        if not self.hypotheses: self.hypotheses=prior_hypotheses(obs.legal_actions,self.config.particle_count)
        if self.last_scene is not None and self.last_action is not None and not deadline.expired():
          mapping=track(self.last_scene,scene); trans=Transition(self.last_scene,self.last_action,scene,mapping,diff_cells(self.last_scene.grid,scene.grid),tuple(set(c.id for c in scene.components)-set(mapping.values())),tuple(set(c.id for c in self.last_scene.components)-set(mapping.keys())),obs.status); self.episode.transitions.append(trans)
          moved_delta=None
          if mapping:
            old,new=next(iter(mapping.items()))
            oc=next(c for c in self.last_scene.components if c.id==old); nc=next(c for c in scene.components if c.id==new); moved_delta=(round(nc.centroid[0]-oc.centroid[0]), round(nc.centroid[1]-oc.centroid[1]))
          self.action_semantics.update_from_delta(self.last_action,moved_delta,len(trans.changed_cells))
          self.hypotheses=update(self.hypotheses,self.last_scene.grid,self.last_action,scene.grid); rules=induce_rules(trans,self.config.max_hypotheses); additions=tuple(Hypothesis(r,-6.0,provenance="induced") for r in rules[:self.config.max_mutations]); self.hypotheses=normalize((self.hypotheses+additions)[:self.config.particle_count])
          if effective_sample_size(self.hypotheses)<max(2,self.config.particle_count/4): self.hypotheses=resample(self.hypotheses,self.config.particle_count,self.config.seed+len(self.episode.transitions))
          self.goals=update_goals(self.goals,scene,trans)
        else: self.goals=update_goals(self.goals,scene,None)
        self.last_scene=scene; self.last_obs=obs; return scene
    def choose_action(self, obs:Observation, per_action_ms:int|None=None):
        deadline=Deadline((per_action_ms or self.config.per_action_ms)/1000); legal=list(obs.legal_actions)
        if not legal: return None
        try:
          scene=self.observe(obs,deadline); h=grid_hash(obs.grid); action,diag=choose(self.config,self.hypotheses,legal,h,self.tried,deadline.expired)
          if action not in legal or deadline.expired(): action=legal[0]
        except Exception as exc:
          action=legal[0]; diag={"fallback":str(exc)}; h=grid_hash(obs.grid)
        self.tried.add((h,str(action))); self.episode.actions.append(action); self.last_action=action; self.loop_counts[h]=self.loop_counts.get(h,0)+1; self.episode.timeline.append({"action":str(action),"state":h,"top_hypotheses":[{"rule":p.rule.operations[0].name,"prob":round(__import__('math').exp(p.log_weight),3)} for p in top(self.hypotheses,3)],"goals":[g.name for g in self.goals[:3]],"semantics":{str(a):self.action_semantics.best(a) for a in obs.legal_actions},"diag":diag})
        if len(self.episode.timeline)>self.config.max_history: self.episode.timeline=self.episode.timeline[-self.config.max_history:]
        return action


%%writefile /kaggle/working/axiom_core/startup_safety.py
from dataclasses import dataclass
@dataclass(frozen=True)
class ActionSafety:
    reversible: bool=True; destructive: bool=False; requires_approval: bool=False; redacted: bool=False
def classify_action(action):
    s=str(action).lower(); destructive=any(w in s for w in ('delete','reset','submit','destroy','purchase','danger'))
    return ActionSafety(reversible=not destructive, destructive=destructive, requires_approval=destructive)
def redact(value): return '<redacted>' if any(w in str(value).lower() for w in ('password','token','secret','key')) else value


%%writefile /kaggle/working/axiom_core/types.py
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Protocol
import hashlib, json, time
Grid = tuple[tuple[int, ...], ...]
Action = Any
class EnvironmentStatus(str, Enum): ACTIVE="active"; WIN="win"; GAME_OVER="game_over"
def as_grid(frame: Any) -> Grid:
    if isinstance(frame, tuple): return tuple(tuple(int(x) for x in r) for r in frame)
    if hasattr(frame, "tolist"): frame = frame.tolist()
    return tuple(tuple(int(x) for x in row) for row in frame)
def grid_shape(grid: Grid) -> tuple[int,int]: return (len(grid), len(grid[0]) if grid else 0)
def grid_hash(grid: Grid) -> str: return hashlib.sha256(json.dumps(grid,separators=(",",":")).encode()).hexdigest()[:16]
def now() -> float: return time.monotonic()
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
class AxiomEnvironment(Protocol):
    def observe(self) -> Observation: ...
    def legal_actions(self) -> list[Action]: ...
    def execute(self, action: Action) -> Observation: ...
    def status(self) -> EnvironmentStatus: ...
def to_jsonable(obj:Any)->Any:
    if hasattr(obj,"__dataclass_fields__"): return {k:to_jsonable(v) for k,v in asdict(obj).items()}
    if isinstance(obj, tuple): return [to_jsonable(x) for x in obj]
    if isinstance(obj, Enum): return obj.value
    return obj


%%writefile /kaggle/working/competition/agent/my_agent.py
from __future__ import annotations
import time, random
from typing import Any
try:
    from arcengine import FrameData, GameAction, GameState
    from agents.agent import Agent
except ImportError:  # local tests define compatible stubs only when official framework is unavailable
    FrameData = Any
    class GameState:
        WIN="WIN"; GAME_OVER="GAME_OVER"; NOT_PLAYED="NOT_PLAYED"
    class _A:
        RESET="RESET"; ACTION1="ACTION1"; ACTION2="ACTION2"; ACTION3="ACTION3"; ACTION4="ACTION4"; ACTION5="ACTION5"; ACTION6="ACTION6"
    GameAction=_A
    class Agent:
        def __init__(self,*args:Any,**kwargs:Any): self.game_id=kwargs.get("game_id","local"); self.name="agent"
from axiom_core.config import AxiomConfig
from axiom_core.runtime import AxiomRuntime
from axiom_core.types import Observation, EnvironmentStatus, as_grid
class MyAgent(Agent):
    MAX_ACTIONS=80
    def __init__(self,*args:Any,**kwargs:Any)->None:
        super().__init__(*args,**kwargs); self.runtime=AxiomRuntime(AxiomConfig(seed=abs(hash(getattr(self,"game_id","local")))%1_000_000, per_action_ms=35)); self._actions=0
    @property
    def name(self)->str: return f"Axiom.{self.MAX_ACTIONS}"
    def is_done(self, frames:list[FrameData], latest_frame:FrameData)->bool:
        return getattr(latest_frame,"state",None) is getattr(GameState,"WIN",None) or str(getattr(latest_frame,"state","")).endswith("WIN")
    def _legal_actions(self):
        try: return [a for a in GameAction if a is not GameAction.RESET]
        except TypeError: return [getattr(GameAction,n) for n in dir(GameAction) if n.startswith("ACTION")]
    def _grid(self, latest_frame):
        for name in ("grid","frame","observation","state"):
            if hasattr(latest_frame,name):
                val=getattr(latest_frame,name)
                if not callable(val):
                    try: return as_grid(val)
                    except Exception: continue
        return ((0,),)
    def _obs(self, latest_frame):
        st=getattr(latest_frame,"state",None); status=EnvironmentStatus.WIN if self.is_done([],latest_frame) else EnvironmentStatus.GAME_OVER if str(st).endswith("GAME_OVER") else EnvironmentStatus.ACTIVE
        return Observation(self._grid(latest_frame), tuple(self._legal_actions()), status, self._actions)
    def choose_action(self, frames:list[FrameData], latest_frame:FrameData)->GameAction:
        st=getattr(latest_frame,"state",None)
        if st in (getattr(GameState,"NOT_PLAYED",None), getattr(GameState,"GAME_OVER",None)) or str(st).endswith("NOT_PLAYED") or str(st).endswith("GAME_OVER"):
            return GameAction.RESET
        legal=self._legal_actions(); obs=self._obs(latest_frame); action=self.runtime.choose_action(obs, per_action_ms=35); action=action if action in legal else legal[0]
        if hasattr(action,"is_complex") and action.is_complex():
            h=len(obs.grid); w=len(obs.grid[0]) if h else 1; action.set_data({"x": min(w-1,w//2), "y": min(h-1,h//2)})
            action.reasoning={"why":"axiom bounded coordinate probe"}
        else:
            try: action.reasoning="axiom symbolic legal action"
            except Exception: action = action
        self._actions+=1; return action

