def track(prev, nxt):
    out={}; used=set()
    for a in prev.components:
      best=None; score=10**9
      aset=set(a.cells)
      for b in nxt.components:
        if b.id in used: continue
        overlap=len(aset & set(b.cells)); dist=abs(a.centroid[0]-b.centroid[0])+abs(a.centroid[1]-b.centroid[1]); s=(a.value!=b.value)*4+(a.signature!=b.signature)*2+dist-overlap
        if s<score: score=s; best=b
      if best and score<7: out[a.id]=best.id; used.add(best.id)
    return out
