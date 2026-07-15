import math, pytest
from axiom_core.types import Observation, EnvironmentStatus, as_grid, grid_hash
from axiom_core.perception.components import connected_components, infer_background
from axiom_core.perception.scene_graph import build_scene
from axiom_core.perception.transitions import diff_cells
from axiom_core.perception.tracking import track
from axiom_core.causality.particles import normalize, entropy, update
from axiom_core.causality.hypotheses import prior_hypotheses
from axiom_core.exploration.reversibility import score as rev
from axiom_core.exploration.risk import score as risk
from axiom_core.exploration.novelty import score as novelty
from axiom_core.runtime import AxiomRuntime
from axiom_core.config import AxiomConfig

def grid(v=2): return ((0,0,0),(0,v,0),(0,0,3))
@pytest.mark.parametrize('conn,expected',[ (4,2),(8,2) ])
def test_components_connectivity(conn,expected): assert len(connected_components(grid(),conn,False,0))==expected
@pytest.mark.parametrize('g,bg',[ (((0,0),(1,0)),0), (((7,7),(7,1)),7), (((1,),),1) ])
def test_background(g,bg): assert infer_background(g)==bg
@pytest.mark.parametrize('a,b,n',[ (grid(),((0,0,0),(0,0,2),(0,0,3)),2), (grid(),grid(),0), (((1,),),((2,),),1) ])
def test_diff_cells(a,b,n): assert len(diff_cells(a,b))==n
@pytest.mark.parametrize('g',[grid(),((0,1),(2,3)),((0,0,4),(4,0,0))])
def test_scene_hash_and_values(g):
 s=build_scene(g); assert s.features['hash']==grid_hash(g); assert set(s.features['values'])=={x for r in g for x in r}
def test_tracking_maps_moved_object(): assert track(build_scene(grid()), build_scene(((0,0,0),(0,0,2),(0,0,3))))
def test_particle_normalization(): assert abs(sum(math.exp(p.log_weight) for p in normalize(prior_hypotheses(['a','b'],8)))-1)<1e-6
def test_entropy_nonnegative(): assert entropy(prior_hypotheses(['a','b'],8))>=0
def test_particle_update_keeps_bounded_particles():
    updated=update(prior_hypotheses(['right'],4), grid(), 'right', grid())
    assert 1 <= len(updated) <= 4
@pytest.mark.parametrize('action,legal,minimum',[('up',['up','down'],1),('fire',['fire'],.4)])
def test_reversibility(action,legal,minimum): assert rev(action,legal)>=minimum
@pytest.mark.parametrize('action,r',[('reset',.2),('left',0)])
def test_risk(action,r): assert risk(action)>=r
@pytest.mark.parametrize('tried,expected',[(set(),1.0),({('s','a')},0.0)])
def test_novelty(tried,expected): assert novelty('s','a',tried)==expected
def test_runtime_legal_under_5ms():
 rt=AxiomRuntime(AxiomConfig(per_action_ms=5,particle_count=8)); obs=Observation(grid(),('up','down','left','right'),EnvironmentStatus.ACTIVE); assert rt.choose_action(obs,5) in obs.legal_actions
def test_runtime_history_bounded():
 rt=AxiomRuntime(AxiomConfig(max_history=3,particle_count=8)); obs=Observation(grid(),('up','down'),EnvironmentStatus.ACTIVE)
 for i in range(8): rt.choose_action(obs,5)
 assert len(rt.episode.timeline)<=3
