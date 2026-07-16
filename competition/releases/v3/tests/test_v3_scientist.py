from __future__ import annotations
import hashlib, importlib.util, json, sys, time
from pathlib import Path
import pytest

ROOT=Path(__file__).parents[1]
spec=importlib.util.spec_from_file_location('v3core', ROOT/'source/axiom_scientist.py')
core=importlib.util.module_from_spec(spec); sys.modules[spec.name]=core; spec.loader.exec_module(core)
# fallback is deliberately loaded into the core namespace as the final bundle does.
exec((ROOT/'source/frozen_v2.py').read_text(), core.__dict__)

MODEL='''
class GeneratedWorldModel:
    name="right mover"; explanation="transition-independent test model"
    def parse_state(self, observation):
        row=[]
        for value, count in observation["grid_rle"][0]: row += [value] * count
        return {"grid": observation["grid_rle"], "x": row[1]}
    def predict(self, state, action):
        result=dict(state)
        if action.get("name")=="right": result["x"] += 1
        return result
    def reconstruct_grid(self, state): return [[9,state["x"]]]
    def candidate_goals(self, state): return [{"goal_name":"reach","confidence":1.0}]
    def goal_score(self, previous_state, state): return state["x"]-previous_state["x"]
    def is_goal(self, state): return state["x"] >= 2
    def state_key(self, state): return str(state["x"])
    def legal_model_actions(self, state, real_legal_actions): return real_legal_actions
'''

def obs(i, x):
    return core.StructuredObservation(i, ((9,x),), [{"name":"right"}], core.components(((0,x),)))

def test_v2_hashes_are_frozen():
    manifest=json.loads((ROOT/'V2_FROZEN_HASHES.json').read_text())
    v2=ROOT.parent/'v2'
    actual={str(p.relative_to(v2)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(v2.rglob('*')) if p.is_file()}
    assert actual==manifest['files']

def test_components_and_rle_are_exact():
    grid=((0,1,1),(2,0,1)); assert len(core.components(grid))==3
    assert core.encode_grid(grid)[0]==[[0,1],[1,2]]

def test_correspondence_tracks_translation():
    assert core.correspond(core.components(((0,1,0),)),core.components(((0,0,1),)))

def test_ontology_error_detects_unexplained_cells():
    a,b=obs(0,0),obs(1,1); b.changed=[[0,1,0,1]]
    assert core.ontology_error(core.Ontology('x'),a,b)>0

@pytest.mark.parametrize('snippet', ['import os','import socket','open("x")','eval("1")','exec("x")','__import__("os")'])
def test_ast_rejects_forbidden_capabilities(snippet):
    assert not core.validate_model_code(MODEL+'\n'+snippet)[0]

def test_ast_accepts_contract(): assert core.validate_model_code(MODEL)[0]
def test_ast_rejects_missing_contract(): assert not core.validate_model_code('class GeneratedWorldModel: pass')[0]
def test_sandbox_executes_model(): assert core.sandbox_call(MODEL,'is_goal',[{'x':2}])=={'ok':True,'value':True}
def test_sandbox_times_out():
    code=MODEL.replace('def is_goal(self, state): return state["x"] >= 2','def is_goal(self, state):\n        while True: state["x"] += 1')
    assert core.sandbox_call(code,'is_goal',[{'x':0}],.01)['error']=='timeout'
def test_replay_verification_exact():
    candidate=core.WorldModelCandidate('m',MODEL,core.Ontology('o'))
    core.verify_replay(candidate,[(obs(0,0),{'name':'right'},obs(1,1))])
    assert candidate.replay_accuracy==1 and candidate.counterexample is None

def test_replay_counterexample_is_minimal():
    candidate=core.WorldModelCandidate('m',MODEL,core.Ontology('o'))
    core.verify_replay(candidate,[(obs(0,0),{'name':'right'},obs(1,0))])
    assert candidate.counterexample and candidate.counterexample.transition_id==1

def test_model_posteriors_normalize():
    models=[core.WorldModelCandidate(str(i),MODEL,core.Ontology('o'),replay_accuracy=i/2) for i in range(3)]
    core.normalize_models(models); assert sum(m.posterior for m in models)==pytest.approx(1)
    assert models[2].posterior>models[0].posterior

def test_disagreement_is_positive(): assert core.model_disagreement([(0.5,'a'),(0.5,'b')])>0.6
def test_disagreement_zero_on_agreement(): assert core.model_disagreement([(0.5,'a'),(0.5,'a')])==pytest.approx(0,abs=1e-9)
def test_controller_maintains_multiple_models():
    c=core.AxiomScientistController(); assert c.add_model('a',MODEL); assert c.add_model('b',MODEL.replace('right mover','other'))
    assert len(c.models)==2

def test_controller_interrupts_plan_on_mismatch():
    c=core.AxiomScientistController(); first=c.observe(((0,0),),[{'name':'right'}]); c.expected_next_key='impossible'; c.last_action={'name':'right'}; c.plan.append(core.PlanStep({'name':'right'},'x'))
    c.observe(((0,1),),[{'name':'right'}]); assert not c.plan and c.mismatches==1

def test_search_finds_verified_plan():
    plan=core.search_model_plan(core.WorldModelCandidate('m',MODEL,core.Ontology('o'),replay_accuracy=1),obs(0,0),max_depth=3)
    assert [p.action for p in plan]==[{'name':'right'},{'name':'right'}]

def test_v2_fallback_avoids_repeat():
    f=core.V2Fallback(); legal=[{'name':'a'},{'name':'b'}]
    assert f.choose('s',legal)!=f.choose('s',legal)

class FailingLLM:
    calls=0
    def complete(self,*args,**kwargs): self.calls+=1; return None

def test_llm_failure_uses_deterministic_fallback():
    c=core.AxiomScientistController(FailingLLM()); o=c.observe(((0,0),),[{'name':'a'}])
    assert c.choose(o,time.monotonic()+.1)=={'name':'a'}

def test_global_deadline_still_returns_legal():
    c=core.AxiomScientistController(); o=c.observe(((0,0),),[{'name':'a'},{'name':'b'}])
    assert c.choose(o,time.monotonic()-1) in o.legal_actions

def test_generated_agent_compiles(): compile((ROOT/'my_agent.py').read_text(),'my_agent.py','exec')
def test_notebook_offline_metadata():
    notebook=json.loads((ROOT/'axiom_v3_submission.ipynb').read_text()); assert notebook['metadata']['kaggle']['isInternetEnabled'] is False
    source=''.join(''.join(c.get('source',[])) for c in notebook['cells']); assert 'huggingface.co' not in source and 'pip install --no-index' in source

class MockLLM:
    def __init__(self, response): self.response=response; self.calls=0; self.tokens=0
    def complete(self,*args,**kwargs): self.calls+=1; return self.response

def test_mock_scientist_generates_and_repairs_model():
    llm=MockLLM('```python\n'+MODEL+'\n```')
    c=core.AxiomScientistController(llm); observation=c.observe(((9,0),),[{'name':'right'}])
    assert c.consult_scientist(observation,time.monotonic()+1)
    assert len(c.models)==1 and c.models[0].replay_accuracy==0
    c.models[0].counterexample=core.Counterexample(1,{'name':'right'},[[9,2]],[[9,1]],[[0,1,2,1]])
    assert c.consult_scientist(observation,time.monotonic()+1,repair=True)

def test_optional_real_local_model_smoke():
    client=core.LocalVLLMClient(timeout=2,max_calls=1,max_tokens=32)
    if not client.health(): pytest.skip('local V3 model server is not available')
    result=client.complete([{'role':'user','content':'Reply exactly TEST_OK'}],16,0,time.monotonic()+5)
    assert result and 'TEST_OK' in result
