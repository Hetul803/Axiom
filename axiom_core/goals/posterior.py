def update(goals, scene, transition=None): return goals or __import__('axiom_core.goals.induction',fromlist=['induce']).induce(scene,transition)
