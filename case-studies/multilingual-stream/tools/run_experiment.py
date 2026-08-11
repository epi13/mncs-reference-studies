#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path

from experiment_build import compile_subjects, sanitizer_observation
from experiment_evaluate import (
    benchmark_report,
    functional_observations,
    provider_observations,
    regeneration_observation,
)
from experiment_report import build_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--skip-benchmark", action="store_true")
    args = parser.parse_args()
    gcc = shutil.which("gcc")
    cargo = shutil.which("cargo")
    if gcc is None or cargo is None:
        missing = [name for name, value in (("gcc", gcc), ("cargo", cargo)) if value is None]
        raise SystemExit("missing required tool(s): " + ", ".join(missing))
    with tempfile.TemporaryDirectory(prefix="mncs-multilingual-") as temporary:
        build = Path(temporary)
        implementations = compile_subjects(gcc, cargo, build)
        direct = functional_observations(implementations)
        direct.extend(provider_observations())
        direct.append(regeneration_observation())
        sanitizer_status, sanitizer_note = sanitizer_observation(gcc, build)
        benchmark = benchmark_report(
            implementations,
            skip=args.skip_benchmark,
        )
        report = build_report(
            gcc,
            cargo,
            implementations,
            direct,
            sanitizer_status,
            sanitizer_note,
            benchmark,
        )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
