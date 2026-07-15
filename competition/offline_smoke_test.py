import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from axiom_core.runtime import AxiomRuntime
from axiom_core.config import AxiomConfig
from axiom_core.types import Observation, EnvironmentStatus
rt=AxiomRuntime(AxiomConfig(per_action_ms=5, particle_count=16)); legal=('up','down','left','right')
a=rt.choose_action(Observation(((0,0,0),(0,2,3),(0,0,0)),legal,EnvironmentStatus.ACTIVE),5)
assert a in legal
open('/tmp/submission.parquet','wb').write(b'smoke')
print({'action':a,'submission':'/tmp/submission.parquet'})
