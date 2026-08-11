from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_language_provider_corpus() -> None:
    subprocess.run([str(ROOT / "scripts/run-language-provider-corpus")], cwd=ROOT, check=True)
