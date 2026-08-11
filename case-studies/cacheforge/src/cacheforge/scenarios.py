from __future__ import annotations

from dataclasses import dataclass

from cacheforge.model import GroupSpec, RequestTrace

DEFAULT_GROUPS = (
    GroupSpec(name="full", mode="full"),
    GroupSpec(name="sliding", mode="sliding", window_blocks=2),
)


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    capacity_blocks: int
    requests: tuple[RequestTrace, ...]
    purpose: str


def _shared_request(
    request_id: str,
    system: str,
    user: str,
    generated: int = 3,
    cancel_after: int | None = None,
) -> RequestTrace:
    return RequestTrace(
        request_id=request_id,
        prompt_blocks=(
            f"sys:{system}:0",
            f"sys:{system}:1",
            f"sys:{system}:2",
            f"user:{user}:0",
            f"user:{user}:1",
        ),
        generated_blocks=generated,
        cancel_after_generated=cancel_after,
    )


def development_scenarios() -> tuple[Scenario, ...]:
    burst = tuple(
        _shared_request(f"burst-{index}", "assistant", f"u{index}", generated=4)
        for index in range(12)
    )
    alternating = tuple(
        _shared_request(
            f"tenant-{index}",
            "coding" if index % 2 == 0 else "research",
            f"tenant-{index}",
            generated=3,
        )
        for index in range(16)
    )
    cancellation = tuple(
        _shared_request(
            f"cancel-{index}",
            "assistant",
            f"cancel-user-{index}",
            generated=5,
            cancel_after=1 if index % 3 == 0 else None,
        )
        for index in range(9)
    )
    unique = tuple(
        RequestTrace(
            request_id=f"unique-{index}",
            prompt_blocks=tuple(f"unique:{index}:{block}" for block in range(5)),
            generated_blocks=2,
        )
        for index in range(10)
    )
    return (
        Scenario("shared-prefix-burst", 24, burst, "repeated system prompt under tail pressure"),
        Scenario("alternating-tenants", 28, alternating, "two reusable tenant prefixes"),
        Scenario("cancellation-pressure", 24, cancellation, "atomic release during cancellation"),
        Scenario("low-reuse-control", 24, unique, "control workload without reusable prefixes"),
    )


def smoke_scenarios() -> tuple[Scenario, ...]:
    return development_scenarios()[:1]
