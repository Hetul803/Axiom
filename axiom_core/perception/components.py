from collections import Counter, deque
from axiom_core.types import Component, Grid, grid_shape
import hashlib
def infer_background(grid:Grid)->int: return Counter(x for r in grid for x in r).most_common(1)[0][0] if grid else 0
def signature(cells):
    ys=[y for y,_ in cells]; xs=[x for _,x in cells]; my,mx=min(ys),min(xs); return hashlib.sha1(repr(tuple(sorted((y-my,x-mx) for y,x in cells))).encode()).hexdigest()[:12]
def connected_components(grid:Grid, connectivity:int=4, include_background:bool=False, background:int|None=None)->tuple[Component,...]:
    h,w=grid_shape(grid); bg=infer_background(grid) if background is None else background; seen=set(); nbr4=((1,0),(-1,0),(0,1),(0,-1)); nbr8=nbr4+((1,1),(1,-1),(-1,1),(-1,-1)); nbrs=nbr8 if connectivity==8 else nbr4; comps=[]; idx=0
    for y in range(h):
      for x in range(w):
        if (y,x) in seen or (not include_background and grid[y][x]==bg): continue
        val=grid[y][x]; q=deque([(y,x)]); seen.add((y,x)); cells=[]
        while q:
          cy,cx=q.popleft(); cells.append((cy,cx))
          for dy,dx in nbrs:
            ny,nx=cy+dy,cx+dx
            if 0<=ny<h and 0<=nx<w and (ny,nx) not in seen and grid[ny][nx]==val:
              seen.add((ny,nx)); q.append((ny,nx))
        ys=[c[0] for c in cells]; xs=[c[1] for c in cells]; bbox=(min(ys),min(xs),max(ys)+1,max(xs)+1); border=tuple(n for n,b in (("top",bbox[0]==0),("left",bbox[1]==0),("bottom",bbox[2]==h),("right",bbox[3]==w)) if b); sig=signature(cells); comps.append(Component(f"v{val}_{idx}_{sig}",val,tuple(sorted(cells)),bbox,(sum(ys)/len(cells),sum(xs)/len(cells)),len(cells),sig,border)); idx+=1
    return tuple(comps)
