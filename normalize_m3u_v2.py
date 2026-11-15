#!/usr/bin/env python3
"""Deprecated entry point kept for compatibility.

Playlist normalisation is now part of ``build.py``. Running this file performs a
full build (fetch -> normalise -> EPG -> write).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())