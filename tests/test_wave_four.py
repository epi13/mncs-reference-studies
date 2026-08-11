from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from mncs_validator.readiness import (
    aggregate_status,
    cross_host_agreement,
    custody_findings,
    evaluate_claim_readiness,
)

ROOT = Path(__file__).resolve().parents[1]
WAVE = ROOT / "case-studies/composed-gateway/wave-four"


def load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_precedence() -> None:
    assert aggregate_status(["PASS", "PASS"]) == "PASS"
    assert aggregate_status(["PASS", "UNKNOWN"]) == "UNKNOWN"
    assert aggregate_status(["PASS", "UNKNOWN", "FAIL"]) == "FAIL"
    assert aggregate_status([]) == "UNKNOWN"


def test_custody_fixtures() -> None:
    valid = load(WAVE / "fixtures/custody/valid-template.json")
    invalid = load(WAVE / "fixtures/custody/invalid-self-custody.json")
    schema = load(ROOT / "schemas/mncs-evidence-custody.schema.json")
    assert not list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(valid))
    assert custody_findings(valid) == []
    assert custody_findings(invalid)


def test_cross_host_fixtures() -> None:
    ubuntu = load(WAVE / "fixtures/cross-host/ubuntu.json")
    macos = load(WAVE / "fixtures/cross-host/macos.json")
    mismatch = load(WAVE / "fixtures/cross-host/mismatch.json")
    unknown = load(WAVE / "fixtures/cross-host/unknown.json")
    assert cross_host_agreement([ubuntu, macos])[0] == "PASS"
    assert cross_host_agreement([ubuntu, mismatch])[0] == "FAIL"
    assert cross_host_agreement([ubuntu, unknown])[0] == "UNKNOWN"


def test_readiness_stays_unknown() -> None:
    record = load(WAVE / "readiness-input.json")
    assert evaluate_claim_readiness(record) == {
        "formal_mncs_status": "UNKNOWN",
        "formal_mncds_status": "UNKNOWN",
        "promotion_authorized": False,
        "disposition": "REVIEW_REQUIRED",
    }


def test_new_schemas_and_checked_records() -> None:
    pairs = [
        ("mncs-cross-host-agreement.schema.json", WAVE / "cross-host-agreement-pending.json"),
        ("mncs-claim-readiness.schema.json", WAVE / "evidence/local-readiness.json"),
    ]
    for schema_name, record_path in pairs:
        schema = load(ROOT / "schemas" / schema_name)
        record = load(record_path)
        assert not list(Draft202012Validator(schema).iter_errors(record))
