# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from bisect import bisect_right
from typing import Protocol

from water_control.model import ControllerState, PlannerProposal, SystemConfig, TelemetrySample

try:
    from generated_planner import (
        DECISION_TABLE,
        DEMAND_BANDS_LPS,
        LEVEL_BANDS_PCT,
        PLANNER_ID,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - configuration error
    raise RuntimeError("machine/ must be present on PYTHONPATH") from exc


class Planner(Protocol):
    planner_id: str

    def propose(
        self,
        sample: TelemetrySample,
        state: ControllerState,
        config: SystemConfig,
    ) -> PlannerProposal: ...


class ReadableBaselinePlanner:
    planner_id = "mncs.remote-water.readable-baseline.v1"

    def propose(
        self,
        sample: TelemetrySample,
        state: ControllerState,
        config: SystemConfig,
    ) -> PlannerProposal:
        del config
        duty_on = state.duty_on
        standby_on = state.standby_on

        if not sample.power_available:
            duty_on = False
            standby_on = False
        elif sample.tank_level_pct < 30.0:
            duty_on = True
            standby_on = sample.demand_lps >= 4.5
        elif sample.tank_level_pct < 45.0:
            duty_on = True
            standby_on = False
        elif sample.tank_level_pct > 55.0:
            duty_on = False
            standby_on = False

        return PlannerProposal(
            duty_on=duty_on,
            standby_on=standby_on,
            reason="readable narrow-band threshold policy",
            planner_id=self.planner_id,
        )


class GeneratedTablePlanner:
    planner_id = PLANNER_ID

    def propose(
        self,
        sample: TelemetrySample,
        state: ControllerState,
        config: SystemConfig,
    ) -> PlannerProposal:
        del config
        level_index = bisect_right(LEVEL_BANDS_PCT, sample.tank_level_pct)
        demand_index = bisect_right(DEMAND_BANDS_LPS, sample.demand_lps)
        quality_index = {"GOOD": 0, "STALE": 1, "CONFLICT": 2}[sample.quality.value]
        index = level_index
        index = index * 3 + demand_index
        index = index * 2 + int(state.duty_on)
        index = index * 2 + int(state.standby_on)
        index = index * 2 + int(sample.power_available)
        index = index * 3 + quality_index
        duty_on, standby_on = DECISION_TABLE[index]
        return PlannerProposal(
            duty_on=duty_on,
            standby_on=standby_on,
            reason=f"generated decision table entry {index}",
            planner_id=self.planner_id,
        )
