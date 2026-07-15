from axiom_core.types import Hypothesis, Rule, Operation
def prior_hypotheses(actions, n=64):
    base=[Hypothesis(Rule(a,(Operation("no_op"),),(),1.0,0), -1.0, provenance="prior") for a in actions]
    return tuple((base or [Hypothesis(Rule(None,(Operation("no_op"),)),0.0)])[(i%max(1,len(base)))] for i in range(max(1,n)))
