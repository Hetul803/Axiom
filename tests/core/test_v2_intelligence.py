from axiom_core.state_graph import StateActionGraph
from axiom_core.types import Observation, EnvironmentStatus, Transition
from axiom_core.runtime import AxiomRuntime
from axiom_core.config import AxiomConfig
from axiom_core.perception.scene_graph import build_scene
from axiom_core.perception.transitions import diff_cells
from axiom_core.perception.tracking import track
from axiom_core.mechanics import detect_mechanics
from axiom_core.roles import infer_controllable_scores, infer_object_roles
from axiom_core.simple_planner import plan_to_adjacent

def test_state_graph_frontier_and_loop_avoidance():
    g=StateActionGraph(); s=g.observe_state(((0,),)); assert g.frontier_actions(s,['a','b'])==['a','b']; g.record(s,'a',s,0); assert g.repeated_ineffective(s,'a')

def test_runtime_systematic_frontier_exploration_no_repeat_first_cycle():
    rt=AxiomRuntime(AxiomConfig(particle_count=8)); legal=('A','B','C'); obs=Observation(((0,2,3),),legal,EnvironmentStatus.ACTIVE)
    chosen=[rt.choose_action(obs,5) for _ in range(3)]
    assert len(set(map(str, chosen))) >= 2

def test_action_semantics_update_from_displacement():
    rt=AxiomRuntime(AxiomConfig(particle_count=8)); legal=('R',)
    rt.choose_action(Observation(((0,2,0),),legal),5)
    rt.choose_action(Observation(((0,0,2),),legal),5)
    assert rt.action_semantics.best('R')[0] in {'move_right','interact'}

def test_mechanic_movement_and_roles():
    s1=build_scene(((0,2,0),)); s2=build_scene(((0,0,2),)); t=Transition(s1,'R',s2,track(s1,s2),diff_cells(s1.grid,s2.grid),(),(),EnvironmentStatus.ACTIVE)
    mechanics=detect_mechanics(t); assert any(m.name=='movement_or_push' for m in mechanics)
    scores=infer_controllable_scores(s2,[t]); roles=infer_object_roles(s2,scores); assert roles

def test_simple_planner_reaches_adjacent_target():
    plan=plan_to_adjacent(((0,0,0),(0,2,0),(0,1,3)),2,[3],legal=('up','down','left','right'))
    assert plan
