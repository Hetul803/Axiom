from axiom_core.exploration.information_gain import expected_information_gain
from axiom_core.exploration.reversibility import score as rev
from axiom_core.exploration.risk import score as risk
from axiom_core.exploration.novelty import score as nov
def choose(config, parts, legal, state_hash, tried, deadline):
    best=legal[0] if legal else None; best_score=-10**9; diag={}
    for a in legal:
      ig=expected_information_gain(parts,a); n=nov(state_hash,a,tried); r=rev(a,legal); q=risk(a); rep=1-n; s=config.w_information*ig+config.w_novelty*n+config.w_reversibility*r-config.w_risk*q-config.w_repeat*rep-config.w_cost
      diag[str(a)]={"score":s,"information":ig,"novelty":n,"reversibility":r,"risk":q}
      if s>best_score or (s==best_score and str(a)<str(best)): best_score=s; best=a
    return best, diag
