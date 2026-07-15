import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from axiom_core.runtime import AxiomRuntime
from axiom_core.config import AxiomConfig
from startup.backend.grid_environment import UnknownGridEnvironment
for env in [UnknownGridEnvironment()]:
 rt=AxiomRuntime(AxiomConfig(per_action_ms=10)); obs=env.observe()
 for _ in range(10):
  a=rt.choose_action(obs,10); obs=env.execute(a)
  if obs.status.value=='win': break
 print({'status':obs.status.value,'actions':rt.episode.actions})
