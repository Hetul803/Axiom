from __future__ import annotations
import ast, hashlib, json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
AGENT=ROOT/'my_agent.py'
NOTEBOOK=ROOT/'axiom_final_submission.ipynb'
CELL_DIR=ROOT/'cells'
MANIFEST=ROOT/'agent_manifest.json'
FORBIDDEN=['import axiom_core','from axiom_core','startup','fastapi','playwright','transformers','vllm','openai','anthropic','google.generative','kagglehub.dataset_download','git clone','huggingface','TODO','NotImplementedError','paste agent code here']
REQUIRED_AGENT=['class MyAgent','def choose_action','def is_done','Deadline(','deadline.expired','_fallback','is_complex','set_data','try:','except Exception']
REQUIRED_CELL3=['KAGGLE_IS_COMPETITION_RERUN','http://gateway:8001/api/games','ARC-AGI-3-Agents','/tmp/my_agent.py','python','main.py','--agent','myagent','submission.parquet','MPLBACKEND']
def fail(msg): raise SystemExit(msg)
def scan_text(path, text):
    lower=text.lower()
    for token in FORBIDDEN:
        if token.lower() in lower: fail(f'{path}: forbidden token {token}')
    for url in re.findall(r'https?://[^\s\"\']+', text):
        if not url.startswith('http://gateway:8001'): fail(f'{path}: non-local URL {url}')
    if 'pip install' in text and '--no-index' not in text: fail(f'{path}: pip without --no-index')
    if re.search(r'game_id\s*==|split\(["\']-["\']\)\[0\]\s*==', text): fail(f'{path}: game-id policy branch')
    if 'while True' in text: fail(f'{path}: unbounded while True')
def main():
    agent=AGENT.read_text(); compile(agent, str(AGENT), 'exec')
    scan_text(AGENT, agent)
    for req in REQUIRED_AGENT:
        if req not in agent: fail(f'missing agent requirement: {req}')
    manifest=json.loads(MANIFEST.read_text()); agent_sha=hashlib.sha256(AGENT.read_bytes()).hexdigest()
    if manifest['agent_sha256']!=agent_sha: fail('agent manifest hash mismatch')
    cells=sorted(CELL_DIR.glob('*.py'))
    if [p.name for p in cells] != ['01_install.py','02_write_agent.py','03_run_competition.py','04_dummy_submission.py']: fail('unexpected final cell set')
    for p in cells:
        text=p.read_text(); scan_text(p, text)
        if not text.startswith('!') and not text.startswith('%%'): compile(text, str(p), 'exec')
    cell2=(CELL_DIR/'02_write_agent.py').read_text()
    if not cell2.startswith('%%writefile /tmp/my_agent.py'): fail('Cell 2 must write /tmp/my_agent.py')
    if manifest['agent_sha256'] not in cell2: fail('Cell 2 missing exact agent hash')
    cell3=(CELL_DIR/'03_run_competition.py').read_text()
    for req in REQUIRED_CELL3:
        if req not in cell3: fail(f'Cell 3 missing {req}')
    nb=json.loads(NOTEBOOK.read_text())
    if len([c for c in nb['cells'] if c.get('cell_type')=='code'])!=4: fail('notebook must have exactly four code cells')
    kg=nb.get('metadata',{}).get('kaggle',{})
    if kg.get('isInternetEnabled') is not False: fail('notebook internet metadata not disabled')
    if kg.get('accelerator') not in ('none','cpu',None): fail('notebook accelerator not CPU/none')
    nb_sources=[c['source'] for c in nb['cells'] if c.get('cell_type')=='code']
    for p,src in zip(cells, nb_sources):
        if src != p.read_text(): fail(f'notebook source mismatch for {p.name}')
    if '/kaggle/working/submission.parquet' not in ''.join(nb_sources): fail('missing submission parquet path')
    print('preflight passed')
if __name__=='__main__': main()
