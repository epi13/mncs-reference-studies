#!/usr/bin/env python3
"""Run declared Forge workflows using limits from mncs-forge.toml."""

from __future__ import annotations

import json
import sys

import forge_workflow as base
from forge_policy import load_forge_workflow_policy


def main() -> int:
    policy = load_forge_workflow_policy()
    base.ENVIRONMENT_ALLOWLIST = policy.environment_allowlist
    arguments = sys.argv[1:]
    if len(arguments) != 1 or arguments[0] not in base.WORKFLOWS:
        payload: dict[str, object] = {
            "status": "UNKNOWN",
            "outcome": "unsupported",
            "conformance_status": "UNKNOWN",
            "limitations": ["expected one declared workflow name"],
            "supported_workflows": sorted(base.WORKFLOWS),
        }
    else:
        name = arguments[0]
        payload = base.run_workflow(
            name,
            base.WORKFLOWS[name],
            output_cap=policy.output_cap,
        )
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
