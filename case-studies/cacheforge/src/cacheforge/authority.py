from __future__ import annotations

from dataclasses import dataclass, field

from cacheforge.model import CacheState, StudyMetrics
from cacheforge.policies import EvictionPolicy, ReferenceLRU


@dataclass
class AllocationAuthority:
    fallback_policy: EvictionPolicy = field(default_factory=ReferenceLRU)

    def authorize_eviction(
        self,
        state: CacheState,
        policy: EvictionPolicy,
        required: int,
        metrics: StudyMetrics,
    ) -> list[int]:
        if required < 1:
            return []
        metrics.planner_calls += 1
        proposal, inspected = policy.propose(state, required)
        metrics.planner_candidates_inspected += inspected
        if self._valid(state, proposal, required):
            return proposal[:required]

        metrics.rejected_proposals += 1
        metrics.fallback_uses += 1
        fallback, fallback_inspected = self.fallback_policy.propose(state, required)
        metrics.planner_candidates_inspected += fallback_inspected
        if not self._valid(state, fallback, required):
            raise RuntimeError("no valid eviction plan is available")
        return fallback[:required]

    @staticmethod
    def _valid(state: CacheState, proposal: list[int], required: int) -> bool:
        if len(proposal) < required:
            return False
        if len(set(proposal)) != len(proposal):
            return False
        selected = proposal[:required]
        for block_id in selected:
            block = state.blocks.get(block_id)
            if block is None or block.owners:
                return False
        return True
