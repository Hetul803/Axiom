# Changes from V1

V1 hidden score was user-reported as 0.06 / 100. Packaging worked, so V2 keeps the same Kaggle harness and changes only intelligence behavior.

## Likely V1 behavior behind 0.06

Without official replay logs in this container, this cannot be proven from public traces. Based on the V1 policy code path, the likely failure modes were repeated weak exploration, insufficient action discovery, weak role/goal inference, and little use of observed state graph structure.

## Material intelligence changes

- Added state-action graph exploration with frontier tracking and repeated ineffective action avoidance.
- Added local diagnostics and HTML replay generation for local/public runs.
- Added action-semantics posterior updates from observed object displacement.
- Added controllable-object and object-role inference from transitions.
- Added mechanic evidence detectors for movement/push, disappearance/collection, appearance/teleport, and toggle/recolor.
- Added simple model-based planning helper for reaching adjacent targets.

## Synthetic/offline measurement

- Completed synthetic permuted-grid task: True
- Steps: 21
- Repeated-action rate: 0.048
- Fallback rate: 0.000
- Mean latency: 1.289 ms
- P95 latency: 1.460 ms
