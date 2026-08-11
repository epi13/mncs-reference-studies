#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from mncs_validator.portable import classify_reproduction_cohort


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not an object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("records", nargs="+", type=Path)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records = [load(path) for path in args.records]
    plan = load(args.plan)
    result = classify_reproduction_cohort(records, plan)
    source_records = [
        {
            "path": str(path),
            "record_id": record.get("record_id"),
            "raw_artifact_identity": record.get("raw_artifact_identity"),
        }
        for path, record in zip(args.records, records, strict=True)
    ]
    output = {
        "schema_version": "0.5-experimental",
        "cohort_id": "composed-gateway-wave5-operator-cohort-v1",
        "plan_id": plan["plan_id"],
        "bundle_id": next(iter({record.get("bundle_id") for record in records}), "unknown"),
        "manifest_identity": next(
            iter({record.get("manifest_identity") for record in records}), "unknown"
        ),
        "candidate_freeze_identity": next(
            iter({record.get("candidate_freeze_identity") for record in records}), "unknown"
        ),
        "source_records": source_records,
        **result,
        "formal_mncs_status": "UNKNOWN",
        "formal_mncds_status": "UNKNOWN",
        "promotion_authorized": False,
        "evaluator_identity": "sha256:" + hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "extensions": {
            "mncs.dev:wave": "five",
            "mncs.dev:operator_controlled": True,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "status": output["status"],
        "evidence_class": output["evidence_class"],
    }
    print(json.dumps(summary, sort_keys=True))
    return 1 if output["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
