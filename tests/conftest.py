"""Make optional cross-repository empirical tests use the frozen standards checkout."""

from __future__ import annotations

import os
import sys
from pathlib import Path


standards_root = os.environ.get("MNCS_STANDARDS_ROOT")
if standards_root:
    sys.path.insert(0, str(Path(standards_root) / "src"))
