import math, random
from axiom_core.types import Hypothesis
from axiom_core.causality.interpreter import execute
def loss(a,b): return 1.0 if len(a)!=len(b) or (a and len(a[0])!=len(b[0])) else sum(a[y][x]!=b[y][x] for y in range(len(a)) for x in range(len(a[0])))/max(1,len(a)*len(a[0]))
def normalize(parts):
    if not parts: return ()
    m=max(p.log_weight for p in parts); vals=[math.exp(p.log_weight-m) for p in parts]; s=sum(vals) or 1.0
    return tuple(Hypothesis(p.rule, math.log(v/s), p.loss, p.contradictions, p.provenance) for p,v in zip(parts,vals))
def entropy(parts):
    ps=[math.exp(p.log_weight) for p in normalize(parts)]; return -sum(p*math.log(p+1e-12) for p in ps)
def effective_sample_size(parts):
    ps=[math.exp(p.log_weight) for p in normalize(parts)]; return 1.0/sum(p*p for p in ps) if ps else 0.0
def deduplicate(parts):
    seen={};
    for p in parts:
        k=repr((p.rule.action,p.rule.operations,p.rule.conditions))
        if k not in seen or p.log_weight>seen[k].log_weight: seen[k]=p
    return tuple(seen.values())
def update(parts, prev_grid, action, next_grid):
    out=[]
    for p in parts:
      pred=execute(prev_grid,p.rule,action); l=loss(pred,next_grid); unexplained=0.15 if l>.25 and p.rule.operations[0].name=='no_op' else 0.0; out.append(Hypothesis(p.rule,p.log_weight-8*l-unexplained-.05*p.rule.complexity,l,p.contradictions+(l>.5),p.provenance))
    return normalize(deduplicate(tuple(out)))
def resample(parts, target, seed=0):
    parts=normalize(parts); ps=[math.exp(p.log_weight) for p in parts]; rng=random.Random(seed); out=[]
    for _ in range(target):
        r=rng.random(); acc=0
        for p,prob in zip(parts,ps):
            acc+=prob
            if r<=acc: out.append(Hypothesis(p.rule, -math.log(target), p.loss, p.contradictions, p.provenance)); break
    return tuple(out) or parts
def top(parts,k=5): return sorted(normalize(parts), key=lambda p:p.log_weight, reverse=True)[:k]
