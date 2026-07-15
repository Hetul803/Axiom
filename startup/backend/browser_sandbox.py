from __future__ import annotations
import random
from axiom_core.types import Observation, EnvironmentStatus
from axiom_core.startup_safety import classify_action
class BrowserSandbox:
    def __init__(self, seed=0): self.rng=random.Random(seed); self.reset()
    def reset(self):
        self.page=0; self.permission=False; self.counter=0; self.theme=self.rng.choice(['blue','green','mono']); self.mapping={'primary':'next','secondary':'grant','danger':'delete','finish':'submit'}; self.done=False; self.deleted=False; return self.observe()
    def _grid(self): return ((self.page,int(self.permission),self.counter,int(self.deleted)),)
    def observe(self): return Observation(self._grid(), tuple(self.legal_actions()), EnvironmentStatus.WIN if self.done else EnvironmentStatus.GAME_OVER if self.deleted else EnvironmentStatus.ACTIVE, metadata={'theme':self.theme,'page':self.page})
    def legal_actions(self): return ['primary','secondary','finish','back','danger']
    def execute(self, action):
        real=self.mapping.get(action, action)
        if classify_action(real).requires_approval: return self.observe()
        if real=='grant': self.permission=True
        elif real=='next' and self.permission: self.page=min(2,self.page+1); self.counter+=1
        elif real=='submit' and self.page>=2: self.done=True
        elif real=='back': self.page=max(0,self.page-1)
        elif real=='delete': self.deleted=True
        return self.observe()
    def status(self): return self.observe().status
    def snapshot(self): return {'page':self.page,'permission':self.permission,'counter':self.counter,'theme':self.theme,'mapping':dict(self.mapping),'done':self.done,'deleted':self.deleted}
    def restore(self,snapshot):
        self.page=snapshot['page']; self.permission=snapshot['permission']; self.counter=snapshot['counter']; self.theme=snapshot['theme']; self.mapping=dict(snapshot['mapping']); self.done=snapshot['done']; self.deleted=snapshot['deleted']
