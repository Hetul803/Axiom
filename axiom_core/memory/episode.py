import json
from axiom_core.types import to_jsonable
def dumps_jsonl(episode): return '\n'.join(json.dumps(to_jsonable(x),sort_keys=True) for x in episode.timeline)
