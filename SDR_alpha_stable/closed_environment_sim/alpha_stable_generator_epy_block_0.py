"""GNU Radio wrapper for the shared framed alpha-stable encoder."""

import sys
from pathlib import Path

_PROJECT_DIR = str(Path(__file__).resolve().parent.parent)
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)

from sender.alpha_stable_generator_epy_block_0 import alpha_encoder

__all__ = ["alpha_encoder"]
