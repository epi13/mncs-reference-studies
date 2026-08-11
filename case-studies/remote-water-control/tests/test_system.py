# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from water_control.checkpoint import CheckpointError, decode_checkpoint, encode_checkpoint
from water_control.controller import Controller
from water_control.journal import IntentJournal
from water_control.model import (
    ControllerState,
    ControlMode,
    PlannerProposal,
    SystemConfig,
    TelemetryQuality,
    TelemetrySample,
)
from water_control.planner import GeneratedTablePlanner, ReadableBaselinePlanner
from water_control.safety import SafetyKernel
from water_control.scenarios import scenario_suite
from water_control.simulator import run_scenario

ROOT = Path(__file__).resolve().parents[1]


class FixedPlanner:
    planner_id = "test-fixed-planner"

    def __init__(self, duty_on: bool, standby_on: bool) -> None:
        self.duty_on = duty_on
        self.standby_on = standby_on

    def propose(
        self,
        sample: TelemetrySample,
        state: ControllerState,
        config: SystemConfig,
    ) -> PlannerProposal:
        del sample, state, config
        return PlannerProposal(self.duty_on, self.standby_on, self.planner_id, "test")


def sample(
    *,
    level: float = 50.0,
    now_s: int = 1_000,
    quality: TelemetryQuality = TelemetryQuality.GOOD,
    power: bool = True,
) -> TelemetrySample:
    return TelemetrySample(now_s, now_s, level, 3.0, power, quality)


def test_generated_planner_matches_spec() -> None:
    from generated_planner import SOURCE_SPEC_SHA256

    expected = hashlib.sha256((ROOT / "generator" / "planner-spec.json").read_bytes()).hexdigest()
    assert expected == SOURCE_SPEC_SHA256


def test_safety_stops_at_high_high() -> None:
    kernel = SafetyKernel(SystemConfig())
    proposal = PlannerProposal(True, True, "test", "test")
    result = kernel.authorize(proposal, sample(level=95.0), ControllerState(), 1_000)
    assert result.mode is ControlMode.EMERGENCY
    assert not result.duty_on
    assert not result.standby_on


def test_safety_holds_on_bad_telemetry() -> None:
    kernel = SafetyKernel(SystemConfig())
    state = ControllerState(duty_on=True, standby_on=False)
    proposal = PlannerProposal(False, True, "test", "test")
    result = kernel.authorize(
        proposal,
        sample(quality=TelemetryQuality.CONFLICT),
        state,
        1_000,
    )
    assert result.mode is ControlMode.DEGRADED
    assert result.duty_on
    assert not result.standby_on


def test_intervention_counts_distinguish_all_dispositions() -> None:
    accepted = Controller(FixedPlanner(False, False))
    accepted.decide(sample(), 1_000)
    assert accepted.intervention_counts == {
        "accepted": 1,
        "modified": 0,
        "held": 0,
        "rejected": 0,
    }

    held = Controller(
        FixedPlanner(False, True),
        state=ControllerState(duty_on=True, standby_on=False),
    )
    held.decide(sample(quality=TelemetryQuality.CONFLICT), 1_000)
    assert held.intervention_counts["held"] == 1

    rejected = Controller(FixedPlanner(True, True))
    rejected.decide(sample(level=95.0), 1_000)
    assert rejected.intervention_counts["rejected"] == 1

    modified = Controller(FixedPlanner(False, True))
    modified.decide(sample(), 1_000)
    assert modified.intervention_counts["modified"] == 1


def test_journal_rejects_replay() -> None:
    controller = Controller(ReadableBaselinePlanner())
    intent = controller.decide(sample(), 1_000)
    with pytest.raises(ValueError, match="advance exactly once"):
        IntentJournal(last_sequence=intent.sequence).append(intent)


def test_checkpoint_corruption_is_rejected() -> None:
    encoded = bytearray(encode_checkpoint({"state": {"sequence": 1}}))
    encoded[len(encoded) // 2] ^= 1
    with pytest.raises(CheckpointError):
        decode_checkpoint(bytes(encoded))


def test_scenario_suite_is_deterministic_and_safe() -> None:
    first = [run_scenario(GeneratedTablePlanner(), item).as_dict() for item in scenario_suite()]
    second = [run_scenario(GeneratedTablePlanner(), item).as_dict() for item in scenario_suite()]
    assert first == second
    assert all(not result["safety_violations"] for result in first)
    assert all(result["sequence_end"] == result["steps"] for result in first)


def test_checkpoint_restart_preserves_sequence() -> None:
    scenario = next(item for item in scenario_suite() if item.scenario_id == "checkpoint-restart")
    result = run_scenario(GeneratedTablePlanner(), scenario)
    assert result.restart_performed
    assert result.sequence_end == result.steps
    assert not result.safety_violations


def test_candidate_meets_declared_development_objective() -> None:
    baseline = [run_scenario(ReadableBaselinePlanner(), item) for item in scenario_suite()]
    candidate = [run_scenario(GeneratedTablePlanner(), item) for item in scenario_suite()]
    baseline_starts = sum(item.pump_starts for item in baseline)
    candidate_starts = sum(item.pump_starts for item in candidate)
    baseline_energy = sum(item.energy_kwh for item in baseline)
    candidate_energy = sum(item.energy_kwh for item in candidate)
    assert candidate_starts / baseline_starts <= 0.75
    assert candidate_energy / baseline_energy <= 1.10
    assert sum(item.unmet_demand_l for item in candidate) == 0.0
    assert sum(item.overflow_l for item in candidate) == 0.0


def test_preregistration_is_json() -> None:
    assert json.loads((ROOT / "preregistration.json").read_text())["study_id"]
