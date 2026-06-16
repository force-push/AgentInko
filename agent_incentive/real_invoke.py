"""
real_invoke.py — Production model invoke function for AgentInko.

DESIGN_BACKEND controls where "claude"-routed tasks go:
  kimi        → all calls go to Kimi K2.6 (default; use when API credits are low)
  claude-cli  → Claude via `claude` CLI subprocess (uses Pro plan quota, no API credits)
  claude-api  → Claude Anthropic API directly (requires ANTHROPIC_API_KEY with credits)

Codegen tasks always go to Kimi K2.6 via NVIDIA API.

Usage:
    from real_invoke import make_invoke, design_models_override
    invoke = make_invoke()
    # Optionally pass design_models_override() to ModelGateway to fix cost tracking:
    gateway = ModelGateway(invoke, models=design_models_override())
"""

import os
import subprocess
from pathlib import Path
from openai import OpenAI

# Auto-load .env from project root (two levels up from agent_incentive/)
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=str(_env_path))
    except ImportError:
        pass

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
NVIDIA_API_KEY    = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL   = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
DESIGN_BACKEND    = os.getenv("DESIGN_BACKEND", "kimi").lower()  # kimi | claude-cli | claude-api

CLAUDE_MODELS = {"claude", "anthropic", "haiku", "sonnet", "opus"}


def _is_claude_spec(model_name: str) -> bool:
    return any(k in model_name.lower() for k in CLAUDE_MODELS)


def invoke_anthropic(model: str, prompt: str) -> tuple[str, int, int]:
    """Call Anthropic API directly (requires credits)."""
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    model_map = {"haiku": "claude-haiku-4-5", "sonnet": "claude-sonnet-4-6", "opus": "claude-opus-4-8"}
    if "claude" in model:
        model_id = model
    else:
        model_id = next((v for k, v in model_map.items() if k in model), "claude-haiku-4-5")
    msg = client.messages.create(
        model=model_id, max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text if msg.content else ""
    return text, msg.usage.input_tokens, msg.usage.output_tokens


def invoke_claude_cli(model: str, prompt: str) -> tuple[str, int, int]:
    """Call Claude via the `claude` CLI subprocess (uses Pro plan quota, not API credits)."""
    model_map = {"haiku": "claude-haiku-4-5", "sonnet": "claude-sonnet-4-6", "opus": "claude-opus-4-8"}
    if "claude" in model:
        model_id = model
    else:
        model_id = next((v for k, v in model_map.items() if k in model.lower()), "claude-haiku-4-5")
    result = subprocess.run(
        ["claude", "-p", prompt, "--model", model_id],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI failed (exit {result.returncode}): {result.stderr[:400]}")
    text = result.stdout.strip()
    # CLI doesn't return token counts; estimate from char length
    in_tok = max(1, len(prompt) // 4)
    out_tok = max(1, len(text) // 4)
    return text, in_tok, out_tok


def invoke_nvidia(model: str, prompt: str) -> tuple[str, int, int]:
    """Call NVIDIA NIM API (OpenAI-compatible) for Kimi K2.6."""
    client = OpenAI(api_key=NVIDIA_API_KEY, base_url=NVIDIA_BASE_URL)
    model_id = "moonshotai/kimi-k2.6" if "kimi" in model.lower() else model
    completion = client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=8192,
        temperature=0.6,
    )
    text = completion.choices[0].message.content or ""
    usage = completion.usage
    return text, usage.prompt_tokens, usage.completion_tokens


def make_invoke():
    """
    Return the unified invoke(spec, prompt) function for ModelGateway.

    Routing based on DESIGN_BACKEND env var:
      kimi        → all calls to Kimi (no Anthropic key needed)
      claude-cli  → Claude specs → `claude` CLI; Kimi specs → NVIDIA
      claude-api  → Claude specs → Anthropic API; Kimi specs → NVIDIA
    """
    if not NVIDIA_API_KEY:
        raise RuntimeError("NVIDIA_API_KEY not set — check .env")
    if DESIGN_BACKEND == "claude-api" and not ANTHROPIC_API_KEY:
        raise RuntimeError("DESIGN_BACKEND=claude-api but ANTHROPIC_API_KEY not set")

    def invoke(spec, prompt: str) -> tuple[str, int, int]:
        model_name = spec.name if hasattr(spec, "name") else str(spec)
        is_claude = _is_claude_spec(model_name)
        if is_claude and DESIGN_BACKEND == "claude-api":
            return invoke_anthropic(model_name, prompt)
        elif is_claude and DESIGN_BACKEND == "claude-cli":
            return invoke_claude_cli(model_name, prompt)
        else:
            # kimi mode, or any non-claude spec
            return invoke_nvidia(model_name, prompt)

    return invoke


def design_models_override() -> dict:
    """
    When DESIGN_BACKEND is kimi or claude-cli, return a models dict that
    replaces the 'claude' entry with accurate Kimi pricing so cost tracking
    reflects what's actually being spent. Pass to ModelGateway(models=...).
    """
    from model_gateway import ModelSpec
    if DESIGN_BACKEND in ("kimi", "claude-cli"):
        # Kimi K2.6 pricing (mid-2026 NVIDIA NIM rates)
        return {"claude": ModelSpec("kimi-k2.6", 0.60, 2.50)}
    return {}


if __name__ == "__main__":
    print(f"DESIGN_BACKEND = {DESIGN_BACKEND}")

    if DESIGN_BACKEND == "kimi":
        print("Testing Kimi for design (DESIGN_BACKEND=kimi)...")
        text, inp, out = invoke_nvidia("moonshotai/kimi-k2.6", "Reply with exactly: DESIGN_OK")
        print(f"  design → {text.strip()!r}  ({inp} in / {out} out tokens)")
    elif DESIGN_BACKEND == "claude-cli":
        print("Testing Claude CLI for design (DESIGN_BACKEND=claude-cli)...")
        text, inp, out = invoke_claude_cli("claude-haiku-4-5", "Reply with exactly: CLAUDE_CLI_OK")
        print(f"  design → {text.strip()!r}  (~{inp} in / ~{out} out tokens)")
    else:
        print("Testing Anthropic API for design (DESIGN_BACKEND=claude-api)...")
        text, inp, out = invoke_anthropic("claude-haiku-4-5", "Reply with exactly: CLAUDE_API_OK")
        print(f"  design → {text.strip()!r}  ({inp} in / {out} out tokens)")

    print("Testing Kimi for codegen...")
    text, inp, out = invoke_nvidia("moonshotai/kimi-k2.6", "Reply with exactly: KIMI_OK")
    print(f"  codegen → {text.strip()!r}  ({inp} in / {out} out tokens)")

    print("\nBackend check OK ✓")
