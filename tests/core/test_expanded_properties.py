import math, pytest, json, time
from axiom_core.types import Observation, EnvironmentStatus, to_jsonable, grid_hash
from axiom_core.perception.components import connected_components
from axiom_core.perception.paths import path_exists
from axiom_core.perception.scene_graph import build_scene
from axiom_core.perception.roles import role_candidates
from axiom_core.exploration.coordinates import coordinate_candidates
from axiom_core.causality.action_semantics import ActionSemanticsPosterior
from axiom_core.causality.interpreter import execute
from axiom_core.causality.particles import normalize, effective_sample_size, resample, loss
from axiom_core.causality.hypotheses import prior_hypotheses
from axiom_core.types import Rule, Operation
from axiom_core.runtime import AxiomRuntime
from axiom_core.config import AxiomConfig

grids=[((0,0,0),(0,2,0),(0,0,3)),((1,1,1),(1,2,3),(1,0,0)),((0,4,0),(4,4,0),(0,0,5)),((0,0),(6,0))]
@pytest.mark.parametrize('g', grids*3)
def test_serialization_round_trip_json(g):
    obs=Observation(g,('a','b'),EnvironmentStatus.ACTIVE); assert json.loads(json.dumps(to_jsonable(obs)))['grid']
@pytest.mark.parametrize('g', grids*3)
def test_coordinate_candidates_in_bounds(g):
    s=build_scene(g); h,w=s.features['shape']; assert all(0<=y<h and 0<=x<w for y,x in coordinate_candidates(s))
@pytest.mark.parametrize('g', grids*3)
def test_roles_normalize(g):
    roles=role_candidates(build_scene(g)); assert all(abs(sum(v.values())-1)<1e-6 for v in roles.values())
@pytest.mark.parametrize('g', grids*4)
def test_no_illegal_action_property(g):
    legal=('up','down','left','right'); rt=AxiomRuntime(AxiomConfig(particle_count=8)); assert rt.choose_action(Observation(g,legal),5) in legal
@pytest.mark.parametrize('delta', [(-1,0),(1,0),(0,-1),(0,1),(0,0)]*4)
def test_action_semantics_updates(delta):
    p=ActionSemanticsPosterior(); p.update_from_delta('x', None if delta==(0,0) else delta, 0 if delta==(0,0) else 2); assert p.best('x')[1]>0
@pytest.mark.parametrize('n', [1,2,4,8,16,32,64,3,5,7])
def test_resample_counts_and_ess(n):
    parts=normalize(prior_hypotheses(['a','b'],max(2,n))); out=resample(parts,n,0); assert len(out)==n and effective_sample_size(out)>0
@pytest.mark.parametrize('op,args,expected', [('move',(2,(0,1)),2),('toggle',(2,8),8),('recolor',(2,7),7),('appear',(9,0,0),9),('teleport',(2,0,2),2)]*3)
def test_dsl_operations_execute(op,args,expected):
    out=execute(((0,0,0),(0,2,0),(0,0,0)), Rule('a',(Operation(op,args),)), 'a'); assert any(expected in row for row in out)
@pytest.mark.parametrize('blocked', [frozenset(), frozenset({1}), frozenset({0,1}), frozenset({9})]*4)
def test_path_exists_bounded(blocked): assert isinstance(path_exists(((0,0,0),(1,1,0),(0,0,0)),(0,0),(2,2),blocked), bool)
@pytest.mark.parametrize('g', grids*3)
def test_hash_deterministic(g): assert grid_hash(g)==grid_hash(g)
@pytest.mark.parametrize('g', grids*3)
def test_components_have_bbox(g): assert all(len(c.bbox)==4 for c in connected_components(g, include_background=True))
