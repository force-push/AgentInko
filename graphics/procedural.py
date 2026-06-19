"""
procedural.py — AI-driven procedural sprite generator for AgentInko.

Asks Kimi to generate GDScript drawing code for each game entity. This is the
primary autonomous graphics path: no external assets, no downloads, all visuals
are code. The AI literally draws everything using Godot's CanvasItem draw_* API.

Usage:
    from graphics.procedural import ProceduralGraphicsAgent
    agent = ProceduralGraphicsAgent(gateway)
    code = agent.generate_sprite("octopus", {"colors": ["teal", "magenta"]})
    # → GDScript class extending Node2D with a _draw() function
"""

from __future__ import annotations

SPRITE_PROMPTS = {
    "octopus": """
Write a Godot 4.x GDScript class (extends Node2D) called OctopusSprite that draws
a cartoon octopus in _draw(). The octopus should:
- Have a round head (ellipse, ~40x35 px) in a color that can be set via exported var `skin_color`
- Have 8 tentacles (bezier curves or line_to arcs) hanging below
- Have two large eyes (white circle + dark pupil) with a slight cartoon expression
- Have a soft bioluminescent glow effect (draw a larger semi-transparent circle behind the body)
- Support `camouflaged: bool` exported var: when true, reduce opacity to 0.3 and desaturate
- Emit signal `color_changed(new_color: Color)` when skin_color changes

The draw code must work with Godot 4.x draw_* API (draw_circle, draw_arc, draw_line, etc.).
Output ONLY the GDScript code, no markdown fences.
""",

    "seabed_band": """
Write a Godot 4.x GDScript class (extends Node2D) called SeabedBand that draws
a scrolling seabed color band in _draw(). It should:
- Accept exported vars: `band_color: Color`, `band_width: float = 800`, `band_height: float = 120`
- Draw a filled rectangle of band_color
- Draw a subtle texture overlay (random noise lines) to suggest sand/rock texture
- Draw the accessibility symbol in the top-right corner (shape varies by color: circle/triangle/square/diamond/cross)
  - Use exported var `symbol: String` (values: "circle", "triangle", "square", "diamond", "cross")
- The symbol should be white with 80% opacity, ~24px size

Output ONLY the GDScript code, no markdown fences.
""",

    "scan_sweep": """
Write a Godot 4.x GDScript class (extends Node2D) called ScanSweep that draws
a hunter scan sweep effect in _draw(). It should:
- Draw a vertical gradient line (top: bright red, bottom: transparent) spanning `screen_height: float = 600`
- Draw a subtle red glow (semi-transparent rectangle, 40px wide) around the sweep line
- Have exported var `intensity: float` (0.0–1.0) that scales opacity — use for telegraph animation
- Draw small scan pattern dots ahead of the sweep to suggest sensor tendrils

Output ONLY the GDScript code, no markdown fences.
""",

    "ink_pearl": """
Write a Godot 4.x GDScript class (extends Node2D) called InkPearl that draws
a collectible ink pearl in _draw(). It should:
- Draw a sphere-shaded circle (~16px radius): white highlight top-left, gradient to deep blue/purple
- Draw a soft bioluminescent glow ring (semi-transparent circle, 24px radius)
- Animate: exports `pulse_phase: float` — scale glow radius by 1.0 + 0.2 * sin(pulse_phase)
- Draw a small "x points" label below when `show_value: bool` is true and `point_value: int` is set

Output ONLY the GDScript code, no markdown fences.
""",

    "reef": """
Write a Godot 4.x GDScript class (extends Node2D) called ReefGoal that draws
a bioluminescent coral reef goal marker in _draw(). It should:
- Draw 5-7 coral branches (polylines with varied heights: 30–80px) in pink/magenta
- Draw small sea anemone circles at branch tips
- Draw a subtle green/teal bioluminescent glow behind the whole reef
- Have exported var `glow_intensity: float` (0.0–1.0) for the win-state pulse animation
- When `active: bool` is false, draw everything desaturated (greyed-out)

Output ONLY the GDScript code, no markdown fences.
""",
}


class ProceduralGraphicsAgent:
    """Generates GDScript sprite code via the model gateway."""

    def __init__(self, gateway) -> None:
        self._gateway = gateway

    def generate_sprite(self, entity: str, context: dict | None = None) -> str:
        """
        Generate GDScript drawing code for `entity` (must be a key in SPRITE_PROMPTS).
        Returns raw GDScript source code.
        """
        if entity not in SPRITE_PROMPTS:
            raise ValueError(f"No prompt defined for entity '{entity}'. "
                             f"Available: {list(SPRITE_PROMPTS)}")
        prompt = SPRITE_PROMPTS[entity]
        if context:
            extras = "\n".join(f"- {k}: {v}" for k, v in context.items())
            prompt += f"\n\nAdditional context:\n{extras}"
        resp = self._gateway.run("build_script", prompt)
        return resp.text.strip()

    def generate_all(self, output_dir: str) -> dict[str, str]:
        """
        Generate all sprite scripts and write them to output_dir.
        Returns dict mapping entity name to file path.
        """
        import os
        os.makedirs(output_dir, exist_ok=True)
        results = {}
        for entity in SPRITE_PROMPTS:
            print(f"  Generating {entity} sprite...")
            code = self.generate_sprite(entity)
            class_name = _entity_to_class(entity)
            path = os.path.join(output_dir, f"{entity}.gd")
            with open(path, "w") as f:
                f.write(code)
            results[entity] = path
            print(f"    → {path} ({len(code)} chars)")
        return results


def _entity_to_class(entity: str) -> str:
    return "".join(w.capitalize() for w in entity.split("_")) + "Sprite"
