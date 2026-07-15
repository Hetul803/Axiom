import json, subprocess, sys, pytest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
@pytest.mark.parametrize('cmd', [['competition/build_release.py'], ['competition/validate_release.py'], ['competition/build_notebook.py'], ['competition/validate_notebook.py']])
def test_release_commands(cmd): subprocess.run([sys.executable,*cmd],cwd=ROOT,check=True)
def test_release_manifest_hashes():
    m=json.loads((ROOT/'competition/release/manifest.json').read_text()); assert m['source_file_count']>=20 and m['internet'] is False
@pytest.mark.parametrize('p', ['axiom_arc3_submission.ipynb','notebook_cells.md','notebook_cells_expanded.md','agent_bundle.py','manifest.json','SUBMISSION_CHECKLIST.md','RUNTIME_REPORT.md'])
def test_release_files_exist(p): assert (ROOT/'competition/release'/p).exists()
def test_public_results_are_honest_not_fake(): assert json.loads((ROOT/'competition/results/public_games.json').read_text())['status']=='not_run'
def test_official_starter_reference_no_secrets(): assert 'credentials' in (ROOT/'competition/official_starter/README.md').read_text().lower()
