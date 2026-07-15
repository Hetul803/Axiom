from __future__ import annotations
import base64, hashlib, io, json, tarfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; REL=ROOT/'competition/release'; REL.mkdir(parents=True, exist_ok=True)
def source_files(): return sorted([p for p in (ROOT/'axiom_core').rglob('*.py')] + [ROOT/'competition/agent/my_agent.py'])
def bundle_bytes():
    bio=io.BytesIO()
    with tarfile.open(fileobj=bio, mode='w:gz') as tar:
        for p in source_files(): tar.add(p, arcname=str(p.relative_to(ROOT)))
    return bio.getvalue()
def main():
    data=bundle_bytes(); b64=base64.b64encode(data).decode(); digest=hashlib.sha256(data).hexdigest()
    compact=f"""# Axiom compact embedded bundle\nimport base64, tarfile, io, sys\nfrom pathlib import Path\nDATA={b64!r}\nroot=Path('/kaggle/working')\nwith tarfile.open(fileobj=io.BytesIO(base64.b64decode(DATA)), mode='r:gz') as tar:\n    tar.extractall(root)\nsys.path.insert(0, str(root))\nBUNDLE_SHA256={digest!r}\n"""
    (REL/'agent_bundle.py').write_text(compact)
    expanded=[]; hashes={}
    for p in source_files():
        rel=str(p.relative_to(ROOT)); text=p.read_text(); hashes[rel]=hashlib.sha256(text.encode()).hexdigest(); expanded.append(f"%%writefile /kaggle/working/{rel}\n{text}\n")
    (REL/'notebook_cells_expanded.md').write_text('\n'.join(expanded))
    (REL/'notebook_cells.md').write_text('# Axiom compact release cells\n\n```python\n'+compact+'\n```\n')
    nb={'cells':[{'cell_type':'markdown','metadata':{},'source':'# Keep Kaggle setup cell before this generated release notebook\n'},{'cell_type':'code','metadata':{},'outputs':[],'execution_count':None,'source':compact}], 'metadata':{'kaggle':{'isInternetEnabled':False,'accelerator':'none','sourceType':'notebook'},'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'}}, 'nbformat':4,'nbformat_minor':5}
    (REL/'axiom_arc3_submission.ipynb').write_text(json.dumps(nb,indent=1))
    manifest={'created_at':time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),'bundle_sha256':digest,'files':hashes,'source_file_count':len(hashes),'internet':False,'accelerator':'cpu'}
    (REL/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True))
    (REL/'SUBMISSION_CHECKLIST.md').write_text('# Submission checklist\n\n- [x] Internet disabled metadata\n- [x] Embedded source bundle generated\n- [x] No external APIs by default\n- [ ] Official public games run in official environment\n- [ ] Kaggle Save & Run All executed\n')
    (REL/'RUNTIME_REPORT.md').write_text('# Runtime report\n\nGenerated release bundle. Run `python competition/runtime_profile.py` for local CPU timing. Official Kaggle timing is not claimed until Save & Run All succeeds.\n')
    print(REL/'axiom_arc3_submission.ipynb')
if __name__=='__main__': main()
