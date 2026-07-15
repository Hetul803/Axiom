from axiom_core.runtime import AxiomRuntime
from axiom_core.config import AxiomConfig
from startup.backend.environment_registry import create_environment
from startup.backend.approvals import APPROVALS
class SessionManager:
    def __init__(self): self.sessions={}
    def create(self, kind='grid'):
      sid=f's{len(self.sessions)+1}'; env=create_environment(kind); self.sessions[sid]={'env':env,'runtime':AxiomRuntime(AxiomConfig(per_action_ms=20)),'timeline':[]}; return sid
    def step(self,sid,action=None,autonomous=False):
      s=self.sessions[sid]; env=s['env']; obs=env.observe(); act=action or s['runtime'].choose_action(obs,20)
      if not APPROVALS.allowed(sid, act):
        nxt=obs; s['timeline'].append({'action':act,'blocked':True,'status':nxt.status.value}); return {'session_id':sid,'action':act,'blocked':True,'observation':nxt.grid,'legal_actions':nxt.legal_actions,'status':nxt.status.value,'timeline':s['timeline'],'world_model':s['runtime'].episode.timeline[-5:]}
      nxt=env.execute(act); s['timeline'].append({'action':act,'observation':nxt.metadata,'status':nxt.status.value}); return {'session_id':sid,'action':act,'observation':nxt.grid,'legal_actions':nxt.legal_actions,'status':nxt.status.value,'timeline':s['timeline'],'world_model':s['runtime'].episode.timeline[-5:]}
    def snapshot(self,sid): return self.sessions[sid]['env'].snapshot()
    def restore(self,sid,snapshot): self.sessions[sid]['env'].restore(snapshot); return self.sessions[sid]['env'].observe()
MANAGER=SessionManager()
