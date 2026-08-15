#!/usr/bin/env python3
"""Attest the frozen RAVEL 0.5 historical limitation without regenerating evidence."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAVEL = ROOT / "case-studies" / "ravel"
RECORD = RAVEL / "ravel-0.5-historical-limitation.json"
EXPECTED_PREFIX = "ravel 0.5 evidence error: canonical artifacts stale or missing:"


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _fail(message: str) -> int:
    print(f"ravel 0.5 historical limitation: {message}", file=sys.stderr)
    return 1


def main() -> int:
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    if record.get("regeneration_authorized") is True:
        return _fail("limitation record must not authorize regeneration")
    inventory = record["frozen_inventory"]
    for name, expected in inventory.items():
        path = RAVEL / name
        if not path.is_file():
            return _fail(f"frozen file missing: {name}")
        actual = _sha256(path)
        if actual != expected:
            return _fail(f"frozen file changed unexpectedly: {name} {actual} != {expected}")

    build = subprocess.run(["make", "ravel_0_5_bin"], cwd=RAVEL, capture_output=True, text=True)
    if build.returncode != 0:
        print(build.stdout)
        print(build.stderr, file=sys.stderr)
        return _fail("could not build the historical 0.5 binary for verification")

    verify = subprocess.run(
        [
            sys.executable,
            "tools/ravel_0_5_evidence.py",
            "verify",
            "--binary",
            "./ravel_0_5_bin",
            "--diagnostics-dir",
            "diagnostics-0.5",
        ],
        cwd=RAVEL,
        capture_output=True,
        text=True,
    )
    combined = (verify.stderr or "") + (verify.stdout or "")
    if verify.returncode == 0:
        return _fail("historical verify unexpectedly passed; frozen identity may have been regenerated")
    if EXPECTED_PREFIX not in combined:
        print(combined, file=sys.stderr)
        return _fail("historical verify failed for an unexpected reason")
    expected = list(record["expected_stale_or_missing"])
    for name in expected:
        if name not in combined:
            return _fail(f"expected stale artifact not reported: {name}")
    unexpected = []
    for name in inventory:
        if name in combined and name not in expected:
            unexpected.append(name)
    if unexpected:
        return _fail(f"unexpected stale/missing artifacts: {unexpected}")

    for name, expected_digest in inventory.items():
        actual = _sha256(RAVEL / name)
        if actual != expected_digest:
            return _fail(f"frozen file changed during verify: {name}")

    print("RAVEL 0.5 historical status: KNOWN LIMITATION")
    print("frozen inventory unchanged")
    print("canonical verify still fails exactly as documented")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
