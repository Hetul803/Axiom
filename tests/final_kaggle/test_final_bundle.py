import importlib.util, subprocess, sys, tempfile, shutil, json
from pathlib import Path
from axiom_core.perception.components import connected_components
from axiom_core.perception.transitions import diff_cells
from axiom_core.perception.scene_graph import build_scene
from axiom_core.perception.tracking import track
from axiom_core.causality.rule_induction import induce_rules
from axiom_core.types import Transition, EnvironmentStatus, Observation
from axiom_core.runtime import AxiomRuntime
from axiom_core.config import AxiomConfig
ROOT=Path(__file__).resolve().parents[2]
FINAL=ROOT/'competition/final_kaggle'

def load_agent(tmp):
    (tmp/'agents').mkdir(); (tmp/'agents/__init__.py').write_text(''); (tmp/'agents/agent.py').write_text('class Agent:\n    def __init__(self,*args,**kwargs): self.game_id=kwargs.get(\'game_id\',\'emu\')\n')
    (tmp/'arcengine.py').write_text('''
class FrameData:
    def __init__(self, state, grid=((0,0,0),(0,2,3),(0,0,0))): self.state=state; self.grid=grid
class _State:
    NOT_PLAYED='NOT_PLAYED'; ACTIVE='ACTIVE'; WIN='WIN'; GAME_OVER='GAME_OVER'
GameState=_State
class _Action:
    def __init__(self, name, complex_=False): self.name=name; self._complex=complex_; self.data=None
    def __repr__(self): return self.name
    def __str__(self): return self.name
    def is_complex(self): return self._complex
    def set_data(self, data): self.data=data
class _Actions:
    RESET=_Action('RESET'); ACTION1=_Action('ACTION1'); ACTION2=_Action('ACTION2'); ACTIONXY=_Action('ACTIONXY', True)
    def __iter__(self): return iter([self.RESET,self.ACTION1,self.ACTION2,self.ACTIONXY])
GameAction=_Actions()
''')
    shutil.copy(FINAL/'my_agent.py', tmp/'my_agent.py'); sys.path.insert(0,str(tmp)); spec=importlib.util.spec_from_file_location('bundle_agent', tmp/'my_agent.py'); mod=importlib.util.module_from_spec(spec); sys.modules['bundle_agent']=mod; spec.loader.exec_module(mod); return mod

def test_builder_and_manifest():
    subprocess.run([sys.executable,'competition/final_kaggle/build_single_file_agent.py'],cwd=ROOT,check=True)
    m=json.loads((FINAL/'agent_manifest.json').read_text()); assert m['agent_sha256'] and m['included_source_count']>=20

def test_bundle_components_diff_and_induction_match_core():
    with tempfile.TemporaryDirectory() as td:
        mod=load_agent(Path(td)); g1=((0,0,0),(0,2,0),(0,0,3)); g2=((0,0,0),(0,0,2),(0,0,3))
        assert len(mod.connected_components(g1))==len(connected_components(g1))
        assert mod.diff_cells(g1,g2)==diff_cells(g1,g2)
        s1=build_scene(g1); s2=build_scene(g2); t=Transition(s1,'a',s2,track(s1,s2),diff_cells(g1,g2),(),(),EnvironmentStatus.ACTIVE)
        assert [r.operations[0].name for r in mod.induce_rules(t)]==[r.operations[0].name for r in induce_rules(t)]

def test_bundle_and_modular_select_legal_action_and_timeout():
    with tempfile.TemporaryDirectory() as td:
        mod=load_agent(Path(td)); from arcengine import FrameData, GameState, GameAction
        agent=mod.MyAgent(game_id='x'); active=FrameData(GameState.ACTIVE); a=agent.choose_action([active], active); assert a in list(GameAction) and a is not GameAction.RESET
        rt=AxiomRuntime(AxiomConfig(per_action_ms=1,particle_count=8)); assert rt.choose_action(Observation(active.grid, tuple(list(GameAction)[1:])),1) in tuple(list(GameAction)[1:])

def test_bundle_coordinate_and_cross_level_state():
    with tempfile.TemporaryDirectory() as td:
        mod=load_agent(Path(td)); from arcengine import FrameData, GameState, GameAction
        agent=mod.MyAgent(game_id='x'); agent.runtime.choose_action=lambda obs, per_action_ms=None: GameAction.ACTIONXY
        a=agent.choose_action([FrameData(GameState.ACTIVE)], FrameData(GameState.ACTIVE)); assert a.data and {'x','y'} <= set(a.data)
        agent._last_level_hash='abc'; assert agent.choose_action([], FrameData(GameState.WIN)) in list(GameAction)
