#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from mncs_validator.readiness import cross_host_agreement


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not an object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("records", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    records = [load(path) for path in args.records]
    status, findings, summary = cross_host_agreement(records)
    evaluator_source = Path(__file__).read_bytes()
    result = {
        "schema_version": "0.4-experimental",
        "agreement_id": "composed-gateway-wave4-cross-host-v1",
        "source_records": [str(path) for path in args.records],
        "system_contract_id": str(records[0].get("system_contract_id", "unknown")),
        "epoch_id": str(records[0].get("epoch_id", "unknown")),
        "status": status,
        "findings": findings,
        "summary": summary,
        "evaluator_identity": "sha256:" + hashlib.sha256(evaluator_source).hexdigest(),
        "extensions": {"mncs.dev:wave": "four", "mncs.dev:evaluator": "reference-not-independent"},
    }
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 1 if status == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
