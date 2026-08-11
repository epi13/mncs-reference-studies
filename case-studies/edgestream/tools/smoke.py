#!/usr/bin/env python3
"""Fast deterministic EdgeStream smoke and evaluator-regression test."""

from __future__ import annotations

import hashlib
import sys
import tempfile
from pathlib import Path

from harness_regression import run_harness_regression
from study_support import (
    ROOT,
    build_all,
    execute,
    generate_candidate,
    generate_workloads,
    program,
    run,
)


def main() -> int:
    generate_workloads()
    generation = generate_candidate()
    build = build_all()
    if generation["status"] != "PASS" or build["status"] != "PASS":
        raise SystemExit("generation or strict build failed")

    source = ROOT / "machine" / "edgestream_generated.c"
    first = hashlib.sha256(source.read_bytes()).digest()
    with tempfile.TemporaryDirectory() as directory:
        other = Path(directory) / "generated.c"
        run(
            [
                sys.executable,
                "generator/generate_candidate.py",
                "--reference",
                "reference/edgestream_reference.c",
                "--output",
                str(other),
            ]
        )
        second = hashlib.sha256(other.read_bytes()).digest()
    if first != second:
        raise SystemExit("candidate regeneration is not byte-identical")

    for workload_name in ("edge-cases.bin", "hostile.bin"):
        workload = ROOT / "workloads" / workload_name
        reference = execute(program("reference"), workload, 3, check=False)
        for chunk in (1, 31, 4096):
            candidate = execute(program("candidate"), workload, chunk, check=False)
            if reference.stdout != candidate.stdout or reference.returncode != candidate.returncode:
                raise SystemExit(
                    f"reference and candidate smoke outputs differ: {workload_name}, chunk={chunk}"
                )

    regression = run_harness_regression()
    if regression["status"] != "PASS":
        raise SystemExit("harness regression corpus failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
