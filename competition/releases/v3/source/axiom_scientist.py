from __future__ import annotations

import ast
import builtins
import copy
import hashlib
import json
import math
import multiprocessing as mp
import resource
import time
import urllib.request
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Any, Callable

Grid = tuple[tuple[int, ...], ...]


def stable_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()[:20]


def as_grid(value: Any) -> Grid:
    if hasattr(value, "tolist"):
        value = value.tolist()
    return tuple(tuple(int(cell) for cell in row) for row in value)


def background(grid: Grid) -> int:
    return Counter(cell for row in grid for cell in row).most_common(1)[0][0] if grid else 0


def components(grid: Grid, diagonal: bool = False, include_background: bool = False) -> list[dict[str, Any]]:
    h, w = len(grid), len(grid[0]) if grid else 0
    bg = background(grid)
    neighbors = ((1, 0), (-1, 0), (0, 1), (0, -1))
    if diagonal:
        neighbors += ((1, 1), (1, -1), (-1, 1), (-1, -1))
    seen: set[tuple[int, int]] = set()
    result: list[dict[str, Any]] = []
    for y in range(h):
        for x in range(w):
            if (y, x) in seen or (grid[y][x] == bg and not include_background):
                continue
            value = grid[y][x]
            queue = deque([(y, x)])
            seen.add((y, x))
            cells: list[tuple[int, int]] = []
            while queue:
                cy, cx = queue.popleft()
                cells.append((cy, cx))
                for dy, dx in neighbors:
                    point = cy + dy, cx + dx
                    if 0 <= point[0] < h and 0 <= point[1] < w and point not in seen and grid[point[0]][point[1]] == value:
                        seen.add(point)
                        queue.append(point)
            ys, xs = zip(*cells)
            normalized = sorted((y - min(ys), x - min(xs)) for y, x in cells)
            result.append({
                "id": f"c{len(result)}", "value": value, "cells": sorted(cells), "area": len(cells),
                "bbox": [min(ys), min(xs), max(ys) + 1, max(xs) + 1],
                "centroid": [sum(ys) / len(cells), sum(xs) / len(cells)],
                "shape": stable_hash(normalized),
            })
    return result


def changed_cells(before: Grid, after: Grid) -> list[list[int]]:
    h, w = len(after), len(after[0]) if after else 0
    return [[y, x, before[y][x] if y < len(before) and x < len(before[y]) else None, after[y][x]] for y in range(h) for x in range(w) if y >= len(before) or x >= len(before[y]) or before[y][x] != after[y][x]]


def correspond(previous: list[dict[str, Any]], current: list[dict[str, Any]]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    unused = {item["id"] for item in current}
    for old in previous:
        ranked = sorted((
            ((old["value"] != new["value"]) * 5 + (old["shape"] != new["shape"]) * 3 + abs(old["centroid"][0] - new["centroid"][0]) + abs(old["centroid"][1] - new["centroid"][1]), new)
            for new in current if new["id"] in unused
        ), key=lambda item: item[0])
        if ranked and ranked[0][0] <= 8:
            mapping[old["id"]] = ranked[0][1]["id"]
            unused.remove(ranked[0][1]["id"])
    return mapping


def encode_grid(grid: Grid) -> list[list[list[int]]]:
    encoded = []
    for row in grid:
        runs: list[list[int]] = []
        for value in row:
            if runs and runs[-1][0] == value:
                runs[-1][1] += 1
            else:
                runs.append([value, 1])
        encoded.append(runs)
    return encoded


@dataclass
class StructuredObservation:
    transition_id: int
    grid: Grid
    legal_actions: list[dict[str, Any]]
    components: list[dict[str, Any]]
    changed: list[list[int]] = field(default_factory=list)
    correspondences: dict[str, str] = field(default_factory=dict)
    created: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    recent_actions: list[dict[str, Any]] = field(default_factory=list)
    terminal: str = "active"

    def compact(self) -> dict[str, Any]:
        return {"transition_id": self.transition_id, "dimensions": [len(self.grid), len(self.grid[0]) if self.grid else 0], "background": background(self.grid), "grid_rle": encode_grid(self.grid), "legal_actions": self.legal_actions, "components": self.components, "changed_cells": self.changed, "correspondences": self.correspondences, "created": self.created, "deleted": self.deleted, "recent_actions": self.recent_actions[-8:], "terminal": self.terminal}


@dataclass
class Ontology:
    name: str
    diagonal: bool = False
    include_background: bool = False
    disconnected_by_value: bool = False
    latent_state: dict[str, Any] = field(default_factory=dict)
    error: float = 1.0


def ontology_error(ontology: Ontology, previous: StructuredObservation | None, current: StructuredObservation) -> float:
    if previous is None:
        return 0.0
    unexplained = len(current.changed)
    explained_objects = len(current.correspondences) + len(current.created) + len(current.deleted)
    arbitrary = len(ontology.latent_state)
    return min(1.0, max(0.0, (unexplained - explained_objects) / max(1, unexplained) + arbitrary * 0.02))


MODEL_METHODS = {"parse_state", "predict", "reconstruct_grid", "candidate_goals", "goal_score", "is_goal", "state_key", "legal_model_actions"}
ALLOWED_IMPORTS = {"collections", "dataclasses", "math", "itertools", "heapq", "copy", "numpy"}
FORBIDDEN_NAMES = {"eval", "exec", "compile", "open", "__import__", "globals", "locals", "getattr", "setattr", "subprocess", "socket", "requests", "urllib", "pathlib", "os", "sys"}


def validate_model_code(code: str) -> tuple[bool, list[str]]:
    errors: list[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return False, [f"syntax:{exc.msg}"]
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "GeneratedWorldModel"]
    if len(classes) != 1:
        errors.append("exactly one GeneratedWorldModel class is required")
    else:
        methods = {node.name for node in classes[0].body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        missing = MODEL_METHODS - methods
        if missing:
            errors.append("missing methods: " + ",".join(sorted(missing)))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] not in ALLOWED_IMPORTS:
                    errors.append(f"forbidden import:{alias.name}")
        elif isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] not in ALLOWED_IMPORTS:
            errors.append(f"forbidden import:{node.module}")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_NAMES:
            errors.append(f"forbidden call:{node.func.id}")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            errors.append(f"forbidden attribute:{node.attr}")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and ("game_id" in node.value.lower() or "http://" in node.value or "https://" in node.value):
            errors.append("forbidden identifier or URL literal")
    return not errors, sorted(set(errors))


def _sandbox_worker(code: str, request: dict[str, Any], output: Any) -> None:
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_CPU, (1, 1))
    def restricted_import(name: str, globals: Any = None, locals: Any = None, fromlist: Any = (), level: int = 0) -> Any:
        if name.split(".")[0] not in ALLOWED_IMPORTS:
            raise ImportError(f"forbidden generated-model import: {name}")
        return builtins.__import__(name, globals, locals, fromlist, level)

    safe_builtins = {name: getattr(builtins, name) for name in ("abs", "all", "any", "bool", "dict", "enumerate", "float", "int", "len", "list", "max", "min", "range", "reversed", "round", "set", "sorted", "str", "sum", "tuple", "zip")}
    safe_builtins["__build_class__"] = builtins.__build_class__
    safe_builtins["object"] = object
    safe_builtins["__import__"] = restricted_import
    namespace: dict[str, Any] = {"__builtins__": safe_builtins, "__name__": "generated_world_model"}
    try:
        exec(compile(code, "<generated-model>", "exec"), namespace, namespace)
        model = namespace["GeneratedWorldModel"]()
        method = getattr(model, request["method"])
        output.put({"ok": True, "value": method(*request.get("args", []))})
    except BaseException as exc:
        output.put({"ok": False, "error": f"{type(exc).__name__}:{exc}"})


def sandbox_call(code: str, method: str, args: list[Any], timeout: float = 0.5) -> dict[str, Any]:
    valid, errors = validate_model_code(code)
    if not valid:
        return {"ok": False, "error": ";".join(errors)}
    context = mp.get_context("fork")
    queue = context.Queue(1)
    process = context.Process(target=_sandbox_worker, args=(code, {"method": method, "args": args}, queue))
    process.start()
    process.join(max(0.001, timeout))
    if process.is_alive():
        process.terminate()
        process.join()
        return {"ok": False, "error": "timeout"}
    return queue.get() if not queue.empty() else {"ok": False, "error": "sandbox exited without output"}


@dataclass
class Counterexample:
    transition_id: int
    action: dict[str, Any]
    predicted_grid: Any
    actual_grid: Any
    differing_cells: list[list[int]]


@dataclass
class WorldModelCandidate:
    name: str
    code: str
    ontology: Ontology
    posterior: float = 0.25
    replay_accuracy: float = 0.0
    object_accuracy: float = 0.0
    complexity: float = 0.0
    contradictions: int = 0
    counterexample: Counterexample | None = None

    def score(self) -> float:
        return 3 * self.replay_accuracy + self.object_accuracy - 0.02 * self.complexity - self.ontology.error - 0.25 * self.contradictions


def verify_replay(candidate: WorldModelCandidate, history: list[tuple[StructuredObservation, dict[str, Any], StructuredObservation]], timeout: float = 0.5) -> WorldModelCandidate:
    correct = 0.0
    candidate.counterexample = None
    for previous, action, actual in history:
        parsed = sandbox_call(candidate.code, "parse_state", [previous.compact()], timeout)
        if not parsed["ok"]:
            candidate.contradictions += 1
            break
        predicted = sandbox_call(candidate.code, "predict", [parsed["value"], action], timeout)
        if not predicted["ok"]:
            candidate.contradictions += 1
            break
        grid_result = sandbox_call(candidate.code, "reconstruct_grid", [predicted["value"]], timeout)
        if not grid_result["ok"]:
            candidate.contradictions += 1
            break
        predicted_grid = as_grid(grid_result["value"])
        differences = changed_cells(predicted_grid, actual.grid)
        transition_accuracy = 1.0 - len(differences) / max(1, len(actual.grid) * len(actual.grid[0]))
        correct += transition_accuracy
        if differences and candidate.counterexample is None:
            candidate.counterexample = Counterexample(actual.transition_id, action, grid_result["value"], [list(row) for row in actual.grid], differences[:64])
    candidate.replay_accuracy = correct / max(1, len(history))
    candidate.complexity = len(ast.dump(ast.parse(candidate.code))) / 100.0
    if candidate.counterexample:
        candidate.contradictions += 1
    return candidate


def normalize_models(models: list[WorldModelCandidate]) -> None:
    if not models:
        return
    scores = [model.score() for model in models]
    peak = max(scores)
    weights = [math.exp(score - peak) for score in scores]
    total = sum(weights)
    for model, weight in zip(models, weights):
        model.posterior = weight / total


def model_disagreement(predictions: list[tuple[float, Any]]) -> float:
    groups: dict[str, float] = {}
    for posterior, outcome in predictions:
        key = stable_hash(outcome)
        groups[key] = groups.get(key, 0.0) + posterior
    return -sum(weight * math.log(weight + 1e-12) for weight in groups.values())


@dataclass
class PlanStep:
    action: dict[str, Any]
    expected_key: str


def search_model_plan(candidate: WorldModelCandidate, observation: StructuredObservation, max_depth: int = 10, max_expansions: int = 512, deadline: float | None = None) -> list[PlanStep]:
    deadline = deadline or time.monotonic() + 1.0
    parsed = sandbox_call(candidate.code, "parse_state", [observation.compact()])
    if not parsed["ok"]:
        return []
    queue = deque([(parsed["value"], [])])
    visited: set[str] = set()
    expansions = 0
    while queue and expansions < max_expansions and time.monotonic() < deadline:
        state, path = queue.popleft()
        key_result = sandbox_call(candidate.code, "state_key", [state])
        key = str(key_result.get("value", stable_hash(state)))
        if key in visited:
            continue
        visited.add(key)
        goal = sandbox_call(candidate.code, "is_goal", [state])
        if goal.get("ok") and goal["value"]:
            return path
        if len(path) >= max_depth:
            continue
        legal = sandbox_call(candidate.code, "legal_model_actions", [state, observation.legal_actions])
        for action in legal.get("value", [])[:32] if legal.get("ok") else []:
            predicted = sandbox_call(candidate.code, "predict", [state, action])
            if predicted.get("ok"):
                next_key = sandbox_call(candidate.code, "state_key", [predicted["value"]]).get("value", stable_hash(predicted["value"]))
                queue.append((predicted["value"], path + [PlanStep(action, str(next_key))]))
        expansions += 1
    return []


class LocalVLLMClient:
    def __init__(self, port: int = 1234, model: str = "vrfai/Qwen3.6-27B-FP8", timeout: float = 45.0, max_calls: int = 12, max_tokens: int = 32768):
        self.url = "http://127.0.0.1:" + str(port) + "/v1/chat/completions"
        self.model = model
        self.timeout = timeout
        self.max_calls = max_calls
        self.max_tokens = max_tokens
        self.calls = 0
        self.tokens = 0

    def reset_game(self) -> None:
        self.calls = 0
        self.tokens = 0

    def health(self) -> bool:
        try:
            with urllib.request.urlopen(self.url.rsplit("/v1/", 1)[0] + "/health", timeout=2) as response:
                return response.status == 200
        except Exception:
            return False

    def complete(self, messages: list[dict[str, str]], max_tokens: int, temperature: float, deadline: float) -> str | None:
        if self.calls >= self.max_calls or self.tokens + max_tokens > self.max_tokens or time.monotonic() >= deadline:
            return None
        request = urllib.request.Request(self.url, data=json.dumps({"model": self.model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}).encode(), headers={"Content-Type": "application/json"})
        try:
            timeout = min(self.timeout, max(0.1, deadline - time.monotonic()))
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.load(response)
            self.calls += 1
            self.tokens += int(payload.get("usage", {}).get("completion_tokens", max_tokens))
            return payload["choices"][0]["message"]["content"]
        except Exception:
            return None


class AxiomScientistController:
    def __init__(self, llm: LocalVLLMClient | None = None, prompts: dict[str, str] | None = None, max_models: int = 4):
        self.llm = llm
        self.prompts = prompts or {}
        self.max_models = max_models
        self.history: list[tuple[StructuredObservation, dict[str, Any], StructuredObservation]] = []
        self.observations: list[StructuredObservation] = []
        self.models: list[WorldModelCandidate] = []
        self.ontologies = [Ontology("four_connected"), Ontology("eight_connected", diagonal=True), Ontology("value_groups", disconnected_by_value=True)]
        self.tried: dict[tuple[str, str], int] = {}
        self.plan: deque[PlanStep] = deque()
        self.expected_next_key: str | None = None
        self.last_action: dict[str, Any] | None = None
        self.mismatches = 0
        self.fallbacks = 0
        self.v2_fallback = V2Fallback()
        self.last_llm_transition = -1
        self.scientist_notes: list[dict[str, str]] = []
        self.critic_notes: list[dict[str, str]] = []

    def _extract_codes(self, text: str | None) -> list[str]:
        if not text:
            return []
        if "```python" in text:
            return [chunk.split("```", 1)[0].strip() for chunk in text.split("```python")[1:] if "```" in chunk]
        try:
            payload = json.loads(text)
            if isinstance(payload, dict) and isinstance(payload.get("models"), list):
                return [item["code"] for item in payload["models"] if isinstance(item, dict) and isinstance(item.get("code"), str)]
            return [payload["code"]] if isinstance(payload, dict) and isinstance(payload.get("code"), str) else []
        except (json.JSONDecodeError, AttributeError):
            return []

    def consult_scientist(self, observation: StructuredObservation, deadline: float, repair: bool = False) -> bool:
        if not self.llm or time.monotonic() >= deadline:
            return False
        counterexamples = [model.counterexample.__dict__ for model in self.models if model.counterexample]
        system = self.prompts.get("world_model_system", "Return one GeneratedWorldModel in a python fenced block. Use only evidence.")
        task_key = "world_model_repair" if repair else "world_model_generate"
        task = self.prompts.get(task_key, "Propose a deterministic executable world model satisfying the required contract.")
        evidence = {"observation": observation.compact(), "history": [{"before": a.compact(), "action": b, "after": c.compact()} for a, b, c in self.history[-12:]], "counterexamples": counterexamples}
        response = self.llm.complete([{"role": "system", "content": system}, {"role": "user", "content": task + "\nEVIDENCE=" + json.dumps(evidence, separators=(",", ":"))}], 4096, 0.15 if repair else 0.45, deadline)
        self.scientist_notes = (self.scientist_notes + [{"transition": str(observation.transition_id), "summary": (response or "request failed")[:800]}])[-12:]
        codes = self._extract_codes(response)
        accepted = 0
        for index, code in enumerate(codes[:3 if not repair else 1]):
            accepted += self.add_model(f"scientist_{self.llm.calls}_{index}", code, min(range(len(self.ontologies)), key=lambda item: self.ontologies[item].error))
        if accepted:
            self.last_llm_transition = observation.transition_id
            return True
        return False

    def consult_critic(self, observation: StructuredObservation, deadline: float) -> dict[str, Any] | None:
        if not self.llm or len(self.models) < 2 or time.monotonic() >= deadline:
            return None
        evidence = {"transition_id": observation.transition_id, "legal_actions": observation.legal_actions, "models": [{"name": model.name, "posterior": model.posterior, "accuracy": model.replay_accuracy, "counterexample": model.counterexample.__dict__ if model.counterexample else None} for model in self.models]}
        response = self.llm.complete([{"role": "system", "content": self.prompts.get("critic_system", "Return strict JSON falsification advice.")}, {"role": "user", "content": self.prompts.get("falsify", "Propose a safe distinguishing experiment.") + "\nEVIDENCE=" + json.dumps(evidence, separators=(",", ":"))}], 2048, 0.0, deadline)
        self.critic_notes = (self.critic_notes + [{"transition": str(observation.transition_id), "summary": (response or "request failed")[:800]}])[-12:]
        try:
            return json.loads(response) if response else None
        except json.JSONDecodeError:
            return None

    def structure(self, grid: Grid, legal: list[dict[str, Any]], terminal: str = "active") -> StructuredObservation:
        current_components = components(grid)
        previous = self.observations[-1] if self.observations else None
        mapping = correspond(previous.components, current_components) if previous else {}
        current_ids = {item["id"] for item in current_components}
        return StructuredObservation(len(self.observations), grid, legal, current_components, changed_cells(previous.grid, grid) if previous else [], mapping, sorted(current_ids - set(mapping.values())), sorted({item["id"] for item in previous.components} - set(mapping)) if previous else [], [pair[1] for pair in self.history[-8:]], terminal)

    def observe(self, grid: Grid, legal: list[dict[str, Any]], terminal: str = "active") -> StructuredObservation:
        observation = self.structure(grid, legal, terminal)
        if self.observations and self.last_action:
            self.history.append((self.observations[-1], self.last_action, observation))
            for ontology in self.ontologies:
                ontology.error = ontology_error(ontology, self.observations[-1], observation)
            for model in self.models:
                verify_replay(model, self.history)
            normalize_models(self.models)
            if self.expected_next_key and stable_hash(observation.grid) != self.expected_next_key:
                self.plan.clear()
                self.mismatches += 1
        self.observations.append(observation)
        return observation

    def add_model(self, name: str, code: str, ontology_index: int = 0) -> bool:
        valid, _ = validate_model_code(code)
        if not valid:
            return False
        candidate = WorldModelCandidate(name, code, self.ontologies[min(ontology_index, len(self.ontologies) - 1)])
        verify_replay(candidate, self.history)
        self.models.append(candidate)
        unique: dict[str, WorldModelCandidate] = {}
        for model in sorted(self.models, key=lambda item: item.score(), reverse=True):
            unique.setdefault(stable_hash(ast.dump(ast.parse(model.code))), model)
        self.models = list(unique.values())[:self.max_models]
        normalize_models(self.models)
        return True

    def action_predictions(self, observation: StructuredObservation, action: dict[str, Any]) -> list[tuple[float, Any]]:
        outcomes = []
        for model in self.models:
            parsed = sandbox_call(model.code, "parse_state", [observation.compact()])
            predicted = sandbox_call(model.code, "predict", [parsed.get("value"), action]) if parsed["ok"] else {"ok": False}
            reconstructed = sandbox_call(model.code, "reconstruct_grid", [predicted.get("value")]) if predicted.get("ok") else {"ok": False}
            if reconstructed.get("ok"):
                outcomes.append((model.posterior, reconstructed["value"]))
        return outcomes

    def choose(self, observation: StructuredObservation, deadline: float) -> dict[str, Any] | None:
        legal = observation.legal_actions
        if not legal:
            return None
        if not self.models and self.llm and self.llm.calls < 3:
            self.consult_scientist(observation, deadline)
        elif self.mismatches and self.last_llm_transition != observation.transition_id and self.llm:
            self.consult_scientist(observation, deadline, repair=True)
        if self.models and max(model.replay_accuracy for model in self.models) >= 0.95 and not self.plan:
            for model in sorted(self.models, key=lambda item: item.posterior, reverse=True):
                plan = search_model_plan(model, observation, deadline=min(deadline, time.monotonic() + 0.03))
                if plan:
                    self.plan.extend(plan)
                    break
        if len(self.models) > 1 and model_disagreement([(model.posterior, model.counterexample.actual_grid if model.counterexample else model.name) for model in self.models]) > 0.3:
            self.consult_critic(observation, min(deadline, time.monotonic() + 0.02))
        state = stable_hash({"grid": observation.grid, "legal": observation.legal_actions})
        if self.plan:
            step = self.plan.popleft()
            if step.action in legal:
                self.expected_next_key = step.expected_key
                self.last_action = step.action
                return step.action
            self.plan.clear()
        ranked = []
        for action in legal[:64]:
            if time.monotonic() >= deadline:
                break
            predictions = self.action_predictions(observation, action)
            disagreement = model_disagreement(predictions) if predictions else 0.0
            repetition = self.tried.get((state, stable_hash(action)), 0)
            complex_bonus = 0.2 if action.get("data") else 0.0
            value = disagreement + (1.0 if repetition == 0 else 0.0) + complex_bonus - 0.8 * repetition
            ranked.append((value, stable_hash(action), action, predictions))
        if ranked:
            _, _, action, predictions = max(ranked)
        else:
            action, predictions = self.v2_fallback.choose(state, legal) or legal[0], []
            self.fallbacks += 1
        self.tried[(state, stable_hash(action))] = self.tried.get((state, stable_hash(action)), 0) + 1
        self.last_action = action
        if predictions:
            self.expected_next_key = stable_hash(as_grid(predictions[0][1]))
        return action
