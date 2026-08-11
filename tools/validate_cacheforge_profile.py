"""Validate CacheForge's historical language-profile amendment locally."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    profile = json.loads(
        (ROOT / "experimental/language-evidence/profiles/python-cpython-3.11-v0.1.json").read_text()
    )
    schema = json.loads(
        (ROOT / "schemas/mncs-language-evidence-profile.schema.json").read_text()
    )
    errors = list(Draft202012Validator(schema).iter_errors(profile))
    if errors:
        raise SystemExit(errors[0].message)
    amendment = json.loads(
        (ROOT / "case-studies/cacheforge/python-language-profile-epoch-3.json").read_text()
    )
    checks = (
        amendment["selected_profile"] == profile["profile_id"],
        amendment["historical_evidence_modified"] is False,
        amendment["claim_boundary"]["formal_mncs_status"] == "UNKNOWN",
        amendment["claim_boundary"]["formal_mncds_status"] == "UNKNOWN",
        amendment["claim_boundary"]["promotion_authorized"] is False,
        amendment["provider"]["result"] == "UNKNOWN",
    )
    if not all(checks):
        raise SystemExit("CacheForge language-profile amendment is inconsistent")
    print(json.dumps({"status": "PASS", "claim": "profile binding only; historical claims unchanged"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

