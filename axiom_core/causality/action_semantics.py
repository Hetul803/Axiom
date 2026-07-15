from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
DIRECTIONS={"up":(-1,0),"down":(1,0),"left":(0,-1),"right":(0,1),"w":(-1,0),"s":(1,0),"a":(0,-1),"d":(0,1)}
@dataclass
class ActionSemanticsPosterior:
    meanings: dict[str, dict[str,float]] = field(default_factory=dict)
    def ensure(self, actions:list[Any]|tuple[Any,...])->None:
        prior={"no_op":.18,"move_up":.14,"move_down":.14,"move_left":.14,"move_right":.14,"select":.08,"toggle":.08,"interact":.1}
        for a in actions: self.meanings.setdefault(str(a), dict(prior))
    def update_from_delta(self, action:Any, moved_delta:tuple[int,int]|None, changed:int)->None:
        self.ensure([action]); dist=self.meanings[str(action)]
        if moved_delta:
            label={(-1,0):"move_up",(1,0):"move_down",(0,-1):"move_left",(0,1):"move_right"}.get(moved_delta,"interact"); dist[label]=dist.get(label,0)+1.0
        elif changed==0: dist["no_op"]=dist.get("no_op",0)+.7
        else: dist["interact"]=dist.get("interact",0)+.6
        s=sum(dist.values()) or 1.0
        for k in list(dist): dist[k]/=s
    def best(self, action:Any)->tuple[str,float]:
        d=self.meanings.get(str(action),{}); return max(d.items(), key=lambda kv:kv[1]) if d else ("unknown",0.0)
