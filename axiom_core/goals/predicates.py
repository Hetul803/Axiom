def contains_value(scene,value): return value in scene.features.get('values',())
def removed_value(scene,value): return value not in scene.features.get('values',())
