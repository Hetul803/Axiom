from collections import deque
def path_exists(grid,start,goal,blocked_values=frozenset({1})):
    h=len(grid); w=len(grid[0]) if h else 0; q=deque([start]); seen={start}
    while q:
        y,x=q.popleft()
        if (y,x)==goal: return True
        for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
            ny,nx=y+dy,x+dx
            if 0<=ny<h and 0<=nx<w and (ny,nx) not in seen and grid[ny][nx] not in blocked_values:
                seen.add((ny,nx)); q.append((ny,nx))
    return False
