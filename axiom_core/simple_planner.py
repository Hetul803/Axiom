from __future__ import annotations
from collections import deque
def find_value(grid, value):
    for y,row in enumerate(grid):
        for x,v in enumerate(row):
            if v==value: return (y,x)
    return None
def plan_to_adjacent(grid, start_value, target_values, legal=('up','down','left','right'), walls=frozenset({1}), max_depth=40):
    start=find_value(grid,start_value)
    targets={pos for tv in target_values for pos in [find_value(grid,tv)] if pos is not None}
    if start is None or not targets: return []
    h=len(grid); w=len(grid[0]) if h else 0; moves={'up':(-1,0),'down':(1,0),'left':(0,-1),'right':(0,1)}; q=deque([(start,[])]); seen={start}
    while q:
        (y,x),path=q.popleft()
        if any(abs(y-ty)+abs(x-tx)<=1 for ty,tx in targets): return path
        if len(path)>=max_depth: continue
        for a,(dy,dx) in moves.items():
            if a not in legal: continue
            ny,nx=y+dy,x+dx
            if 0<=ny<h and 0<=nx<w and (ny,nx) not in seen and grid[ny][nx] not in walls:
                seen.add((ny,nx)); q.append(((ny,nx),path+[a]))
    return []
