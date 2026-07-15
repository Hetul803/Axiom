from axiom_core.types import Observation, EnvironmentStatus
class UnknownGridEnvironment:
    def __init__(self): self.reset()
    def reset(self): self.grid=[[0,0,0,0],[0,2,0,3],[0,1,0,0],[0,0,0,0]]; self.done=False; return self.observe()
    def observe(self): return Observation(tuple(tuple(r) for r in self.grid), tuple(self.legal_actions()), EnvironmentStatus.WIN if self.done else EnvironmentStatus.ACTIVE)
    def legal_actions(self): return ['up','down','left','right','inspect']
    def execute(self, action):
      ys=[(y,x) for y,r in enumerate(self.grid) for x,v in enumerate(r) if v==2]
      if ys and action in {'up','down','left','right'}:
        y,x=ys[0]; dy,dx={'up':(-1,0),'down':(1,0),'left':(0,-1),'right':(0,1)}[action]; ny,nx=y+dy,x+dx
        if 0<=ny<4 and 0<=nx<4 and self.grid[ny][nx]!=1:
          hit=self.grid[ny][nx]; self.grid[y][x]=0; self.grid[ny][nx]=2; self.done=hit==3
      return self.observe()
    def status(self): return EnvironmentStatus.WIN if self.done else EnvironmentStatus.ACTIVE

    def snapshot(self): return {'grid':[row[:] for row in self.grid], 'done':self.done}
    def restore(self, snapshot): self.grid=[row[:] for row in snapshot['grid']]; self.done=bool(snapshot['done'])
