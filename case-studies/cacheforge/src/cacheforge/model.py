from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from typing import Any


@dataclass(frozen=True)
class GroupSpec:
    name: str
    mode: str
    window_blocks: int | None = None

    def __post_init__(self) -> None:
        if self.mode not in {"full", "sliding"}:
            raise ValueError(f"unsupported group mode: {self.mode}")
        if self.mode == "sliding" and (self.window_blocks is None or self.window_blocks < 1):
            raise ValueError("sliding groups require a positive window_blocks value")
        if self.mode == "full" and self.window_blocks is not None:
            raise ValueError("full groups must not define window_blocks")


@dataclass(frozen=True)
class RequestTrace:
    request_id: str
    prompt_blocks: tuple[str, ...]
    generated_blocks: int
    priority: int = 1
    cancel_after_generated: int | None = None

    def __post_init__(self) -> None:
        if not self.request_id:
            raise ValueError("request_id must not be empty")
        if not self.prompt_blocks:
            raise ValueError("prompt_blocks must not be empty")
        if self.generated_blocks < 0:
            raise ValueError("generated_blocks must be non-negative")
        if self.priority < 0:
            raise ValueError("priority must be non-negative")
        if self.cancel_after_generated is not None and (
            self.cancel_after_generated < 0 or self.cancel_after_generated > self.generated_blocks
        ):
            raise ValueError("cancel_after_generated is outside the generated block range")


@dataclass
class CacheBlock:
    block_id: int
    group: str
    key: str
    kind: str
    shared: bool
    created_at: int
    last_used: int
    reuse_count: int = 0
    owners: set[str] = field(default_factory=set)

    def to_json(self) -> dict[str, Any]:
        result = asdict(self)
        result["owners"] = sorted(self.owners)
        return result

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> CacheBlock:
        return cls(
            block_id=int(payload["block_id"]),
            group=str(payload["group"]),
            key=str(payload["key"]),
            kind=str(payload["kind"]),
            shared=bool(payload["shared"]),
            created_at=int(payload["created_at"]),
            last_used=int(payload["last_used"]),
            reuse_count=int(payload["reuse_count"]),
            owners=set(str(owner) for owner in payload["owners"]),
        )


@dataclass
class CacheState:
    capacity_blocks: int
    clock: int = 0
    next_block_id: int = 0
    blocks: dict[int, CacheBlock] = field(default_factory=dict)
    key_index: dict[tuple[str, str], int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.capacity_blocks < 1:
            raise ValueError("capacity_blocks must be positive")

    def tick(self) -> int:
        self.clock += 1
        return self.clock

    def digest(self) -> str:
        payload = self.snapshot()
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return sha256(canonical).hexdigest()

    def snapshot(self) -> dict[str, Any]:
        return {
            "capacity_blocks": self.capacity_blocks,
            "clock": self.clock,
            "next_block_id": self.next_block_id,
            "blocks": [self.blocks[block_id].to_json() for block_id in sorted(self.blocks)],
        }

    @classmethod
    def restore(cls, payload: dict[str, Any]) -> CacheState:
        state = cls(
            capacity_blocks=int(payload["capacity_blocks"]),
            clock=int(payload["clock"]),
            next_block_id=int(payload["next_block_id"]),
        )
        for raw_block in payload["blocks"]:
            block = CacheBlock.from_json(raw_block)
            state.blocks[block.block_id] = block
            state.key_index[(block.group, block.key)] = block.block_id
        state.validate()
        return state

    def validate(self) -> None:
        if len(self.blocks) > self.capacity_blocks:
            raise ValueError("cache capacity exceeded")
        if len(self.key_index) != len(self.blocks):
            raise ValueError("key index cardinality mismatch")
        seen_keys: set[tuple[str, str]] = set()
        for block_id, block in self.blocks.items():
            if block_id != block.block_id:
                raise ValueError("block id mismatch")
            identity = (block.group, block.key)
            if identity in seen_keys:
                raise ValueError("duplicate cache identity")
            seen_keys.add(identity)
            if self.key_index.get(identity) != block_id:
                raise ValueError("key index points to the wrong block")
            if block.kind not in {"prompt", "generated"}:
                raise ValueError("unsupported block kind")
            if block.created_at > block.last_used or block.last_used > self.clock:
                raise ValueError("invalid block timestamps")
            if block.reuse_count < 0:
                raise ValueError("negative reuse count")
        if self.next_block_id < 0:
            raise ValueError("invalid next block id")


@dataclass
class StudyMetrics:
    requests: int = 0
    cancelled_requests: int = 0
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    recomputed_blocks: int = 0
    planner_calls: int = 0
    planner_candidates_inspected: int = 0
    rejected_proposals: int = 0
    fallback_uses: int = 0
    peak_resident_blocks: int = 0

    def merge(self, other: StudyMetrics) -> None:
        for field_name in self.__dataclass_fields__:
            setattr(self, field_name, getattr(self, field_name) + getattr(other, field_name))

    def to_json(self) -> dict[str, int | float]:
        requests = max(self.requests, 1)
        accesses = self.hits + self.misses
        return {
            **asdict(self),
            "hit_rate": round(self.hits / accesses, 6) if accesses else 0.0,
            "recomputed_blocks_per_request": round(self.recomputed_blocks / requests, 6),
        }
