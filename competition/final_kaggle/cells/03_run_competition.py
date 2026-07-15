import os, shutil, subprocess, sys, time
from pathlib import Path
os.environ["MPLBACKEND"] = "agg"
TRUE_SUBMISSION = bool(os.getenv("KAGGLE_IS_COMPETITION_RERUN"))
ROOT = Path("/kaggle/input/competitions/arc-prize-2026-arc-agi-3")
WORK = Path("/kaggle/working")
GATEWAY = "http://gateway:8001/api/games"

def wait_for_gateway(timeout_seconds=600):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        code = subprocess.call(["curl", "--fail", "--silent", "--show-error", GATEWAY])
        if code == 0:
            return
        time.sleep(5)
    raise TimeoutError("Local competition gateway did not become ready")

if TRUE_SUBMISSION:
    agents_src = ROOT / "ARC-AGI-3-Agents"
    agents_dst = WORK / "ARC-AGI-3-Agents"
    if not agents_src.exists():
        raise FileNotFoundError(f"Missing official agents framework: {agents_src}")
    wait_for_gateway()
    if agents_dst.exists():
        shutil.rmtree(agents_dst)
    shutil.copytree(agents_src, agents_dst)
    template_dir = agents_dst / "agents" / "templates"
    template_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile("/tmp/my_agent.py", template_dir / "my_agent.py")
    (agents_dst / "agents" / "__init__.py").write_text(
        "from typing import Type\n"
        "from dotenv import load_dotenv\n"
        "from .agent import Agent, Playback\n"
        "from .swarm import Swarm\n"
        "from .templates.random_agent import Random\n"
        "from .templates.my_agent import MyAgent\n"
        "load_dotenv()\n"
        "AVAILABLE_AGENTS: dict[str, Type[Agent]] = {'random': Random, 'myagent': MyAgent}\n"
    )
    (agents_dst / ".env").write_text(
        "SCHEME=http\n"
        "HOST=gateway\n"
        "PORT=8001\n"
        "ARC_API_KEY=test-key-123\n"
        "ARC_BASE_URL=http://gateway:8001/\n"
        "OPERATION_MODE=online\n"
        "ENVIRONMENTS_DIR=\n"
        "RECORDINGS_DIR=/kaggle/working/server_recording\n"
    )
    try:
        subprocess.check_call(["python", "main.py", "--agent", "myagent"], cwd=str(agents_dst))
    finally:
        if not (WORK / "submission.parquet").exists():
            print("WARNING: official gateway run ended without /kaggle/working/submission.parquet")
else:
    print("Not a competition rerun; Cell 4 will create the Save & Run All dummy submission.")
