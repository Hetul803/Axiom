# Ready to Submit Handoff

- Fully embedded code: yes, Cell 2 writes the complete self-contained agent to `/tmp/my_agent.py`.
- Agent SHA-256: `8fa165a7abe66613e1cec31827b03d6c5ed413c071d09668fa8330e2c4747a3c`
- Notebook SHA-256: `da2dfa489335610478ca8b666f300e86ca663fb5a4d34e8bd32cf44a4fe5041b`
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
