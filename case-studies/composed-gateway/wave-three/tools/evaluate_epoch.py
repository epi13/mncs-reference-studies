#!/usr/bin/env python3
from __future__ import annotations

# Source layout is frozen for evidence identity; embedded fixtures may exceed line length.
# ruff: noqa: E501
# fmt: off

import argparse
import json
import pathlib
from typing import Any

from jsonschema import Draft202012Validator

WAVE = pathlib.Path(__file__).resolve().parents[1]
REPO = WAVE.parents[2]
SCHEMA = REPO / "schemas/mncs-composed-evidence-epoch.schema.json"


def expected_result(epoch: dict[str, Any]) -> str:
    build = epoch["build_results"]
    drills = epoch["recovery_drill"]
    mutation = epoch["mutation_campaign"]
    statuses = [
        build["c11_build"],
        build["go_tests"],
        build["go_vet"],
        build["go_race"],
        build["go_fuzz_smoke"],
        build["rust_toolchain"],
        drills["recovery"],
        drills["replacement"],
        mutation["status"],
        epoch["partitions"]["protected_holdout"],
        epoch["independent_evaluation"],
        epoch["cross_host_reproduction"],
    ]
    if "FAIL" in statuses:
        return "FAIL"
    if "UNKNOWN" in statuses:
        return "REVIEW_REQUIRED"
    return "PASS"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("epoch", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    epoch = json.loads(args.epoch.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(epoch),
        key=lambda error: list(error.absolute_path),
    )
    findings: list[str] = []
    if errors:
        findings.append(f"schema: {errors[0].message}")
    computed = expected_result(epoch)
    if epoch.get("propagated_result") != computed:
        findings.append(
            f"propagation mismatch: recorded={epoch.get('propagated_result')} computed={computed}"
        )
    if epoch.get("formal_mncs_status") != "UNKNOWN":
        findings.append("formal MNCS status must remain UNKNOWN in Wave Three")
    if epoch.get("formal_mncds_status") != "UNKNOWN":
        findings.append("formal MNCDS status must remain UNKNOWN in Wave Three")
    if epoch.get("promotion_authorized") is not False:
        findings.append("promotion must remain unauthorized")
    d4 = epoch.get("d4_regeneration_replacement_subclaim")
    if d4 == "PASS":
        if epoch["build_results"]["binding_regeneration"] != "PASS":
            findings.append("D4 subclaim lacks binding regeneration")
        if epoch["recovery_drill"]["replacement"] != "PASS":
            findings.append("D4 subclaim lacks replacement drill")
    if epoch["partitions"]["protected_holdout"] != "UNKNOWN":
        findings.append("public repository cannot assert protected holdout PASS")
    if epoch["independent_evaluation"] != "UNKNOWN":
        findings.append("structural evaluator separation is not independent custody")

    report = {
        "schema_version": "0.3-experimental",
        "evaluator_id": "composed-wave3-second-implementation-evaluator-0.1.0",
        "organizationally_independent": False,
        "epoch_id": epoch.get("epoch_id"),
        "computed_result": computed,
        "recorded_result": epoch.get("propagated_result"),
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
        "claim_boundary": "This is a second implementation of aggregation and schema checks, not an independent evaluator or evidence custodian.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
# fmt: on
