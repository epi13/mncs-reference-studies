from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "machine"))

from cacheforge.model import CacheState, RequestTrace  # noqa: E402
from cacheforge.policies import InvalidDuplicatePolicy, SegmentedLRU  # noqa: E402
from cacheforge.scenarios import (  # noqa: E402
    DEFAULT_GROUPS,
    development_scenarios,
    smoke_scenarios,
)
from cacheforge.simulator import CacheSimulator  # noqa: E402
from cacheforge.study import compare_candidate  # noqa: E402
from generated_policy import GeneratedEvictionPolicy  # noqa: E402


def test_generated_policy_is_current() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "tools" / "generate_policy.py"), "--check"],
        check=True,
    )


def test_candidate_meets_preregistered_gates() -> None:
    result = compare_candidate(GeneratedEvictionPolicy, development_scenarios())
    assert result["status"] == "PASS", json.dumps(result, indent=2)


def test_capacity_and_ownership_invariants_hold() -> None:
    scenario = development_scenarios()[2]
    simulator = CacheSimulator(DEFAULT_GROUPS, scenario.capacity_blocks, GeneratedEvictionPolicy())
    simulator.run(scenario.requests)
    simulator.state.validate()
    assert len(simulator.state.blocks) <= scenario.capacity_blocks
    assert all(not block.owners for block in simulator.state.blocks.values())
    assert simulator.metrics.cancelled_requests > 0


def test_invalid_machine_proposal_falls_back_without_corruption() -> None:
    scenario = smoke_scenarios()[0]
    simulator = CacheSimulator(DEFAULT_GROUPS, scenario.capacity_blocks, InvalidDuplicatePolicy())
    simulator.run(scenario.requests)
    simulator.state.validate()
    assert simulator.metrics.rejected_proposals > 0
    assert simulator.metrics.fallback_uses == simulator.metrics.rejected_proposals


def test_checkpoint_round_trip_matches_uninterrupted_execution() -> None:
    scenario = development_scenarios()[0]
    split = 5
    staged = CacheSimulator(DEFAULT_GROUPS, scenario.capacity_blocks, GeneratedEvictionPolicy())
    staged.run(scenario.requests[:split])
    checkpoint = staged.checkpoint()

    restored = CacheSimulator(DEFAULT_GROUPS, scenario.capacity_blocks, GeneratedEvictionPolicy())
    restored.restore_state(checkpoint)
    restored.run(scenario.requests[split:])

    uninterrupted = CacheSimulator(
        DEFAULT_GROUPS, scenario.capacity_blocks, GeneratedEvictionPolicy()
    )
    uninterrupted.run(scenario.requests)
    assert restored.state.digest() == uninterrupted.state.digest()


def test_checkpoint_rejects_policy_identity_change() -> None:
    scenario = smoke_scenarios()[0]
    source = CacheSimulator(DEFAULT_GROUPS, scenario.capacity_blocks, GeneratedEvictionPolicy())
    source.run(scenario.requests[:2])
    target = CacheSimulator(DEFAULT_GROUPS, scenario.capacity_blocks, SegmentedLRU())
    with pytest.raises(ValueError, match="policy identity mismatch"):
        target.restore_state(source.checkpoint())


def test_cache_state_restore_rejects_duplicate_identity() -> None:
    payload = {
        "capacity_blocks": 2,
        "clock": 1,
        "next_block_id": 2,
        "blocks": [
            {
                "block_id": 0,
                "group": "full",
                "key": "same",
                "kind": "prompt",
                "shared": False,
                "created_at": 1,
                "last_used": 1,
                "reuse_count": 0,
                "owners": [],
            },
            {
                "block_id": 1,
                "group": "full",
                "key": "same",
                "kind": "prompt",
                "shared": False,
                "created_at": 1,
                "last_used": 1,
                "reuse_count": 0,
                "owners": [],
            },
        ],
    }
    with pytest.raises(ValueError):
        CacheState.restore(payload)


def test_request_validation_rejects_invalid_cancel_point() -> None:
    with pytest.raises(ValueError):
        RequestTrace("bad", ("p0",), generated_blocks=1, cancel_after_generated=2)
