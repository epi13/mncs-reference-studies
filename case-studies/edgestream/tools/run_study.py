#!/usr/bin/env python3
"""Build, evaluate, benchmark, and emit EdgeStream development evidence."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from typing import Any

from harness_regression import run_harness_regression
from study_evaluation import (
    benchmark,
    checkpoint_tests,
    differential_tests,
    environment_record,
    mutation_test,
    sanitizer_tests,
    structural_checks,
)
from study_support import (
    RESULTS,
    build_all,
    generate_candidate,
    generate_workloads,
    sha256,
    write_json,
)

ALLOWED = {"PASS", "FAIL", "UNKNOWN"}


def aggregate_status(values: list[str]) -> str:
    if "FAIL" in values:
        return "FAIL"
    if "UNKNOWN" in values:
        return "UNKNOWN"
    return "PASS" if values and all(item == "PASS" for item in values) else "UNKNOWN"


def status_of(value: dict[str, Any]) -> str:
    status = value.get("status")
    return str(status) if status in ALLOWED else "UNKNOWN"


def clear_results() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    for path in RESULTS.glob("*.json"):
        path.unlink()


def compact_benchmark_summary(value: dict[str, Any]) -> dict[str, Any]:
    latency = value.get("latency_by_workload", {})
    latency_ratios = {
        name: record.get("p99_ratio")
        for name, record in latency.items()
        if isinstance(record, dict)
    }
    return {
        "status": value.get("status", "UNKNOWN"),
        "raw_benchmark_sha256": sha256(RESULTS / "benchmark.json"),
        "protocol": value.get("protocol"),
        "sample_count_per_implementation": value.get("sample_count_per_implementation"),
        "mean_throughput_ratio": value.get("mean_throughput_ratio"),
        "mean_throughput_ratio_method": value.get("mean_throughput_ratio_method"),
        "median_paired_throughput_ratio": value.get("median_paired_throughput_ratio"),
        "paired_mean_ratio_bootstrap_ci95": value.get("paired_mean_ratio_bootstrap_ci95"),
        "worst_workload_p99_batch_latency_ratio": value.get(
            "worst_workload_p99_batch_latency_ratio"
        ),
        "workload_p99_latency_ratios": latency_ratios,
        "threshold": value.get("threshold"),
        "maximum_latency_ratio": value.get("maximum_latency_ratio"),
    }


def run_generation() -> dict[str, dict[str, Any]]:
    generate_workloads()
    return {"generation": generate_candidate()}


def run_build() -> dict[str, dict[str, Any]]:
    results = run_generation()
    results["compiler_matrix"] = build_all()
    return results


def run_tests() -> dict[str, dict[str, Any]]:
    results = run_build()
    evaluators: tuple[tuple[str, Callable[[], dict[str, Any]]], ...] = (
        ("differential", differential_tests),
        ("mutation", mutation_test),
        ("checkpoint_recovery", checkpoint_tests),
        ("sanitizers", sanitizer_tests),
        ("structural", structural_checks),
        ("harness_regression", run_harness_regression),
    )
    for name, evaluator in evaluators:
        results[name] = evaluator()
    summary = {
        "status": aggregate_status([status_of(value) for value in results.values()]),
        "statuses": {name: status_of(value) for name, value in results.items()},
        "evidence": {
            path.name: sha256(path)
            for path in sorted(RESULTS.glob("*.json"))
            if path.name != "test-summary.json"
        },
    }
    write_json(RESULTS / "test-summary.json", summary)
    return results


def run_benchmark() -> dict[str, dict[str, Any]]:
    results = run_build()
    results["differential"] = differential_tests()
    if status_of(results["differential"]) != "PASS":
        results["benchmark"] = {
            "status": "FAIL",
            "reason": "semantic identity failed before performance measurement",
        }
        write_json(RESULTS / "benchmark.json", results["benchmark"])
    else:
        results["benchmark"] = benchmark()
    write_json(RESULTS / "benchmark-summary.json", compact_benchmark_summary(results["benchmark"]))
    return results


def run_all() -> dict[str, dict[str, Any]]:
    results = run_tests()
    if status_of(results["differential"]) == "PASS":
        results["benchmark"] = benchmark()
    else:
        results["benchmark"] = {
            "status": "FAIL",
            "reason": "semantic identity failed before performance measurement",
        }
        write_json(RESULTS / "benchmark.json", results["benchmark"])
    write_json(RESULTS / "benchmark-summary.json", compact_benchmark_summary(results["benchmark"]))
    results["environment"] = environment_record()
    statuses = {name: status_of(value) for name, value in results.items()}
    overall = aggregate_status(list(statuses.values()))
    evidence_files = sorted(
        path for path in RESULTS.glob("*.json") if path.name != "study-summary.json"
    )
    benchmark_value = results["benchmark"]
    write_json(
        RESULTS / "study-summary.json",
        {
            "status": overall,
            "target": "MNCDS-D2 / MNCS-L4 development study",
            "statuses": statuses,
            "benchmark": {
                "mean_throughput_ratio": benchmark_value.get("mean_throughput_ratio"),
                "median_paired_throughput_ratio": benchmark_value.get(
                    "median_paired_throughput_ratio"
                ),
                "paired_mean_ratio_bootstrap_ci95": benchmark_value.get(
                    "paired_mean_ratio_bootstrap_ci95"
                ),
                "worst_workload_p99_batch_latency_ratio": benchmark_value.get(
                    "worst_workload_p99_batch_latency_ratio"
                ),
            },
            "evidence": {path.name: sha256(path) for path in evidence_files},
            "limitations": [
                "The performance result is scoped to the captured development host.",
                (
                    "Repository-visible separated workloads are not blind third-party "
                    "holdout evidence."
                ),
                "Joern is optional for this study and was unavailable in the captured environment.",
                "This development run is not an accredited certification claim.",
            ],
        },
    )
    return results


def exit_code(results: dict[str, dict[str, Any]]) -> int:
    overall = aggregate_status([status_of(value) for value in results.values()])
    if overall == "PASS":
        return 0
    if overall == "UNKNOWN":
        return 3
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("all", "generate", "build", "test", "benchmark", "harness-regression"),
        nargs="?",
        default="all",
    )
    args = parser.parse_args()
    clear_results()

    if args.command == "generate":
        results = run_generation()
    elif args.command == "build":
        results = run_build()
    elif args.command == "test":
        results = run_tests()
    elif args.command == "benchmark":
        results = run_benchmark()
    elif args.command == "harness-regression":
        results = run_generation()
        results["harness_regression"] = run_harness_regression()
    else:
        results = run_all()
    return exit_code(results)


if __name__ == "__main__":
    raise SystemExit(main())
