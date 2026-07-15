from axiom_core.causality.particles import entropy
def expected_information_gain(parts, action): return max(0.0, entropy(parts)-entropy(tuple(p for p in parts if str(p.rule.action)==str(action)) or parts)*0.9)
