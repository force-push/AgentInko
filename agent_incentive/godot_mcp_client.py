"""
Godot MCP client — AgentInko's adapter over a Godot MCP server.

The real execution surface is an installed Godot MCP server (e.g. GDAI MCP or
godot-mcp), which exposes tools for scene/script editing, running the game
headless, capturing screenshots, reading errors, and sending input. This class
wraps those tools behind stable method names so the rest of AgentInko doesn't
care which server is connected.

Transport is INJECTED: pass `call_tool(name, args) -> dict`. In production that
dispatches to the connected MCP server; in tests it dispatches to the in-memory
mock (mock_godot_mcp.MockGodotMCP). This keeps the whole pipeline runnable and
testable without a live engine.
"""

from __future__ import annotations

from typing import Callable


class GodotMCPClient:
    def __init__(self, call_tool: Callable[[str, dict], dict]) -> None:
        self._call = call_tool

    # --- project / asset authoring -------------------------------------- #
    def scaffold_project(self, name: str, path: str) -> dict:
        return self._call("scaffold_project", {"name": name, "path": path})

    def write_script(self, project_path: str, res_path: str, code: str) -> dict:
        return self._call("write_script",
                          {"project_path": project_path, "res_path": res_path,
                           "code": code})

    def write_scene(self, project_path: str, res_path: str, tscn: str) -> dict:
        return self._call("write_scene",
                          {"project_path": project_path, "res_path": res_path,
                           "tscn": tscn})

    # --- running / inspecting ------------------------------------------- #
    def run_headless(self, project_path: str, max_seconds: float = 5.0) -> dict:
        """Run the game headless. Returns {'output': str, 'exit_code': int}."""
        return self._call("run_headless",
                          {"project_path": project_path, "max_seconds": max_seconds})

    def read_errors(self, project_path: str) -> dict:
        """Returns {'errors': [str, ...]}."""
        return self._call("read_errors", {"project_path": project_path})

    def capture_screenshot(self, project_path: str, label: str = "") -> dict:
        """Returns {'png_path': str}."""
        return self._call("capture_screenshot",
                          {"project_path": project_path, "label": label})

    # --- driving the running game (used by the playtest agent) ----------- #
    def send_input(self, project_path: str, input_sequence: list[dict]) -> dict:
        """Send a batched input sequence to a running game and read the result.
        Returns {'output': str, 'result': {...}} where result holds runtime
        markers the game emitted (completed, time_s, deaths, softlock)."""
        return self._call("send_input",
                          {"project_path": project_path,
                           "input_sequence": input_sequence})
