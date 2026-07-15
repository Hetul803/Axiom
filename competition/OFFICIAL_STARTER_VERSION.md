# Official ARC-AGI-3 Kaggle Starter Inspection

Repository: https://github.com/arcprize/ARC-AGI-3-Kaggle-Starter
Branch inspected: `main`
Inspection date: 2026-07-15

Commit SHA: unavailable in this execution environment because `git ls-remote` and GitHub API requests were blocked by a 403 CONNECT tunnel. Raw source files and repository HTML were inspected through the browser tool.

Official interfaces observed from starter:

- `MyAgent` subclasses `agents.agent.Agent`.
- `MyAgent.is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool`.
- `MyAgent.choose_action(self, frames: list[FrameData], latest_frame: FrameData) -> GameAction`.
- Official imports used by starter: `from arcengine import FrameData, GameAction, GameState` and `from agents.agent import Agent`.
- Starter returns `latest_frame.state is GameState.WIN` from `is_done`.
- Starter returns `GameAction.RESET` when latest state is `GameState.NOT_PLAYED` or `GameState.GAME_OVER`.
- Complex/coordinate actions are detected via `action.is_complex()` and populated via `action.set_data({"x": ..., "y": ...})`.
- Kaggle rerun is detected with `KAGGLE_IS_COMPETITION_RERUN`.
- Offline wheelhouse path: `/kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels`.
- Framework copy path: `/kaggle/input/competitions/arc-prize-2026-arc-agi-3/ARC-AGI-3-Agents`.
- Gateway URL: `http://gateway:8001`.
- Official harness runs `python main.py --agent myagent` and produces `/kaggle/working/submission.parquet`.
