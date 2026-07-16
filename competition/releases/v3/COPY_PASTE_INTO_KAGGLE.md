# Axiom Scientist V3 — copy into Kaggle

## Cell 0
Keep Kaggle's generic setup cell unchanged.

## Cell 1 — Offline installation

```python
!pip install --no-index --find-links /kaggle/input/arc3-vllm-h100-wheelhouse-v3 --find-links /kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels arc-agi python-dotenv vllm
```

## Cell 2 — Start offline local model

```python
import atexit, json, os, subprocess, time, urllib.request
from pathlib import Path
os.environ.update({"HF_HUB_OFFLINE":"1", "TRANSFORMERS_OFFLINE":"1", "DO_NOT_TRACK":"1", "VLLM_NO_USAGE_STATS":"1", "AXIOM_V3_LLM":"0"})
GLOBAL_DEADLINE = time.monotonic() + 9 * 60 * 60
MODEL_NAME = "vrfai/Qwen3.6-27B-FP8"
MODEL_ROOT = Path("/kaggle/input/vrfai-qwen3-6-27b-fp8-hf-snapshot")
MODEL_PATH = next((p for p in MODEL_ROOT.rglob("config.json")), None)
VLLM_PROCESS = None
def stop_vllm():
    global VLLM_PROCESS
    if VLLM_PROCESS and VLLM_PROCESS.poll() is None:
        VLLM_PROCESS.terminate()
        try: VLLM_PROCESS.wait(timeout=30)
        except subprocess.TimeoutExpired: VLLM_PROCESS.kill()
atexit.register(stop_vllm)
if MODEL_PATH:
    command = ["python", "-m", "vllm.entrypoints.openai.api_server", "--model", str(MODEL_PATH.parent), "--served-model-name", MODEL_NAME, "--host", "127.0.0.1", "--port", "1234", "--enable-prefix-caching", "--disable-log-stats", "--max-model-len", "16384", "--gpu-memory-utilization", "0.90"]
    VLLM_PROCESS = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    ready_by = min(GLOBAL_DEADLINE - 2400, time.monotonic() + 900)
    while time.monotonic() < ready_by and VLLM_PROCESS.poll() is None:
        try:
            with urllib.request.urlopen("http://127.0.0.1:1234/health", timeout=2) as response:
                if response.status == 200: break
        except Exception: time.sleep(5)
    try:
        payload = json.dumps({"model":MODEL_NAME,"messages":[{"role":"user","content":"Reply exactly AXIOM_V3_READY"}],"max_tokens":16,"temperature":0}).encode()
        request = urllib.request.Request("http://127.0.0.1:1234/v1/chat/completions", data=payload, headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(request, timeout=60) as response: smoke = json.load(response)
        if "AXIOM_V3_READY" in smoke["choices"][0]["message"]["content"]: os.environ["AXIOM_V3_LLM"] = "1"
    except Exception: stop_vllm()
print("Axiom V3 model mode:", os.environ["AXIOM_V3_LLM"])
```

## Cell 3 — Write complete V3 agent

```python
%%writefile /tmp/my_agent.py
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

"""V2-compatible deterministic fallback, copied into V3 without importing frozen artifacts."""

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

EMBEDDED_PROMPTS = {'critic_system': 'You are the Falsification Critic. You cannot act. Return strict JSON. Challenge hidden assumptions, overfitting, ontology errors, and unsupported goals using transition IDs.\n', 'falsify': 'Return {"assumptions":[],"counterexamples":[],"experiments":[{"action":{},"distinguishes_models":[],"predicted_outcomes":[],"risk":0.0,"reversibility":0.0,"evidence_transition_ids":[]}],"ranking":[]}. Choose the smallest safe legal experiment.\n', 'goal_induction': 'Return {"goals":[{"goal_name":"...","success_predicate":"...","progress_measure":"...","supporting_evidence":[],"contradicting_evidence":[],"confidence":0.0}]}. Predicates must be executable by the candidate model and evidence must cite transition IDs.\n', 'ontology_system': 'You are the Ontologist. Return strict JSON only. Propose competing segmentations, roles, latent variables, and explicitly list unexplained evidence by transition_id. Never infer from game names or fixed colors.\n', 'ontology_update': 'Given exact grid RLE, components, correspondences, changed cells, and residuals, return {"ontologies": [{"name":"...","assumptions":[],"roles":{},"latent_state":{},"explains_transition_ids":[],"unexplained_transition_ids":[],"confidence":0.0}]}. Prefer revising ontology over coordinate exceptions.\n', 'plan': 'Return {"model_names":[],"goal_name":"...","plan":[{"action":{},"expected_state_key":"..."}],"risk":0.0,"assumptions":[],"verified":false}. Use only verified models and legal actions; simulate every step.\n', 'recover_after_timeout': 'Return strict JSON with a compact evidence summary and one deterministic safe legal action ranked by novelty, reversibility, and low terminal risk. Do not invent model claims.\n', 'refactor_between_levels': 'Return a simpler reusable GeneratedWorldModel preserving replay on all completed levels. Remove coordinates and visual-instance details; retain only verified action semantics, mechanics, roles, and goal grammar.\n', 'world_model_generate': 'Generate three diverse compact executable models: the simplest model, the most accurate model, and an alternate-ontology falsification model. State explicit assumptions, general transition rules, predicted outcomes, confidence, and evidence transition IDs. Return three separate ```python fenced blocks.\n', 'world_model_repair': 'Repair the candidate against the supplied smallest counterexample while preserving every earlier replay. Do not add coordinate-specific exceptions or memorize frames. Return only the complete replacement class in a ```python fenced block.\n', 'world_model_system': 'You are the World-Model Scientist. Output one deterministic Python class GeneratedWorldModel implementing parse_state, predict, reconstruct_grid, candidate_goals, goal_score, is_goal, state_key, legal_model_actions. Use only allowed imports. No I/O, networking, eval, exec, dynamic imports, framework inspection, game identifiers, or hard-coded frames. Cite transition IDs in explanation.\n'}

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
```

## Cell 4 — Official V2-proven competition harness

```python
import os, shutil, subprocess, time
from pathlib import Path
os.environ["MPLBACKEND"] = "agg"
TRUE_SUBMISSION = bool(os.getenv("KAGGLE_IS_COMPETITION_RERUN"))
ROOT = Path("/kaggle/input/competitions/arc-prize-2026-arc-agi-3")
WORK = Path("/kaggle/working")
GATEWAY = "http://gateway:8001/api/games"
def wait_for_gateway(timeout_seconds=600):
    deadline = min(time.monotonic() + timeout_seconds, GLOBAL_DEADLINE - 2400)
    while time.monotonic() < deadline:
        if subprocess.call(["curl", "--fail", "--silent", "--show-error", GATEWAY]) == 0: return
        time.sleep(5)
    raise TimeoutError("Local competition gateway did not become ready")
if TRUE_SUBMISSION:
    source, destination = ROOT / "ARC-AGI-3-Agents", WORK / "ARC-AGI-3-Agents"
    wait_for_gateway()
    if destination.exists(): shutil.rmtree(destination)
    shutil.copytree(source, destination)
    template = destination / "agents" / "templates"
    template.mkdir(parents=True, exist_ok=True)
    shutil.copyfile("/tmp/my_agent.py", template / "my_agent.py")
    (destination / "agents" / "__init__.py").write_text("from typing import Type\nfrom dotenv import load_dotenv\nfrom .agent import Agent, Playback\nfrom .swarm import Swarm\nfrom .templates.random_agent import Random\nfrom .templates.my_agent import MyAgent\nload_dotenv()\nAVAILABLE_AGENTS: dict[str, Type[Agent]] = {'random': Random, 'myagent': MyAgent}\n")
    (destination / ".env").write_text("SCHEME=http\nHOST=gateway\nPORT=8001\nARC_API_KEY=test-key-123\nARC_BASE_URL=http://gateway:8001/\nOPERATION_MODE=online\nENVIRONMENTS_DIR=\nRECORDINGS_DIR=/kaggle/working/server_recording\n")
    try: subprocess.check_call(["python", "main.py", "--agent", "myagent"], cwd=str(destination), timeout=max(1, GLOBAL_DEADLINE - time.monotonic() - 2400))
    finally: stop_vllm()
else:
    import pandas as pd
    pd.DataFrame([["1_0", "1", True, 1]], columns=["row_id", "game_id", "end_of_game", "score"]).to_parquet(WORK / "submission.parquet", index=False)
    stop_vllm()
```
