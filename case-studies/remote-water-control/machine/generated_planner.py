# SPDX-License-Identifier: Apache-2.0
"""Generated decision table. Do not edit by hand."""

SOURCE_SPEC_SHA256 = "01ce91e7535a9e55a8e8dd30ef089443c245a540b92bf63f32d5e9b5a2d46c3f"
PLANNER_ID = "mncs.remote-water.generated-table.v1"
LEVEL_BANDS_PCT = (15.0, 35.0, 50.0, 65.0, 75.0, 90.0)
DEMAND_BANDS_LPS = (2.5, 4.5)
TABLE_SHAPE = (7, 3, 2, 2, 2, 3)


def _decision(
    level_index: int,
    demand_index: int,
    duty_on: int,
    standby_on: int,
    power_available: int,
    quality_index: int,
) -> tuple[bool, bool]:
    if not power_available:
        return False, False
    if quality_index != 0:
        return bool(duty_on), bool(standby_on)
    if level_index == 0:
        return True, True
    high_demand = demand_index == 2
    if level_index in {1, 2}:
        return True, bool(standby_on and high_demand)
    if level_index == 3:
        return bool(duty_on), bool(standby_on and high_demand)
    if level_index == 4:
        return bool(duty_on and high_demand), bool(standby_on and high_demand)
    return False, False


DECISION_TABLE: tuple[tuple[bool, bool], ...] = tuple(
    _decision(level, demand, duty, standby, power, quality)
    for level in range(TABLE_SHAPE[0])
    for demand in range(TABLE_SHAPE[1])
    for duty in range(TABLE_SHAPE[2])
    for standby in range(TABLE_SHAPE[3])
    for power in range(TABLE_SHAPE[4])
    for quality in range(TABLE_SHAPE[5])
)
