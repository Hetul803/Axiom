from __future__ import annotations
from dataclasses import dataclass
from typing import Any
@dataclass(frozen=True)
class MechanicEvidence:
    name: str
    action: Any
    confidence: float
    rule_hint: tuple
    reason: str
def detect_mechanics(transition):
    out=[]
    moved=[]
    for old,new in transition.mapping.items():
        po=next(c for c in transition.previous.components if c.id==old); no=next(c for c in transition.result.components if c.id==new)
        dy=round(no.centroid[0]-po.centroid[0]); dx=round(no.centroid[1]-po.centroid[1])
        if (dy,dx)!=(0,0): moved.append((po,no,(dy,dx)))
    if moved: out.append(MechanicEvidence('movement_or_push', transition.action, min(0.9,0.45+0.2*len(moved)), ('move', moved[0][0].value, moved[0][2]), 'object displacement after action'))
    if transition.deleted: out.append(MechanicEvidence('collection_or_disappearance', transition.action, .65, ('collect', transition.deleted), 'object disappeared after action'))
    if transition.created: out.append(MechanicEvidence('appearance_or_teleport', transition.action, .55, ('appear', transition.created), 'object appeared after action'))
    if len(transition.changed_cells)>0 and not moved and not transition.created and not transition.deleted: out.append(MechanicEvidence('toggle_or_recolor', transition.action, .5, ('toggle',), 'cell values changed without object motion'))
    if len(moved)>=2: out.append(MechanicEvidence('push', transition.action, .7, ('push',), 'multiple objects displaced together'))
    return tuple(out)
