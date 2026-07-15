from startup.backend.grid_environment import UnknownGridEnvironment
from startup.backend.web_simulator import WorkflowSimulator
from startup.backend.browser_sandbox import BrowserSandbox
def create_environment(kind): return BrowserSandbox() if kind=='browser' else WorkflowSimulator() if kind=='workflow' else UnknownGridEnvironment()
