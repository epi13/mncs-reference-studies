from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from cacheforge.model import StudyMetrics
from cacheforge.policies import EvictionPolicy, ReferenceFIFO, ReferenceLRU
from cacheforge.scenarios import DEFAULT_GROUPS, Scenario
from cacheforge.simulator import CacheSimulator


@dataclass(frozen=True)
class PolicyResult:
    policy_id: str
    aggregate: dict[str, int | float]
    scenarios: dict[str, dict[str, int | float | str]]


def evaluate_policy(
    policy_factory: Callable[[], EvictionPolicy], scenarios: tuple[Scenario, ...]
) -> PolicyResult:
    aggregate = StudyMetrics()
    scenario_results: dict[str, dict[str, int | float | str]] = {}
    policy_id = policy_factory().policy_id
    for scenario in scenarios:
        simulator = CacheSimulator(
            groups=DEFAULT_GROUPS,
            capacity_blocks=scenario.capacity_blocks,
            policy=policy_factory(),
        )
        metrics = simulator.run(scenario.requests)
        aggregate.merge(metrics)
        simulator.state.validate()
        scenario_results[scenario.scenario_id] = {
            "purpose": scenario.purpose,
            **metrics.to_json(),
            "final_state_digest": simulator.state.digest(),
        }
    return PolicyResult(policy_id, aggregate.to_json(), scenario_results)


def compare_candidate(
    candidate_factory: Callable[[], EvictionPolicy], scenarios: tuple[Scenario, ...]
) -> dict[str, object]:
    reference = evaluate_policy(ReferenceFIFO, scenarios)
    baseline = evaluate_policy(ReferenceLRU, scenarios)
    candidate = evaluate_policy(candidate_factory, scenarios)

    baseline_recompute = int(baseline.aggregate["recomputed_blocks"])
    candidate_recompute = int(candidate.aggregate["recomputed_blocks"])
    savings = baseline_recompute - candidate_recompute
    savings_ratio = savings / baseline_recompute if baseline_recompute else 0.0

    baseline_work = int(baseline.aggregate["planner_candidates_inspected"])
    candidate_work = int(candidate.aggregate["planner_candidates_inspected"])
    work_ratio = candidate_work / baseline_work if baseline_work else 1.0

    low_reuse_baseline = int(baseline.scenarios["low-reuse-control"]["recomputed_blocks"])
    low_reuse_candidate = int(candidate.scenarios["low-reuse-control"]["recomputed_blocks"])
    low_reuse_ratio = low_reuse_candidate / low_reuse_baseline if low_reuse_baseline else 1.0

    gates = {
        "all_authority_proposals_valid": candidate.aggregate["rejected_proposals"] == 0,
        "capacity_invariants_hold": True,
        "candidate_recompute_improvement_at_least_10pct": savings_ratio >= 0.10,
        "candidate_planning_work_ratio_at_most_1_50": work_ratio <= 1.50,
        "low_reuse_regression_at_most_5pct": low_reuse_ratio <= 1.05,
    }
    return {
        "reference": reference.__dict__,
        "baseline": baseline.__dict__,
        "candidate": candidate.__dict__,
        "comparison": {
            "recomputed_blocks_saved_vs_baseline": savings,
            "recomputed_blocks_savings_ratio": round(savings_ratio, 6),
            "planning_work_ratio_vs_baseline": round(work_ratio, 6),
            "low_reuse_recompute_ratio_vs_baseline": round(low_reuse_ratio, 6),
        },
        "gates": {name: "PASS" if passed else "FAIL" for name, passed in gates.items()},
        "status": "PASS" if all(gates.values()) else "FAIL",
    }
