"""
AgentSkills — composable game-dev capabilities for AgentInko.

Each skill routes through the ModelGateway (Claude for design, Kimi for build)
and acts on the Godot project through the GodotMCPClient. The storyboard is a
STRUCTURED SPEC (not prose) — the principal-agent handoff contract between the
Claude design step and the Kimi build step.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from model_gateway import ModelGateway
from godot_mcp_client import GodotMCPClient


@dataclass
class Storyboard:
    """The handoff contract from design (Claude) to build (Kimi)."""
    title: str
    genre: str
    goal: str
    mechanics: list[str]
    win_condition: str
    fail_condition: str
    entities: list[dict] = field(default_factory=list)

    def to_spec(self) -> str:
        return json.dumps(self.__dict__, indent=2)


class GameDevSkills:
    def __init__(self, gateway: ModelGateway, mcp: GodotMCPClient) -> None:
        self.gateway = gateway
        self.mcp = mcp

    # --- design (Claude) ------------------------------------------------ #
    def ideate(self, theme: str) -> str:
        prompt = f"Pitch one tightly-scoped 2D game concept on the theme: {theme}."
        return self.gateway.run("ideate", prompt).text.strip()

    def storyboard(self, idea: str) -> Storyboard:
        """Claude turns a loose idea into a structured, buildable spec.
        The injected model is expected to return JSON; we parse defensively."""
        prompt = (f"Turn this idea into a JSON game spec with keys title, genre, "
                  f"goal, mechanics[], win_condition, fail_condition, entities[]: {idea}")
        raw = self.gateway.run("storyboard", prompt).text
        data = json.loads(raw)
        return Storyboard(
            title=data["title"], genre=data["genre"], goal=data["goal"],
            mechanics=data.get("mechanics", []),
            win_condition=data["win_condition"], fail_condition=data["fail_condition"],
            entities=data.get("entities", []),
        )

    # --- build (Kimi) --------------------------------------------------- #
    def build_from_storyboard(self, storyboard: Storyboard, project_path: str) -> dict:
        """Kimi generates GDScript from the spec; we write it via MCP and run it.
        Returns {'output', 'errors', 'script_res'}."""
        prompt = (f"Write Godot 4 GDScript implementing this spec. Print '[INKO]' "
                  f"markers (game_ready, result completed=.. time=..). Spec:\n"
                  f"{storyboard.to_spec()}")
        code = self.gateway.run("build_script", prompt).text
        res_path = "res://scripts/main.gd"
        self.mcp.write_script(project_path, res_path, code)
        run = self.mcp.run_headless(project_path)
        errs = self.mcp.read_errors(project_path)
        return {"output": run.get("output", ""), "errors": errs.get("errors", []),
                "script_res": res_path}

    def fix_bug(self, project_path: str, errors: list[str]) -> dict:
        """Kimi attempts a fix given the error log, then re-runs."""
        prompt = "Fix this Godot script given errors:\n" + "\n".join(errors)
        code = self.gateway.run("fix_bug", prompt).text
        self.mcp.write_script(project_path, "res://scripts/main.gd", code)
        run = self.mcp.run_headless(project_path)
        errs = self.mcp.read_errors(project_path)
        return {"output": run.get("output", ""), "errors": errs.get("errors", [])}
