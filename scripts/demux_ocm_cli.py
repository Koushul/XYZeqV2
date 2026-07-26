#!/usr/bin/env python3
"""Thin CLI wrapper for simpleaf workflow external_commands."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from simpleleaf.cli import main

if __name__ == "__main__":
    # Translate legacy-style flags into `simpleleaf demux`
    argv = ["demux", *sys.argv[1:]]
    raise SystemExit(main(argv))
