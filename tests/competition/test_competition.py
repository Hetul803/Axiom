import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def test_build_notebook(): subprocess.run([sys.executable,'competition/build_notebook.py'],cwd=ROOT,check=True); assert (ROOT/'competition/axiom_arc3_submission.ipynb').exists()
def test_validate_notebook(): subprocess.run([sys.executable,'competition/validate_notebook.py'],cwd=ROOT,check=True)
def test_offline_smoke(): subprocess.run([sys.executable,'competition/offline_smoke_test.py'],cwd=ROOT,check=True)
def test_runtime_profile(): subprocess.run([sys.executable,'competition/runtime_profile.py'],cwd=ROOT,check=True)
def test_manifest_and_cells_md(): assert (ROOT/'competition/cells_manifest.json').exists() and '01_install_arc_runtime' in (ROOT/'competition/notebook_cells.md').read_text()
def test_myagent_interface_methods():
 from competition.agent.my_agent import MyAgent
 assert hasattr(MyAgent,'is_done') and hasattr(MyAgent,'choose_action')
def test_official_version_recorded(): assert 'MyAgent.choose_action' in (ROOT/'competition/OFFICIAL_STARTER_VERSION.md').read_text()
