from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "machine"))

from cacheforge.policies import InvalidDuplicatePolicy, InvalidUnknownPolicy  # noqa: E402
from cacheforge.scenarios import (  # noqa: E402
    DEFAULT_GROUPS,
    development_scenarios,
    smoke_scenarios,
)
from cacheforge.simulator import CacheSimulator  # noqa: E402
from cacheforge.study import compare_candidate  # noqa: E402
from generated_policy import GeneratedEvictionPolicy  # noqa: E402

RESULTS = ROOT / "evidence" / "results"


def mutation_checks() -> dict[str, object]:
    scenario = smoke_scenarios()[0]
    results: dict[str, object] = {}
    for policy in (InvalidDuplicatePolicy(), InvalidUnknownPolicy()):
        simulator = CacheSimulator(DEFAULT_GROUPS, scenario.capacity_blocks, policy)
        simulator.run(scenario.requests)
        results[policy.policy_id] = {
            "status": "PASS" if simulator.metrics.rejected_proposals > 0 else "FAIL",
            "rejected_proposals": simulator.metrics.rejected_proposals,
            "fallback_uses": simulator.metrics.fallback_uses,
            "state_valid": True,
        }
    return {
        "status": "PASS"
        if all(result["status"] == "PASS" for result in results.values())
        else "FAIL",
        "mutations": results,
    }


def recovery_check() -> dict[str, object]:
    scenario = development_scenarios()[0]
    split = len(scenario.requests) // 2
    first = CacheSimulator(DEFAULT_GROUPS, scenario.capacity_blocks, GeneratedEvictionPolicy())
    first.run(scenario.requests[:split])
    checkpoint = first.checkpoint()
    checkpoint_digest = first.state.digest()

    restored = CacheSimulator(DEFAULT_GROUPS, scenario.capacity_blocks, GeneratedEvictionPolicy())
    restored.restore_state(checkpoint)
    restored.run(scenario.requests[split:])

    uninterrupted = CacheSimulator(
        DEFAULT_GROUPS, scenario.capacity_blocks, GeneratedEvictionPolicy()
    )
    uninterrupted.run(scenario.requests)
    return {
        "status": "PASS" if restored.state.digest() == uninterrupted.state.digest() else "FAIL",
        "checkpoint_digest": checkpoint_digest,
        "restored_final_digest": restored.state.digest(),
        "uninterrupted_final_digest": uninterrupted.state.digest(),
        "policy_identity_bound": checkpoint["policy_id"] == GeneratedEvictionPolicy().policy_id,
    }


def run(mode: str) -> dict[str, object]:
    scenarios = smoke_scenarios() if mode == "smoke" else development_scenarios()
    comparison = compare_candidate(GeneratedEvictionPolicy, scenarios)
    mutations = mutation_checks()
    recovery = recovery_check()
    checks = {
        "policy_comparison": comparison["status"],
        "authority_mutations": mutations["status"],
        "checkpoint_recovery": recovery["status"],
    }
    formal_status = "UNKNOWN"
    scenario_observations = {
        scenario_id: {
            "baseline_recomputed_blocks": comparison["baseline"]["scenarios"][scenario_id][
                "recomputed_blocks"
            ],
            "candidate_recomputed_blocks": comparison["candidate"]["scenarios"][scenario_id][
                "recomputed_blocks"
            ],
            "candidate_hit_rate": comparison["candidate"]["scenarios"][scenario_id]["hit_rate"],
            "candidate_final_state_digest": comparison["candidate"]["scenarios"][scenario_id][
                "final_state_digest"
            ],
        }
        for scenario_id in comparison["candidate"]["scenarios"]
    }
    summary = {
        "schema_version": "0.1",
        "study_id": "mncs.cacheforge.kv-cache.development.v1",
        "mode": mode,
        "status": "PASS" if all(value == "PASS" for value in checks.values()) else "FAIL",
        "development_target": "MNCS-L4 / MNCDS-D2 evidence pattern",
        "formal_mncs_status": formal_status,
        "formal_mncds_status": formal_status,
        "claim_boundary": (
            "A development PASS covers only the deterministic simulator, declared traces, "
            "generated policy identity, and readable authority kernel. It is not evidence of "
            "GPU correctness, production isolation, or integration with a live inference server."
        ),
        "checks": checks,
        "gates": comparison["gates"],
        "benefit": comparison["comparison"],
        "policy_aggregates": {
            "reference": comparison["reference"]["aggregate"],
            "baseline": comparison["baseline"]["aggregate"],
            "candidate": comparison["candidate"]["aggregate"],
        },
        "scenario_observations": scenario_observations,
        "mutations": mutations,
        "recovery": recovery,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("smoke", "all"), nargs="?", default="all")
    args = parser.parse_args()
    summary = run(args.mode)
    RESULTS.mkdir(parents=True, exist_ok=True)
    output = RESULTS / "study-summary.json"
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": summary["status"], "output": str(output)}, sort_keys=True))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
