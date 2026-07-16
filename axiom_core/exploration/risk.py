def score(action, predicted_terminal=False): return min(1.0, (.8 if predicted_terminal else 0.0)+(.2 if str(action).lower() in {"reset","quit","delete"} else 0.0))
