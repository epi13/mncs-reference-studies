from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from cacheforge.model import CacheBlock, CacheState


class EvictionPolicy(Protocol):
    policy_id: str

    def propose(self, state: CacheState, required: int) -> tuple[list[int], int]: ...


def _evictable(state: CacheState) -> list[CacheBlock]:
    return [block for block in state.blocks.values() if not block.owners]


@dataclass(frozen=True)
class ReferenceFIFO:
    policy_id: str = "cacheforge.reference.fifo.v1"

    def propose(self, state: CacheState, required: int) -> tuple[list[int], int]:
        candidates = sorted(_evictable(state), key=lambda block: (block.created_at, block.block_id))
        return [block.block_id for block in candidates[:required]], len(candidates)


@dataclass(frozen=True)
class ReferenceLRU:
    policy_id: str = "cacheforge.baseline.lru.v1"

    def propose(self, state: CacheState, required: int) -> tuple[list[int], int]:
        candidates = sorted(_evictable(state), key=lambda block: (block.last_used, block.block_id))
        return [block.block_id for block in candidates[:required]], len(candidates)


@dataclass(frozen=True)
class SegmentedLRU:
    policy_id: str = "cacheforge.readable.segmented-lru.v1"

    def propose(self, state: CacheState, required: int) -> tuple[list[int], int]:
        candidates = _evictable(state)

        def rank(block: CacheBlock) -> tuple[int, int, int]:
            segment = 0 if block.kind == "generated" else 1
            return (segment, block.last_used, block.block_id)

        candidates.sort(key=rank)
        return [block.block_id for block in candidates[:required]], len(candidates)


@dataclass(frozen=True)
class InvalidDuplicatePolicy:
    policy_id: str = "cacheforge.mutation.duplicate-victim"

    def propose(self, state: CacheState, required: int) -> tuple[list[int], int]:
        candidates = _evictable(state)
        if not candidates:
            return [], 0
        return [candidates[0].block_id] * max(required, 2), len(candidates)


@dataclass(frozen=True)
class InvalidUnknownPolicy:
    policy_id: str = "cacheforge.mutation.unknown-victim"

    def propose(self, state: CacheState, required: int) -> tuple[list[int], int]:
        return [state.next_block_id + 1000 + index for index in range(required)], len(state.blocks)
