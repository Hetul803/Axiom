import os, subprocess, sys, time
from pathlib import Path
if TRUE_SUBMISSION:
    if should_stop_now():
        raise TimeoutError('Stopping before Kaggle hard timeout')
    subprocess.call(['curl','--fail','--retry','999','--retry-all-errors','--retry-delay','5','--retry-max-time','600','http://gateway:8001/api/games'])
    src=Path('/kaggle/input/competitions/arc-prize-2026-arc-agi-3/ARC-AGI-3-Agents')
    dst=Path('/kaggle/working/ARC-AGI-3-Agents')
    if not src.exists(): raise FileNotFoundError(src)
    subprocess.check_call(['cp','-r',str(src),str(dst)])
    subprocess.check_call(['cp','/tmp/my_agent.py',str(dst/'agents/templates/my_agent.py')])
    (dst/'agents/__init__.py').write_text("from typing import Type\nfrom dotenv import load_dotenv\nfrom .agent import Agent, Playback\nfrom .swarm import Swarm\nfrom .templates.random_agent import Random\nfrom .templates.my_agent import MyAgent\nload_dotenv()\nAVAILABLE_AGENTS: dict[str, Type[Agent]] = {'random': Random, 'myagent': MyAgent}\n")
    (dst/'.env').write_text('SCHEME=http\nHOST=gateway\nPORT=8001\nARC_API_KEY=test-key-123\nARC_BASE_URL=http://gateway:8001/\nOPERATION_MODE=online\nENVIRONMENTS_DIR=\nRECORDINGS_DIR=/kaggle/working/server_recording\n')
    subprocess.check_call(['python','main.py','--agent','myagent'], cwd=str(dst))
else:
    try:
        import pandas as pd
        pd.DataFrame([['1_0','1',True,1]], columns=['row_id','game_id','end_of_game','score']).to_parquet('/kaggle/working/submission.parquet', index=False)
    except Exception:
        Path('/kaggle/working/submission.parquet').write_bytes(b'row_id,game_id,end_of_game,score\n1_0,1,True,1\n')
