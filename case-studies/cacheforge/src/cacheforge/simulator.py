from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass

from cacheforge.authority import AllocationAuthority
from cacheforge.model import CacheBlock, CacheState, GroupSpec, RequestTrace, StudyMetrics
from cacheforge.policies import EvictionPolicy


@dataclass
class CacheSimulator:
    groups: tuple[GroupSpec, ...]
    capacity_blocks: int
    policy: EvictionPolicy

    def __post_init__(self) -> None:
        if not self.groups:
            raise ValueError("at least one cache group is required")
        self.state = CacheState(capacity_blocks=self.capacity_blocks)
        self.metrics = StudyMetrics()
        self.authority = AllocationAuthority()

    def run(self, requests: Iterable[RequestTrace]) -> StudyMetrics:
        for request in requests:
            self.process(request)
        self.state.validate()
        return self.metrics

    def process(self, request: RequestTrace) -> None:
        self.metrics.requests += 1
        owned: set[int] = set()
        sliding_windows: dict[str, deque[int]] = {
            group.name: deque() for group in self.groups if group.mode == "sliding"
        }

        for prompt_key in request.prompt_blocks:
            for group in self.groups:
                block_id = self._access(
                    request=request,
                    group=group,
                    key=prompt_key,
                    kind="prompt",
                    shared=prompt_key.startswith("sys:"),
                )
                owned.add(block_id)
                self._advance_sliding(group, block_id, request.request_id, sliding_windows, owned)

        for generated_index in range(request.generated_blocks):
            if request.cancel_after_generated == generated_index:
                self.metrics.cancelled_requests += 1
                break
            generated_key = f"gen:{request.request_id}:{generated_index}"
            for group in self.groups:
                block_id = self._access(
                    request=request,
                    group=group,
                    key=generated_key,
                    kind="generated",
                    shared=False,
                )
                owned.add(block_id)
                self._advance_sliding(group, block_id, request.request_id, sliding_windows, owned)
        else:
            if request.cancel_after_generated == request.generated_blocks:
                self.metrics.cancelled_requests += 1

        for block_id in tuple(owned):
            block = self.state.blocks.get(block_id)
            if block is not None:
                block.owners.discard(request.request_id)
        self.state.validate()

    def checkpoint(self) -> dict[str, object]:
        return {
            "policy_id": self.policy.policy_id,
            "groups": [group.__dict__ for group in self.groups],
            "state": self.state.snapshot(),
            "metrics": self.metrics.to_json(),
        }

    def restore_state(self, checkpoint: dict[str, object]) -> None:
        if checkpoint.get("policy_id") != self.policy.policy_id:
            raise ValueError("checkpoint policy identity mismatch")
        raw_state = checkpoint.get("state")
        if not isinstance(raw_state, dict):
            raise ValueError("checkpoint state is missing")
        self.state = CacheState.restore(raw_state)

    def _access(
        self,
        request: RequestTrace,
        group: GroupSpec,
        key: str,
        kind: str,
        shared: bool,
    ) -> int:
        now = self.state.tick()
        identity = (group.name, key)
        existing_id = self.state.key_index.get(identity)
        if existing_id is not None:
            block = self.state.blocks[existing_id]
            block.last_used = now
            block.reuse_count += 1
            block.owners.add(request.request_id)
            self.metrics.hits += 1
            return existing_id

        self.metrics.misses += 1
        self.metrics.recomputed_blocks += 1
        if len(self.state.blocks) >= self.state.capacity_blocks:
            victims = self.authority.authorize_eviction(
                state=self.state,
                policy=self.policy,
                required=1,
                metrics=self.metrics,
            )
            for victim_id in victims:
                self._evict(victim_id)

        block_id = self.state.next_block_id
        self.state.next_block_id += 1
        block = CacheBlock(
            block_id=block_id,
            group=group.name,
            key=key,
            kind=kind,
            shared=shared,
            created_at=now,
            last_used=now,
            owners={request.request_id},
        )
        self.state.blocks[block_id] = block
        self.state.key_index[identity] = block_id
        self.metrics.peak_resident_blocks = max(
            self.metrics.peak_resident_blocks, len(self.state.blocks)
        )
        return block_id

    def _evict(self, block_id: int) -> None:
        block = self.state.blocks[block_id]
        if block.owners:
            raise RuntimeError("authority attempted to evict a live block")
        del self.state.blocks[block_id]
        del self.state.key_index[(block.group, block.key)]
        self.metrics.evictions += 1

    def _advance_sliding(
        self,
        group: GroupSpec,
        block_id: int,
        request_id: str,
        windows: dict[str, deque[int]],
        owned: set[int],
    ) -> None:
        if group.mode != "sliding":
            return
        assert group.window_blocks is not None
        window = windows[group.name]
        window.append(block_id)
        while len(window) > group.window_blocks:
            expired_id = window.popleft()
            expired = self.state.blocks.get(expired_id)
            if expired is not None:
                expired.owners.discard(request_id)
            owned.discard(expired_id)
