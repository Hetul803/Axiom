import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import time, statistics, json
from axiom_core.runtime import AxiomRuntime
from axiom_core.config import AxiomConfig
from axiom_core.types import Observation, EnvironmentStatus
rt=AxiomRuntime(AxiomConfig(per_action_ms=5, particle_count=16)); l=[]; legal=('up','down','left','right')
for i in range(30):
 t=time.monotonic(); assert rt.choose_action(Observation(((0,0,0),(0,2,3),(0,0,0)),legal,EnvironmentStatus.ACTIVE,i),5) in legal; l.append((time.monotonic()-t)*1000)
print(json.dumps({'actions':len(l),'p50_ms':statistics.median(l),'p95_ms':sorted(l)[int(.95*len(l))-1],'max_ms':max(l)},sort_keys=True))
