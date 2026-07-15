from axiom_core.types import Grid, Rule
MOVE={"up":(-1,0),"down":(1,0),"left":(0,-1),"right":(0,1),"w":(-1,0),"s":(1,0),"a":(0,-1),"d":(0,1)}
def _set(grid,y,x,v): r=[list(row) for row in grid]; r[y][x]=v; return tuple(tuple(row) for row in r)
def execute(grid:Grid, rule:Rule, action)->Grid:
    if rule.action is not None and str(rule.action)!=str(action): return grid
    g=[list(r) for r in grid]; bg=max({v:sum(row.count(v) for row in g) for v in {x for r in g for x in r}}.items(), key=lambda kv:kv[1])[0]
    for op in rule.operations:
      if op.name=="no_op": continue
      if op.name in ("move","push"):
        val,delta=op.args[0], op.args[1] if len(op.args)>1 else MOVE.get(str(action),(0,0)); cells=[(y,x) for y,row in enumerate(g) for x,v in enumerate(row) if v==val]; dest=[(y+delta[0],x+delta[1]) for y,x in cells]
        if cells and all(0<=y<len(g) and 0<=x<len(g[0]) and (g[y][x] in (bg,val)) for y,x in dest):
          for y,x in cells: g[y][x]=bg
          for y,x in dest: g[y][x]=val
      elif op.name in ("collect","disappear"):
        val=op.args[0]; g=[[bg if v==val else v for v in row] for row in g]
      elif op.name in ("toggle","recolor"):
        a,b=op.args[:2]; g=[[b if v==a else v for v in row] for row in g]
      elif op.name=="appear":
        val,y,x=op.args[:3]
        if 0<=y<len(g) and 0<=x<len(g[0]): g[y][x]=val
      elif op.name=="teleport":
        val,y,x=op.args[:3]; g=[[bg if v==val else v for v in row] for row in g]
        if 0<=y<len(g) and 0<=x<len(g[0]): g[y][x]=val
    return tuple(tuple(r) for r in g)
