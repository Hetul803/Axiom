import json,re,sys
from pathlib import Path
NB=Path(__file__).resolve().parent/'axiom_arc3_submission.ipynb'
def main():
    text=NB.read_text() if NB.exists() else ''; nb=json.loads(text); src='\n'.join(''.join(c.get('source','')) for c in nb['cells'])
    errors=[]
    if 'pip' in src and '--no-index' not in src: errors.append('pip install without --no-index')
    banned=['git clone','kagglehub.dataset_download','huggingface','openai','anthropic','generativelanguage','http://','https://']
    for b in banned:
      if b in src and 'http://gateway:8001' not in src.replace(b,'http://gateway:8001',1): errors.append(f'banned token: {b}')
    if 'submission.parquet' not in src: errors.append('missing submission.parquet generation')
    if re.search(r'game_id\s*==|split\("-"\)\[0\]\s*==', src): errors.append('game-id conditional')
    if 'while True' in src and 'should_stop_now' not in src: errors.append('unbounded while True')
    if 'from axiom_core' in src and "write_text" not in src: errors.append('unresolved axiom_core import before embedding')
    if errors: raise SystemExit('\n'.join(errors))
    print('notebook validation passed')
if __name__=='__main__': main()
