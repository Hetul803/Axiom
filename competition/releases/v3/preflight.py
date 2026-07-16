from __future__ import annotations
import ast, hashlib, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
errors=[]
manifest=json.loads((ROOT/'V2_FROZEN_HASHES.json').read_text()); v2=ROOT.parent/'v2'
actual={str(p.relative_to(v2)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(v2.rglob('*')) if p.is_file()}
if actual!=manifest['files']: errors.append('V2 frozen hash mismatch')
agent=(ROOT/'my_agent.py').read_text(); ast.parse(agent)
notebook=json.loads((ROOT/'axiom_v3_submission.ipynb').read_text())
source=''.join(''.join(cell.get('source',[])) for cell in notebook['cells'])
if notebook['metadata']['kaggle'].get('isInternetEnabled') is not False: errors.append('internet metadata is not disabled')
required=['--no-index','127.0.0.1','--enable-prefix-caching','KAGGLE_IS_COMPETITION_RERUN','submission.parquet','stop_vllm','AXIOM_V3_LLM']
for token in required:
    if token not in source: errors.append('missing '+token)
for pattern in ('kagglehub.dataset_download','git clone','huggingface.co','api.openai.com','api.anthropic.com'):
    if pattern in source.lower(): errors.append('forbidden '+pattern)
for url in re.findall(r'https?://[^"\\s]+',source):
    if not (url.startswith('http://127.0.0.1') or url.startswith('http://gateway')): errors.append('non-local URL '+url)
if 'competition/releases/v2' in agent or 'axiom_core' in agent: errors.append('runtime repository dependency')
if errors: raise SystemExit('\n'.join(errors))
print('V3 preflight passed; V2 hashes unchanged; notebook offline and self-contained')
