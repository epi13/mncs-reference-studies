from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "machine"))

from cacheforge.epoch2 import (  # noqa: E402
    CAPACITY_SWEEP,
    DEVELOPMENT_SEEDS,
    epoch2_scenarios,
    evaluate_epoch2,
    generate_epoch2_scenario,
)
from cacheforge.trace_bundle import (  # noqa: E402
    evaluate_trace_bundle,
    load_trace_bundle,
)
from generated_policy import GeneratedEvictionPolicy  # noqa: E402


def _bundle_payload() -> dict[str, object]:
    return {
        "schema_version": "0.1",
        "bundle_id": "cacheforge.test.external.v1",
        "scenarios": [
            {
                "scenario_id": "external-small",
                "capacity_blocks": 16,
                "purpose": "test external bundle",
                "requests": [
                    {
                        "request_id": "request-0",
                        "prompt_blocks": [
                            "sys:shared:0",
                            "sys:shared:1",
                            "user:a:0",
                        ],
                        "generated_blocks": 2,
                    },
                    {
                        "request_id": "request-1",
                        "prompt_blocks": [
                            "sys:shared:0",
                            "sys:shared:1",
                            "user:b:0",
                        ],
                        "generated_blocks": 2,
                        "cancel_after_generated": 1,
                    },
                ],
            }
        ],
    }


def _write_bundle(tmp_path: Path, payload: dict[str, object]) -> Path:
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(payload, sort_keys=True))
    return bundle_path


def test_epoch2_workload_is_deterministic_and_paired() -> None:
    first = generate_epoch2_scenario(DEVELOPMENT_SEEDS[0], CAPACITY_SWEEP[0])
    second = generate_epoch2_scenario(DEVELOPMENT_SEEDS[0], CAPACITY_SWEEP[-1])
    assert first.requests == second.requests
    assert first.capacity_blocks != second.capacity_blocks

    scenarios = epoch2_scenarios()
    assert len(scenarios) == len(DEVELOPMENT_SEEDS) * len(CAPACITY_SWEEP)
    assert len({scenario.scenario_id for scenario in scenarios}) == len(scenarios)


def test_epoch2_candidate_meets_frozen_development_gates() -> None:
    result = evaluate_epoch2(GeneratedEvictionPolicy)
    assert result["development_result"] == "PASS", json.dumps(result, indent=2)
    assert result["formal_mncs_status"] == "UNKNOWN"
    assert result["promotion_authorized"] is False
    assert result["aggregate"]["candidate_recomputed_blocks"] == 39654
    assert result["aggregate"]["strongest_baseline_recomputed_blocks"] == 41167
    assert result["aggregate"]["improved_scenarios"] == 53
    assert len(result["observations"]) == 64
    assert result["scenario_observation_digest"].startswith("sha256:")

    seed_summary = result["seed_cluster_summary"]
    assert seed_summary["independent_seed_count"] == 16
    assert seed_summary["favorable_seed_aggregates"] == 16
    assert seed_summary["all_capacities_improved_seeds"] == 7
    assert seed_summary["seeds_with_any_regression"] == 9
    assert seed_summary["maximum_regressed_capacities_for_one_seed"] == 2

    high_capacity = result["high_capacity_regime"]["by_hot_prefix_families"]
    assert high_capacity["1"]["improved"] == 0
    assert high_capacity["1"]["regressed"] == 4
    assert high_capacity["2"]["improved"] == 0
    assert high_capacity["2"]["regressed"] == 4
    assert high_capacity["3"]["improved"] == 4
    assert high_capacity["3"]["regressed"] == 0
    assert high_capacity["4"]["improved"] == 3
    assert high_capacity["4"]["regressed"] == 1


def test_external_trace_bundle_never_auto_promotes(tmp_path: Path) -> None:
    bundle = load_trace_bundle(_write_bundle(tmp_path, _bundle_payload()))
    result = evaluate_trace_bundle(bundle, GeneratedEvictionPolicy)
    assert result["bundle_id"] == "cacheforge.test.external.v1"
    assert result["schema_valid"] is True
    assert result["protocol_eligible"] == "NOT_ESTABLISHED"
    assert result["custody_verified"] == "NOT_ESTABLISHED"
    assert result["evaluation_result"] == "REVIEW_REQUIRED"
    assert result["promotion_authorized"] is False
    assert result["formal_mncs_status"] == "UNKNOWN"
    assert result["disposition"] == "REVIEW_REQUIRED"


def test_external_trace_bundle_rejects_duplicate_request_ids(tmp_path: Path) -> None:
    payload = _bundle_payload()
    scenario = payload["scenarios"][0]
    assert isinstance(scenario, dict)
    requests = scenario["requests"]
    assert isinstance(requests, list)
    requests.append(dict(requests[0]))

    with pytest.raises(ValueError, match="duplicate request_id"):
        load_trace_bundle(_write_bundle(tmp_path, payload))


def test_external_trace_bundle_enforces_additional_properties(tmp_path: Path) -> None:
    payload = _bundle_payload()
    payload["unexpected"] = True
    with pytest.raises(ValueError, match="schema validation failed"):
        load_trace_bundle(_write_bundle(tmp_path, payload))


@pytest.mark.parametrize("invalid_priority", ["1", 1.5, True])
def test_external_trace_bundle_enforces_priority_type(
    tmp_path: Path, invalid_priority: object
) -> None:
    payload = _bundle_payload()
    scenario = payload["scenarios"][0]
    assert isinstance(scenario, dict)
    requests = scenario["requests"]
    assert isinstance(requests, list)
    request = requests[0]
    assert isinstance(request, dict)
    request["priority"] = invalid_priority

    with pytest.raises(ValueError, match="schema validation failed"):
        load_trace_bundle(_write_bundle(tmp_path, payload))


def test_external_trace_bundle_rejects_invalid_cancellation_point(tmp_path: Path) -> None:
    payload = _bundle_payload()
    scenario = payload["scenarios"][0]
    assert isinstance(scenario, dict)
    requests = scenario["requests"]
    assert isinstance(requests, list)
    request = requests[0]
    assert isinstance(request, dict)
    request["cancel_after_generated"] = 3

    with pytest.raises(ValueError, match="outside the generated block range"):
        load_trace_bundle(_write_bundle(tmp_path, payload))
