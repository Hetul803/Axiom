from axiom_core.types import Grid, Scene, grid_hash, grid_shape
from axiom_core.perception.components import connected_components, infer_background
def build_scene(grid:Grid)->Scene:
    comps=connected_components(grid); rel=[]
    for i,a in enumerate(comps):
      for b in comps[i+1:]:
        if a.value==b.value: rel.append((a.id,"same_value",b.id))
        if a.signature==b.signature: rel.append((a.id,"same_shape",b.id))
        if any(abs(y1-y2)+abs(x1-x2)==1 for y1,x1 in a.cells for y2,x2 in b.cells): rel.append((a.id,"touching",b.id))
    return Scene(grid, comps, tuple(rel), {"hash":grid_hash(grid),"shape":grid_shape(grid),"background":infer_background(grid),"values":tuple(sorted({x for r in grid for x in r}))})
