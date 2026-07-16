from __future__ import annotations
import importlib.util, os, sys, tempfile, types, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent
print('PACKAGING EMULATION ONLY: this is not public ARC evaluation and not hidden competition scoring.')
class GameState:
    NOT_PLAYED='NOT_PLAYED'; ACTIVE='ACTIVE'; WIN='WIN'; GAME_OVER='GAME_OVER'
class Action:
    def __init__(self, name, complex_=False): self.name=name; self._complex=complex_; self.data=None; self.reasoning=''
    def __repr__(self): return self.name
    def __str__(self): return self.name
    def is_complex(self): return self._complex
    def set_data(self, data): self.data=data
class GameAction:
    RESET=Action('RESET'); ACTION1=Action('ACTION1'); ACTION2=Action('ACTION2'); ACTIONXY=Action('ACTIONXY', True)
    @classmethod
    def __iter__(cls): return iter([cls.RESET, cls.ACTION1, cls.ACTION2, cls.ACTIONXY])
class FrameData:
    def __init__(self, state, grid=((0,0,0),(0,2,3),(0,0,0))): self.state=state; self.grid=grid
class Agent:
    def __init__(self,*args,**kwargs): self.game_id=kwargs.get('game_id','emu')

def install_mock_official(root:Path):
    (root/'agents').mkdir(); (root/'agents/__init__.py').write_text(''); (root/'agents/agent.py').write_text('class Agent:\n    def __init__(self,*args,**kwargs): self.game_id=kwargs.get(\'game_id\',\'emu\')\n')
    (root/'arcengine.py').write_text('''
class FrameData:
    def __init__(self, state, grid=((0,0,0),(0,2,3),(0,0,0))): self.state=state; self.grid=grid
class _State:
    NOT_PLAYED='NOT_PLAYED'; ACTIVE='ACTIVE'; WIN='WIN'; GAME_OVER='GAME_OVER'
GameState=_State
class _Action:
    def __init__(self, name, complex_=False): self.name=name; self._complex=complex_; self.data=None; self.reasoning=''
    def __repr__(self): return self.name
    def __str__(self): return self.name
    def is_complex(self): return self._complex
    def set_data(self, data): self.data=data
class _Actions:
    RESET=_Action('RESET'); ACTION1=_Action('ACTION1'); ACTION2=_Action('ACTION2'); ACTIONXY=_Action('ACTIONXY', True)
    def __iter__(self): return iter([self.RESET,self.ACTION1,self.ACTION2,self.ACTIONXY])
GameAction=_Actions()
''')

def main():
    with tempfile.TemporaryDirectory() as td:
        t=Path(td); install_mock_official(t); shutil.copyfile(ROOT/'my_agent.py', t/'my_agent.py'); sys.path.insert(0,str(t))
        spec=importlib.util.spec_from_file_location('my_agent', t/'my_agent.py'); mod=importlib.util.module_from_spec(spec); sys.modules['my_agent']=mod; spec.loader.exec_module(mod)
        from arcengine import FrameData, GameState, GameAction
        agent=mod.MyAgent(game_id='emulation')
        assert agent.choose_action([], FrameData(GameState.NOT_PLAYED)) is GameAction.RESET
        active=FrameData(GameState.ACTIVE)
        for ms in [1,5,20]:
            agent.runtime.config=mod.AxiomConfig(per_action_ms=ms, particle_count=8)
            a=agent.choose_action([active], active)
            assert a in list(GameAction) and a is not GameAction.RESET
        complex_action=GameAction.ACTIONXY
        agent.runtime.choose_action=lambda obs, per_action_ms=None: complex_action
        a=agent.choose_action([active], active)
        assert a is complex_action and isinstance(a.data, dict) and {'x','y'} <= set(a.data)
        assert agent.is_done([], FrameData(GameState.WIN)) is True
        assert agent.choose_action([], FrameData(GameState.GAME_OVER)) is GameAction.RESET
    class DummyDF:
        def __init__(self, data, columns): self.data=data; self.columns=columns
        def to_parquet(self, path, index=False): Path(path).parent.mkdir(parents=True, exist_ok=True); Path(path).write_bytes(b'PAR1-emulated')
    fake_pd=types.SimpleNamespace(DataFrame=DummyDF)
    sys.modules['pandas']=fake_pd
    os.environ.pop('KAGGLE_IS_COMPETITION_RERUN', None)
    exec((ROOT/'cells/04_dummy_submission.py').read_text(), {})
    out=Path('/kaggle/working/submission.parquet')
    assert out.exists() and out.read_bytes().startswith(b'PAR1')
    print('emulation passed')
if __name__=='__main__': main()
