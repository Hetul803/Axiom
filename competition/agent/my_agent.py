from __future__ import annotations
import time, random
from typing import Any
try:
    from arcengine import FrameData, GameAction, GameState
    from agents.agent import Agent
except ImportError:  # local tests define compatible stubs only when official framework is unavailable
    FrameData = Any
    class GameState:
        WIN="WIN"; GAME_OVER="GAME_OVER"; NOT_PLAYED="NOT_PLAYED"
    class _A:
        RESET="RESET"; ACTION1="ACTION1"; ACTION2="ACTION2"; ACTION3="ACTION3"; ACTION4="ACTION4"; ACTION5="ACTION5"; ACTION6="ACTION6"
    GameAction=_A
    class Agent:
        def __init__(self,*args:Any,**kwargs:Any): self.game_id=kwargs.get("game_id","local"); self.name="agent"
from axiom_core.config import AxiomConfig
from axiom_core.runtime import AxiomRuntime
from axiom_core.types import Observation, EnvironmentStatus, as_grid
class MyAgent(Agent):
    MAX_ACTIONS=80
    def __init__(self,*args:Any,**kwargs:Any)->None:
        super().__init__(*args,**kwargs); self.runtime=AxiomRuntime(AxiomConfig(seed=abs(hash(getattr(self,"game_id","local")))%1_000_000, per_action_ms=35)); self._actions=0
    @property
    def name(self)->str: return f"Axiom.{self.MAX_ACTIONS}"
    def is_done(self, frames:list[FrameData], latest_frame:FrameData)->bool:
        return getattr(latest_frame,"state",None) is getattr(GameState,"WIN",None) or str(getattr(latest_frame,"state","")).endswith("WIN")
    def _legal_actions(self):
        try: return [a for a in GameAction if a is not GameAction.RESET]
        except TypeError: return [getattr(GameAction,n) for n in dir(GameAction) if n.startswith("ACTION")]
    def _grid(self, latest_frame):
        for name in ("grid","frame","observation","state"):
            if hasattr(latest_frame,name):
                val=getattr(latest_frame,name)
                if not callable(val):
                    try: return as_grid(val)
                    except Exception: continue
        return ((0,),)
    def _obs(self, latest_frame):
        st=getattr(latest_frame,"state",None); status=EnvironmentStatus.WIN if self.is_done([],latest_frame) else EnvironmentStatus.GAME_OVER if str(st).endswith("GAME_OVER") else EnvironmentStatus.ACTIVE
        return Observation(self._grid(latest_frame), tuple(self._legal_actions()), status, self._actions)
    def choose_action(self, frames:list[FrameData], latest_frame:FrameData)->GameAction:
        st=getattr(latest_frame,"state",None)
        if st in (getattr(GameState,"NOT_PLAYED",None), getattr(GameState,"GAME_OVER",None)) or str(st).endswith("NOT_PLAYED") or str(st).endswith("GAME_OVER"):
            return GameAction.RESET
        legal=self._legal_actions(); obs=self._obs(latest_frame); action=self.runtime.choose_action(obs, per_action_ms=35); action=action if action in legal else legal[0]
        if hasattr(action,"is_complex") and action.is_complex():
            h=len(obs.grid); w=len(obs.grid[0]) if h else 1; action.set_data({"x": min(w-1,w//2), "y": min(h-1,h//2)})
            action.reasoning={"why":"axiom bounded coordinate probe"}
        else:
            try: action.reasoning="axiom symbolic legal action"
            except Exception: action = action
        self._actions+=1; return action
