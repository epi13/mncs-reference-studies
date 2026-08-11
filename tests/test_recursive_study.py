from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from mncs_validator.assurance import validate_rc_file

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "studies/recursive-analyzer"


def test_two_epoch_study_reproduces_without_claim_promotion() -> None:
    process = subprocess.run(
        [sys.executable, str(STUDY / "run_study.py")],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    assert process.returncode == 0, process.stderr
    result = json.loads(process.stdout)
    assert result["identity_match"] is True
    assert result["comparison"]["incorrect_pass_delta"] == -3
    assert result["comparison"]["false_negative_delta"] == -2
    assert result["comparison"]["false_positive_delta"] == 0
    assert result["selection"]["internal_selection_status"] == "PASS"
    assert result["selection"]["mncs_claim_status"] == "UNKNOWN"
    assert result["selection"]["external_independence"] == "UNKNOWN"


def test_selected_study_assurance_bundle_remains_unknown() -> None:
    report = validate_rc_file(
        STUDY / "assurance-bundle/assurance-case.json",
        "assurance",
    )
    assert report.valid
    assert report.category == "UNKNOWN"
