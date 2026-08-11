from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


def load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def test_preflight_cross_language_report_validates() -> None:
    schema = load(ROOT / "schemas/mncs-cross-language-comparison.schema.json")
    report = load(
        ROOT
        / "case-studies/multilingual-stream/evidence/results"
        / "cross-language-comparison-preflight.json"
    )
    errors = sorted(
        Draft202012Validator(schema).iter_errors(report),
        key=lambda error: list(error.absolute_path),
    )
    assert not errors


def test_provider_descriptors_are_explicit_and_bounded() -> None:
    descriptor_dir = ROOT / "experimental/language-evidence/providers/descriptors"
    for path in sorted(descriptor_dir.glob("*.json")):
        descriptor = load(path)
        assert descriptor["protocol_version"] == "0.1"
        assert descriptor["timeout_seconds"] == 2
        assert descriptor["command"][0] == "python3"
        assert descriptor["extensions"]["mncs.dev:execution"] == "explicit-only"
