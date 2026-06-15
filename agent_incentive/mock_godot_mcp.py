"""
In-memory mock of a Godot MCP server.

Simulates a buildable, runnable, playable Godot project so the whole AgentInko
pipeline (build -> Tier 1 verify -> Tier 2 playtest) runs end-to-end in the
sandbox with no engine installed. The mock models the "Inko Coin Dash" loop:
a player must move right to reach a coin within a time budget.

Use it as the `call_tool` transport for GodotMCPClient:

    mock = MockGodotMCP()
    client = GodotMCPClient(mock.call_tool)

Construct with `fault="parse_error"` to simulate a broken build, or tune
`coin_x`, `player_x`, `speed`, `time_budget` to change difficulty.
"""

from __future__ import annotations

import random


class MockGodotMCP:
    def __init__(self, fault: str | None = None, coin_x: float = 380.0,
                 player_x: float = 100.0, speed: float = 220.0,
                 time_budget: float = 2.0, softlock_zone: tuple | None = None,
                 seed: int | None = None) -> None:
        self.fault = fault
        self.coin_x = coin_x
        self.player_x = player_x
        self.speed = speed
        self.time_budget = time_budget
        # softlock_zone = (lo, hi): if the player lands in [lo,hi] they get stuck.
        self.softlock_zone = softlock_zone
        self._rng = random.Random(seed)
        self._scripts: dict[str, str] = {}

    # The single entry point GodotMCPClient calls.
    def call_tool(self, name: str, args: dict) -> dict:
        handler = getattr(self, f"_tool_{name}", None)
        if handler is None:
            return {"error": f"unknown tool '{name}'"}
        return handler(args)

    # --- authoring ------------------------------------------------------ #
    def _tool_scaffold_project(self, args: dict) -> dict:
        return {"ok": True, "path": args["path"]}

    def _tool_write_script(self, args: dict) -> dict:
        self._scripts[args["res_path"]] = args["code"]
        return {"ok": True, "res_path": args["res_path"]}

    def _tool_write_scene(self, args: dict) -> dict:
        return {"ok": True, "res_path": args["res_path"]}

    # --- running -------------------------------------------------------- #
    def _tool_run_headless(self, args: dict) -> dict:
        if self.fault == "parse_error":
            return {"exit_code": 1, "output": (
                "Godot Engine v4.3.stable.official\n"
                'SCRIPT ERROR: Parse Error: Identifier "_playr" not declared.\n'
                'ERROR: Failed to load script "res://scripts/main.gd".\n')}
        if self.fault == "crash":
            return {"exit_code": 139, "output": (
                "[INKO] game_ready scene=Main headless=true\n"
                "ERROR: Attempt to call function on a null instance.\n")}
        # healthy headless run auto-drives to the coin and exits cleanly
        return {"exit_code": 0, "output": (
            "Godot Engine v4.3.stable.official\n"
            "[INKO] game_ready scene=Main headless=true\n"
            "[INKO] coin_collected t=1.27\n"
            "[INKO] playtest_done collected=true frames_ok=true\n")}

    def _tool_read_errors(self, args: dict) -> dict:
        if self.fault == "parse_error":
            return {"errors": ['Parse Error: Identifier "_playr" not declared.']}
        if self.fault == "crash":
            return {"errors": ["Attempt to call function on a null instance."]}
        return {"errors": []}

    def _tool_capture_screenshot(self, args: dict) -> dict:
        return {"png_path": f"/tmp/inko_{args.get('label','frame')}.png"}

    # --- playing: resolve an input sequence into a session outcome ------- #
    def _tool_send_input(self, args: dict) -> dict:
        if self.fault in ("parse_error", "crash"):
            return {"output": "game did not start", "result": {
                "completed": False, "time_s": 0.0, "deaths": 0, "softlock": False}}

        x = self.player_x
        t = 0.0
        dt = 1.0 / 60.0
        softlock = False
        for step in args["input_sequence"]:
            # step: {"dir": -1|0|1, "frames": int}
            direction = float(step.get("dir", 0))
            for _ in range(int(step.get("frames", 0))):
                x += direction * self.speed * dt
                x = max(0.0, min(480.0, x))
                t += dt
                if self.softlock_zone and self.softlock_zone[0] <= x <= self.softlock_zone[1]:
                    softlock = True
                    break
                if abs(x - self.coin_x) < 16.0:
                    return {"output": f"[INKO] result completed=true time={t:.2f}",
                            "result": {"completed": True, "time_s": round(t, 2),
                                       "deaths": 0, "softlock": False}}
                if t >= self.time_budget:
                    break
            if softlock or t >= self.time_budget:
                break
        return {"output": f"[INKO] result completed=false time={t:.2f}",
                "result": {"completed": False, "time_s": round(t, 2),
                           "deaths": 0, "softlock": softlock}}
