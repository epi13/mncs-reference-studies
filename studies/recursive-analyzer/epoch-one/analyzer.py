#!/usr/bin/env python3
"""Frozen epoch-one bounded structural classifier."""

# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import sys
from typing import Any

TOOL_ID = "analyzer.epoch-one"


def classify(case: dict[str, Any]) -> dict[str, str]:
    language = case.get("language")
    source = case.get("source")
    if language != "python" or not isinstance(source, str):
        return {"status": "UNKNOWN", "diagnostic": "unsupported language or source"}
    if "eval(" in source:
        return {"status": "FAIL", "diagnostic": "direct eval call"}
    return {"status": "PASS", "diagnostic": "no direct eval call found"}


def main() -> int:
    value = json.load(sys.stdin)
    if not isinstance(value, dict):
        raise TypeError("case must be an object")
    print(json.dumps({"tool_id": TOOL_ID, **classify(value)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
