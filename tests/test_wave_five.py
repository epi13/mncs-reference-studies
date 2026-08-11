from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from mncs_validator.portable import classify_reproduction_cohort

ROOT = Path(__file__).resolve().parents[1]
WAVE = ROOT / "case-studies/composed-gateway/wave-five"
MANIFEST_IDENTITY = "sha256:ca4053025b6cdc0b17ee910c0a09011eba18fd5774df891d87a7465277126402"
ARCHIVE_IDENTITY = "sha256:98a6d338b7a60067781cd7cb41d9a9458917dbe0b3c9b2348b926e122439f7e8"
FREEZE_IDENTITY = "sha256:d858508276593494f9e8a255e07a2265954ac37424212f71f4bfa94aacbc4de9"
SEMANTIC_DIGEST = "0bd3bcf6bc40caf9b15e9148972f822ef2a1afbe1a03a882ff765aba398ff2d4"


def load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def validate(instance: dict[str, object], schema_name: str) -> None:
    schema = load(ROOT / "schemas" / schema_name)
    errors = list(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(instance)
    )
    assert not errors, errors


def host(
    label: str,
    os_family: str,
    distribution: str,
    arch: str,
    operator: str = "operator:alexander",
) -> dict[str, object]:
    return {
        "schema_version": "0.5-experimental",
        "record_id": f"host:{label}:1",
        "bundle_id": "composed-gateway-wave5-portable-evaluator-v1",
        "manifest_identity": MANIFEST_IDENTITY,
        "transport_archive_identity": ARCHIVE_IDENTITY,
        "candidate_freeze_identity": FREEZE_IDENTITY,
        "machine_label": label,
        "operator_id": operator,
        "operator_controlled": True,
        "evidence_class": "OPERATOR_CONTROLLED",
        "started_at_unix": 1.0,
        "finished_at_unix": 2.0,
        "environment": {
            "os_family": os_family,
            "os_release": "fixture",
            "distribution": distribution,
            "architecture": arch,
            "python_version": "3.11.0",
            "python_implementation": "CPython",
            "cpu_count": 4,
            "machine_fingerprint": "sha256:" + label.encode().hex()[:64].ljust(64, "0"),
        },
        "capabilities": {
            name: {"status": "UNKNOWN", "executable": None, "version": None}
            for name in ("go", "rustc", "c_compiler")
        },
        "gates": {
            "bundle_integrity": "PASS",
            "deterministic_vectors": "PASS",
            "checkpoint_resume": "PASS",
            "corruption_rejection": "PASS",
            "offline_capability": "PASS",
        },
        "semantic_output_digest": SEMANTIC_DIGEST,
        "raw_artifact_identity": "sha256:" + ("a" * 64),
        "result": "PASS",
        "findings": [],
        "independent_evaluation_status": "UNKNOWN",
        "protected_holdout_status": "UNKNOWN",
        "extensions": {},
    }


def test_bundle_determinism_and_host_schema() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / "dist"
        command = [
            sys.executable,
            str(WAVE / "tools/build_bundle.py"),
            "--output",
            str(output),
            "--check-lock",
            str(WAVE / "bundle-lock.json"),
        ]
        subprocess.run(command, check=True)
        manifest = load(output / "manifest.json")
        validate(manifest, "mncs-portable-evaluation-bundle.schema.json")
        extract = Path(temporary) / "extract"
        with zipfile.ZipFile(output / "mncs-wave-five-portable-evaluator.zip") as archive:
            archive.extractall(extract)
        record_path = Path(temporary) / "host.json"
        subprocess.run(
            [
                sys.executable,
                str(extract / "evaluator.py"),
                "--machine-label",
                "local-test",
                "--operator-id",
                "operator:test",
                "--output",
                str(record_path),
                "--archive-identity",
                ARCHIVE_IDENTITY,
            ],
            check=True,
        )
        validate(load(record_path), "mncs-host-execution-record.schema.json")


def test_five_machine_operator_cohort() -> None:
    records = [
        host("windows-a", "Windows", "Windows 11", "x86_64"),
        host("windows-b", "Windows", "Windows 11", "x86_64"),
        host("fedora-a", "Linux", "Fedora Linux", "x86_64"),
        host("fedora-b", "Linux", "Fedora Linux", "x86_64"),
        host("pios-arm", "Linux", "Raspberry Pi OS", "arm64"),
    ]
    result = classify_reproduction_cohort(records, load(WAVE / "machine-plan.json"))
    assert result["status"] == "PASS"
    assert result["evidence_class"] == "OPERATOR_CONTROLLED_CROSS_HOST"
    assert result["public_reproduction_status"] == "PASS"
    assert result["independent_evaluation_status"] == "UNKNOWN"
    assert result["summary"]["machine_count"] == 5
    assert len(result["summary"]["architectures"]) >= 2


def test_missing_pi_is_unknown_and_mismatch_fails() -> None:
    records = [
        host("windows-a", "Windows", "Windows 11", "x86_64"),
        host("windows-b", "Windows", "Windows 11", "x86_64"),
        host("fedora-a", "Linux", "Fedora Linux", "x86_64"),
        host("fedora-b", "Linux", "Fedora Linux", "x86_64"),
    ]
    missing = classify_reproduction_cohort(records, load(WAVE / "machine-plan.json"))
    assert missing["status"] == "UNKNOWN"
    mismatched = [*records, host("pios-arm", "Linux", "Raspberry Pi OS", "arm64")]
    mismatched[-1]["semantic_output_digest"] = "f" * 64
    mismatch_result = classify_reproduction_cohort(mismatched, load(WAVE / "machine-plan.json"))
    assert mismatch_result["status"] == "FAIL"


def test_pending_cohort_schema() -> None:
    validate(
        load(WAVE / "evidence/pending-cohort.json"),
        "mncs-reproduction-cohort.schema.json",
    )
