# Axiom Intelligence V2 Plan

1. Preserve the exact v1 score-0.06 Kaggle artifacts under `competition/releases/v1_score_0_06/`.
2. Add competition-safe diagnostics and a replay analyzer for local/public runs only.
3. Improve the policy core with a state-action graph, systematic frontier exploration, controllable-object/action discovery, role inference, verified mechanic detectors, simple goal inference, and model-based grid planning.
4. Evaluate on available offline/synthetic environments because the official public ARC runtime is not available in this container.
5. Generate v2 using the already-working four-cell Kaggle harness under `competition/releases/v2/`.
6. Run all tests, final package preflight, and emulation; report only measured results.
