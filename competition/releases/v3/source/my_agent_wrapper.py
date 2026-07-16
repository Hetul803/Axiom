from __future__ import annotations

import os
import time
from typing import Any

from arcengine import FrameData, GameAction, GameState
from agents.agent import Agent


def _state_name(value: Any) -> str:
    return str(getattr(value, "name", value))


class MyAgent(Agent):
    MAX_ACTIONS = 80

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        enabled = os.getenv("AXIOM_V3_LLM", "1") == "1"
        client = LocalVLLMClient() if enabled else None
        self.controller = AxiomScientistController(client, EMBEDDED_PROMPTS)
        self.action_count = 0

    @property
    def name(self) -> str:
        return f"AxiomScientistV3.{self.MAX_ACTIONS}"

    def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool:
        return _state_name(getattr(latest_frame, "state", None)).endswith(_state_name(GameState.WIN))

    def _legal(self) -> list[Any]:
        try:
            return [action for action in GameAction if action is not GameAction.RESET]
        except TypeError:
            return [getattr(GameAction, name) for name in dir(GameAction) if name.startswith("ACTION")]

    def _grid(self, frame: FrameData) -> Grid:
        for name in ("grid", "frame", "observation", "array"):
            value = getattr(frame, name, None)
            if value is not None and not callable(value):
                try:
                    return as_grid(value)
                except (TypeError, ValueError):
                    continue
        return ((0,),)

    def _action_dicts(self, actions: list[Any], grid: Grid) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        encoded, lookup = [], {}
        h, w = len(grid), len(grid[0]) if grid else 1
        for action in actions:
            name = _state_name(action)
            if hasattr(action, "is_complex") and action.is_complex():
                points = {(h // 2, w // 2), (0, 0), (max(0, h - 1), max(0, w - 1))}
                for component in components(grid)[:16]:
                    points.add((round(component["centroid"][0]), round(component["centroid"][1])))
                for y, x in sorted(points)[:32]:
                    item = {"name": name, "data": {"x": int(x), "y": int(y)}}
                    encoded.append(item)
                    lookup[stable_hash(item)] = action
            else:
                item = {"name": name}
                encoded.append(item)
                lookup[stable_hash(item)] = action
        return encoded, lookup

    def _materialize(self, specification: dict[str, Any], lookup: dict[str, Any], grid: Grid) -> Any:
        action = lookup.get(stable_hash(specification))
        if action is None:
            action = next(iter(lookup.values()), GameAction.RESET)
        if specification.get("data") and hasattr(action, "set_data"):
            h, w = len(grid), len(grid[0]) if grid else 1
            data = specification["data"]
            action.set_data({"x": max(0, min(w - 1, int(data["x"]))), "y": max(0, min(h - 1, int(data["y"])))})
        return action

    def choose_action(self, frames: list[FrameData], latest_frame: FrameData) -> GameAction:
        deadline = time.monotonic() + (60.0 if self.controller.llm else 0.12)
        try:
            state = getattr(latest_frame, "state", None)
            if _state_name(state).endswith(_state_name(GameState.NOT_PLAYED)) or _state_name(state).endswith(_state_name(GameState.GAME_OVER)):
                return GameAction.RESET
            legal = self._legal()
            if not legal:
                return GameAction.RESET
            grid = self._grid(latest_frame)
            encoded, lookup = self._action_dicts(legal, grid)
            observation = self.controller.observe(grid, encoded, "win" if self.is_done(frames, latest_frame) else "active")
            selected = self.controller.choose(observation, deadline)
            action = self._materialize(selected or encoded[0], lookup, grid)
            self.action_count += 1
            return action if action in legal else legal[0]
        except Exception:
            legal = self._legal()
            return legal[0] if legal else GameAction.RESET
