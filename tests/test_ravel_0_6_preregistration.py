"""Structure and immutability checks for the RAVEL 0.6 preregistration."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker

pytestmark = pytest.mark.experimental

ROOT = Path(__file__).resolve().parents[1]
RAVEL = ROOT / "case-studies" / "ravel"
PREREGISTRATION = RAVEL / "ravel-0.6-preregistration.json"

FROZEN_IDENTITIES = {
    "ravel_0_4.c": "5243022245bce97b2e3be6dd46e397d33445c25469b8ce9a364c6a104e757cd4",
    "ravel-0.4-preregistration.json": (
        "d2e5e268392d0b341cfee96401d9da9bde36e8df8b69501512d54ee1bd373c8f"
    ),
    "ravel-0.4-source-manifest.json": (
        "c3b590a93313c929ef667f7c41100eb51a130c5015b2b2b7789bb6bf2033d768"
    ),
    "ravel-0.4-raw-observations.json": (
        "c7c71ad964b2cc06584a21185930eca5cb361112e4a9e1d9f6bc541b1d47f4e2"
    ),
    "ravel-0.4-trial-evidence.json": (
        "a5ffbfdbf2f46274413edf0644df2afa36df27da629c777bcf59b1f6e79066aa"
    ),
    "ravel-0.4-assurance-case.json": (
        "e64418234551ed4b80a570cfc67c2828976ffbddab21a062424273f9eafc6469"
    ),
    "ravel_0_5.c": "1a8466ea1805811873c461fb891aaeaec18f6c9e7491b5ea7bd09bf698be102d",
    "ravel-0.5-preregistration.json": (
        "f240c391b92823471132ffce1eeed154b3f03dc2af1e3e1f789690a99eb4cfaa"
    ),
    "ravel-0.5-source-and-execution-manifest.json": (
        "18006006db509269ee374a39133bb25d8452edc0fe0103a43fa92c5660fd89d0"
    ),
    "ravel-0.5-raw-observations.json": (
        "bb34d0292a9286ea321d50d31919dc43793a58b90b4c7a7892f91552b841f354"
    ),
    "ravel-0.5-trial-evidence.json": (
        "9ffefe97e5331b65e5b998f9c2d3aac91cdf9cca246a377ca421a3bef0ba0e80"
    ),
    "ravel-0.5-assurance-case.json": (
        "4bcce0a8dbcc6ff2ce085b809736be33511fffdc648f0c1545daeac7e695f429"
    ),
}


def _load(path: Path) -> dict[str, Any]:
    result = json.loads(path.read_text())
    assert isinstance(result, dict)
    return result


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_preregistration_schema_and_initial_status() -> None:
    schema = _load(RAVEL / "ravel-0.6-preregistration.schema.json")
    preregistration = _load(PREREGISTRATION)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(preregistration)
    assert preregistration["status_precedence"] == "FAIL > UNKNOWN > PASS"
    assert preregistration["initial_disposition"] == {
        "candidate_implementation": "NOT_IMPLEMENTED",
        "development_evaluation": "UNKNOWN",
        "final_evaluation": "UNKNOWN",
        "protected_custody": "UNKNOWN",
        "independent_evaluation": "UNKNOWN",
        "formal_mncs_status": "UNKNOWN",
        "formal_mncds_status": "UNKNOWN",
        "promotion_authorized": False,
    }


def test_partition_identities_and_seed_domains_are_unique() -> None:
    preregistration = _load(PREREGISTRATION)
    partitions = preregistration["partitions"]
    identifiers = [item["partition_id"] for item in partitions]
    domains = [item["seed_domain"] for item in partitions]
    assert len(identifiers) == len(set(identifiers)) == 6
    assert len(domains) == len(set(domains)) == 6
    required = {
        "ravel-0.6-development-adaptation-v1",
        "ravel-0.6-selection-v1",
        "ravel-0.6-future-final-reservation-v1",
        "ravel-0.6-retention-holdout-v1",
        "ravel-0.6-transition-retention-v1",
        "ravel-0.6-planning-diagnostics-v1",
    }
    assert set(identifiers) == required


def test_development_and_selection_seeds_match_derivation_and_do_not_overlap() -> None:
    preregistration = _load(PREREGISTRATION)
    derivation = preregistration["seed_derivation"]
    root_seed = int(derivation["root_seed"], 16).to_bytes(8, "big")
    observed: set[str] = set()
    for phase, key in (
        ("development", "development_seeds"),
        ("selection", "selection_seeds"),
    ):
        per_regime_index: dict[str, int] = {}
        for trial in derivation[key]:
            regime = trial["regime"]
            per_regime_index[regime] = per_regime_index.get(regime, 0) + 1
            framed = (
                root_seed
                + b"ravel-0.6\0"
                + phase.encode()
                + b"\0"
                + regime.encode()
                + b"\0"
                + per_regime_index[regime].to_bytes(4, "big")
            )
            expected = "0x" + hashlib.sha256(framed).digest()[:8].hex()
            assert trial["seed"] == expected
            assert trial["seed"] not in observed
            observed.add(trial["seed"])


def test_no_ravel_0_5_final_seed_is_reused_and_final_material_is_absent() -> None:
    prior = _load(RAVEL / "ravel-0.5-preregistration.json")
    preregistration = _load(PREREGISTRATION)
    prior_seeds = {trial["seed"] for trial in prior["trials"]}
    derivation = preregistration["seed_derivation"]
    new_seeds = {
        trial["seed"]
        for key in ("development_seeds", "selection_seeds")
        for trial in derivation[key]
    }
    assert new_seeds.isdisjoint(prior_seeds)
    assert derivation["future_final_seeds"] == []
    assert derivation["future_final_seed_state"] == "NOT_OBTAINED"
    assert preregistration["future_final_protocol"]["seed_material_present"] is False
    assert preregistration["future_final_protocol"]["same_epoch_repair_feedback"] is False


def test_ravel_0_4_and_0_5_frozen_identities_are_unchanged() -> None:
    for relative, expected in FROZEN_IDENTITIES.items():
        assert _sha256(RAVEL / relative) == expected, relative
    preregistration = _load(PREREGISTRATION)
    baseline = preregistration["baseline"]
    assert baseline["source_sha256"] == FROZEN_IDENTITIES["ravel_0_5.c"]
    assert baseline["preregistration_sha256"] == FROZEN_IDENTITIES["ravel-0.5-preregistration.json"]
    assert (
        baseline["manifest_sha256"]
        == FROZEN_IDENTITIES["ravel-0.5-source-and-execution-manifest.json"]
    )
    assert baseline["immutable"] is True


def test_ravel_0_5_disposition_remains_fail_unknown_unknown_no_promotion() -> None:
    assurance = _load(RAVEL / "ravel-0.5-assurance-case.json")
    development = _load(RAVEL / "ravel-0.6-development-record.json")
    assert assurance["development_result"] == "FAIL"
    assert assurance["formal_mncs_status"] == "UNKNOWN"
    assert assurance["formal_mncds_status"] == "UNKNOWN"
    assert assurance["promotion_authorized"] is False
    assert development["baseline"] == {
        "candidate_id": "ravel-0.5-candidate-1",
        "development_result": "FAIL",
        "formal_mncs_status": "UNKNOWN",
        "formal_mncds_status": "UNKNOWN",
        "promotion_authorized": False,
        "immutable": True,
    }


def test_preregistration_does_not_claim_an_implementation_or_evaluation() -> None:
    preregistration = _load(PREREGISTRATION)
    development = _load(RAVEL / "ravel-0.6-development-record.json")
    assert not list(RAVEL.glob("ravel_0_6_candidate_*.c"))
    assert preregistration["candidate_policy"]["implementation_status"] == "NOT_IMPLEMENTED"
    assert preregistration["candidate_policy"]["selected_candidate"] is None
    assert development["candidate"]["implementation_status"] == "NOT_IMPLEMENTED"
    assert development["development_evaluation"] == {
        "status": "UNKNOWN",
        "executed": False,
        "evidence": [],
    }
    assert development["final_evaluation"] == {
        "status": "UNKNOWN",
        "executed": False,
        "seed_material_present": False,
        "evidence": [],
    }
