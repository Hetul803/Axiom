def role_candidates(scene, previous=None):
    roles={}
    values=scene.features.get('values',())
    for c in scene.components:
        r={"controllable":0.18,"obstacle":0.16,"target":0.16,"collectible":0.16,"hazard":0.08,"portal":0.08,"key":0.08,"door":0.08,"counter":0.02}
        if c.area==1: r["controllable"]+=.12; r["collectible"]+=.08
        if c.border: r["obstacle"]+=.08
        if len(values)>4: r["counter"]+=.04
        s=sum(r.values()); roles[c.id]={k:v/s for k,v in r.items()}
    return roles
