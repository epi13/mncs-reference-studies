# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import random

from water_control.model import Scenario


def _randomized_scenarios() -> tuple[Scenario, ...]:
    scenarios: list[Scenario] = []
    for seed in range(8):
        rng = random.Random(10_000 + seed)
        duration_s = 28_800
        split_a = 7_200
        split_b = 21_600
        demand_profile = (
            (0, split_a, round(rng.uniform(2.4, 3.8), 3)),
            (split_a, split_b, round(rng.uniform(3.5, 6.2), 3)),
            (split_b, duration_s, round(rng.uniform(2.2, 4.2), 3)),
        )
        outage_start = rng.choice((0, 7_200, 14_400, 21_600))
        outage = ((outage_start, min(duration_s, outage_start + rng.choice((0, 1_800, 3_600)))),)
        outage = tuple(window for window in outage if window[0] < window[1])
        stale_start = rng.choice((5_400, 10_800, 16_200))
        stale = ((stale_start, stale_start + rng.choice((0, 900, 1_800))),)
        stale = tuple(window for window in stale if window[0] < window[1])
        scenarios.append(
            Scenario(
                scenario_id=f"randomized-{seed:02d}",
                duration_s=duration_s,
                step_s=60,
                initial_level_pct=round(rng.uniform(22.0, 78.0), 3),
                demand_profile=demand_profile,
                power_outages=outage,
                stale_windows=stale,
                restart_at_s=14_400 if seed % 3 == 0 else None,
                observed_demand_scale=round(rng.uniform(0.78, 1.22), 3),
                randomized=True,
                seed=10_000 + seed,
            )
        )
    return tuple(scenarios)


def scenario_suite() -> tuple[Scenario, ...]:
    declared = (
        Scenario(
            scenario_id="normal-day",
            duration_s=43_200,
            step_s=60,
            initial_level_pct=60.0,
            demand_profile=(
                (0, 10_800, 2.2),
                (10_800, 21_600, 4.2),
                (21_600, 32_400, 3.0),
                (32_400, 43_200, 4.8),
            ),
        ),
        Scenario(
            scenario_id="peak-demand",
            duration_s=28_800,
            step_s=60,
            initial_level_pct=58.0,
            demand_profile=((0, 7_200, 3.5), (7_200, 24_000, 5.8), (24_000, 28_800, 3.0)),
        ),
        Scenario(
            scenario_id="power-outage",
            duration_s=28_800,
            step_s=60,
            initial_level_pct=70.0,
            demand_profile=((0, 28_800, 3.2),),
            power_outages=((7_200, 10_800),),
        ),
        Scenario(
            scenario_id="stale-telemetry",
            duration_s=21_600,
            step_s=60,
            initial_level_pct=55.0,
            demand_profile=((0, 21_600, 3.4),),
            stale_windows=((7_200, 9_000),),
        ),
        Scenario(
            scenario_id="conflicting-sensor",
            duration_s=21_600,
            step_s=60,
            initial_level_pct=55.0,
            demand_profile=((0, 21_600, 3.1),),
            conflict_windows=((5_400, 7_200),),
        ),
        Scenario(
            scenario_id="checkpoint-restart",
            duration_s=28_800,
            step_s=60,
            initial_level_pct=62.0,
            demand_profile=((0, 14_400, 3.0), (14_400, 28_800, 4.6)),
            restart_at_s=14_400,
        ),
        Scenario(
            scenario_id="outage-plus-stale-telemetry",
            duration_s=28_800,
            step_s=60,
            initial_level_pct=64.0,
            demand_profile=((0, 28_800, 3.8),),
            power_outages=((8_400, 12_000),),
            stale_windows=((7_800, 12_600),),
        ),
        Scenario(
            scenario_id="restart-during-degraded-telemetry",
            duration_s=28_800,
            step_s=60,
            initial_level_pct=58.0,
            demand_profile=((0, 28_800, 3.6),),
            stale_windows=((12_600, 16_200),),
            restart_at_s=14_400,
        ),
        Scenario(
            scenario_id="near-empty-initial-storage",
            duration_s=21_600,
            step_s=60,
            initial_level_pct=16.5,
            demand_profile=((0, 7_200, 2.8), (7_200, 21_600, 4.4)),
        ),
        Scenario(
            scenario_id="demand-model-underestimate",
            duration_s=28_800,
            step_s=60,
            initial_level_pct=52.0,
            demand_profile=((0, 28_800, 4.4),),
            observed_demand_scale=0.72,
        ),
        Scenario(
            scenario_id="demand-model-overestimate",
            duration_s=28_800,
            step_s=60,
            initial_level_pct=52.0,
            demand_profile=((0, 28_800, 3.2),),
            observed_demand_scale=1.30,
        ),
    )
    return declared + _randomized_scenarios()


def smoke_suite() -> tuple[Scenario, ...]:
    scenarios = scenario_suite()
    return scenarios[0], scenarios[3], scenarios[5], scenarios[6], scenarios[8]
