# Ready to Submit Handoff

- Fully embedded code: yes, Cell 2 writes the complete self-contained agent to `/tmp/my_agent.py`.
- Agent SHA-256: `043c61c7fc87a1bf1a50f45869452617e1a8338acbf61ae3f93f989d99cc9c78`
- Notebook SHA-256: `f65203e1c8a8f9c24853145d7352c32f27f025142e588b85b69076b403ce836c`
- Cell order: Cell 1 install, Cell 2 write agent, Cell 3 run official competition rerun, Cell 4 dummy non-rerun submission.
- Kaggle settings: internet disabled, CPU/None accelerator, Python, ARC Prize 2026 ARC-AGI-3 data attached.
- Save & Run All behavior: outside rerun, Cell 4 creates `/kaggle/working/submission.parquet`.
- Competition rerun behavior: Cell 3 waits for local gateway, copies official framework, registers `MyAgent`, runs `python main.py --agent myagent`, and expects the gateway/framework to create `/kaggle/working/submission.parquet`.
- Known unverified item: real Kaggle gateway execution.
- Known unverified item: hidden leaderboard score.

## Checklist

- [ ] Create or open Kaggle competition notebook
- [ ] Keep generic setup cell
- [ ] Paste Cells 1–4
- [ ] Disable internet
- [ ] Select CPU
- [ ] Save Version
- [ ] Run All
- [ ] Confirm status is complete
- [ ] Confirm `submission.parquet` exists under Output
- [ ] Click Submit to Competition
- [ ] Select `submission.parquet`
- [ ] Record leaderboard score and logs
