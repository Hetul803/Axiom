import pytest
from startup.backend.environment_registry import create_environment
from startup.backend.session_manager import SessionManager
from startup.backend.approvals import APPROVALS
from startup.backend.benchmarks import run_baseline
@pytest.mark.parametrize('kind', ['grid','workflow','browser']*4)
def test_snapshot_restore(kind):
    e=create_environment(kind); snap=e.snapshot(); e.execute(e.legal_actions()[0]); e.restore(snap); assert e.snapshot()==snap
@pytest.mark.parametrize('kind,policy', [(k,p) for k in ['grid','workflow','browser'] for p in ['axiom','random','novelty']])
def test_baselines_run(kind,policy): assert run_baseline(kind,policy,5)['steps']>=1
def test_destructive_action_blocked_without_approval():
    m=SessionManager(); sid=m.create('browser'); r=m.step(sid,'danger'); assert r.get('blocked') is True
def test_destructive_action_allowed_after_approval():
    m=SessionManager(); sid=m.create('browser'); APPROVALS.approve(sid,'danger'); r=m.step(sid,'danger'); assert r.get('blocked') is not True
def test_session_snapshot_api():
    m=SessionManager(); sid=m.create('workflow'); snap=m.snapshot(sid); m.step(sid,'open_settings'); obs=m.restore(sid,snap); assert obs.metadata['screen']=='home'
