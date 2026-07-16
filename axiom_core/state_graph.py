from __future__ import annotations
from dataclasses import dataclass, field
from collections import deque
from typing import Any
from axiom_core.types import Grid, grid_hash
@dataclass
class StateNode:
    state_hash: str
    first_grid: Grid
    visits: int = 0
    terminal: str = 'active'
@dataclass
class StateActionEdge:
    source: str
    action: str
    target: str
    count: int = 1
    changed: int = 0
    reversible: bool = False
    ineffective: bool = False
@dataclass
class StateActionGraph:
    nodes: dict[str, StateNode] = field(default_factory=dict)
    edges: dict[tuple[str,str], StateActionEdge] = field(default_factory=dict)
    action_attempts: dict[tuple[str,str], int] = field(default_factory=dict)
    def observe_state(self, grid:Grid, terminal='active') -> str:
        h=grid_hash(grid); node=self.nodes.setdefault(h, StateNode(h, grid, 0, terminal)); node.visits += 1; node.terminal=terminal; return h
    def record(self, source:str, action:Any, target:str, changed:int) -> None:
        key=(source,str(action)); self.action_attempts[key]=self.action_attempts.get(key,0)+1
        edge=self.edges.get(key)
        if edge is None: edge=StateActionEdge(source,str(action),target,1,changed,False,changed==0); self.edges[key]=edge
        else: edge.target=target; edge.count+=1; edge.changed=changed; edge.ineffective=edge.ineffective and changed==0
        rev=self.edges.get((target,str(action)))
        if rev and rev.target==source: edge.reversible=True; rev.reversible=True
    def tried(self, state_hash:str, action:Any)->int: return self.action_attempts.get((state_hash,str(action)),0)
    def frontier_actions(self, state_hash:str, legal:list[Any]) -> list[Any]: return [a for a in legal if self.tried(state_hash,a)==0]
    def repeated_ineffective(self, state_hash:str, action:Any)->bool:
        edge=self.edges.get((state_hash,str(action))); return bool(edge and edge.ineffective and edge.count>=1)
    def loop_score(self, state_hash:str)->float:
        n=self.nodes.get(state_hash); return min(1.0, max(0, (n.visits-1)/5)) if n else 0.0
    def shortest_path(self, start:str, goal:str):
        q=deque([(start,[])]); seen={start}
        while q:
            s,path=q.popleft()
            if s==goal: return path
            for e in self.edges.values():
                if e.source==s and e.target not in seen:
                    seen.add(e.target); q.append((e.target,path+[e.action]))
        return []
