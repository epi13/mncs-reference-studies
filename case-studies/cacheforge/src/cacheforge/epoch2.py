from __future__ import annotations

import hashlib
import json
import math
import random
import statistics
from collections.abc import Callable

from cacheforge.model import RequestTrace
from cacheforge.policies import EvictionPolicy, ReferenceLRU, SegmentedLRU
from cacheforge.scenarios import Scenario
from cacheforge.study import PolicyResult, evaluate_policy

CAPACITY_SWEEP = (16, 24, 32, 48)
DEVELOPMENT_SEEDS = tuple(range(1000, 1016))
REQUESTS_PER_SCENARIO = 48

AGGREGATE_RATIO_MAX = 0.98
MEDIAN_RATIO_MAX = 0.98
P95_RATIO_MAX = 1.05
WORST_RATIO_MAX = 1.06
IMPROVED_SCENARIO_FRACTION_MIN = 0.75


def generate_epoch2_scenario(seed: int, capacity_blocks: int) -> Scenario:
    if seed < 0:
        raise ValueError("seed must be non-negative")
    if capacity_blocks not in CAPACITY_SWEEP:
        raise ValueError(f"unsupported epoch-2 capacity: {capacity_blocks}")

    rng = random.Random(seed)
    tenants = tuple(f"tenant-{index}" for index in range(4))
    system_pool = ("assistant", "coding", "research", "analysis")
    hot_systems = system_pool[: 1 + seed % len(system_pool)]
    requests = []

    for index in range(REQUESTS_PER_SCENARIO):
        tenant = rng.choice(tenants)
        system = rng.choice(hot_systems) if rng.random() < 0.70 else f"cold-{seed}-{index // 4}"

        generated_blocks = rng.randint(1, 6)
        cancel_after = 1 if generated_blocks > 1 and rng.random() < 0.12 else None
        requests.append(
            RequestTrace(
                request_id=f"seed-{seed}-request-{index}",
                prompt_blocks=(
                    f"sys:{system}:0",
                    f"sys:{system}:1",
                    f"sys:{system}:2",
                    f"user:{tenant}:{index % 6}:0",
                    f"user:{tenant}:{index % 6}:1",
                ),
                generated_blocks=generated_blocks,
                cancel_after_generated=cancel_after,
            )
        )

    return Scenario(
        scenario_id=f"seeded-{seed}-capacity-{capacity_blocks}",
        capacity_blocks=capacity_blocks,
        requests=tuple(requests),
        purpose="paired seeded prefix-reuse, cancellation, and request-length stress",
    )


def epoch2_scenarios() -> tuple[Scenario, ...]:
    return tuple(
        generate_epoch2_scenario(seed, capacity)
        for seed in DEVELOPMENT_SEEDS
        for capacity in CAPACITY_SWEEP
    )


def _nearest_rank(values: list[float], percentile: float) -> float:
    if not values:
        return 1.0
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index]


def _metric(result: PolicyResult, scenario_id: str, name: str) -> int:
    return int(result.scenarios[scenario_id][name])


def _scenario_seed(scenario_id: str) -> int | None:
    parts = scenario_id.split("-")
    if len(parts) != 4 or parts[0] != "seeded" or parts[2] != "capacity":
        return None
    try:
        return int(parts[1])
    except ValueError:
        return None


def _new_bucket() -> dict[str, object]:
    return {
        "scenario_count": 0,
        "lru_recomputed_blocks": 0,
        "segmented_lru_recomputed_blocks": 0,
        "candidate_recomputed_blocks": 0,
        "strongest_baseline_recomputed_blocks": 0,
        "ratios": [],
        "improved": 0,
        "tied": 0,
        "regressed": 0,
    }


def _add_to_bucket(
    bucket: dict[str, object],
    *,
    lru_recomputed: int,
    segmented_recomputed: int,
    candidate_recomputed: int,
    strongest_recomputed: int,
    ratio: float,
    relation: str,
) -> None:
    bucket["scenario_count"] = int(bucket["scenario_count"]) + 1
    for name, value in (
        ("lru_recomputed_blocks", lru_recomputed),
        ("segmented_lru_recomputed_blocks", segmented_recomputed),
        ("candidate_recomputed_blocks", candidate_recomputed),
        ("strongest_baseline_recomputed_blocks", strongest_recomputed),
    ):
        bucket[name] = int(bucket[name]) + value
    ratios = bucket["ratios"]
    assert isinstance(ratios, list)
    ratios.append(ratio)
    key = relation.lower()
    bucket[key] = int(bucket[key]) + 1


def _finalize_bucket(bucket: dict[str, object]) -> dict[str, int | float | bool]:
    ratios = bucket["ratios"]
    assert isinstance(ratios, list)
    candidate_total = int(bucket["candidate_recomputed_blocks"])
    strongest_total = int(bucket["strongest_baseline_recomputed_blocks"])
    ratio = candidate_total / strongest_total if strongest_total else 1.0
    return {
        **{name: int(value) for name, value in bucket.items() if name != "ratios"},
        "candidate_to_strongest_baseline_ratio": round(ratio, 6),
        "median_scenario_ratio": round(statistics.median(ratios), 6) if ratios else 1.0,
        "aggregate_non_regressive": ratio <= 1.0,
    }


def summarize_policy_results(
    scenarios: tuple[Scenario, ...],
    lru: PolicyResult,
    segmented: PolicyResult,
    candidate: PolicyResult,
) -> dict[str, object]:
    observations: dict[str, dict[str, object]] = {}
    ratios: list[float] = []
    by_capacity: dict[int, dict[str, object]] = {}
    by_seed: dict[int, dict[str, object]] = {}
    by_hot_prefix_families: dict[int, dict[str, object]] = {}
    high_capacity_by_hot_prefix_families: dict[int, dict[str, object]] = {}
    totals = {
        "lru_recomputed_blocks": 0,
        "segmented_lru_recomputed_blocks": 0,
        "candidate_recomputed_blocks": 0,
        "strongest_baseline_recomputed_blocks": 0,
    }
    improved = 0
    tied = 0
    regressed = 0

    for scenario in scenarios:
        scenario_id = scenario.scenario_id
        lru_recomputed = _metric(lru, scenario_id, "recomputed_blocks")
        segmented_recomputed = _metric(segmented, scenario_id, "recomputed_blocks")
        candidate_recomputed = _metric(candidate, scenario_id, "recomputed_blocks")
        strongest_recomputed = min(lru_recomputed, segmented_recomputed)
        strongest_baseline_id = (
            lru.policy_id if lru_recomputed <= segmented_recomputed else segmented.policy_id
        )
        ratio = candidate_recomputed / strongest_recomputed if strongest_recomputed else 1.0
        ratios.append(ratio)

        if candidate_recomputed < strongest_recomputed:
            relation = "IMPROVED"
            improved += 1
        elif candidate_recomputed == strongest_recomputed:
            relation = "TIED"
            tied += 1
        else:
            relation = "REGRESSED"
            regressed += 1

        seed = _scenario_seed(scenario_id)
        hot_prefix_families = 1 + seed % 4 if seed is not None else None
        observations[scenario_id] = {
            "seed": seed,
            "hot_prefix_families": hot_prefix_families,
            "capacity_blocks": scenario.capacity_blocks,
            "request_count": len(scenario.requests),
            "configured_cancellation_count": sum(
                request.cancel_after_generated is not None for request in scenario.requests
            ),
            "lru_recomputed_blocks": lru_recomputed,
            "segmented_lru_recomputed_blocks": segmented_recomputed,
            "candidate_recomputed_blocks": candidate_recomputed,
            "strongest_baseline_id": strongest_baseline_id,
            "strongest_baseline_recomputed_blocks": strongest_recomputed,
            "candidate_to_strongest_baseline_ratio": round(ratio, 6),
            "relation_to_strongest_baseline": relation,
            "lru_final_state_digest": lru.scenarios[scenario_id]["final_state_digest"],
            "segmented_lru_final_state_digest": segmented.scenarios[scenario_id][
                "final_state_digest"
            ],
            "candidate_final_state_digest": candidate.scenarios[scenario_id]["final_state_digest"],
        }

        totals["lru_recomputed_blocks"] += lru_recomputed
        totals["segmented_lru_recomputed_blocks"] += segmented_recomputed
        totals["candidate_recomputed_blocks"] += candidate_recomputed
        totals["strongest_baseline_recomputed_blocks"] += strongest_recomputed

        bucket_args = {
            "lru_recomputed": lru_recomputed,
            "segmented_recomputed": segmented_recomputed,
            "candidate_recomputed": candidate_recomputed,
            "strongest_recomputed": strongest_recomputed,
            "ratio": ratio,
            "relation": relation,
        }
        _add_to_bucket(
            by_capacity.setdefault(scenario.capacity_blocks, _new_bucket()), **bucket_args
        )
        if seed is not None and hot_prefix_families is not None:
            _add_to_bucket(by_seed.setdefault(seed, _new_bucket()), **bucket_args)
            _add_to_bucket(
                by_hot_prefix_families.setdefault(hot_prefix_families, _new_bucket()),
                **bucket_args,
            )
            if scenario.capacity_blocks == max(CAPACITY_SWEEP):
                _add_to_bucket(
                    high_capacity_by_hot_prefix_families.setdefault(
                        hot_prefix_families, _new_bucket()
                    ),
                    **bucket_args,
                )

    scenario_count = len(scenarios)
    aggregate_ratio = (
        totals["candidate_recomputed_blocks"] / totals["strongest_baseline_recomputed_blocks"]
        if totals["strongest_baseline_recomputed_blocks"]
        else 1.0
    )
    improved_fraction = improved / scenario_count if scenario_count else 0.0

    capacity_summary = {
        str(capacity): _finalize_bucket(bucket) for capacity, bucket in sorted(by_capacity.items())
    }
    all_capacity_aggregates_non_regressive = all(
        bool(bucket["aggregate_non_regressive"]) for bucket in capacity_summary.values()
    )
    seed_summary = {str(seed): _finalize_bucket(bucket) for seed, bucket in sorted(by_seed.items())}
    hot_prefix_summary = {
        str(count): _finalize_bucket(bucket)
        for count, bucket in sorted(by_hot_prefix_families.items())
    }
    high_capacity_summary = {
        str(count): _finalize_bucket(bucket)
        for count, bucket in sorted(high_capacity_by_hot_prefix_families.items())
    }

    favorable_seed_aggregates = sum(
        bool(bucket["aggregate_non_regressive"]) for bucket in seed_summary.values()
    )
    all_capacities_improved = sum(
        int(bucket["improved"]) == len(CAPACITY_SWEEP) for bucket in seed_summary.values()
    )
    seeds_with_any_regression = sum(
        int(bucket["regressed"]) > 0 for bucket in seed_summary.values()
    )
    maximum_regressed_capacities = max(
        (int(bucket["regressed"]) for bucket in seed_summary.values()), default=0
    )

    mean_ratio = statistics.mean(ratios) if ratios else 1.0
    median_ratio = statistics.median(ratios) if ratios else 1.0
    p95_ratio = _nearest_rank(ratios, 0.95)
    worst_ratio = max(ratios, default=1.0)
    gates = {
        "aggregate_ratio_at_most_0_98": aggregate_ratio <= AGGREGATE_RATIO_MAX,
        "median_ratio_at_most_0_98": median_ratio <= MEDIAN_RATIO_MAX,
        "p95_ratio_at_most_1_05": p95_ratio <= P95_RATIO_MAX,
        "worst_ratio_at_most_1_06": worst_ratio <= WORST_RATIO_MAX,
        "improved_scenario_fraction_at_least_0_75": improved_fraction
        >= IMPROVED_SCENARIO_FRACTION_MIN,
        "all_capacity_aggregates_non_regressive": all_capacity_aggregates_non_regressive,
        "candidate_used_no_fallback": int(candidate.aggregate["fallback_uses"]) == 0,
        "candidate_proposals_all_valid": int(candidate.aggregate["rejected_proposals"]) == 0,
    }
    observation_digest = hashlib.sha256(
        json.dumps(observations, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    return {
        "status": "PASS" if all(gates.values()) else "FAIL",
        "gates": {name: "PASS" if passed else "FAIL" for name, passed in gates.items()},
        "aggregate": {
            **totals,
            "candidate_to_strongest_baseline_ratio": round(aggregate_ratio, 6),
            "mean_scenario_ratio": round(mean_ratio, 6),
            "median_scenario_ratio": round(median_ratio, 6),
            "p95_scenario_ratio": round(p95_ratio, 6),
            "worst_scenario_ratio": round(worst_ratio, 6),
            "improved_scenarios": improved,
            "tied_scenarios": tied,
            "regressed_scenarios": regressed,
            "improved_scenario_fraction": round(improved_fraction, 6),
            "candidate_fallback_uses": int(candidate.aggregate["fallback_uses"]),
            "candidate_rejected_proposals": int(candidate.aggregate["rejected_proposals"]),
        },
        "by_capacity": capacity_summary,
        "by_seed": seed_summary,
        "seed_cluster_summary": {
            "independent_seed_count": len(seed_summary),
            "favorable_seed_aggregates": favorable_seed_aggregates,
            "all_capacities_improved_seeds": all_capacities_improved,
            "seeds_with_any_regression": seeds_with_any_regression,
            "maximum_regressed_capacities_for_one_seed": maximum_regressed_capacities,
        },
        "by_hot_prefix_families": hot_prefix_summary,
        "high_capacity_regime": {
            "capacity_blocks": max(CAPACITY_SWEEP),
            "by_hot_prefix_families": high_capacity_summary,
        },
        "observations": observations,
        "scenario_observation_digest": f"sha256:{observation_digest}",
    }


def evaluate_epoch2(
    candidate_factory: Callable[[], EvictionPolicy],
) -> dict[str, object]:
    scenarios = epoch2_scenarios()
    lru = evaluate_policy(ReferenceLRU, scenarios)
    segmented = evaluate_policy(SegmentedLRU, scenarios)
    candidate = evaluate_policy(candidate_factory, scenarios)
    summary = summarize_policy_results(scenarios, lru, segmented, candidate)
    return {
        "schema_version": "0.3",
        "study_id": "mncs.cacheforge.kv-cache.epoch-2-development.v1",
        "mode": "repository-visible-seeded-development",
        "development_result": summary["status"],
        "formal_mncs_status": "UNKNOWN",
        "formal_mncds_status": "UNKNOWN",
        "disposition": "REVIEW_REQUIRED",
        "promotion_authorized": False,
        "candidate_id": candidate.policy_id,
        "baseline_ids": [lru.policy_id, segmented.policy_id],
        "workload": {
            "seeds": list(DEVELOPMENT_SEEDS),
            "capacity_blocks": list(CAPACITY_SWEEP),
            "independent_trace_count": len(DEVELOPMENT_SEEDS),
            "capacity_repeated_evaluation_count": len(scenarios),
            "scenario_count": len(scenarios),
            "requests_per_scenario": REQUESTS_PER_SCENARIO,
            "total_requests": len(scenarios) * REQUESTS_PER_SCENARIO,
            "paired_capacity_sweep": True,
        },
        **summary,
        "limitations": [
            "All epoch-2 seeded scenarios remain repository-visible development evidence.",
            "The 64 evaluations contain 16 independent traces repeated at four capacities.",
            "The seeded generator is deterministic and is not a blind third-party holdout.",
            "The simulator processes requests sequentially and does not model continuous batching.",
            "The simulator does not execute a model or allocate accelerator memory.",
            "Candidate weights remain human-specified rather than learned from protected traces.",
            "A development PASS cannot promote formal MNCS or MNCDS status.",
        ],
    }
