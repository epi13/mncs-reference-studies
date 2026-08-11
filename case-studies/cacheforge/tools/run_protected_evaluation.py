from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "machine"))

from cacheforge.trace_bundle import evaluate_trace_bundle, load_trace_bundle  # noqa: E402
from generated_policy import GeneratedEvictionPolicy  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    bundle = load_trace_bundle(args.bundle)
    summary = evaluate_trace_bundle(bundle, GeneratedEvictionPolicy)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "bundle_id": bundle.bundle_id,
                "observed_gate_result": summary["observed_gate_result"],
                "promotion_authorized": summary["promotion_authorized"],
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
