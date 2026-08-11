# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from water_control.checkpoint import decode_checkpoint, encode_checkpoint
from water_control.controller import Controller
from water_control.model import (
    ControlMode,
    PlantState,
    Scenario,
    ScenarioResult,
    SystemConfig,
    TelemetryQuality,
    TelemetrySample,
)
from water_control.planner import Planner


@dataclass
class Plant:
    config: SystemConfig
    state: PlantState

    @classmethod
    def at_level(cls, config: SystemConfig, level_pct: float) -> Plant:
        return cls(config, PlantState(config.tank_capacity_l * level_pct / 100.0))

    @property
    def level_pct(self) -> float:
        return self.state.tank_volume_l / self.config.tank_capacity_l * 100.0

    def step(
        self,
        *,
        duty_command: bool,
        standby_command: bool,
        demand_lps: float,
        power_available: bool,
        duration_s: int,
    ) -> None:
        duty_running = duty_command and power_available
        standby_running = standby_command and power_available
        if duty_running and not self.state.duty_running:
            self.state.duty_starts += 1
        if standby_running and not self.state.standby_running:
            self.state.standby_starts += 1
        self.state.duty_running = duty_running
        self.state.standby_running = standby_running
        inflow_l = duration_s * (
            self.config.duty_flow_lps * int(duty_running)
            + self.config.standby_flow_lps * int(standby_running)
        )
        demand_l = duration_s * demand_lps
        available_l = self.state.tank_volume_l + inflow_l
        delivered_l = min(available_l, demand_l)
        self.state.unmet_demand_l += demand_l - delivered_l
        next_volume_l = available_l - delivered_l
        if next_volume_l > self.config.tank_capacity_l:
            self.state.overflow_l += next_volume_l - self.config.tank_capacity_l
            next_volume_l = self.config.tank_capacity_l
        self.state.tank_volume_l = max(0.0, next_volume_l)
        self.state.energy_kwh += (
            duration_s
            / 3600.0
            * (
                self.config.duty_power_kw * int(duty_running)
                + self.config.standby_power_kw * int(standby_running)
            )
        )


def _inside(now_s: int, windows: tuple[tuple[int, int], ...]) -> bool:
    return any(start <= now_s < end for start, end in windows)


def _demand_at(now_s: int, scenario: Scenario) -> float:
    for start, end, demand in scenario.demand_profile:
        if start <= now_s < end:
            return demand
    raise ValueError(f"scenario {scenario.scenario_id} has no demand value at {now_s}")


def _checkpoint_payload(plant: Plant, controller: Controller) -> dict[str, Any]:
    return {
        "schema_version": "0.2",
        "plant_state": plant.state.as_dict(),
        "controller": controller.checkpoint_payload(),
    }


def run_scenario(
    planner: Planner, scenario: Scenario, config: SystemConfig | None = None
) -> ScenarioResult:
    active_config = config or SystemConfig()
    plant = Plant.at_level(active_config, scenario.initial_level_pct)
    controller = Controller(planner, active_config)
    last_good_level = plant.level_pct
    last_good_at_s = 0
    previous_duty = controller.state.duty_on
    previous_standby = controller.state.standby_on
    emergency_steps = 0
    degraded_steps = 0
    safety_violations: list[str] = []
    restart_performed = False

    for now_s in range(0, scenario.duration_s, scenario.step_s):
        power_available = not _inside(now_s, scenario.power_outages)
        demand_lps = _demand_at(now_s, scenario)
        quality = TelemetryQuality.GOOD
        observed_level = plant.level_pct
        observed_at_s = now_s
        if _inside(now_s, scenario.stale_windows):
            quality = TelemetryQuality.STALE
            observed_level = last_good_level
            observed_at_s = last_good_at_s
        elif _inside(now_s, scenario.conflict_windows):
            quality = TelemetryQuality.CONFLICT
            observed_level = min(100.0, plant.level_pct + 12.0)
        else:
            last_good_level = observed_level
            last_good_at_s = now_s

        sample = TelemetrySample(
            observed_at_s=observed_at_s,
            received_at_s=now_s,
            tank_level_pct=observed_level,
            demand_lps=demand_lps * scenario.observed_demand_scale,
            power_available=power_available,
            quality=quality,
        )
        intent = controller.decide(sample, now_s)
        if intent.mode is ControlMode.EMERGENCY:
            emergency_steps += 1
        if intent.mode is ControlMode.DEGRADED:
            degraded_steps += 1
        if quality is not TelemetryQuality.GOOD and (
            intent.duty_on != previous_duty or intent.standby_on != previous_standby
        ):
            safety_violations.append(f"{now_s}: command changed on degraded telemetry")
        if sample.tank_level_pct >= active_config.high_high_pct and (
            intent.duty_on or intent.standby_on
        ):
            safety_violations.append(f"{now_s}: pumps enabled at high-high level")
        if intent.standby_on and not intent.duty_on:
            safety_violations.append(f"{now_s}: standby enabled without duty")
        if intent.expires_at_s <= intent.issued_at_s:
            safety_violations.append(f"{now_s}: non-positive intent lifetime")

        plant.step(
            duty_command=intent.duty_on,
            standby_command=intent.standby_on,
            demand_lps=demand_lps,
            power_available=power_available,
            duration_s=scenario.step_s,
        )
        previous_duty = intent.duty_on
        previous_standby = intent.standby_on

        if scenario.restart_at_s == now_s + scenario.step_s:
            encoded = encode_checkpoint(_checkpoint_payload(plant, controller))
            restored = decode_checkpoint(encoded)
            plant = Plant(active_config, PlantState.from_dict(restored["plant_state"]))
            controller = Controller.restore(planner, restored["controller"], active_config)
            restart_performed = True

    if not controller.journal.verify():
        safety_violations.append("journal hash chain verification failed")
    return ScenarioResult(
        scenario_id=scenario.scenario_id,
        planner_id=planner.planner_id,
        steps=scenario.duration_s // scenario.step_s,
        initial_level_pct=scenario.initial_level_pct,
        final_level_pct=round(plant.level_pct, 6),
        energy_kwh=round(plant.state.energy_kwh, 6),
        pump_starts=plant.state.duty_starts + plant.state.standby_starts,
        unmet_demand_l=round(plant.state.unmet_demand_l, 6),
        overflow_l=round(plant.state.overflow_l, 6),
        emergency_steps=emergency_steps,
        degraded_steps=degraded_steps,
        safety_interventions=dict(controller.intervention_counts),
        safety_violations=safety_violations,
        sequence_end=controller.state.last_sequence,
        journal_tail_hash=controller.journal.tail_hash,
        restart_performed=restart_performed,
        randomized=scenario.randomized,
        seed=scenario.seed,
    )
