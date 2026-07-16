from __future__ import annotations
import argparse, json, time, statistics, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from axiom_core.runtime import AxiomRuntime
from axiom_core.config import AxiomConfig
from axiom_core.types import Observation, EnvironmentStatus
from axiom_core.diagnostics import render_html
class PermutedGrid:
    def __init__(self, mapping=None):
        self.mapping=mapping or {'A':(-1,0),'B':(1,0),'C':(0,-1),'D':(0,1)}; self.reset()
    def reset(self): self.grid=[[0,0,0,0,0],[0,2,0,3,0],[0,1,0,0,0],[0,0,0,0,0]]; self.done=False; return self.obs()
    def obs(self,i=0): return Observation(tuple(tuple(r) for r in self.grid), tuple(self.mapping), EnvironmentStatus.WIN if self.done else EnvironmentStatus.ACTIVE, i)
    def step(self,a):
        dy,dx=self.mapping[str(a)]; y,x=next((y,x) for y,r in enumerate(self.grid) for x,v in enumerate(r) if v==2); ny,nx=y+dy,x+dx
        if 0<=ny<len(self.grid) and 0<=nx<len(self.grid[0]) and self.grid[ny][nx]!=1:
            hit=self.grid[ny][nx]; self.grid[y][x]=0; self.grid[ny][nx]=2; self.done=hit==3
        return self.obs()
def run_episode(agent_kind='v2', max_steps=30):
    env=PermutedGrid(); rt=AxiomRuntime(AxiomConfig(per_action_ms=10, particle_count=32)); rt.diagnostics.enabled=True; obs=env.reset(); lats=[]; repeated=0; fallback=0
    for i in range(max_steps):
        t=time.monotonic(); a=rt.choose_action(obs,10); lats.append((time.monotonic()-t)*1000); repeated += int(rt.last_diag.get('repeated_state_action',False)); fallback += int(rt.last_diag.get('fallback_used',False)); obs=env.step(a); obs=Observation(obs.grid, obs.legal_actions, obs.status, i+1)
        if obs.status is EnvironmentStatus.WIN: break
    return {'completed':obs.status is EnvironmentStatus.WIN,'steps':len(lats),'repeated_action_rate':repeated/max(1,len(lats)),'fallback_rate':fallback/max(1,len(lats)),'mean_latency_ms':statistics.mean(lats),'p95_latency_ms':sorted(lats)[int(.95*len(lats))-1] if lats else 0,'diagnostics':rt.diagnostics.events}
def main():
    p=argparse.ArgumentParser(); p.add_argument('--out',default='competition/releases/v2/offline_results.json'); args=p.parse_args(); out=Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
    result=run_episode(); out.write_text(json.dumps(result,indent=2,default=str)); render_html(result['diagnostics'], out.with_suffix('.html')); print(json.dumps({k:v for k,v in result.items() if k!='diagnostics'},sort_keys=True))
if __name__=='__main__': main()
