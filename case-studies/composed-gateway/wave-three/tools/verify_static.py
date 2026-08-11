#!/usr/bin/env python3
from __future__ import annotations

# Source layout is frozen for evidence identity; embedded fixtures may exceed line length.
# ruff: noqa: E501
# fmt: off

import hashlib
import json
import os
import pathlib
import subprocess
import sys

from jsonschema import Draft202012Validator

WAVE = pathlib.Path(__file__).resolve().parents[1]
REPO = pathlib.Path(os.environ.get("MNCS_STANDARDS_ROOT", WAVE.parents[2])).resolve()
PAIRS = [
    (WAVE / "boundary-native-v2.json", REPO / "schemas/mncs-boundary-contract.schema.json"),
    (WAVE / "boundary-process-v2.json", REPO / "schemas/mncs-boundary-contract.schema.json"),
    (WAVE / "composed-assurance-v2.json", REPO / "schemas/mncs-composed-assurance-case.schema.json"),
    (WAVE / "evidence/local-development-epoch.json", REPO / "schemas/mncs-composed-evidence-epoch.schema.json"),
]


def main() -> int:
    findings: list[str] = []
    for data_path, schema_path in PAIRS:
        data = json.loads(data_path.read_text(encoding="utf-8"))
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        errors = sorted(
            Draft202012Validator(schema).iter_errors(data),
            key=lambda error: list(error.absolute_path),
        )
        if errors:
            findings.append(f"{data_path.relative_to(REPO)}: {errors[0].message}")

    generated = subprocess.run(
        [sys.executable, str(WAVE / "tools/generate_binding.py"), "--check"],
        check=False,
    )
    if generated.returncode != 0:
        findings.append("generated binding drift")

    commitment = json.loads((WAVE / "holdout/commitment.json").read_text(encoding="utf-8"))
    prereg_hash = hashlib.sha256((WAVE / "preregistration.json").read_bytes()).hexdigest()
    if commitment["preregistration_sha256"] != prereg_hash:
        findings.append("holdout commitment does not bind the preregistration")

    expected_mutations = json.loads((WAVE / "mutation-campaign-v2.json").read_text(encoding="utf-8"))
    if len(expected_mutations["fixtures"]) < 16:
        findings.append("mutation campaign is incomplete")

    print(json.dumps({"status": "PASS" if not findings else "FAIL", "findings": findings}, indent=2))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
# fmt: on
