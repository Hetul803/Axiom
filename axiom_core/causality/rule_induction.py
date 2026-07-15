from axiom_core.types import Rule, Operation
def induce_rules(transition, limit=96):
    rules=[Rule(transition.action,(Operation("no_op"),),(),1.0,1)]
    for old,new in transition.mapping.items():
      a=next(c for c in transition.previous.components if c.id==old); b=next(c for c in transition.result.components if c.id==new); dy=round(b.centroid[0]-a.centroid[0]); dx=round(b.centroid[1]-a.centroid[1])
      if (dy,dx)!=(0,0): rules.append(Rule(transition.action,(Operation("move",(a.value,(dy,dx))),),(),2.0,1))
    vals0={c.value for c in transition.previous.components}; vals1={c.value for c in transition.result.components}
    for v in vals0-vals1: rules.append(Rule(transition.action,(Operation("collect",(v,)),),(),2.0,1))
    for v in vals1-vals0:
      c=next(c for c in transition.result.components if c.value==v); y,x=c.cells[0]; rules.append(Rule(transition.action,(Operation("appear",(v,y,x)),),(),3.0,1))
    return tuple(rules[:limit])
