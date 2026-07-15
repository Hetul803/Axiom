import pytest, time
from axiom_core.goals.induction import induce
from axiom_core.goals.predicates import contains_value, removed_value
from axiom_core.perception.scene_graph import build_scene
from axiom_core.planning.search import bfs
from axiom_core.runtime import AxiomRuntime
from axiom_core.config import AxiomConfig
from axiom_core.types import Observation, EnvironmentStatus

def test_goal_induction_values(): assert induce(build_scene(((0,2),(0,3))))
def test_goal_predicates():
 s=build_scene(((0,2),)); assert contains_value(s,2); assert removed_value(s,9)
def test_bfs_plan(): assert bfs(0,lambda s:s==3,lambda s:[('inc',s+1)],5)==['inc','inc','inc']
def test_bfs_deadline(): assert bfs(0,lambda s:False,lambda s:[('inc',s+1)],100,deadline=lambda:True)==[]
@pytest.mark.parametrize('ms',[5,10,20,1,2])
def test_runtime_deadlines(ms):
 rt=AxiomRuntime(AxiomConfig(per_action_ms=ms,particle_count=8)); obs=Observation(((0,2,3),),('left','right'),EnvironmentStatus.ACTIVE); t=time.monotonic(); assert rt.choose_action(obs,ms) in obs.legal_actions; assert (time.monotonic()-t)<.2
def test_memory_consolidation():
 from axiom_core.memory.consolidation import consolidate
 rt=AxiomRuntime(AxiomConfig()); obs=Observation(((0,2,3),),('left','right'),EnvironmentStatus.ACTIVE); rt.choose_action(obs,5); assert consolidate(rt.episode)['actions']==1
def test_belief_planner_interface():
 from axiom_core.planning.belief_planner import confident_plan
 assert confident_plan((1,), (1,), ['a'])==['a']
def test_simulator_interface():
 from axiom_core.planning.simulator import simulate
 from axiom_core.causality.hypotheses import prior_hypotheses
 assert simulate(((0,),), prior_hypotheses(['a'],1)[0], 'a')==((0,),)
