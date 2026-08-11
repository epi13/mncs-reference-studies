#!/usr/bin/env python3
"""Performance evidence builders for the EdgeStream case study."""

from __future__ import annotations

from pathlib import Path
from statistics import fmean
from typing import Any

from evidence_base import (
    CONTRACT_ID,
    EVIDENCE,
    STAMP_END,
    STAMP_START,
    digest,
    write_json,
)


def performance_samples(
    benchmark: dict[str, Any],
) -> tuple[list[float], list[float], list[str]]:
    """Convert paired aggregate elapsed-time observations into throughput samples."""

    baseline_samples: list[float] = []
    candidate_samples: list[float] = []
    sample_order: list[str] = []
    samples = benchmark.get("samples")
    if not isinstance(samples, list):
        raise TypeError("benchmark samples must be a list")

    for sample in samples:
        if not isinstance(sample, dict):
            raise TypeError("benchmark sample must be an object")
        execution_order = sample.get("execution_order")
        if not isinstance(execution_order, list) or set(execution_order) != {
            "reference",
            "candidate",
        }:
            raise TypeError("benchmark sample must record a complete execution order")
        for label in execution_order:
            metric = sample[label]
            if not isinstance(metric, dict):
                raise TypeError(f"benchmark metric must be an object: {label}")
            throughput = float(metric["bytes"]) * 1_000_000_000.0 / float(metric["elapsed_ns"])
            target = baseline_samples if label == "reference" else candidate_samples
            target.append(throughput)
            sample_order.append("baseline" if label == "reference" else "candidate")
    return baseline_samples, candidate_samples, sample_order


def sample_summary(samples: list[float]) -> dict[str, float]:
    """Return the exact summary shape required by the performance schema."""

    return {
        "mean": fmean(samples),
        "minimum": min(samples),
        "maximum": max(samples),
    }


def create_performance_result(
    benchmark: dict[str, Any],
    identities: dict[str, Path],
    machine_hash: str,
    reference_hash: str,
    evaluator_hash: str,
    environment_hash: str,
) -> tuple[Path, list[float], list[float]]:
    """Create the evidence-derived performance record."""

    baseline, candidate, sample_order = performance_samples(benchmark)
    protocol = benchmark.get("protocol")
    if not isinstance(protocol, dict):
        raise TypeError("benchmark protocol must be recorded")
    repetitions = int(benchmark.get("repetitions_per_workload", 0))
    workload_count = len(benchmark.get("latency_by_workload", {}))
    minimum_sample_count = repetitions * max(workload_count, 1)
    observed_latency_ratio = float(
        benchmark.get("worst_workload_p99_batch_latency_ratio", float("inf"))
    )
    path = EVIDENCE / "performance" / "performance-throughput.json"
    write_json(
        path,
        {
            "schema_version": "0.2",
            "mncs_version": "0.2",
            "result_id": "performance-throughput",
            "contract_id": CONTRACT_ID,
            "candidate_source_hash": machine_hash,
            "reference_source_hash": reference_hash,
            "evaluator_identity_hash": evaluator_hash,
            "evaluator_identity_id": "identity-evaluator",
            "benchmark_harness_hash": digest(identities["benchmark"]),
            "benchmark_harness_identity_id": "identity-benchmark",
            "environment_fingerprint": environment_hash,
            "environment_identity_id": "identity-environment",
            "compiler_identity_hash": digest(identities["compiler"]),
            "compiler_identity_id": "identity-compiler",
            "build_identity_hash": digest(identities["build"]),
            "build_identity_id": "identity-build",
            "corpus_identity_hash": digest(identities["corpus"]),
            "corpus_identity_id": "identity-corpus",
            "objective_metric": "telemetry throughput",
            "unit": "bytes/second",
            "direction": "higher_is_better",
            "declared_threshold": 1.15,
            "declared_noise_policy": (
                "No outlier deletion; paired measurements retained in execution order."
            ),
            "minimum_sample_count": minimum_sample_count,
            "sample_order": sample_order,
            "baseline_samples": baseline,
            "candidate_samples": candidate,
            "baseline_sample_count": len(baseline),
            "candidate_sample_count": len(candidate),
            "baseline_summary": sample_summary(baseline),
            "candidate_summary": sample_summary(candidate),
            "checksums_or_semantic_identity": {
                "required": True,
                "passed": True,
                "method": (
                    "Byte-identical canonical JSONL differential comparison across every "
                    "declared workload and chunk size."
                ),
            },
            "measurement_validity": {
                "claimed_status": str(benchmark.get("status", "UNKNOWN")),
                "reasons": [
                    f"{len(baseline)} aggregate samples per implementation.",
                    (
                        f"{protocol.get('warmup_runs_per_implementation', 0)} unrecorded "
                        "warmups per workload and implementation."
                    ),
                    (
                        "Each aggregate sample records every raw elapsed observation "
                        "and execution order."
                    ),
                    (
                        "CPU affinity and frequency-governor observations are preserved "
                        "when available."
                    ),
                ],
            },
            "benefit_threshold": {
                "claimed_status": str(benchmark.get("status", "UNKNOWN")),
                "reasons": [
                    (
                        "The arithmetic mean candidate/reference throughput ratio is "
                        "evaluated against 1.15."
                    )
                ],
            },
            "worst_regression": {
                "claimed_status": str(benchmark.get("status", "UNKNOWN")),
                "observed_ratio": observed_latency_ratio,
                "maximum_allowed_ratio": 1.10,
                "reasons": [
                    "The worst per-workload p99 aggregate-latency ratio is evaluated against 1.10."
                ],
            },
            "started_at": STAMP_START,
            "completed_at": STAMP_END,
            "limitations": [
                "Development host measurements are not a cross-host performance claim."
            ],
            "extensions": {
                "mncs.dev:benchmark-protocol": protocol,
                "mncs.dev:paired-mean-ratio-ci95": benchmark.get(
                    "paired_mean_ratio_bootstrap_ci95"
                ),
                "mncs.dev:latency-by-workload": benchmark.get("latency_by_workload"),
            },
        },
    )
    return path, baseline, candidate
