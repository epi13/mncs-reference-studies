#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from mncs_validator.readiness import (
    cross_host_agreement,
    custody_findings,
    evaluate_claim_readiness,
)

ROOT = Path(os.environ.get("MNCS_STANDARDS_ROOT", Path(__file__).resolve().parents[4])).resolve()
WAVE = Path(__file__).resolve().parents[1]


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not an object")
    return value


def validate(instance: Path, schema: Path) -> list[str]:
    validator = Draft202012Validator(load(schema), format_checker=FormatChecker())
    return [f"{instance}: {error.message}" for error in validator.iter_errors(load(instance))]


def main() -> int:
    findings: list[str] = []
    pairs = [
        (
            WAVE / "fixtures/custody/valid-template.json",
            ROOT / "schemas/mncs-evidence-custody.schema.json",
        ),
        (
            WAVE / "cross-host-agreement-pending.json",
            ROOT / "schemas/mncs-cross-host-agreement.schema.json",
        ),
        (WAVE / "evidence/local-readiness.json", ROOT / "schemas/mncs-claim-readiness.schema.json"),
        (WAVE / "service-boundary.json", ROOT / "schemas/mncs-boundary-contract.schema.json"),
    ]
    for instance, schema in pairs:
        findings.extend(validate(instance, schema))

    valid_custody = load(WAVE / "fixtures/custody/valid-template.json")
    invalid_custody = load(WAVE / "fixtures/custody/invalid-self-custody.json")
    if custody_findings(valid_custody):
        findings.append("valid custody fixture produced findings")
    if not custody_findings(invalid_custody):
        findings.append("invalid custody fixture was not rejected")

    ubuntu = load(WAVE / "fixtures/cross-host/ubuntu.json")
    macos = load(WAVE / "fixtures/cross-host/macos.json")
    mismatch = load(WAVE / "fixtures/cross-host/mismatch.json")
    unknown = load(WAVE / "fixtures/cross-host/unknown.json")
    if cross_host_agreement([ubuntu, macos])[0] != "PASS":
        findings.append("cross-host PASS fixture did not pass")
    if cross_host_agreement([ubuntu, mismatch])[0] != "FAIL":
        findings.append("cross-host mismatch fixture did not fail")
    if cross_host_agreement([ubuntu, unknown])[0] != "UNKNOWN":
        findings.append("cross-host UNKNOWN fixture did not remain unknown")

    readiness = load(WAVE / "readiness-input.json")
    evaluated = evaluate_claim_readiness(readiness)
    if evaluated != {
        "formal_mncs_status": "UNKNOWN",
        "formal_mncds_status": "UNKNOWN",
        "promotion_authorized": False,
        "disposition": "REVIEW_REQUIRED",
    }:
        findings.append("local readiness propagation changed")

    go_result = subprocess.run(
        ["go", "test", "./..."],
        cwd=WAVE / "service-host",
        text=True,
        capture_output=True,
        check=False,
    )
    if go_result.returncode:
        findings.append("loopback service tests failed: " + go_result.stderr)

    report = {"wave": "four", "status": "PASS" if not findings else "FAIL", "findings": findings}
    print(json.dumps(report, indent=2, sort_keys=True))
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
