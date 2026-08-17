"""GNU Radio wrapper for the shared framed alpha-stable decoder."""

import sys
from pathlib import Path

_PROJECT_DIR = str(Path(__file__).resolve().parent.parent)
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)

from receiver.alpha_stable_generator_epy_block_1 import alpha_decoder

__all__ = ["alpha_decoder"]
