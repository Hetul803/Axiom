from axiom_core.types import Goal
def induce(scene, transition=None):
    vals=scene.features.get("values",()) if scene else (); goals=[]
    for v in vals: goals.append(Goal(f"reach_or_affect_value_{v}",1/max(1,len(vals)),v,("visual_value",)))
    if transition and transition.deleted: goals.append(Goal("remove_or_collect_objects",.7,transition.deleted,("disappearance",)))
    if transition and transition.terminal.value=='win': goals.append(Goal("terminal_success_configuration",.95,scene.features.get('hash'),("win",)))
    if len(vals)>3: goals.append(Goal("match_or_transform_pattern",.35,tuple(vals),("multi_value_scene",)))
    return tuple(sorted(goals, key=lambda g:g.probability, reverse=True))
def progress(goal, scene):
    vals=set(scene.features.get('values',()))
    if goal.name.startswith('reach_or_affect'): return 1.0 if goal.target in vals else 0.0
    if goal.name.startswith('remove'): return .5
    return 0.0
