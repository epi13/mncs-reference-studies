#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "machine"))

from water_control.checkpoint import (  # noqa: E402
    CheckpointError,
    decode_checkpoint,
    encode_checkpoint,
)
from water_control.model import SystemConfig  # noqa: E402
from water_control.planner import GeneratedTablePlanner, ReadableBaselinePlanner  # noqa: E402
from water_control.scenarios import scenario_suite, smoke_suite  # noqa: E402
from water_control.simulator import run_scenario  # noqa: E402

PER_SCENARIO_NORMALIZED_ENERGY_RATIO_MAX = 1.20
PER_SCENARIO_TERMINAL_RESERVE_DEFICIT_PCT_MAX = 10.0


def sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def aggregate(results: list[dict[str, Any]]) -> dict[str, float | int | dict[str, int]]:
    interventions = {"accepted": 0, "modified": 0, "held": 0, "rejected": 0}
    for item in results:
        for key, value in item["safety_interventions"].items():
            interventions[key] = interventions.get(key, 0) + int(value)
    return {
        "energy_kwh": round(sum(float(item["energy_kwh"]) for item in results), 6),
        "pump_starts": sum(int(item["pump_starts"]) for item in results),
        "unmet_demand_l": round(sum(float(item["unmet_demand_l"]) for item in results), 6),
        "overflow_l": round(sum(float(item["overflow_l"]) for item in results), 6),
        "safety_violations": sum(len(item["safety_violations"]) for item in results),
        "safety_interventions": interventions,
    }


def checkpoint_corruption_probe() -> dict[str, Any]:
    original = encode_checkpoint({"sequence": 14, "tail_hash": "abc"})
    cases: list[dict[str, str]] = []
    for repetition in range(3):
        for corruption in ("middle-bit", "header-bit", "truncated"):
            encoded = bytearray(original)
            if corruption == "middle-bit":
                encoded[len(encoded) // 2] ^= 1 << repetition
            elif corruption == "header-bit":
                encoded[min(4 + repetition, len(encoded) - 1)] ^= 1
            else:
                del encoded[-(1 + repetition) :]
            try:
                decode_checkpoint(bytes(encoded))
            except CheckpointError as exc:
                cases.append(
                    {
                        "corruption": corruption,
                        "repetition": str(repetition),
                        "status": "PASS",
                        "observation": str(exc),
                    }
                )
            else:
                cases.append(
                    {
                        "corruption": corruption,
                        "repetition": str(repetition),
                        "status": "FAIL",
                        "observation": "corrupted checkpoint was accepted",
                    }
                )
    return {
        "status": "PASS" if all(case["status"] == "PASS" for case in cases) else "FAIL",
        "cases": cases,
    }


def validate_experimental_records() -> dict[str, Any]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return {"status": "UNKNOWN", "observation": "jsonschema is not installed"}
    checks = (
        ("mncs-contract-profile.schema.json", ROOT / "contract" / "contract-profile.json"),
        ("mncs-assurance-case.schema.json", ROOT / "assurance-case.json"),
    )
    failures: list[str] = []
    for schema_name, record_path in checks:
        schema = json.loads((REPOSITORY_ROOT / "schemas" / schema_name).read_text())
        record = json.loads(record_path.read_text())
        errors = sorted(
            Draft202012Validator(schema).iter_errors(record), key=lambda item: item.path
        )
        failures.extend(f"{record_path.name}: {error.message}" for error in errors)
    return {"status": "FAIL" if failures else "PASS", "failures": failures}


def _equivalent_storage_energy_kwh(level_deficit_pct: float) -> float:
    config = SystemConfig()
    liters = max(0.0, level_deficit_pct) / 100.0 * config.tank_capacity_l
    return liters / config.duty_flow_lps / 3600.0 * config.duty_power_kw


def scenario_comparisons(
    baseline: list[dict[str, Any]], candidate: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    baseline_by_id = {item["scenario_id"]: item for item in baseline}
    comparisons: list[dict[str, Any]] = []
    for cand in candidate:
        base = baseline_by_id[cand["scenario_id"]]
        common_terminal = max(float(base["final_level_pct"]), float(cand["final_level_pct"]))
        base_adjusted = float(base["energy_kwh"]) + _equivalent_storage_energy_kwh(
            common_terminal - float(base["final_level_pct"])
        )
        cand_adjusted = float(cand["energy_kwh"]) + _equivalent_storage_energy_kwh(
            common_terminal - float(cand["final_level_pct"])
        )
        normalized_ratio = cand_adjusted / max(0.000001, base_adjusted)
        terminal_deficit = float(base["final_level_pct"]) - float(cand["final_level_pct"])
        status = (
            "PASS"
            if (
                normalized_ratio <= PER_SCENARIO_NORMALIZED_ENERGY_RATIO_MAX
                and terminal_deficit <= PER_SCENARIO_TERMINAL_RESERVE_DEFICIT_PCT_MAX
                and float(cand["unmet_demand_l"]) <= float(base["unmet_demand_l"])
                and float(cand["overflow_l"]) <= float(base["overflow_l"])
                and not cand["safety_violations"]
            )
            else "FAIL"
        )
        comparisons.append(
            {
                "scenario_id": cand["scenario_id"],
                "status": status,
                "randomized": cand["randomized"],
                "seed": cand["seed"],
                "terminal_normalization_target_pct": round(common_terminal, 6),
                "baseline_normalized_energy_kwh": round(base_adjusted, 6),
                "candidate_normalized_energy_kwh": round(cand_adjusted, 6),
                "candidate_to_baseline_normalized_energy_ratio": round(normalized_ratio, 6),
                "terminal_reserve_deficit_pct": round(terminal_deficit, 6),
                "limits": {
                    "normalized_energy_ratio_max": PER_SCENARIO_NORMALIZED_ENERGY_RATIO_MAX,
                    "terminal_reserve_deficit_pct_max": (
                        PER_SCENARIO_TERMINAL_RESERVE_DEFICIT_PCT_MAX
                    ),
                    "unmet_demand_regression_l_max": 0.0,
                    "overflow_regression_l_max": 0.0,
                },
            }
        )
    return comparisons


def run(mode: str) -> dict[str, Any]:
    scenarios = smoke_suite() if mode == "smoke" else scenario_suite()
    planners = (ReadableBaselinePlanner(), GeneratedTablePlanner())
    observations: list[dict[str, Any]] = []
    grouped: dict[str, list[dict[str, Any]]] = {}
    for planner in planners:
        planner_results = [run_scenario(planner, scenario).as_dict() for scenario in scenarios]
        grouped[planner.planner_id] = planner_results
        observations.extend(planner_results)

    candidate_id = GeneratedTablePlanner.planner_id
    baseline_id = ReadableBaselinePlanner.planner_id
    candidate_replay = [
        run_scenario(GeneratedTablePlanner(), scenario).as_dict() for scenario in scenarios
    ]
    deterministic_replay = candidate_replay == grouped[candidate_id]
    checkpoint_probe = checkpoint_corruption_probe()
    schema_validation = validate_experimental_records()

    candidate = aggregate(grouped[candidate_id])
    baseline = aggregate(grouped[baseline_id])
    starts_ratio = float(candidate["pump_starts"]) / max(1.0, float(baseline["pump_starts"]))
    energy_ratio = float(candidate["energy_kwh"]) / max(0.000001, float(baseline["energy_kwh"]))
    comparisons = scenario_comparisons(grouped[baseline_id], grouped[candidate_id])
    per_scenario_pass = all(item["status"] == "PASS" for item in comparisons)
    objective_pass = starts_ratio <= 0.75 and energy_ratio <= 1.10 and per_scenario_pass
    scenario_gates_pass = all(
        not result["safety_violations"]
        and result["sequence_end"] == result["steps"]
        and ("restart" not in result["scenario_id"] or result["restart_performed"])
        for result in grouped[candidate_id]
    )
    hard_gates_pass = (
        scenario_gates_pass
        and deterministic_replay
        and checkpoint_probe["status"] == "PASS"
        and schema_validation["status"] == "PASS"
    )

    summary = {
        "schema_version": "0.2",
        "study_id": "mncs.remote-water-control.development-epoch-2",
        "mode": mode,
        "development_result": "PASS" if hard_gates_pass and objective_pass else "FAIL",
        "formal_mncs_status": "UNKNOWN",
        "formal_mncds_status": "UNKNOWN",
        "protected_evaluation_status": "UNKNOWN",
        "disposition": "REVIEW_REQUIRED",
        "claim_note": (
            "This development run does not claim MNCS-L5 or MNCDS-D3. "
            "Independent protected holdout evaluation, release binding, "
            "and operational evidence remain outstanding."
        ),
        "hard_gates": {
            "scenario_safety": "PASS" if scenario_gates_pass else "FAIL",
            "deterministic_replay": "PASS" if deterministic_replay else "FAIL",
            "checkpoint_corruption_rejection": checkpoint_probe["status"],
            "experimental_schema_validation": schema_validation["status"],
            "per_scenario_regression_limits": "PASS" if per_scenario_pass else "FAIL",
        },
        "checkpoint_probe": checkpoint_probe,
        "schema_validation": schema_validation,
        "objective": {
            "status": "PASS" if objective_pass else "FAIL",
            "candidate_to_baseline_pump_start_ratio": round(starts_ratio, 6),
            "candidate_to_baseline_energy_ratio": round(energy_ratio, 6),
            "required_pump_start_ratio_max": 0.75,
            "required_energy_ratio_max": 1.10,
            "terminal_normalization": (
                "Both planners are charged equivalent duty-pump energy to the "
                "higher terminal storage level before each per-scenario comparison."
            ),
        },
        "scenario_comparisons": comparisons,
        "aggregates": {"baseline": baseline, "candidate": candidate},
        "identities": {
            "planner_spec": sha256(ROOT / "generator" / "planner-spec.json"),
            "generated_planner": sha256(ROOT / "machine" / "generated_planner.py"),
            "safety_kernel": sha256(ROOT / "src" / "water_control" / "safety.py"),
            "simulator": sha256(ROOT / "src" / "water_control" / "simulator.py"),
            "evaluator": sha256(Path(__file__)),
            "preregistration": sha256(ROOT / "preregistration.json"),
        },
        "limitations": [
            "Randomized scenarios are deterministic and repository-visible development scenarios.",
            "The plant model is a bounded digital twin and is not a hydraulic design model.",
            "No live PLC, SCADA, pump, valve, or field network is connected.",
            "The generated planner is a development candidate, not an accepted release artifact.",
            "Protected holdout, independent evaluation, and operational evidence remain open.",
        ],
    }
    if mode == "all":
        output = ROOT / "evidence" / "results"
        output.mkdir(parents=True, exist_ok=True)
        (output / "scenario-results.json").write_text(
            json.dumps({"schema_version": "0.2", "results": observations}, indent=2) + "\n"
        )
        (output / "study-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("smoke", "all"), nargs="?", default="smoke")
    args = parser.parse_args()
    summary = run(args.mode)
    print(json.dumps(summary, indent=2))
    return 0 if summary["development_result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
