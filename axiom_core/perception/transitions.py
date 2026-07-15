from axiom_core.types import Grid, grid_shape
def diff_cells(a:Grid,b:Grid)->tuple[tuple[int,int],...]:
    h,w=grid_shape(b); return tuple((y,x) for y in range(h) for x in range(w) if y>=len(a) or x>=len(a[y]) or a[y][x]!=b[y][x])
def changed_regions(a:Grid,b:Grid): return diff_cells(a,b)
