from __future__ import annotations
import hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
FINAL=ROOT/'competition/final_kaggle'
CELLS=FINAL/'cells'
AGENT=FINAL/'my_agent.py'
def main():
    CELLS.mkdir(parents=True, exist_ok=True)
    agent_text=AGENT.read_text()
    agent_sha=hashlib.sha256(AGENT.read_bytes()).hexdigest()
    cell1="""!pip install --no-index --find-links \\
  /kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels \\
  arc-agi python-dotenv
"""
    cell2=f"%%writefile /tmp/my_agent.py\n# AXIOM_FINAL_AGENT_SHA256={agent_sha}\n"+agent_text
    cell3=r'''import os, shutil, subprocess, sys, time
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
'''
    cell4=r'''import os
if not bool(os.getenv("KAGGLE_IS_COMPETITION_RERUN")):
    import pandas as pd
    submission = pd.DataFrame(
        data=[["1_0", "1", True, 1]],
        columns=["row_id", "game_id", "end_of_game", "score"],
    )
    submission.to_parquet(
        "/kaggle/working/submission.parquet",
        index=False,
    )
'''
    cells=[cell1,cell2,cell3,cell4]
    for i,src in enumerate(cells,1): (CELLS/f"{i:02d}_{['install','write_agent','run_competition','dummy_submission'][i-1]}.py").write_text(src)
    md=['# Axiom Final Kaggle Copy/Paste Cells\n\n## Cell 0 — keep Kaggle generic setup cell\n\nDo not edit Kaggle\'s generic first cell. Paste the following four cells after it.\n']
    for i,src in enumerate(cells,1): md.append(f"## Cell {i}\n\n```python\n{src}\n```\n")
    (FINAL/'COPY_PASTE_INTO_KAGGLE.md').write_text('\n'.join(md))
    nb_cells=[{'cell_type':'markdown','metadata':{},'source':'# Cell 0 — keep Kaggle generic setup cell before these four generated cells\n'}]
    for src in cells: nb_cells.append({'cell_type':'code','metadata':{},'outputs':[],'execution_count':None,'source':src})
    nb={'cells':nb_cells,'metadata':{'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'},'language_info':{'name':'python'},'kaggle':{'isInternetEnabled':False,'accelerator':'none','sourceType':'notebook','language':'python'}},'nbformat':4,'nbformat_minor':5}
    nb_path=FINAL/'axiom_final_submission.ipynb'; nb_path.write_text(json.dumps(nb,indent=1))
    settings='''# Kaggle Settings\n\n- Internet: disabled\n- Accelerator: CPU / None\n- Language: Python\n- Competition data: ARC Prize 2026 ARC-AGI-3 attached automatically\n\nThe current Axiom agent is symbolic and CPU-first. Switch to T4 only after adding and measuring a local neural component that improves public-game results and fits runtime limits.\n'''
    (FINAL/'KAGGLE_SETTINGS.md').write_text(settings)
    ready=f'''# Ready to Submit Handoff\n\n- Fully embedded code: yes, Cell 2 writes the complete self-contained agent to `/tmp/my_agent.py`.\n- Agent SHA-256: `{agent_sha}`\n- Notebook SHA-256: `{hashlib.sha256(nb_path.read_bytes()).hexdigest()}`\n- Cell order: Cell 1 install, Cell 2 write agent, Cell 3 run official competition rerun, Cell 4 dummy non-rerun submission.\n- Kaggle settings: internet disabled, CPU/None accelerator, Python, ARC Prize 2026 ARC-AGI-3 data attached.\n- Save & Run All behavior: outside rerun, Cell 4 creates `/kaggle/working/submission.parquet`.\n- Competition rerun behavior: Cell 3 waits for local gateway, copies official framework, registers `MyAgent`, runs `python main.py --agent myagent`, and expects the gateway/framework to create `/kaggle/working/submission.parquet`.\n- Known unverified item: real Kaggle gateway execution.\n- Known unverified item: hidden leaderboard score.\n\n## Checklist\n\n- [ ] Create or open Kaggle competition notebook\n- [ ] Keep generic setup cell\n- [ ] Paste Cells 1–4\n- [ ] Disable internet\n- [ ] Select CPU\n- [ ] Save Version\n- [ ] Run All\n- [ ] Confirm status is complete\n- [ ] Confirm `submission.parquet` exists under Output\n- [ ] Click Submit to Competition\n- [ ] Select `submission.parquet`\n- [ ] Record leaderboard score and logs\n'''
    (FINAL/'READY_TO_SUBMIT.md').write_text(ready)
    print(json.dumps({'agent_sha256':agent_sha,'notebook_sha256':hashlib.sha256(nb_path.read_bytes()).hexdigest(),'notebook_size':nb_path.stat().st_size},sort_keys=True))
if __name__=='__main__': main()
