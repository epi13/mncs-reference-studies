#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

REPO = Path(__file__).resolve().parents[4]


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not an object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--machine-label", required=True)
    parser.add_argument("--operator-id", default="operator:github-actions")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    lock = load(args.lock)
    with tempfile.TemporaryDirectory() as temporary:
        extracted = Path(temporary) / "bundle"
        with zipfile.ZipFile(args.archive) as archive:
            archive.extractall(extracted)
        command = [
            sys.executable,
            str(extracted / "evaluator.py"),
            "--machine-label",
            args.machine_label,
            "--operator-id",
            args.operator_id,
            "--output",
            str(args.output),
            "--archive-identity",
            lock["archive_identity"],
        ]
        result = subprocess.run(command, check=False)
    record = load(args.output)
    schema = load(REPO / "schemas/mncs-host-execution-record.schema.json")
    errors = list(Draft202012Validator(schema).iter_errors(record))
    if errors:
        for error in errors:
            print(error.message, file=sys.stderr)
        return 1
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
