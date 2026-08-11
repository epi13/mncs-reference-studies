#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from mncs_validator.readiness import evaluate_claim_readiness


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    record: dict[str, Any] = json.loads(args.input.read_text(encoding="utf-8"))
    record.update(evaluate_claim_readiness(record))
    rendered = json.dumps(record, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 1 if record["disposition"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
