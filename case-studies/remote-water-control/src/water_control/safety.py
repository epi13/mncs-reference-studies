# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import math

from water_control.model import (
    Adjudication,
    ControllerState,
    ControlMode,
    PlannerProposal,
    SystemConfig,
    TelemetryQuality,
    TelemetrySample,
)


class SafetyKernel:
    """Readable authority boundary that can reject or modify planner proposals."""

    def __init__(self, config: SystemConfig) -> None:
        self.config = config

    def authorize(
        self,
        proposal: PlannerProposal,
        sample: TelemetrySample,
        state: ControllerState,
        now_s: int,
    ) -> Adjudication:
        invalid = not all(
            math.isfinite(value) for value in (sample.tank_level_pct, sample.demand_lps)
        )
        invalid = invalid or not 0.0 <= sample.tank_level_pct <= 100.0
        invalid = invalid or sample.demand_lps < 0.0
        if invalid:
            return self._hold(state, ControlMode.HOLD, "invalid telemetry")

        if sample.quality is not TelemetryQuality.GOOD:
            return self._hold(state, ControlMode.DEGRADED, "telemetry quality is not GOOD")
        if sample.age_s > self.config.telemetry_max_age_s:
            return self._hold(state, ControlMode.DEGRADED, "telemetry exceeds freshness limit")
        if not sample.power_available:
            return Adjudication(False, False, ControlMode.EMERGENCY, ("power unavailable",))
        if sample.tank_level_pct >= self.config.high_high_pct:
            return Adjudication(False, False, ControlMode.EMERGENCY, ("high-high tank level",))
        if sample.tank_level_pct <= self.config.low_low_pct:
            return Adjudication(True, True, ControlMode.EMERGENCY, ("low-low tank level",))

        duty_on = proposal.duty_on
        standby_on = proposal.standby_on
        reasons: list[str] = []
        if standby_on and not duty_on:
            duty_on = True
            reasons.append("standby requires duty")

        duty_on, duty_reason = self._apply_dwell(
            requested=duty_on,
            current=state.duty_on,
            last_changed_s=state.duty_last_changed_s,
            now_s=now_s,
        )
        standby_on, standby_reason = self._apply_dwell(
            requested=standby_on,
            current=state.standby_on,
            last_changed_s=state.standby_last_changed_s,
            now_s=now_s,
        )
        if duty_reason:
            reasons.append(f"duty {duty_reason}")
        if standby_reason:
            reasons.append(f"standby {standby_reason}")
        if standby_on and not duty_on:
            standby_on = False
            reasons.append("standby removed after duty dwell adjudication")
        if not reasons:
            reasons.append("proposal accepted")
        return Adjudication(duty_on, standby_on, ControlMode.NORMAL, tuple(reasons))

    def _apply_dwell(
        self,
        *,
        requested: bool,
        current: bool,
        last_changed_s: int,
        now_s: int,
    ) -> tuple[bool, str | None]:
        if requested == current:
            return current, None
        elapsed = now_s - last_changed_s
        minimum = self.config.min_on_s if current else self.config.min_off_s
        if elapsed < minimum:
            return current, f"minimum dwell retained for {minimum - elapsed}s"
        return requested, None

    @staticmethod
    def _hold(
        state: ControllerState,
        mode: ControlMode,
        reason: str,
    ) -> Adjudication:
        return Adjudication(state.duty_on, state.standby_on, mode, (reason,))
