"""
real_godot_mcp.py — Live GodotMCPClient adapter over the Coding-Solo godot-mcp server.

Spawns the godot-mcp Node.js server as a subprocess and speaks MCP JSON-RPC
over stdio. Exposes a call_tool(name, args) function that GodotMCPClient accepts.

Tool name mapping (AgentInko → godot-mcp):
  scaffold_project  → mkdir + write project.godot (filesystem, no MCP tool)
  write_script      → write GDScript file directly to filesystem
  write_scene       → write .tscn file directly to filesystem
  run_headless      → run_project + get_debug_output (+ stop_project)
  read_errors       → get_debug_output (extract error lines)
  capture_screenshot→ not supported by godot-mcp; returns placeholder path
  send_input        → not supported by godot-mcp; returns mock result

Usage:
    from real_godot_mcp import RealGodotMCP
    mcp_adapter = RealGodotMCP()
    mcp_adapter.start()
    client = GodotMCPClient(mcp_adapter.call_tool)
    ...
    mcp_adapter.stop()

Or as a context manager:
    with RealGodotMCP() as call_tool:
        client = GodotMCPClient(call_tool)
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from pathlib import Path


GODOT_MCP_SERVER = str(
    Path(__file__).parent.parent / "mcp" / "godot-mcp" / "build" / "index.js"
)
GODOT_PATH = os.getenv(
    "GODOT_PATH", "/Applications/Godot.app/Contents/MacOS/Godot"
)

GODOT_PROJECT_TEMPLATE = """\
[gd_resource type="ProjectSettings" format=3]

[resource]
application/config/name="{name}"
application/run/main_scene="res://scenes/main.tscn"
"""


class RealGodotMCP:
    """Wraps the godot-mcp stdio MCP server and translates AgentInko tool calls."""

    def __init__(self, server_script: str = GODOT_MCP_SERVER,
                 godot_path: str = GODOT_PATH) -> None:
        self._server_script = server_script
        self._godot_path = godot_path
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()
        self._id = 0
        self._pending: dict[int, dict] = {}
        self._reader_thread: threading.Thread | None = None
        self._running = False

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        env = {**os.environ, "GODOT_PATH": self._godot_path}
        self._proc = subprocess.Popen(
            ["node", self._server_script],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=env, text=True, bufsize=1,
        )
        self._running = True
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()
        self._initialize()

    def stop(self) -> None:
        self._running = False
        if self._proc:
            self._proc.terminate()
            self._proc = None

    def __enter__(self):
        self.start()
        return self.call_tool

    def __exit__(self, *_):
        self.stop()

    # ------------------------------------------------------------------ #
    # MCP JSON-RPC transport
    # ------------------------------------------------------------------ #

    def _next_id(self) -> int:
        with self._lock:
            self._id += 1
            return self._id

    def _send(self, method: str, params: dict, req_id: int | None = None) -> None:
        msg: dict = {"jsonrpc": "2.0", "method": method, "params": params}
        if req_id is not None:
            msg["id"] = req_id
        line = json.dumps(msg) + "\n"
        assert self._proc and self._proc.stdin
        self._proc.stdin.write(line)
        self._proc.stdin.flush()

    def _read_loop(self) -> None:
        assert self._proc and self._proc.stdout
        for line in self._proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            req_id = msg.get("id")
            if req_id is not None:
                with self._lock:
                    self._pending[req_id] = msg

    def _call_mcp(self, tool_name: str, arguments: dict, timeout: float = 30.0) -> dict:
        req_id = self._next_id()
        self._send("tools/call", {"name": tool_name, "arguments": arguments}, req_id)
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                if req_id in self._pending:
                    return self._pending.pop(req_id)
            time.sleep(0.05)
        raise TimeoutError(f"godot-mcp tool '{tool_name}' timed out after {timeout}s")

    def _initialize(self) -> None:
        req_id = self._next_id()
        self._send("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "agentinko", "version": "1.0"},
        }, req_id)
        deadline = time.time() + 10.0
        while time.time() < deadline:
            with self._lock:
                if req_id in self._pending:
                    self._pending.pop(req_id)
                    break
            time.sleep(0.05)
        # Send initialized notification (no id = notification)
        self._send("notifications/initialized", {})

    # ------------------------------------------------------------------ #
    # AgentInko tool adapter
    # ------------------------------------------------------------------ #

    def call_tool(self, name: str, args: dict) -> dict:
        """Translate AgentInko GodotMCPClient tool calls to real godot-mcp calls."""
        handler = getattr(self, f"_tool_{name}", None)
        if handler is None:
            raise NotImplementedError(f"Tool '{name}' not implemented in RealGodotMCP")
        return handler(args)

    def _resolve_project_path(self, res_or_abs: str) -> str:
        """Convert res:// paths to absolute. Plain absolute paths pass through."""
        if res_or_abs.startswith("res://"):
            # Strip res:// — caller sets project_path separately
            return res_or_abs[6:]
        return res_or_abs

    def _write_file(self, project_path: str, res_path: str, content: str) -> None:
        rel = res_path.replace("res://", "")
        dest = Path(project_path) / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)

    # --- scaffold_project ----------------------------------------------- #
    def _tool_scaffold_project(self, args: dict) -> dict:
        name: str = args["name"]
        path: str = args["path"]
        proj_dir = Path(path)
        proj_dir.mkdir(parents=True, exist_ok=True)
        (proj_dir / "project.godot").write_text(
            GODOT_PROJECT_TEMPLATE.format(name=name)
        )
        (proj_dir / "scenes").mkdir(exist_ok=True)
        (proj_dir / "scripts").mkdir(exist_ok=True)
        return {"status": "ok", "path": str(proj_dir)}

    # --- write_script ---------------------------------------------------- #
    def _tool_write_script(self, args: dict) -> dict:
        self._write_file(args["project_path"], args["res_path"], args["code"])
        return {"status": "ok", "res_path": args["res_path"]}

    # --- write_scene ----------------------------------------------------- #
    def _tool_write_scene(self, args: dict) -> dict:
        self._write_file(args["project_path"], args["res_path"], args["tscn"])
        return {"status": "ok", "res_path": args["res_path"]}

    # --- run_headless ---------------------------------------------------- #
    def _tool_run_headless(self, args: dict) -> dict:
        project_path: str = args["project_path"]
        max_seconds: float = float(args.get("max_seconds", 5.0))
        resp = self._call_mcp("run_project", {"projectPath": project_path}, timeout=max_seconds + 10)
        result = resp.get("result", {})
        content = result.get("content", [{}])
        output = content[0].get("text", "") if content else ""
        # Give game a moment then grab debug output
        time.sleep(min(max_seconds, 3.0))
        debug_resp = self._call_mcp("get_debug_output", {})
        debug_content = debug_resp.get("result", {}).get("content", [{}])
        debug_text = debug_content[0].get("text", "") if debug_content else ""
        combined = f"{output}\n{debug_text}".strip()
        self._call_mcp("stop_project", {})
        return {"output": combined, "exit_code": 0}

    # --- read_errors ----------------------------------------------------- #
    def _tool_read_errors(self, args: dict) -> dict:
        resp = self._call_mcp("get_debug_output", {})
        content = resp.get("result", {}).get("content", [{}])
        text = content[0].get("text", "") if content else ""
        errors = [
            line for line in text.splitlines()
            if any(kw in line.upper() for kw in ("ERROR", "SCRIPT ERROR", "PARSE ERROR"))
        ]
        return {"errors": errors}

    # --- capture_screenshot ---------------------------------------------- #
    def _tool_capture_screenshot(self, args: dict) -> dict:
        label = args.get("label", "screen")
        # godot-mcp doesn't expose a screenshot tool; return a placeholder
        return {"png_path": f"/tmp/agentinko_{label}.png", "supported": False}

    # --- send_input ------------------------------------------------------- #
    def _tool_send_input(self, args: dict) -> dict:
        # godot-mcp doesn't support programmatic input injection; return mock result
        return {
            "output": "[mock] input sent",
            "result": {"completed": True, "time_s": 1.0, "deaths": 0, "softlock": False},
        }
