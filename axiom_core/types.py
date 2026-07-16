from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Protocol
import hashlib, json, time
Grid = tuple[tuple[int, ...], ...]
Action = Any
class EnvironmentStatus(str, Enum): ACTIVE="active"; WIN="win"; GAME_OVER="game_over"
def as_grid(frame: Any) -> Grid:
    if isinstance(frame, tuple): return tuple(tuple(int(x) for x in r) for r in frame)
    if hasattr(frame, "tolist"): frame = frame.tolist()
    return tuple(tuple(int(x) for x in row) for row in frame)
def grid_shape(grid: Grid) -> tuple[int,int]: return (len(grid), len(grid[0]) if grid else 0)
def grid_hash(grid: Grid) -> str: return hashlib.sha256(json.dumps(grid,separators=(",",":")).encode()).hexdigest()[:16]
def now() -> float: return time.monotonic()
@dataclass(frozen=True)
class Observation: grid: Grid; legal_actions: tuple[Action,...]; status: EnvironmentStatus=EnvironmentStatus.ACTIVE; frame_index:int=0; metadata:dict[str,Any]=field(default_factory=dict)
@dataclass(frozen=True)
class Component: id:str; value:int; cells:tuple[tuple[int,int],...]; bbox:tuple[int,int,int,int]; centroid:tuple[float,float]; area:int; signature:str; border:tuple[str,...]=()
@dataclass(frozen=True)
class Scene: grid:Grid; components:tuple[Component,...]; relations:tuple[tuple[str,str,str],...]; features:dict[str,Any]
@dataclass(frozen=True)
class Transition: previous:Scene; action:Action; result:Scene; mapping:dict[str,str]; changed_cells:tuple[tuple[int,int],...]; created:tuple[str,...]; deleted:tuple[str,...]; terminal:EnvironmentStatus
@dataclass(frozen=True)
class Operation: name:str; args:tuple[Any,...]=()
@dataclass(frozen=True)
class Rule: action:Action|None; operations:tuple[Operation,...]; conditions:tuple[str,...]=(); complexity:float=1.0; evidence:int=0
@dataclass(frozen=True)
class Hypothesis: rule:Rule; log_weight:float; loss:float=0.0; contradictions:int=0; provenance:str="prior"
@dataclass(frozen=True)
class Goal: name:str; probability:float; target:Any=None; evidence:tuple[str,...]=()
@dataclass
class Episode: observations:list[Observation]=field(default_factory=list); transitions:list[Transition]=field(default_factory=list); actions:list[Action]=field(default_factory=list); timeline:list[dict[str,Any]]=field(default_factory=list)
class AxiomEnvironment(Protocol):
    def observe(self) -> Observation: ...
    def legal_actions(self) -> list[Action]: ...
    def execute(self, action: Action) -> Observation: ...
    def status(self) -> EnvironmentStatus: ...
def to_jsonable(obj:Any)->Any:
    if hasattr(obj,"__dataclass_fields__"): return {k:to_jsonable(v) for k,v in asdict(obj).items()}
    if isinstance(obj, tuple): return [to_jsonable(x) for x in obj]
    if isinstance(obj, Enum): return obj.value
    return obj
