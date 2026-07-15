# Axiom ARC-AGI-3 Notebook Cells

# Cell 00 — User keeps Kaggle setup cell

Keep Kaggle's generic competition setup cell unchanged. Copy the generated cells 01–06 after it.

## 01_install_arc_runtime

```python
from pathlib import Path
import sys, subprocess
ROOT = Path('/kaggle/input/competitions/arc-prize-2026-arc-agi-3')
WHEELHOUSE = ROOT / 'arc_agi_3_wheels'
if not WHEELHOUSE.exists():
    raise FileNotFoundError(f'Missing offline ARC wheelhouse: {WHEELHOUSE}')
subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--no-index', '--find-links', str(WHEELHOUSE), 'arc-agi', 'python-dotenv'])

```

## 02_environment_and_runtime

```python
import os, random, time
from pathlib import Path
TRUE_SUBMISSION = bool(os.getenv('KAGGLE_IS_COMPETITION_RERUN'))
OUTPUT_DIR = Path('/kaggle/working'); OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SEED = 20260715
random.seed(SEED)
GLOBAL_DEADLINE = time.monotonic() + (11 * 60 if TRUE_SUBMISSION else 60)
PER_ACTION_SOFT_DEADLINE_MS = 35
PARTICLE_BUDGET = 64
MAX_HYPOTHESES = 96
MAX_HISTORY = 256
NEURAL_PROPOSER_ENABLED = False
LOG_LEVEL = 'WARNING' if TRUE_SUBMISSION else 'INFO'
ACCELERATOR = 'cpu'
def should_stop_now(margin_seconds=15):
    return time.monotonic() + margin_seconds >= GLOBAL_DEADLINE

```

## 03_write_axiom_core

```python
from pathlib import Path
ROOT = Path('/kaggle/working/axiom_core')
ROOT.mkdir(parents=True, exist_ok=True)
(ROOT / '__init__.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / '__init__.py').write_text('\n')
(ROOT / 'causality/__init__.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'causality/__init__.py').write_text('\n')
(ROOT / 'causality/dsl.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'causality/dsl.py').write_text('PREDICATES=("action_is","touching","aligned","at_border","path_exists","selected","terminal","state_variable_equals")\nOPERATIONS=("no_op","move","push","collect","appear","disappear","toggle","recolor","teleport","open","close","increment","decrement","sequence_activate")\n')
(ROOT / 'causality/hypotheses.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'causality/hypotheses.py').write_text('from axiom_core.types import Hypothesis, Rule, Operation\ndef prior_hypotheses(actions, n=64):\n    base=[Hypothesis(Rule(a,(Operation("no_op"),),(),1.0,0), -1.0, provenance="prior") for a in actions]\n    return tuple((base or [Hypothesis(Rule(None,(Operation("no_op"),)),0.0)])[(i%max(1,len(base)))] for i in range(max(1,n)))\n')
(ROOT / 'causality/interpreter.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'causality/interpreter.py').write_text('from axiom_core.types import Grid, Rule\nMOVE={"up":(-1,0),"down":(1,0),"left":(0,-1),"right":(0,1),"w":(-1,0),"s":(1,0),"a":(0,-1),"d":(0,1)}\ndef _set(grid,y,x,v): r=[list(row) for row in grid]; r[y][x]=v; return tuple(tuple(row) for row in r)\ndef execute(grid:Grid, rule:Rule, action)->Grid:\n    if rule.action is not None and str(rule.action)!=str(action): return grid\n    g=[list(r) for r in grid]; bg=max({v:sum(row.count(v) for row in g) for v in {x for r in g for x in r}}.items(), key=lambda kv:kv[1])[0]\n    for op in rule.operations:\n      if op.name=="no_op": continue\n      if op.name in ("move","push"):\n        val,delta=op.args[0], op.args[1] if len(op.args)>1 else MOVE.get(str(action),(0,0)); cells=[(y,x) for y,row in enumerate(g) for x,v in enumerate(row) if v==val]; dest=[(y+delta[0],x+delta[1]) for y,x in cells]\n        if cells and all(0<=y<len(g) and 0<=x<len(g[0]) and (g[y][x] in (bg,val)) for y,x in dest):\n          for y,x in cells: g[y][x]=bg\n          for y,x in dest: g[y][x]=val\n      elif op.name in ("collect","disappear"):\n        val=op.args[0]; g=[[bg if v==val else v for v in row] for row in g]\n      elif op.name in ("toggle","recolor"):\n        a,b=op.args[:2]; g=[[b if v==a else v for v in row] for row in g]\n      elif op.name=="appear":\n        val,y,x=op.args[:3]\n        if 0<=y<len(g) and 0<=x<len(g[0]): g[y][x]=val\n      elif op.name=="teleport":\n        val,y,x=op.args[:3]; g=[[bg if v==val else v for v in row] for row in g]\n        if 0<=y<len(g) and 0<=x<len(g[0]): g[y][x]=val\n    return tuple(tuple(r) for r in g)\n')
(ROOT / 'causality/particles.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'causality/particles.py').write_text('import math\nfrom axiom_core.types import Hypothesis\nfrom axiom_core.causality.interpreter import execute\ndef loss(a,b): return 1.0 if len(a)!=len(b) or (a and len(a[0])!=len(b[0])) else sum(a[y][x]!=b[y][x] for y in range(len(a)) for x in range(len(a[0])))/max(1,len(a)*len(a[0]))\ndef normalize(parts):\n    if not parts: return ()\n    m=max(p.log_weight for p in parts); vals=[math.exp(p.log_weight-m) for p in parts]; s=sum(vals) or 1.0\n    return tuple(Hypothesis(p.rule, math.log(v/s), p.loss, p.contradictions, p.provenance) for p,v in zip(parts,vals))\ndef update(parts, prev_grid, action, next_grid):\n    out=[]\n    for p in parts:\n      pred=execute(prev_grid,p.rule,action); l=loss(pred,next_grid); out.append(Hypothesis(p.rule,p.log_weight-8*l-.05*p.rule.complexity,l,p.contradictions+(l>.5),p.provenance))\n    return normalize(tuple(out))\ndef entropy(parts):\n    ps=[math.exp(p.log_weight) for p in normalize(parts)]; return -sum(p*math.log(p+1e-12) for p in ps)\ndef top(parts,k=5): return sorted(normalize(parts), key=lambda p:p.log_weight, reverse=True)[:k]\n')
(ROOT / 'causality/rule_induction.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'causality/rule_induction.py').write_text('from axiom_core.types import Rule, Operation\ndef induce_rules(transition, limit=96):\n    rules=[Rule(transition.action,(Operation("no_op"),),(),1.0,1)]\n    for old,new in transition.mapping.items():\n      a=next(c for c in transition.previous.components if c.id==old); b=next(c for c in transition.result.components if c.id==new); dy=round(b.centroid[0]-a.centroid[0]); dx=round(b.centroid[1]-a.centroid[1])\n      if (dy,dx)!=(0,0): rules.append(Rule(transition.action,(Operation("move",(a.value,(dy,dx))),),(),2.0,1))\n    vals0={c.value for c in transition.previous.components}; vals1={c.value for c in transition.result.components}\n    for v in vals0-vals1: rules.append(Rule(transition.action,(Operation("collect",(v,)),),(),2.0,1))\n    for v in vals1-vals0:\n      c=next(c for c in transition.result.components if c.value==v); y,x=c.cells[0]; rules.append(Rule(transition.action,(Operation("appear",(v,y,x)),),(),3.0,1))\n    return tuple(rules[:limit])\n')
(ROOT / 'config.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'config.py').write_text('from dataclasses import dataclass\n@dataclass(frozen=True)\nclass AxiomConfig:\n    seed:int=0; particle_count:int=64; max_hypotheses:int=96; max_mutations:int=32; max_history:int=256; planning_depth:int=18; coordinate_candidate_limit:int=64; per_action_ms:int=35; global_seconds:int=11*60\n    w_information:float=1.0; w_progress:float=.8; w_novelty:float=.75; w_reversibility:float=.35; w_risk:float=1.2; w_repeat:float=.8; w_cost:float=.02; neural_proposer_enabled:bool=False\n')
(ROOT / 'exploration/__init__.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'exploration/__init__.py').write_text('\n')
(ROOT / 'exploration/information_gain.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'exploration/information_gain.py').write_text('from axiom_core.causality.particles import entropy\ndef expected_information_gain(parts, action): return max(0.0, entropy(parts)-entropy(tuple(p for p in parts if str(p.rule.action)==str(action)) or parts)*0.9)\n')
(ROOT / 'exploration/novelty.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'exploration/novelty.py').write_text('def score(state_hash, action, tried): return 0.0 if (state_hash,str(action)) in tried else 1.0\n')
(ROOT / 'exploration/reversibility.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'exploration/reversibility.py').write_text('def score(action, legal):\n    inv={"up":"down","down":"up","left":"right","right":"left","w":"s","s":"w","a":"d","d":"a"}; return 1.0 if inv.get(str(action)) in {str(a) for a in legal} else .45\n')
(ROOT / 'exploration/risk.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'exploration/risk.py').write_text('def score(action, predicted_terminal=False): return min(1.0, (.8 if predicted_terminal else 0.0)+(.2 if str(action).lower() in {"reset","quit","delete"} else 0.0))\n')
(ROOT / 'exploration/selector.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'exploration/selector.py').write_text('from axiom_core.exploration.information_gain import expected_information_gain\nfrom axiom_core.exploration.reversibility import score as rev\nfrom axiom_core.exploration.risk import score as risk\nfrom axiom_core.exploration.novelty import score as nov\ndef choose(config, parts, legal, state_hash, tried, deadline):\n    best=legal[0] if legal else None; best_score=-10**9; diag={}\n    for a in legal:\n      ig=expected_information_gain(parts,a); n=nov(state_hash,a,tried); r=rev(a,legal); q=risk(a); rep=1-n; s=config.w_information*ig+config.w_novelty*n+config.w_reversibility*r-config.w_risk*q-config.w_repeat*rep-config.w_cost\n      diag[str(a)]={"score":s,"information":ig,"novelty":n,"reversibility":r,"risk":q}\n      if s>best_score or (s==best_score and str(a)<str(best)): best_score=s; best=a\n    return best, diag\n')
(ROOT / 'goals/__init__.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'goals/__init__.py').write_text('\n')
(ROOT / 'goals/induction.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'goals/induction.py').write_text('from axiom_core.types import Goal\ndef induce(scene, transition=None):\n    vals=scene.features.get("values",()) if scene else (); goals=[]\n    for v in vals: goals.append(Goal(f"reach_or_affect_value_{v}",1/max(1,len(vals)),v,("visual_value",)))\n    if transition and transition.deleted: goals.append(Goal("remove_or_collect_objects",.6,transition.deleted,("disappearance",)))\n    return tuple(goals)\n')
(ROOT / 'goals/posterior.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'goals/posterior.py').write_text("def update(goals, scene, transition=None): return goals or __import__('axiom_core.goals.induction',fromlist=['induce']).induce(scene,transition)\n")
(ROOT / 'goals/predicates.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'goals/predicates.py').write_text("def contains_value(scene,value): return value in scene.features.get('values',())\ndef removed_value(scene,value): return value not in scene.features.get('values',())\n")
(ROOT / 'memory/__init__.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'memory/__init__.py').write_text('\n')
(ROOT / 'memory/consolidation.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'memory/consolidation.py').write_text('def consolidate(episode): return {"transitions":len(episode.transitions),"actions":len(episode.actions)}\n')
(ROOT / 'memory/episode.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'memory/episode.py').write_text("import json\nfrom axiom_core.types import to_jsonable\ndef dumps_jsonl(episode): return '\\n'.join(json.dumps(to_jsonable(x),sort_keys=True) for x in episode.timeline)\n")
(ROOT / 'perception/__init__.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'perception/__init__.py').write_text('\n')
(ROOT / 'perception/components.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'perception/components.py').write_text('from collections import Counter, deque\nfrom axiom_core.types import Component, Grid, grid_shape\nimport hashlib\ndef infer_background(grid:Grid)->int: return Counter(x for r in grid for x in r).most_common(1)[0][0] if grid else 0\ndef signature(cells):\n    ys=[y for y,_ in cells]; xs=[x for _,x in cells]; my,mx=min(ys),min(xs); return hashlib.sha1(repr(tuple(sorted((y-my,x-mx) for y,x in cells))).encode()).hexdigest()[:12]\ndef connected_components(grid:Grid, connectivity:int=4, include_background:bool=False, background:int|None=None)->tuple[Component,...]:\n    h,w=grid_shape(grid); bg=infer_background(grid) if background is None else background; seen=set(); nbr4=((1,0),(-1,0),(0,1),(0,-1)); nbr8=nbr4+((1,1),(1,-1),(-1,1),(-1,-1)); nbrs=nbr8 if connectivity==8 else nbr4; comps=[]; idx=0\n    for y in range(h):\n      for x in range(w):\n        if (y,x) in seen or (not include_background and grid[y][x]==bg): continue\n        val=grid[y][x]; q=deque([(y,x)]); seen.add((y,x)); cells=[]\n        while q:\n          cy,cx=q.popleft(); cells.append((cy,cx))\n          for dy,dx in nbrs:\n            ny,nx=cy+dy,cx+dx\n            if 0<=ny<h and 0<=nx<w and (ny,nx) not in seen and grid[ny][nx]==val:\n              seen.add((ny,nx)); q.append((ny,nx))\n        ys=[c[0] for c in cells]; xs=[c[1] for c in cells]; bbox=(min(ys),min(xs),max(ys)+1,max(xs)+1); border=tuple(n for n,b in (("top",bbox[0]==0),("left",bbox[1]==0),("bottom",bbox[2]==h),("right",bbox[3]==w)) if b); sig=signature(cells); comps.append(Component(f"v{val}_{idx}_{sig}",val,tuple(sorted(cells)),bbox,(sum(ys)/len(cells),sum(xs)/len(cells)),len(cells),sig,border)); idx+=1\n    return tuple(comps)\n')
(ROOT / 'perception/scene_graph.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'perception/scene_graph.py').write_text('from axiom_core.types import Grid, Scene, grid_hash, grid_shape\nfrom axiom_core.perception.components import connected_components, infer_background\ndef build_scene(grid:Grid)->Scene:\n    comps=connected_components(grid); rel=[]\n    for i,a in enumerate(comps):\n      for b in comps[i+1:]:\n        if a.value==b.value: rel.append((a.id,"same_value",b.id))\n        if a.signature==b.signature: rel.append((a.id,"same_shape",b.id))\n        if any(abs(y1-y2)+abs(x1-x2)==1 for y1,x1 in a.cells for y2,x2 in b.cells): rel.append((a.id,"touching",b.id))\n    return Scene(grid, comps, tuple(rel), {"hash":grid_hash(grid),"shape":grid_shape(grid),"background":infer_background(grid),"values":tuple(sorted({x for r in grid for x in r}))})\n')
(ROOT / 'perception/tracking.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'perception/tracking.py').write_text('def track(prev, nxt):\n    out={}; used=set()\n    for a in prev.components:\n      best=None; score=10**9\n      aset=set(a.cells)\n      for b in nxt.components:\n        if b.id in used: continue\n        overlap=len(aset & set(b.cells)); dist=abs(a.centroid[0]-b.centroid[0])+abs(a.centroid[1]-b.centroid[1]); s=(a.value!=b.value)*4+(a.signature!=b.signature)*2+dist-overlap\n        if s<score: score=s; best=b\n      if best and score<7: out[a.id]=best.id; used.add(best.id)\n    return out\n')
(ROOT / 'perception/transitions.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'perception/transitions.py').write_text('from axiom_core.types import Grid, grid_shape\ndef diff_cells(a:Grid,b:Grid)->tuple[tuple[int,int],...]:\n    h,w=grid_shape(b); return tuple((y,x) for y in range(h) for x in range(w) if y>=len(a) or x>=len(a[y]) or a[y][x]!=b[y][x])\ndef changed_regions(a:Grid,b:Grid): return diff_cells(a,b)\n')
(ROOT / 'planning/__init__.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'planning/__init__.py').write_text('\n')
(ROOT / 'planning/belief_planner.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'planning/belief_planner.py').write_text('def confident_plan(parts, goals, legal, threshold=.65): return [legal[0]] if legal and parts and goals else []\n')
(ROOT / 'planning/search.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'planning/search.py').write_text('from collections import deque\ndef bfs(start,is_goal,successors,max_depth=18,deadline=lambda:False):\n    q=deque([(start,[])]); seen={repr(start)}\n    while q and not deadline():\n      s,path=q.popleft()\n      if is_goal(s): return path\n      if len(path)>=max_depth: continue\n      for a,n in successors(s):\n        k=repr(n)\n        if k not in seen: seen.add(k); q.append((n,path+[a]))\n    return []\n')
(ROOT / 'planning/simulator.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'planning/simulator.py').write_text('from axiom_core.causality.interpreter import execute\ndef simulate(grid,hypothesis,action): return execute(grid,hypothesis.rule,action)\n')
(ROOT / 'runtime.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'runtime.py').write_text('from __future__ import annotations\nimport time, random\nfrom axiom_core.config import AxiomConfig\nfrom axiom_core.types import Observation, EnvironmentStatus, Episode, Transition, as_grid, grid_hash\nfrom axiom_core.perception.scene_graph import build_scene\nfrom axiom_core.perception.tracking import track\nfrom axiom_core.perception.transitions import diff_cells\nfrom axiom_core.causality.hypotheses import prior_hypotheses\nfrom axiom_core.causality.particles import update, normalize, top\nfrom axiom_core.causality.rule_induction import induce_rules\nfrom axiom_core.types import Hypothesis\nfrom axiom_core.exploration.selector import choose\nfrom axiom_core.goals.posterior import update as update_goals\nclass Deadline:\n    def __init__(self, seconds): self.end=time.monotonic()+max(0.001,seconds)\n    def expired(self): return time.monotonic()>=self.end\n    def remaining(self): return max(0.0,self.end-time.monotonic())\nclass AxiomRuntime:\n    def __init__(self, config:AxiomConfig|None=None):\n        self.config=config or AxiomConfig(); self.rng=random.Random(self.config.seed); self.episode=Episode(); self.hypotheses=(); self.goals=(); self.tried=set(); self.last_scene=None; self.last_obs=None; self.last_action=None; self.grammar={}; self.loop_counts={}\n    def reset_episode(self): self.episode=Episode(); self.hypotheses=(); self.goals=(); self.tried=set(); self.last_scene=None; self.last_obs=None; self.last_action=None; self.loop_counts={}\n    def observe(self, obs:Observation, deadline:Deadline):\n        scene=build_scene(obs.grid); self.episode.observations.append(obs)\n        if not self.hypotheses: self.hypotheses=prior_hypotheses(obs.legal_actions,self.config.particle_count)\n        if self.last_scene is not None and self.last_action is not None and not deadline.expired():\n          mapping=track(self.last_scene,scene); trans=Transition(self.last_scene,self.last_action,scene,mapping,diff_cells(self.last_scene.grid,scene.grid),tuple(set(c.id for c in scene.components)-set(mapping.values())),tuple(set(c.id for c in self.last_scene.components)-set(mapping.keys())),obs.status); self.episode.transitions.append(trans)\n          self.hypotheses=update(self.hypotheses,self.last_scene.grid,self.last_action,scene.grid); rules=induce_rules(trans,self.config.max_hypotheses); additions=tuple(Hypothesis(r,-6.0,provenance="induced") for r in rules[:self.config.max_mutations]); self.hypotheses=normalize((self.hypotheses+additions)[:self.config.particle_count]); self.goals=update_goals(self.goals,scene,trans)\n        else: self.goals=update_goals(self.goals,scene,None)\n        self.last_scene=scene; self.last_obs=obs; return scene\n    def choose_action(self, obs:Observation, per_action_ms:int|None=None):\n        deadline=Deadline((per_action_ms or self.config.per_action_ms)/1000); legal=list(obs.legal_actions)\n        if not legal: return None\n        try:\n          scene=self.observe(obs,deadline); h=grid_hash(obs.grid); action,diag=choose(self.config,self.hypotheses,legal,h,self.tried,deadline.expired)\n          if action not in legal or deadline.expired(): action=legal[0]\n        except Exception as exc:\n          action=legal[0]; diag={"fallback":str(exc)}; h=grid_hash(obs.grid)\n        self.tried.add((h,str(action))); self.episode.actions.append(action); self.last_action=action; self.loop_counts[h]=self.loop_counts.get(h,0)+1; self.episode.timeline.append({"action":str(action),"state":h,"top_hypotheses":[{"rule":p.rule.operations[0].name,"prob":round(__import__(\'math\').exp(p.log_weight),3)} for p in top(self.hypotheses,3)],"goals":[g.name for g in self.goals[:3]],"diag":diag})\n        if len(self.episode.timeline)>self.config.max_history: self.episode.timeline=self.episode.timeline[-self.config.max_history:]\n        return action\n')
(ROOT / 'types.py').parent.mkdir(parents=True, exist_ok=True)
(ROOT / 'types.py').write_text('from __future__ import annotations\nfrom dataclasses import dataclass, field, asdict\nfrom enum import Enum\nfrom typing import Any, Protocol\nimport hashlib, json, time\nGrid = tuple[tuple[int, ...], ...]\nAction = Any\nclass EnvironmentStatus(str, Enum): ACTIVE="active"; WIN="win"; GAME_OVER="game_over"\ndef as_grid(frame: Any) -> Grid:\n    if isinstance(frame, tuple): return tuple(tuple(int(x) for x in r) for r in frame)\n    if hasattr(frame, "tolist"): frame = frame.tolist()\n    return tuple(tuple(int(x) for x in row) for row in frame)\ndef grid_shape(grid: Grid) -> tuple[int,int]: return (len(grid), len(grid[0]) if grid else 0)\ndef grid_hash(grid: Grid) -> str: return hashlib.sha256(json.dumps(grid,separators=(",",":")).encode()).hexdigest()[:16]\ndef now() -> float: return time.monotonic()\n@dataclass(frozen=True)\nclass Observation: grid: Grid; legal_actions: tuple[Action,...]; status: EnvironmentStatus=EnvironmentStatus.ACTIVE; frame_index:int=0; metadata:dict[str,Any]=field(default_factory=dict)\n@dataclass(frozen=True)\nclass Component: id:str; value:int; cells:tuple[tuple[int,int],...]; bbox:tuple[int,int,int,int]; centroid:tuple[float,float]; area:int; signature:str; border:tuple[str,...]=()\n@dataclass(frozen=True)\nclass Scene: grid:Grid; components:tuple[Component,...]; relations:tuple[tuple[str,str,str],...]; features:dict[str,Any]\n@dataclass(frozen=True)\nclass Transition: previous:Scene; action:Action; result:Scene; mapping:dict[str,str]; changed_cells:tuple[tuple[int,int],...]; created:tuple[str,...]; deleted:tuple[str,...]; terminal:EnvironmentStatus\n@dataclass(frozen=True)\nclass Operation: name:str; args:tuple[Any,...]=()\n@dataclass(frozen=True)\nclass Rule: action:Action|None; operations:tuple[Operation,...]; conditions:tuple[str,...]=(); complexity:float=1.0; evidence:int=0\n@dataclass(frozen=True)\nclass Hypothesis: rule:Rule; log_weight:float; loss:float=0.0; contradictions:int=0; provenance:str="prior"\n@dataclass(frozen=True)\nclass Goal: name:str; probability:float; target:Any=None; evidence:tuple[str,...]=()\n@dataclass\nclass Episode: observations:list[Observation]=field(default_factory=list); transitions:list[Transition]=field(default_factory=list); actions:list[Action]=field(default_factory=list); timeline:list[dict[str,Any]]=field(default_factory=list)\nclass AxiomEnvironment(Protocol):\n    def observe(self) -> Observation: ...\n    def legal_actions(self) -> list[Action]: ...\n    def execute(self, action: Action) -> Observation: ...\n    def status(self) -> EnvironmentStatus: ...\ndef to_jsonable(obj:Any)->Any:\n    if hasattr(obj,"__dataclass_fields__"): return {k:to_jsonable(v) for k,v in asdict(obj).items()}\n    if isinstance(obj, tuple): return [to_jsonable(x) for x in obj]\n    if isinstance(obj, Enum): return obj.value\n    return obj\n')
import sys
sys.path.insert(0, '/kaggle/working')

```

## 04_define_competition_agent

```python
from pathlib import Path
Path('/tmp').mkdir(parents=True, exist_ok=True)
Path('/tmp/my_agent.py').write_text('from __future__ import annotations\nimport time, random\nfrom typing import Any\ntry:\n    from arcengine import FrameData, GameAction, GameState\n    from agents.agent import Agent\nexcept ImportError:  # local tests define compatible stubs only when official framework is unavailable\n    FrameData = Any\n    class GameState:\n        WIN="WIN"; GAME_OVER="GAME_OVER"; NOT_PLAYED="NOT_PLAYED"\n    class _A:\n        RESET="RESET"; ACTION1="ACTION1"; ACTION2="ACTION2"; ACTION3="ACTION3"; ACTION4="ACTION4"; ACTION5="ACTION5"; ACTION6="ACTION6"\n    GameAction=_A\n    class Agent:\n        def __init__(self,*args:Any,**kwargs:Any): self.game_id=kwargs.get("game_id","local"); self.name="agent"\nfrom axiom_core.config import AxiomConfig\nfrom axiom_core.runtime import AxiomRuntime\nfrom axiom_core.types import Observation, EnvironmentStatus, as_grid\nclass MyAgent(Agent):\n    MAX_ACTIONS=80\n    def __init__(self,*args:Any,**kwargs:Any)->None:\n        super().__init__(*args,**kwargs); self.runtime=AxiomRuntime(AxiomConfig(seed=abs(hash(getattr(self,"game_id","local")))%1_000_000, per_action_ms=35)); self._actions=0\n    @property\n    def name(self)->str: return f"Axiom.{self.MAX_ACTIONS}"\n    def is_done(self, frames:list[FrameData], latest_frame:FrameData)->bool:\n        return getattr(latest_frame,"state",None) is getattr(GameState,"WIN",None) or str(getattr(latest_frame,"state","")).endswith("WIN")\n    def _legal_actions(self):\n        try: return [a for a in GameAction if a is not GameAction.RESET]\n        except TypeError: return [getattr(GameAction,n) for n in dir(GameAction) if n.startswith("ACTION")]\n    def _grid(self, latest_frame):\n        for name in ("grid","frame","observation","state"):\n            if hasattr(latest_frame,name):\n                val=getattr(latest_frame,name)\n                if not callable(val):\n                    try: return as_grid(val)\n                    except Exception: continue\n        return ((0,),)\n    def _obs(self, latest_frame):\n        st=getattr(latest_frame,"state",None); status=EnvironmentStatus.WIN if self.is_done([],latest_frame) else EnvironmentStatus.GAME_OVER if str(st).endswith("GAME_OVER") else EnvironmentStatus.ACTIVE\n        return Observation(self._grid(latest_frame), tuple(self._legal_actions()), status, self._actions)\n    def choose_action(self, frames:list[FrameData], latest_frame:FrameData)->GameAction:\n        st=getattr(latest_frame,"state",None)\n        if st in (getattr(GameState,"NOT_PLAYED",None), getattr(GameState,"GAME_OVER",None)) or str(st).endswith("NOT_PLAYED") or str(st).endswith("GAME_OVER"):\n            return GameAction.RESET\n        legal=self._legal_actions(); obs=self._obs(latest_frame); action=self.runtime.choose_action(obs, per_action_ms=35); action=action if action in legal else legal[0]\n        if hasattr(action,"is_complex") and action.is_complex():\n            h=len(obs.grid); w=len(obs.grid[0]) if h else 1; action.set_data({"x": min(w-1,w//2), "y": min(h-1,h//2)})\n            action.reasoning={"why":"axiom bounded coordinate probe"}\n        else:\n            try: action.reasoning="axiom symbolic legal action"\n            except Exception: action = action\n        self._actions+=1; return action\n')

```

## 05_competition_harness

```python
import os, subprocess, sys, time
from pathlib import Path
if TRUE_SUBMISSION:
    if should_stop_now():
        raise TimeoutError('Stopping before Kaggle hard timeout')
    subprocess.call(['curl','--fail','--retry','999','--retry-all-errors','--retry-delay','5','--retry-max-time','600','http://gateway:8001/api/games'])
    src=Path('/kaggle/input/competitions/arc-prize-2026-arc-agi-3/ARC-AGI-3-Agents')
    dst=Path('/kaggle/working/ARC-AGI-3-Agents')
    if not src.exists(): raise FileNotFoundError(src)
    subprocess.check_call(['cp','-r',str(src),str(dst)])
    subprocess.check_call(['cp','/tmp/my_agent.py',str(dst/'agents/templates/my_agent.py')])
    (dst/'agents/__init__.py').write_text("from typing import Type\nfrom dotenv import load_dotenv\nfrom .agent import Agent, Playback\nfrom .swarm import Swarm\nfrom .templates.random_agent import Random\nfrom .templates.my_agent import MyAgent\nload_dotenv()\nAVAILABLE_AGENTS: dict[str, Type[Agent]] = {'random': Random, 'myagent': MyAgent}\n")
    (dst/'.env').write_text('SCHEME=http\nHOST=gateway\nPORT=8001\nARC_API_KEY=test-key-123\nARC_BASE_URL=http://gateway:8001/\nOPERATION_MODE=online\nENVIRONMENTS_DIR=\nRECORDINGS_DIR=/kaggle/working/server_recording\n')
    subprocess.check_call(['python','main.py','--agent','myagent'], cwd=str(dst))
else:
    try:
        import pandas as pd
        pd.DataFrame([['1_0','1',True,1]], columns=['row_id','game_id','end_of_game','score']).to_parquet('/kaggle/working/submission.parquet', index=False)
    except Exception:
        Path('/kaggle/working/submission.parquet').write_bytes(b'row_id,game_id,end_of_game,score\n1_0,1,True,1\n')

```

## 06_local_diagnostics

```python
if not TRUE_SUBMISSION:
    import platform, statistics, time
    from axiom_core.runtime import AxiomRuntime
    from axiom_core.config import AxiomConfig
    from axiom_core.types import Observation, EnvironmentStatus
    legal=('up','down','left','right')
    rt=AxiomRuntime(AxiomConfig(per_action_ms=10, particle_count=16))
    lats=[]; illegal=0
    for i in range(5):
        obs=Observation(((0,0,0),(0,2,0),(0,0,3)), legal, EnvironmentStatus.ACTIVE, i)
        t=time.monotonic(); a=rt.choose_action(obs,10); lats.append((time.monotonic()-t)*1000); illegal += a not in legal
    print({'python':platform.python_version(),'cpu':platform.processor(),'action_budget_ms':PER_ACTION_SOFT_DEADLINE_MS,'particle_budget':PARTICLE_BUDGET,'visible_games':'not queried in diagnostics','illegal_actions':illegal,'p50_latency_ms':statistics.median(lats),'p95_latency_ms':max(lats),'submission_path':'/kaggle/working/submission.parquet'})

```
