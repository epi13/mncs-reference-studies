#!/usr/bin/env python3
"""Regression corpus for the EdgeStream evaluator and structural provider."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from study_evaluation import percentile, structural_checks
from study_support import RESULTS, ROOT, sha256, write_json


def _mutated_source(source: str, mutation: str) -> str:
    if mutation == "missing-generated-marker":
        return source.replace("MNCS-GENERATED", "MNCS-REMOVED", 2)
    if mutation == "dynamic-allocation":
        needle = "    memset(p, 0, sizeof(*p));"
        replacement = "    (void)malloc(1u);\n" + needle
        if needle not in source:
            raise ValueError("allocation fixture anchor missing")
        return source.replace(needle, replacement, 1)
    if mutation == "missing-frame-length-check":
        return source.replace(
            "frame_length != ES_MAX_FRAME_SIZE",
            "frame_length == ES_MAX_FRAME_SIZE",
            1,
        )
    if mutation == "checksum-after-accept":
        return source.replace("if (expected != actual)", "if (expected == actual)", 1)
    if mutation == "benchmark-aware-branch":
        needle = "void es_init(es_processor *p, bool quiet) {"
        replacement = needle + '\n    if (getenv("steady.bin") != NULL) { p->accepted = 1u; }'
        if needle not in source:
            raise ValueError("benchmark fixture anchor missing")
        return source.replace(needle, replacement, 1)
    if mutation == "checkpoint-crc-bypass":
        return source.replace(
            "header.crc != crc32_slow",
            "header.crc == crc32_slow",
            1,
        )
    raise ValueError(f"unknown mutation: {mutation}")


def run_harness_regression() -> dict[str, Any]:
    candidate = ROOT / "machine" / "edgestream_generated.c"
    source = candidate.read_text(encoding="utf-8")
    positive = structural_checks(candidate, write_result=False)
    cases: list[dict[str, Any]] = [
        {
            "fixture": "current-candidate",
            "expected_status": "PASS",
            "observed_status": positive["status"],
            "status": "PASS" if positive["status"] == "PASS" else "FAIL",
            "candidate_sha256": sha256(candidate),
        }
    ]
    expectations = {
        "missing-generated-marker": "generated_marker",
        "dynamic-allocation": "no_dynamic_allocation_in_processor_ast",
        "missing-frame-length-check": "frame_length_checked",
        "checksum-after-accept": "checksum_precedes_accept",
        "benchmark-aware-branch": "no_benchmark_workload_branch",
        "checkpoint-crc-bypass": "checkpoint_integrity",
    }
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for mutation, expected_check in expectations.items():
            path = root / f"{mutation}.c"
            path.write_text(_mutated_source(source, mutation), encoding="utf-8")
            observed = structural_checks(path, write_result=False)
            check_status = observed["check_statuses"].get(expected_check, "UNKNOWN")
            passed = observed["status"] == "FAIL" and check_status == "FAIL"
            cases.append(
                {
                    "fixture": mutation,
                    "expected_status": "FAIL",
                    "observed_status": observed["status"],
                    "expected_failed_check": expected_check,
                    "observed_check_status": check_status,
                    "status": "PASS" if passed else "FAIL",
                    "fixture_sha256": sha256(path),
                }
            )

    percentile_cases = [
        ("p50", percentile([1.0, 2.0, 3.0, 4.0], 0.50), 2.0),
        ("p95", percentile([1.0, 2.0, 3.0, 4.0], 0.95), 4.0),
        ("p99", percentile([1.0, 2.0, 3.0, 4.0], 0.99), 4.0),
    ]
    for name, observed, expected in percentile_cases:
        cases.append(
            {
                "fixture": f"percentile-{name}",
                "expected": expected,
                "observed": observed,
                "status": "PASS" if observed == expected else "FAIL",
            }
        )

    status = "PASS" if all(case["status"] == "PASS" for case in cases) else "FAIL"
    result = {
        "status": status,
        "provider_version": "edgestream-clang-structural-checker/2.0",
        "case_count": len(cases),
        "cases": cases,
        "purpose": (
            "Ensure the evaluator rejects representative missing-marker, dynamic-allocation, "
            "validation-order, benchmark-awareness, and checkpoint-integrity defects."
        ),
    }
    write_json(RESULTS / "harness-regression.json", result)
    return result


def main() -> int:
    result = run_harness_regression()
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
