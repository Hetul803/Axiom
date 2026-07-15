def test_grid_env():
 from startup.backend.grid_environment import UnknownGridEnvironment
 e=UnknownGridEnvironment(); assert e.legal_actions(); assert e.execute('right').grid
def test_workflow_env_completion():
 from startup.backend.web_simulator import WorkflowSimulator
 e=WorkflowSimulator()
 for a in ['open_settings','grant_permission','open_editor','save_draft','submit']: obs=e.execute(a)
 assert obs.status.value=='win'
def test_session_manager_grid():
 from startup.backend.session_manager import SessionManager
 m=SessionManager(); sid=m.create('grid'); assert m.step(sid)['action']
def test_session_manager_workflow():
 from startup.backend.session_manager import SessionManager
 m=SessionManager(); sid=m.create('workflow'); assert 'legal_actions' in m.step(sid)
def test_backend_health():
 from startup.backend.main import health
 assert health()['ok'] is True
def test_replay():
 from startup.backend.session_manager import SessionManager
 m=SessionManager(); sid=m.create('grid'); m.step(sid); assert m.sessions[sid]['timeline']
