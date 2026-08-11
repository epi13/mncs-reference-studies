#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "generator" / "planner-spec.json"
OUTPUT_PATH = ROOT / "machine" / "generated_planner.py"


def render(spec_bytes: bytes) -> str:
    spec = json.loads(spec_bytes)
    lines = [
        "# SPDX-License-Identifier: Apache-2.0",
        '"""Generated decision table. Do not edit by hand."""',
        "",
        f'SOURCE_SPEC_SHA256 = "{hashlib.sha256(spec_bytes).hexdigest()}"',
        f'PLANNER_ID = "{spec["planner_id"]}"',
        f"LEVEL_BANDS_PCT = {tuple(spec['level_bands_pct'])!r}",
        f"DEMAND_BANDS_LPS = {tuple(spec['demand_bands_lps'])!r}",
        f"TABLE_SHAPE = ({len(spec['level_names'])}, {len(spec['demand_names'])}, 2, 2, 2, 3)",
        "",
        "",
        "def _decision(",
        "    level_index: int,",
        "    demand_index: int,",
        "    duty_on: int,",
        "    standby_on: int,",
        "    power_available: int,",
        "    quality_index: int,",
        ") -> tuple[bool, bool]:",
        "    if not power_available:",
        "        return False, False",
        "    if quality_index != 0:",
        "        return bool(duty_on), bool(standby_on)",
        "    if level_index == 0:",
        "        return True, True",
        "    high_demand = demand_index == 2",
        "    if level_index in {1, 2}:",
        "        return True, bool(standby_on and high_demand)",
        "    if level_index == 3:",
        "        return bool(duty_on), bool(standby_on and high_demand)",
        "    if level_index == 4:",
        "        return bool(duty_on and high_demand), bool(standby_on and high_demand)",
        "    return False, False",
        "",
        "",
        "DECISION_TABLE: tuple[tuple[bool, bool], ...] = tuple(",
        "    _decision(level, demand, duty, standby, power, quality)",
        "    for level in range(TABLE_SHAPE[0])",
        "    for demand in range(TABLE_SHAPE[1])",
        "    for duty in range(TABLE_SHAPE[2])",
        "    for standby in range(TABLE_SHAPE[3])",
        "    for power in range(TABLE_SHAPE[4])",
        "    for quality in range(TABLE_SHAPE[5])",
        ")",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    rendered = render(SPEC_PATH.read_bytes())
    if args.check and (not OUTPUT_PATH.exists() or OUTPUT_PATH.read_text() != rendered):
        raise SystemExit("generated planner is out of date")
    if args.check:
        return 0

    OUTPUT_PATH.write_text(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
