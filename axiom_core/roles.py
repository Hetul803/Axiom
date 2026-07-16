from __future__ import annotations
def infer_controllable_scores(scene, transitions, action_semantics=None):
    scores={c.id:0.05 for c in scene.components}
    for t in transitions[-12:]:
        for old,new in t.mapping.items():
            po=next((c for c in t.previous.components if c.id==old),None); no=next((c for c in t.result.components if c.id==new),None)
            if po and no and po.centroid!=no.centroid:
                scores[no.id]=scores.get(no.id,0)+1.0
                if po.value==no.value: scores[no.id]+=0.25
    total=sum(scores.values()) or 1
    return {k:v/total for k,v in sorted(scores.items(), key=lambda kv:kv[1], reverse=True)}
def infer_object_roles(scene, controllable_scores=None):
    controllable_scores=controllable_scores or {}
    roles={}
    for c in scene.components:
        r={'player':controllable_scores.get(c.id,0.05),'movable':0.15,'wall':0.12,'target':0.12,'collectible':0.12,'hazard':0.05,'key':0.07,'door':0.07,'switch':0.07,'portal':0.06,'counter':0.02,'pattern':0.1}
        if c.area==1: r['player']+=0.08; r['collectible']+=0.05
        if c.border: r['wall']+=0.1
        s=sum(r.values()); roles[c.id]={k:v/s for k,v in r.items()}
    return roles
