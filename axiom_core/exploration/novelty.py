def score(state_hash, action, tried): return 0.0 if (state_hash,str(action)) in tried else 1.0
