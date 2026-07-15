from pathlib import Path
import sys, subprocess
ROOT = Path('/kaggle/input/competitions/arc-prize-2026-arc-agi-3')
WHEELHOUSE = ROOT / 'arc_agi_3_wheels'
if not WHEELHOUSE.exists():
    raise FileNotFoundError(f'Missing offline ARC wheelhouse: {WHEELHOUSE}')
subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--no-index', '--find-links', str(WHEELHOUSE), 'arc-agi', 'python-dotenv'])
