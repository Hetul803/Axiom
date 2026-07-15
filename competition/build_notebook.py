from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
ACCELERATOR='cpu'
ACCELS={'cpu':{'name':'none','gpu':False},'t4':{'name':'nvidiaTeslaT4','gpu':True}}
def code(src): return {'cell_type':'code','metadata':{'trusted':True},'outputs':[],'execution_count':None,'source':src}
def md(src): return {'cell_type':'markdown','metadata':{},'source':src}
def main():
    cells=[md('# Cell 00 — Kaggle setup\nKeep Kaggle generic setup cell unchanged before these generated cells.\n')]
    doc=['# Axiom ARC-AGI-3 Notebook Cells\n']
    manifest=[]
    for p in sorted((ROOT/'notebook_cells').iterdir()):
        if p.name.startswith('00_'): doc.append(p.read_text()); continue
        title=f'## {p.stem}\n'; src=p.read_text(); cells += [md(title), code(src)]; doc += [title, '```python\n'+src+'\n```\n']; manifest.append({'file':str(p.relative_to(ROOT)),'type':'code'})
    nb={'cells':cells,'metadata':{'kernelspec':{'language':'python','display_name':'Python 3','name':'python3'},'language_info':{'name':'python'},'kaggle':{'accelerator':ACCELS[ACCELERATOR]['name'],'isInternetEnabled':False,'isGpuEnabled':ACCELS[ACCELERATOR]['gpu'],'language':'python','sourceType':'notebook'}},'nbformat':4,'nbformat_minor':5}
    (ROOT/'axiom_arc3_submission.ipynb').write_text(json.dumps(nb,indent=1)); (ROOT/'notebook_cells.md').write_text('\n'.join(doc)); (ROOT/'cells_manifest.json').write_text(json.dumps(manifest,indent=2)); print(ROOT/'axiom_arc3_submission.ipynb')
if __name__=='__main__': main()
