# Final Kaggle Packaging Plan

1. Freeze the current competition architecture and include only inference-time Axiom logic in one self-contained `/tmp/my_agent.py` file.
2. Generate `competition/final_kaggle/my_agent.py` deterministically from a builder, recording source hashes, final agent hash, timestamp, and git commit.
3. Generate exactly four copy/paste cells: offline install, write complete agent, official competition rerun, and non-rerun dummy submission.
4. Generate the final copy/paste Markdown document and final notebook using only the four cells after the user's generic Kaggle setup cell.
5. Add preflight validation for self-containment, offline-only runtime, exact cell count/order, notebook metadata, agent hash, deadline/fallback/complex-action handling, and forbidden tokens.
6. Add an offline packaging emulation with mock official `arcengine` and `agents.agent` interfaces; do not claim public or hidden ARC evaluation.
7. Run `python -m pytest`, the builder, preflight, and emulation with no failures.
