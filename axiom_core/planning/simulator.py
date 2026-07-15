from axiom_core.causality.interpreter import execute
def simulate(grid,hypothesis,action): return execute(grid,hypothesis.rule,action)
