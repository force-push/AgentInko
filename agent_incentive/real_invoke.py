"""
real_invoke.py — Production model invoke function for AgentInko.

Routes:
  - design tasks (Claude) → Anthropic API (claude-haiku-4-5 for speed, sonnet for quality)
  - codegen tasks (Kimi) → NVIDIA API (kimi-k2.6)

Usage:
    from real_invoke import make_invoke
    gateway = ModelGateway(make_invoke())

The returned function matches the signature expected by ModelGateway:
    invoke(spec: ModelSpec, prompt: str) -> tuple[str, int, int]
Returns (text, input_tokens, output_tokens).
"""

import os
from pathlib import Path
import anthropic
from openai import OpenAI

# Auto-load .env from project root (two levels up from agent_incentive/)
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=str(_env_path))
    except ImportError:
        pass  # dotenv optional; keys can be set in env directly

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
NVIDIA_API_KEY    = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL   = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")

# Which model names route to which backend
CLAUDE_MODELS = {"claude", "anthropic", "haiku", "sonnet", "opus"}
KIMI_MODELS   = {"kimi", "nvidia", "moonshotai"}


def _is_claude(model_name: str) -> bool:
    return any(k in model_name.lower() for k in CLAUDE_MODELS)


def invoke_anthropic(model: str, prompt: str) -> tuple[str, int, int]:
    """Call Anthropic API directly."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    # Map shorthand names to real model IDs
    # Model ID mapping
    model_map = {
        "haiku": "claude-haiku-4-5",
        "sonnet": "claude-sonnet-4-5",
        "opus":   "claude-opus-4-5",
    }
    if "claude" in model:
        model_id = model
    else:
        model_id = next((v for k, v in model_map.items() if k in model), "claude-haiku-4-5")
    msg = client.messages.create(
        model=model_id,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text if msg.content else ""
    return text, msg.usage.input_tokens, msg.usage.output_tokens


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
    choice = completion.choices[0]
    text = choice.message.content or ""
    usage = completion.usage
    return text, usage.prompt_tokens, usage.completion_tokens


def make_invoke():
    """
    Return the real invoke function to inject into ModelGateway.

    Routing logic:
      spec.model contains "claude" / "haiku" / "sonnet" / "opus" → Anthropic
      spec.model contains "kimi" / "nvidia" / "moonshotai"        → NVIDIA/Kimi
    """
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set — check .env")
    if not NVIDIA_API_KEY:
        raise RuntimeError("NVIDIA_API_KEY not set — check .env")

    def invoke(spec, prompt: str) -> tuple[str, int, int]:
        # ModelSpec uses .name (not .model)
        model_name = spec.name if hasattr(spec, 'name') else str(spec)
        if _is_claude(model_name):
            return invoke_anthropic(model_name, prompt)
        else:
            return invoke_nvidia(model_name, prompt)

    return invoke


if __name__ == "__main__":
    # Smoke test both backends
    from dotenv import load_dotenv
    load_dotenv(dotenv_path="./../.env")

    print("Testing Anthropic (Claude Haiku)...")
    text, inp, out = invoke_anthropic("claude-haiku-4-5",
                                      "Reply with exactly: CLAUDE_OK")
    print(f"  → {text.strip()!r}  ({inp} in / {out} out tokens)")

    print("Testing NVIDIA (Kimi K2.6)...")
    text, inp, out = invoke_nvidia("moonshotai/kimi-k2.6",
                                   "Reply with exactly: KIMI_OK")
    print(f"  → {text.strip()!r}  ({inp} in / {out} out tokens)")

    print("\nBoth backends OK ✓")
