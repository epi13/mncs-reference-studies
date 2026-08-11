from __future__ import annotations

import json
from pathlib import Path

from mncs_validator.language_profiles import (
    validate_language_profile,
    validate_language_profile_file,
)

ROOT = Path(__file__).resolve().parents[1]


def test_all_language_profiles_validate() -> None:
    profiles = ROOT / "experimental/language-evidence/profiles"
    for path in sorted(profiles.glob("*.json")):
        assert validate_language_profile_file(path) == []


def test_negative_profile_fixture_fails() -> None:
    path = (
        ROOT
        / "experimental/language-evidence/fixtures/profiles"
        / "invalid-missing-unknown-conditions.json"
    )
    profile = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_language_profile(profile)
    assert any("unknown_conditions" in error for error in errors)
