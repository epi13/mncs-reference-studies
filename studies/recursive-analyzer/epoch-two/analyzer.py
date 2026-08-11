#!/usr/bin/env python3
"""Frozen epoch-two classifier improved from epoch-one disagreements."""

# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import re
import sys
from typing import Any

TOOL_ID = "analyzer.epoch-two"
DIRECT_EVAL = re.compile(r"\beval\s*\(")
ALIAS_ASSIGNMENT = re.compile(r"(?m)^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*eval\s*;?\s*$")


def classify(case: dict[str, Any]) -> dict[str, str]:
    language = case.get("language")
    source = case.get("source")
    if language != "python" or not isinstance(source, str):
        return {"status": "UNKNOWN", "diagnostic": "unsupported language or source"}
    if DIRECT_EVAL.search(source):
        return {"status": "FAIL", "diagnostic": "direct eval call"}
    aliases = ALIAS_ASSIGNMENT.findall(source)
    if any(re.search(rf"\b{re.escape(alias)}\s*\(", source) for alias in aliases):
        return {"status": "FAIL", "diagnostic": "eval alias call"}
    if "getattr(" in source or "__builtins__[" in source:
        return {"status": "UNKNOWN", "diagnostic": "dynamic call target is unsupported"}
    return {"status": "PASS", "diagnostic": "supported call forms contain no eval"}


def main() -> int:
    value = json.load(sys.stdin)
    if not isinstance(value, dict):
        raise TypeError("case must be an object")
    print(json.dumps({"tool_id": TOOL_ID, **classify(value)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
