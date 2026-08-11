# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class TelemetryQuality(StrEnum):
    GOOD = "GOOD"
    STALE = "STALE"
    CONFLICT = "CONFLICT"


class ControlMode(StrEnum):
    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"
    HOLD = "HOLD"
    EMERGENCY = "EMERGENCY"


@dataclass(frozen=True)
class SystemConfig:
    tank_capacity_l: float = 100_000.0
    duty_flow_lps: float = 4.0
    standby_flow_lps: float = 3.0
    duty_power_kw: float = 7.5
    standby_power_kw: float = 5.5
    low_low_pct: float = 15.0
    high_high_pct: float = 90.0
    min_on_s: int = 600
    min_off_s: int = 300
    telemetry_max_age_s: int = 180
    intent_ttl_s: int = 120


@dataclass(frozen=True)
class TelemetrySample:
    observed_at_s: int
    received_at_s: int
    tank_level_pct: float
    demand_lps: float
    power_available: bool
    quality: TelemetryQuality = TelemetryQuality.GOOD

    @property
    def age_s(self) -> int:
        return max(0, self.received_at_s - self.observed_at_s)


@dataclass(frozen=True)
class PlannerProposal:
    duty_on: bool
    standby_on: bool
    reason: str
    planner_id: str


@dataclass(frozen=True)
class Adjudication:
    duty_on: bool
    standby_on: bool
    mode: ControlMode
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class AuthorizedIntent:
    sequence: int
    issued_at_s: int
    expires_at_s: int
    duty_on: bool
    standby_on: bool
    mode: ControlMode
    planner_id: str
    proposal_reason: str
    safety_reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["mode"] = self.mode.value
        payload["safety_reasons"] = list(self.safety_reasons)
        return payload


@dataclass
class ControllerState:
    duty_on: bool = False
    standby_on: bool = False
    duty_last_changed_s: int = -10_000
    standby_last_changed_s: int = -10_000
    last_sequence: int = 0
    last_mode: ControlMode = ControlMode.NORMAL

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["last_mode"] = self.last_mode.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ControllerState:
        return cls(
            duty_on=bool(payload["duty_on"]),
            standby_on=bool(payload["standby_on"]),
            duty_last_changed_s=int(payload["duty_last_changed_s"]),
            standby_last_changed_s=int(payload["standby_last_changed_s"]),
            last_sequence=int(payload["last_sequence"]),
            last_mode=ControlMode(payload["last_mode"]),
        )


@dataclass
class PlantState:
    tank_volume_l: float
    duty_running: bool = False
    standby_running: bool = False
    energy_kwh: float = 0.0
    duty_starts: int = 0
    standby_starts: int = 0
    unmet_demand_l: float = 0.0
    overflow_l: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> PlantState:
        return cls(
            tank_volume_l=float(payload["tank_volume_l"]),
            duty_running=bool(payload["duty_running"]),
            standby_running=bool(payload["standby_running"]),
            energy_kwh=float(payload["energy_kwh"]),
            duty_starts=int(payload["duty_starts"]),
            standby_starts=int(payload["standby_starts"]),
            unmet_demand_l=float(payload["unmet_demand_l"]),
            overflow_l=float(payload["overflow_l"]),
        )


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    duration_s: int
    step_s: int
    initial_level_pct: float
    demand_profile: tuple[tuple[int, int, float], ...]
    power_outages: tuple[tuple[int, int], ...] = ()
    stale_windows: tuple[tuple[int, int], ...] = ()
    conflict_windows: tuple[tuple[int, int], ...] = ()
    restart_at_s: int | None = None
    observed_demand_scale: float = 1.0
    randomized: bool = False
    seed: int | None = None


@dataclass
class ScenarioResult:
    scenario_id: str
    planner_id: str
    steps: int
    initial_level_pct: float
    final_level_pct: float
    energy_kwh: float
    pump_starts: int
    unmet_demand_l: float
    overflow_l: float
    emergency_steps: int
    degraded_steps: int
    safety_interventions: dict[str, int] = field(default_factory=dict)
    safety_violations: list[str] = field(default_factory=list)
    sequence_end: int = 0
    journal_tail_hash: str = ""
    restart_performed: bool = False
    randomized: bool = False
    seed: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
