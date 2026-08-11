from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mncs_validator.schemas import schema_errors

ROOT = Path(__file__).resolve().parents[1]
WAVE = ROOT / "case-studies/composed-gateway/wave-three"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_local_wave_three_epoch_validates() -> None:
    record = load(WAVE / "evidence/local-development-epoch.json")
    assert schema_errors(record, "composed-evidence-epoch") == []
    assert record["propagated_result"] == "REVIEW_REQUIRED"
    assert record["formal_mncs_status"] == "UNKNOWN"
    assert record["formal_mncds_status"] == "UNKNOWN"
    assert record["promotion_authorized"] is False


def test_wave_three_does_not_relabel_public_data_as_holdout() -> None:
    record = load(WAVE / "evidence/local-development-epoch.json")
    commitment = load(WAVE / "holdout/commitment.json")
    assert record["partitions"]["protected_holdout"] == "UNKNOWN"
    assert commitment["protected_corpus_in_repository"] is False
    assert commitment["default_status"] == "UNKNOWN"


def test_wave_three_assurance_preserves_rust_unknown() -> None:
    record = load(WAVE / "composed-assurance-v2.json")
    statuses = {item["id"]: item["status"] for item in record["components"]}
    assert statuses["rust-authority-v2"] == "UNKNOWN"
    assert record["propagated_result"] == "REVIEW_REQUIRED"
    assert record["promotion_authorized"] is False
