import os, random, time
from pathlib import Path
TRUE_SUBMISSION = bool(os.getenv('KAGGLE_IS_COMPETITION_RERUN'))
OUTPUT_DIR = Path('/kaggle/working'); OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SEED = 20260715
random.seed(SEED)
GLOBAL_DEADLINE = time.monotonic() + (11 * 60 if TRUE_SUBMISSION else 60)
PER_ACTION_SOFT_DEADLINE_MS = 35
PARTICLE_BUDGET = 64
MAX_HYPOTHESES = 96
MAX_HISTORY = 256
NEURAL_PROPOSER_ENABLED = False
LOG_LEVEL = 'WARNING' if TRUE_SUBMISSION else 'INFO'
ACCELERATOR = 'cpu'
def should_stop_now(margin_seconds=15):
    return time.monotonic() + margin_seconds >= GLOBAL_DEADLINE
