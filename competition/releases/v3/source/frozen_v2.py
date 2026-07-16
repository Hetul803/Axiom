"""V2-compatible deterministic fallback, copied into V3 without importing frozen artifacts."""
from dataclasses import dataclass, field
from typing import Any

@dataclass
class V2Fallback:
    tried: dict[tuple[str, str], int] = field(default_factory=dict)

    def choose(self, state_key: str, legal: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not legal:
            return None
        frontier = [action for action in legal if self.tried.get((state_key, stable_hash(action)), 0) == 0]
        selected = sorted(frontier or legal, key=stable_hash)[0]
        key = state_key, stable_hash(selected)
        self.tried[key] = self.tried.get(key, 0) + 1
        return selected
