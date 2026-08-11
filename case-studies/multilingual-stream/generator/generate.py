#!/usr/bin/env python3
"""Deterministically materialize the frozen Wave One candidate sources."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    spec = json.loads((ROOT / "generator/spec.json").read_text(encoding="utf-8"))
    findings: list[str] = []
    for output in spec["outputs"]:
        template = ROOT / output["template"]
        destination = ROOT / output["path"]
        content = template.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        if digest != output["sha256"]:
            findings.append(f"template identity mismatch: {output['template']}")
            continue
        if args.check:
            if not destination.is_file() or destination.read_bytes() != content:
                findings.append(f"generated output mismatch: {output['path']}")
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
    if findings:
        for finding in findings:
            print(finding)
        return 1
    print("candidate regeneration identity: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
