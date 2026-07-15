from collections import deque
import heapq
def bfs(start,is_goal,successors,max_depth=18,deadline=lambda:False):
    q=deque([(start,[])]); seen={repr(start)}
    while q and not deadline():
      s,path=q.popleft()
      if is_goal(s): return path
      if len(path)>=max_depth: continue
      for a,n in successors(s):
        k=repr(n)
        if k not in seen: seen.add(k); q.append((n,path+[a]))
    return []
def astar(start,is_goal,successors,heuristic,max_depth=32,deadline=lambda:False):
    heap=[(heuristic(start),0,repr(start),start,[])]; best={repr(start):0}
    while heap and not deadline():
      _,cost,_,state,path=heapq.heappop(heap)
      if is_goal(state): return path
      if len(path)>=max_depth: continue
      for action,nxt in successors(state):
        nc=cost+1; k=repr(nxt)
        if nc<best.get(k,10**9): best[k]=nc; heapq.heappush(heap,(nc+heuristic(nxt),nc,k,nxt,path+[action]))
    return []
def iterative_deepening(start,is_goal,successors,max_depth=32,deadline=lambda:False):
    for d in range(max_depth+1):
        plan=bfs(start,is_goal,successors,d,deadline)
        if plan or deadline(): return plan
    return []
