"""Validate an experimental language-evidence profile against its local schema."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", type=Path)
    args = parser.parse_args()
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    schema = json.loads(
        (ROOT / "schemas/mncs-language-evidence-profile.schema.json").read_text(
            encoding="utf-8"
        )
    )
    errors = sorted(
        Draft202012Validator(schema).iter_errors(profile),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        raise SystemExit(errors[0].message)
    print(f"PROFILE-VALID: {args.profile}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

