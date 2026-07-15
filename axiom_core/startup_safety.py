from dataclasses import dataclass
@dataclass(frozen=True)
class ActionSafety:
    reversible: bool=True; destructive: bool=False; requires_approval: bool=False; redacted: bool=False
def classify_action(action):
    s=str(action).lower(); destructive=any(w in s for w in ('delete','reset','submit','destroy','purchase','danger'))
    return ActionSafety(reversible=not destructive, destructive=destructive, requires_approval=destructive)
def redact(value): return '<redacted>' if any(w in str(value).lower() for w in ('password','token','secret','key')) else value
