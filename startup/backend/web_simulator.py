from axiom_core.types import Observation, EnvironmentStatus
class WorkflowSimulator:
    def __init__(self): self.reset()
    def reset(self): self.screen='home'; self.permission=False; self.saved=False; self.done=False; return self.observe()
    def _grid(self):
      states={'home':1,'settings':2,'editor':3,'review':4}; return ((states[self.screen], int(self.permission), int(self.saved)),)
    def observe(self): return Observation(self._grid(), tuple(self.legal_actions()), EnvironmentStatus.WIN if self.done else EnvironmentStatus.ACTIVE, metadata={'screen':self.screen})
    def legal_actions(self): return ['open_settings','grant_permission','open_editor','save_draft','submit','back']
    def execute(self, action):
      if action=='open_settings': self.screen='settings'
      elif action=='grant_permission' and self.screen=='settings': self.permission=True
      elif action=='open_editor' and self.permission: self.screen='editor'
      elif action=='save_draft' and self.screen=='editor': self.saved=True
      elif action=='submit' and self.saved: self.screen='review'; self.done=True
      elif action=='back': self.screen='home'
      return self.observe()
    def status(self): return EnvironmentStatus.WIN if self.done else EnvironmentStatus.ACTIVE

    def snapshot(self): return {'screen':self.screen,'permission':self.permission,'saved':self.saved,'done':self.done}
    def restore(self, snapshot): self.screen=snapshot['screen']; self.permission=bool(snapshot['permission']); self.saved=bool(snapshot['saved']); self.done=bool(snapshot['done'])
