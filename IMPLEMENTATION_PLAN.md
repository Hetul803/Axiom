# Implementation Plan

1. Inspect current repository and official ARC-AGI-3 starter interfaces from GitHub raw files.
2. Remove repository-local fake dependency packages and move reusable symbolic logic into `axiom_core`.
3. Create `competition` with official-style `MyAgent(Agent)` interface, offline notebook cells, notebook builder, validator, smoke test, and runtime profiler.
4. Create `startup` adaptive-environment MVP with an SDK protocol, grid and workflow demos, a FastAPI-compatible backend module, and React/Vite frontend files.
5. Add bounded deadlines, legal fallback, state hashing, loop/repeat penalties, hypothesis limits, and self-contained notebook embedding.
6. Replace eight-test suite with substantial core, mechanics, goal/planning, deadline, competition, startup, and notebook validation tests.
7. Run tests and required commands, repair failures, commit, and create PR metadata.
