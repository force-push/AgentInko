"""
kenney.py — Kenney CC0 asset pack downloader for AgentInko.

Kenney.nl provides high-quality game assets under CC0 (public domain).
No attribution required. This module downloads and extracts the most
relevant packs for Inko's underwater world.

Relevant packs:
  - Simple Space         (abstract shapes, good for Camouflage bands)
  - 1-Bit Pack           (pixel art, 16×16, solid retro feel)
  - Abstract Platformer  (shapes and tiles)
  - Platformer Art Complete (full tileset)

Usage:
    from graphics.kenney import KenneyPacks
    packs = KenneyPacks(dest="assets/kenney/")
    packs.download("simple-space")
    packs.download("1-bit-pack")
"""

from __future__ import annotations

import os
import urllib.request
import zipfile
from pathlib import Path

# CC0 direct download URLs from kenney.nl (verified June 2026)
PACK_URLS: dict[str, str] = {
    "simple-space": "https://kenney.nl/assets/simple-space/zip",
    "1-bit-pack": "https://kenney.nl/assets/1-bit-pack/zip",
    "platformer-art-complete": "https://kenney.nl/assets/platformer-art-complete-pack/zip",
    "abstract-platformer": "https://kenney.nl/assets/abstract-platformer/zip",
    "fish-pack": "https://kenney.nl/assets/fish-pack/zip",
    "nature-kit": "https://kenney.nl/assets/nature-kit/zip",
    "ui-pack": "https://kenney.nl/assets/ui-pack/zip",
    "game-icons": "https://kenney.nl/assets/game-icons/zip",
}

# Best picks for Inko universe (why each pack fits)
RECOMMENDED = {
    "1-bit-pack": "Pixel art sprites — immediate retro prototyping, good octopus approximation",
    "fish-pack": "Direct marine life sprites: fish, bubbles, coral outlines",
    "simple-space": "Abstract colored shapes — perfect for Camouflage band tiles",
    "game-icons": "UI icons for HUD elements (lives, score, shield pearl)",
    "ui-pack": "Menu and button assets",
}


class KenneyPacks:
    def __init__(self, dest: str = "assets/kenney") -> None:
        self.dest = Path(dest)
        self.dest.mkdir(parents=True, exist_ok=True)

    def download(self, pack_name: str, force: bool = False) -> Path:
        """
        Download and extract a Kenney pack by name.
        Returns the directory the pack was extracted to.
        Skips download if already present unless force=True.
        """
        if pack_name not in PACK_URLS:
            raise ValueError(f"Unknown pack '{pack_name}'. Available: {list(PACK_URLS)}")
        out_dir = self.dest / pack_name
        if out_dir.exists() and not force:
            print(f"  {pack_name}: already downloaded → {out_dir}")
            return out_dir
        url = PACK_URLS[pack_name]
        zip_path = self.dest / f"{pack_name}.zip"
        print(f"  Downloading {pack_name} from {url}...")
        try:
            urllib.request.urlretrieve(url, zip_path)
        except Exception as e:
            print(f"  ⚠ Download failed for {pack_name}: {e}")
            print(f"    Manual URL: https://kenney.nl/assets/{pack_name}")
            return out_dir
        out_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(out_dir)
        zip_path.unlink()
        print(f"  ✓ {pack_name} extracted to {out_dir}")
        return out_dir

    def download_recommended(self) -> dict[str, Path]:
        """Download all recommended packs for AgentInko."""
        results = {}
        for name, reason in RECOMMENDED.items():
            print(f"\n[kenney] {name} — {reason}")
            results[name] = self.download(name)
        return results

    def list_assets(self, pack_name: str, ext: str = ".png") -> list[Path]:
        """List all assets of a given extension in a downloaded pack."""
        out_dir = self.dest / pack_name
        if not out_dir.exists():
            raise FileNotFoundError(f"Pack '{pack_name}' not downloaded yet.")
        return sorted(out_dir.rglob(f"*{ext}"))
