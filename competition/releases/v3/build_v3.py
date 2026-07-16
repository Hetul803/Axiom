from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bundle_agent() -> str:
    scientist = (ROOT / "source/axiom_scientist.py").read_text()
    fallback = (ROOT / "source/frozen_v2.py").read_text().replace("from dataclasses import dataclass, field\nfrom typing import Any\n", "")
    wrapper = (ROOT / "source/my_agent_wrapper.py").read_text()
    wrapper = wrapper.replace("from __future__ import annotations\n\n", "").replace("import os\nimport time\nfrom typing import Any\n\n", "")
    prompts = {path.stem: path.read_text() for path in sorted((ROOT / "prompts").glob("*.txt"))}
    embedded = "EMBEDDED_PROMPTS = " + repr(prompts)
    return scientist.rstrip() + "\n\n" + fallback.rstrip() + "\n\n" + embedded + "\n\n" + wrapper.rstrip() + "\n"


def cells(agent: str) -> list[tuple[str, str]]:
    install = """!pip install --no-index --find-links /kaggle/input/arc3-vllm-h100-wheelhouse-v3 --find-links /kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels arc-agi python-dotenv vllm
"""
    model = r'''import atexit, json, os, subprocess, time, urllib.request
from pathlib import Path
os.environ.update({"HF_HUB_OFFLINE":"1", "TRANSFORMERS_OFFLINE":"1", "DO_NOT_TRACK":"1", "VLLM_NO_USAGE_STATS":"1", "AXIOM_V3_LLM":"0"})
GLOBAL_DEADLINE = time.monotonic() + 9 * 60 * 60
MODEL_NAME = "vrfai/Qwen3.6-27B-FP8"
MODEL_ROOT = Path("/kaggle/input/vrfai-qwen3-6-27b-fp8-hf-snapshot")
MODEL_PATH = next((p for p in MODEL_ROOT.rglob("config.json")), None)
VLLM_PROCESS = None
def stop_vllm():
    global VLLM_PROCESS
    if VLLM_PROCESS and VLLM_PROCESS.poll() is None:
        VLLM_PROCESS.terminate()
        try: VLLM_PROCESS.wait(timeout=30)
        except subprocess.TimeoutExpired: VLLM_PROCESS.kill()
atexit.register(stop_vllm)
if MODEL_PATH:
    command = ["python", "-m", "vllm.entrypoints.openai.api_server", "--model", str(MODEL_PATH.parent), "--served-model-name", MODEL_NAME, "--host", "127.0.0.1", "--port", "1234", "--enable-prefix-caching", "--disable-log-stats", "--max-model-len", "16384", "--gpu-memory-utilization", "0.90"]
    VLLM_PROCESS = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    ready_by = min(GLOBAL_DEADLINE - 2400, time.monotonic() + 900)
    while time.monotonic() < ready_by and VLLM_PROCESS.poll() is None:
        try:
            with urllib.request.urlopen("http://127.0.0.1:1234/health", timeout=2) as response:
                if response.status == 200: break
        except Exception: time.sleep(5)
    try:
        payload = json.dumps({"model":MODEL_NAME,"messages":[{"role":"user","content":"Reply exactly AXIOM_V3_READY"}],"max_tokens":16,"temperature":0}).encode()
        request = urllib.request.Request("http://127.0.0.1:1234/v1/chat/completions", data=payload, headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(request, timeout=60) as response: smoke = json.load(response)
        if "AXIOM_V3_READY" in smoke["choices"][0]["message"]["content"]: os.environ["AXIOM_V3_LLM"] = "1"
    except Exception: stop_vllm()
print("Axiom V3 model mode:", os.environ["AXIOM_V3_LLM"])
'''
    write_agent = "%%writefile /tmp/my_agent.py\n" + agent
    harness = '''import os, shutil, subprocess, time
from pathlib import Path
os.environ["MPLBACKEND"] = "agg"
TRUE_SUBMISSION = bool(os.getenv("KAGGLE_IS_COMPETITION_RERUN"))
ROOT = Path("/kaggle/input/competitions/arc-prize-2026-arc-agi-3")
WORK = Path("/kaggle/working")
GATEWAY = "http://gateway:8001/api/games"
def wait_for_gateway(timeout_seconds=600):
    deadline = min(time.monotonic() + timeout_seconds, GLOBAL_DEADLINE - 2400)
    while time.monotonic() < deadline:
        if subprocess.call(["curl", "--fail", "--silent", "--show-error", GATEWAY]) == 0: return
        time.sleep(5)
    raise TimeoutError("Local competition gateway did not become ready")
if TRUE_SUBMISSION:
    source, destination = ROOT / "ARC-AGI-3-Agents", WORK / "ARC-AGI-3-Agents"
    wait_for_gateway()
    if destination.exists(): shutil.rmtree(destination)
    shutil.copytree(source, destination)
    template = destination / "agents" / "templates"
    template.mkdir(parents=True, exist_ok=True)
    shutil.copyfile("/tmp/my_agent.py", template / "my_agent.py")
    (destination / "agents" / "__init__.py").write_text("from typing import Type\\nfrom dotenv import load_dotenv\\nfrom .agent import Agent, Playback\\nfrom .swarm import Swarm\\nfrom .templates.random_agent import Random\\nfrom .templates.my_agent import MyAgent\\nload_dotenv()\\nAVAILABLE_AGENTS: dict[str, Type[Agent]] = {'random': Random, 'myagent': MyAgent}\\n")
    (destination / ".env").write_text("SCHEME=http\\nHOST=gateway\\nPORT=8001\\nARC_API_KEY=test-key-123\\nARC_BASE_URL=http://gateway:8001/\\nOPERATION_MODE=online\\nENVIRONMENTS_DIR=\\nRECORDINGS_DIR=/kaggle/working/server_recording\\n")
    try: subprocess.check_call(["python", "main.py", "--agent", "myagent"], cwd=str(destination), timeout=max(1, GLOBAL_DEADLINE - time.monotonic() - 2400))
    finally: stop_vllm()
else:
    import pandas as pd
    pd.DataFrame([["1_0", "1", True, 1]], columns=["row_id", "game_id", "end_of_game", "score"]).to_parquet(WORK / "submission.parquet", index=False)
    stop_vllm()
'''
    return [("Offline installation", install), ("Start offline local model", model), ("Write complete V3 agent", write_agent), ("Official V2-proven competition harness", harness)]


def main() -> None:
    agent = bundle_agent()
    compile(agent, "my_agent.py", "exec")
    (ROOT / "my_agent.py").write_text(agent)
    notebook_cells = cells(agent)
    notebook = {"cells": [{"cell_type": "markdown", "metadata": {}, "source": ["# Keep Kaggle's generic setup cell unchanged\n"]}] + [{"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": source.splitlines(True)} for _, source in notebook_cells], "metadata": {"kaggle": {"accelerator": "nvidiaRtxPro6000", "dataSources": ["arc-prize-2026-arc-agi-3", "driessmit1/arc3-vllm-h100-wheelhouse-v3", "driessmit1/vrfai-qwen3-6-27b-fp8-hf-snapshot"], "isInternetEnabled": False}, "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python", "version": "3.12"}}, "nbformat": 4, "nbformat_minor": 5}
    (ROOT / "axiom_v3_submission.ipynb").write_text(json.dumps(notebook, indent=1) + "\n")
    document = ["# Axiom Scientist V3 — copy into Kaggle\n", "## Cell 0\nKeep Kaggle's generic setup cell unchanged.\n"]
    for index, (title, source) in enumerate(notebook_cells, 1):
        document.extend([f"## Cell {index} — {title}\n", "```python\n" + source + "```\n"])
    (ROOT / "COPY_PASTE_INTO_KAGGLE.md").write_text("\n".join(document))
    sources = {str(path.relative_to(ROOT)): sha(path) for path in sorted((ROOT / "source").glob("*.py"))}
    manifest = {"version": "3", "generated_utc": datetime.now(timezone.utc).isoformat(), "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "agent_sha256": sha(ROOT / "my_agent.py"), "notebook_sha256": sha(ROOT / "axiom_v3_submission.ipynb"), "sources": sources, "model": "vrfai/Qwen3.6-27B-FP8", "vllm": {"host": "127.0.0.1", "port": 1234, "prefix_caching": True}}
    (ROOT / "V3_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
