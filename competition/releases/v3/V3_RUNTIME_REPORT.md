# V3 runtime report

Local CPU evaluation ran 12 hidden-action-permutation synthetic games with the LLM disabled: 50% solved, 27.5 mean actions, 0.0% repeated state-action pairs, 0.130 ms mean controller selection, and 0.238 ms maximum per-game p95. These measurements do not include subprocess world-model simulation or the unavailable 27B model server.

The Kaggle notebook reserves 40 minutes for harness closure, starts one local vLLM server, enables prefix caching, caps each game at 12 calls/32,768 generated tokens, and uses a 60-second action budget only while the model client is enabled. Actual RTX Pro 6000 startup, tokens/second, calls/game, and end-to-end runtime remain unmeasured until Kaggle execution.
