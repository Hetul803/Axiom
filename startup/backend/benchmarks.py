from startup.backend.environment_registry import create_environment
from axiom_core.runtime import AxiomRuntime
from axiom_core.config import AxiomConfig
def run_baseline(kind='grid', policy='axiom', steps=30):
    env=create_environment(kind); rt=AxiomRuntime(AxiomConfig(per_action_ms=10)); obs=env.observe(); actions=[]
    for i in range(steps):
        if policy=='random': action=env.legal_actions()[i % len(env.legal_actions())]
        elif policy=='novelty': action=env.legal_actions()[len(actions) % len(env.legal_actions())]
        else: action=rt.choose_action(obs,10)
        obs=env.execute(action); actions.append(action)
        if obs.status.value!='active': break
    return {'kind':kind,'policy':policy,'steps':len(actions),'status':obs.status.value,'actions':actions}
