"""
Model gateway — the OpenClaw-style model-agnostic router for AgentInko.

Routes each task type to a model (Claude for design/ideation, Kimi for
high-volume build/codegen — see ../godot-agentinko-guidance.md), and tracks
per-call cost so model spend can be charged against the agent's earned budget
in the Treasury. A cheaper build model => wider earned margin for the agent.

Routing is per-skill and fully configurable; nothing is hardcoded to a vendor.
Actual model invocation is INJECTED (`invoke`) so this layer stays testable and
key-free: in production wire `invoke` to the real Claude/Kimi APIs; in tests,
pass a fake.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModelSpec:
    name: str
    input_per_mtok: float     # USD per 1M input tokens
    output_per_mtok: float    # USD per 1M output tokens


@dataclass
class ModelResponse:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


# Prices reflect mid-2026 public rates (see guidance doc sources); edit freely.
DEFAULT_MODELS = {
    "claude": ModelSpec("claude-opus-4-8", 5.00, 25.00),
    "kimi": ModelSpec("kimi-k2.6", 0.60, 2.50),
}

# Claude owns reasoning/design; Kimi owns mechanical, high-volume codegen.
DEFAULT_ROUTES = {
    "ideate": "claude",
    "storyboard": "claude",
    "design_review": "claude",
    "interpret_playtest": "claude",
    "build_script": "kimi",
    "fix_bug": "kimi",
}


class ModelGateway:
    def __init__(self, invoke, routes: dict | None = None,
                 models: dict | None = None) -> None:
        # invoke(spec: ModelSpec, prompt: str) -> (text, in_tokens, out_tokens)
        self._invoke = invoke
        self._routes = {**DEFAULT_ROUTES, **(routes or {})}
        self._models = {**DEFAULT_MODELS, **(models or {})}
        self.total_cost_usd = 0.0
        self.calls: list[tuple[str, ModelResponse]] = []

    def model_for(self, task_type: str) -> ModelSpec:
        key = self._routes.get(task_type)
        if key is None:
            raise KeyError(f"No model route configured for task '{task_type}'.")
        if key not in self._models:
            raise KeyError(f"Route '{task_type}' -> unknown model '{key}'.")
        return self._models[key]

    def run(self, task_type: str, prompt: str) -> ModelResponse:
        spec = self.model_for(task_type)
        text, in_tok, out_tok = self._invoke(spec, prompt)
        cost = (in_tok / 1e6) * spec.input_per_mtok + \
               (out_tok / 1e6) * spec.output_per_mtok
        resp = ModelResponse(text, spec.name, in_tok, out_tok, cost)
        self.total_cost_usd += cost
        self.calls.append((task_type, resp))
        return resp

    def cost_by_model(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for _, r in self.calls:
            out[r.model] = out.get(r.model, 0.0) + r.cost_usd
        return out
