#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from mncs_validator.portable import classify_reproduction_cohort

WAVE = Path(__file__).resolve().parents[1]
REPO = Path(os.environ.get("MNCS_STANDARDS_ROOT", Path(__file__).resolve().parents[4])).resolve()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not an object")
    return value


def validate(instance: dict[str, Any], schema: Path) -> list[str]:
    validator = Draft202012Validator(load(schema), format_checker=FormatChecker())
    return [error.message for error in validator.iter_errors(instance)]


def fixture_host(
    label: str, os_family: str, distribution: str, architecture: str
) -> dict[str, Any]:
    return {
        "bundle_id": "composed-gateway-wave5-portable-evaluator-v1",
        "manifest_identity": load(WAVE / "bundle-lock.json")["manifest_identity"],
        "candidate_freeze_identity": load(WAVE / "bundle-lock.json")["candidate_freeze_identity"],
        "machine_label": label,
        "operator_id": "operator:alexander",
        "result": "PASS",
        "gates": {
            "bundle_integrity": "PASS",
            "deterministic_vectors": "PASS",
            "checkpoint_resume": "PASS",
            "corruption_rejection": "PASS",
            "offline_capability": "PASS",
        },
        "semantic_output_digest": (
            "0bd3bcf6bc40caf9b15e9148972f822ef2a1afbe1a03a882ff765aba398ff2d4"
        ),
        "environment": {
            "os_family": os_family,
            "distribution": distribution,
            "architecture": architecture,
        },
    }


def main() -> int:
    findings: list[str] = []
    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / "dist"
        build = subprocess.run(
            [
                sys.executable,
                str(WAVE / "tools/build_bundle.py"),
                "--output",
                str(output),
                "--check-lock",
                str(WAVE / "bundle-lock.json"),
            ],
            check=False,
        )
        if build.returncode:
            findings.append("deterministic portable bundle build failed")
        manifest = load(output / "manifest.json")
        findings.extend(
            validate(manifest, REPO / "schemas/mncs-portable-evaluation-bundle.schema.json")
        )
        extracted = Path(temporary) / "extracted"
        with zipfile.ZipFile(output / "mncs-wave-five-portable-evaluator.zip") as archive:
            archive.extractall(extracted)
        host_record = Path(temporary) / "host-record.json"
        run = subprocess.run(
            [
                sys.executable,
                str(extracted / "evaluator.py"),
                "--machine-label",
                "local-reference",
                "--operator-id",
                "operator:repository",
                "--output",
                str(host_record),
                "--archive-identity",
                load(WAVE / "bundle-lock.json")["archive_identity"],
            ],
            check=False,
        )
        if run.returncode:
            findings.append("portable evaluator local execution failed")
        findings.extend(
            validate(load(host_record), REPO / "schemas/mncs-host-execution-record.schema.json")
        )

    records = [
        fixture_host("windows-a", "Windows", "Windows 11", "x86_64"),
        fixture_host("windows-b", "Windows", "Windows 11", "x86_64"),
        fixture_host("fedora-a", "Linux", "Fedora Linux", "x86_64"),
        fixture_host("fedora-b", "Linux", "Fedora Linux", "x86_64"),
        fixture_host("pios-arm", "Linux", "Raspberry Pi OS", "arm64"),
    ]
    cohort = classify_reproduction_cohort(records, load(WAVE / "machine-plan.json"))
    if cohort["status"] != "PASS":
        findings.append("five-host operator cohort fixture did not pass")
    if cohort["independent_evaluation_status"] != "UNKNOWN":
        findings.append("same-operator cohort was mislabeled independent")
    findings.extend(
        validate(
            load(WAVE / "evidence/pending-cohort.json"),
            REPO / "schemas/mncs-reproduction-cohort.schema.json",
        )
    )
    report = {
        "wave": "five",
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
