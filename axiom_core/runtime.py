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
