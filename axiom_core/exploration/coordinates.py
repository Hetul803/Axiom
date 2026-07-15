def coordinate_candidates(scene, limit=64):
    h,w=scene.features.get('shape',(0,0)); pts={(0,0),(max(0,h-1),0),(0,max(0,w-1)),(max(0,h-1),max(0,w-1)),(h//2 if h else 0,w//2 if w else 0)}
    for c in scene.components:
        cy,cx=c.centroid; pts.add((round(cy),round(cx)))
        y0,x0,y1,x1=c.bbox
        for p in ((y0,x0),(y0,x1-1),(y1-1,x0),(y1-1,x1-1)): pts.add(p)
        for y,x in c.cells[:4]: pts.add((y,x))
    return tuple((y,x) for y,x in sorted(pts) if 0<=y<h and 0<=x<w)[:limit]
