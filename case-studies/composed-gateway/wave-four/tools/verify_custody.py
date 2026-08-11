#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from mncs_validator.readiness import custody_findings

ROOT = Path(__file__).resolve().parents[4]


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not an object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("record", type=Path)
    args = parser.parse_args()
    record = load(args.record)
    schema = load(ROOT / "schemas/mncs-evidence-custody.schema.json")
    schema_findings = [
        error.message
        for error in Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(
            record
        )
    ]
    findings = sorted(schema_findings + custody_findings(record))
    result = {
        "record": str(args.record),
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
