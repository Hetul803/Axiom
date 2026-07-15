import pytest
from axiom_core.types import Rule, Operation, Transition, EnvironmentStatus
from axiom_core.perception.scene_graph import build_scene
from axiom_core.causality.interpreter import execute
from axiom_core.causality.rule_induction import induce_rules

def test_move(): assert execute(((0,0,0),(0,2,0),(0,0,0)), Rule('r',(Operation('move',(2,(0,1))),)), 'r')[1][2]==2
def test_collision_blocks(): assert execute(((0,0,0),(0,2,1),(0,0,0)), Rule('r',(Operation('move',(2,(0,1))),)), 'r')[1][1]==2
def test_collect(): assert 3 not in {x for r in execute(((0,3),(2,0)),Rule('a',(Operation('collect',(3,)),)),'a') for x in r}
def test_toggle(): assert execute(((1,0),),Rule('a',(Operation('toggle',(1,5)),)),'a')[0][0]==5
def test_recolor(): assert execute(((1,0),),Rule('a',(Operation('recolor',(1,6)),)),'a')[0][0]==6
def test_appear(): assert execute(((0,0),),Rule('a',(Operation('appear',(9,0,1)),)),'a')[0][1]==9
def test_teleport(): assert execute(((2,0,0),),Rule('a',(Operation('teleport',(2,0,2)),)),'a')[0][2]==2
def test_hidden_action_binding(): assert execute(((0,2,0),),Rule('secret',(Operation('move',(2,(0,1))),)),'other')==((0,2,0),)
def test_induce_movement():
 t=Transition(build_scene(((0,2,0),)), 'a', build_scene(((0,0,2),)), {}, ((0,1),(0,2)), (), (), EnvironmentStatus.ACTIVE); assert any(r.operations[0].name in {'no_op','move'} for r in induce_rules(t))
def test_induce_collection():
 t=Transition(build_scene(((0,3),)), 'a', build_scene(((0,0),)), {}, ((0,1),), (), (), EnvironmentStatus.ACTIVE); assert any(r.operations[0].name=='collect' for r in induce_rules(t))
def test_candidate_key_door_vocab(): from axiom_core.causality.dsl import OPERATIONS; assert 'open' in OPERATIONS and 'sequence_activate' in OPERATIONS
