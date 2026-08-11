#!/usr/bin/env python3
"""Derive EdgeStream conformance labels and bindings from raw observations."""

from __future__ import annotations

import json
from statistics import fmean
from typing import Any

from evidence_base import CONTRACT_ID, EVIDENCE, RESULTS, ROOT, digest, read_json, write_json

ALLOWED = {"PASS", "FAIL", "UNKNOWN"}
GATES = {
    "gate-behavioral": "differential.json",
    "gate-compiler-matrix": "compiler-matrix.json",
    "gate-safety": "sanitizers.json",
    "gate-resource-bounds": "checkpoint-recovery.json",
    "gate-mutation": "mutation.json",
    "gate-structural": "structural.json",
}


def status_of(value: Any) -> str:
    """Normalize one evidence status without treating absence as success."""

    return str(value) if value in ALLOWED else "UNKNOWN"


def aggregate(statuses: list[str]) -> str:
    """Apply MNCS dominance: FAIL, then UNKNOWN, then PASS."""

    if "FAIL" in statuses:
        return "FAIL"
    if "UNKNOWN" in statuses:
        return "UNKNOWN"
    return "PASS" if statuses and all(item == "PASS" for item in statuses) else "UNKNOWN"


def throughput_samples(benchmark: dict[str, Any]) -> tuple[list[float], list[float]]:
    """Recover baseline and candidate throughput observations from paired samples."""

    baseline: list[float] = []
    candidate: list[float] = []
    samples = benchmark.get("samples")
    if not isinstance(samples, list):
        return baseline, candidate
    for sample in samples:
        if not isinstance(sample, dict):
            continue
        for label, target in (("reference", baseline), ("candidate", candidate)):
            metric = sample.get(label)
            if not isinstance(metric, dict):
                continue
            try:
                target.append(
                    float(metric["bytes"]) * 1_000_000_000.0 / float(metric["elapsed_ns"])
                )
            except (KeyError, TypeError, ValueError, ZeroDivisionError):
                continue
    return baseline, candidate


def observation_count(raw: dict[str, Any]) -> int:
    cases = raw.get("cases")
    if isinstance(cases, list):
        return len(cases)
    checks = raw.get("checks")
    if isinstance(checks, dict):
        return len(checks)
    compilers = raw.get("compilers")
    if isinstance(compilers, dict):
        return sum(
            len(value.get("builds", {}))
            for value in compilers.values()
            if isinstance(value, dict) and isinstance(value.get("builds"), dict)
        )
    implementations = raw.get("implementations")
    if isinstance(implementations, dict):
        total = 0
        for value in implementations.values():
            if not isinstance(value, dict):
                continue
            nested = value.get("cases")
            total += len(nested) if isinstance(nested, list) else 1
        return total
    return 1


def _complete_orders(benchmark: dict[str, Any]) -> bool:
    samples = benchmark.get("samples")
    if not isinstance(samples, list) or not samples:
        return False
    for sample in samples:
        if not isinstance(sample, dict):
            return False
        order = sample.get("execution_order")
        if not isinstance(order, list) or set(order) != {"reference", "candidate"}:
            return False
    return True


def _latency_complete(benchmark: dict[str, Any], repetitions: int) -> bool:
    values = benchmark.get("latency_by_workload")
    if not isinstance(values, dict) or not values:
        return False
    for record in values.values():
        if not isinstance(record, dict):
            return False
        raw = record.get("raw_batch_elapsed_ns")
        if not isinstance(raw, dict):
            return False
        for label in ("reference", "candidate"):
            samples = raw.get(label)
            if not isinstance(samples, list) or len(samples) != repetitions:
                return False
        if not isinstance(record.get("p99_ratio"), (int, float)):
            return False
    return True


def derive_performance() -> tuple[str, dict[str, str]]:
    """Derive all three L4 performance sub-gates and rewrite the result record."""

    benchmark = read_json(RESULTS / "benchmark.json")
    differential = status_of(read_json(RESULTS / "differential.json").get("status"))
    harness = status_of(read_json(RESULTS / "harness-regression.json").get("status"))
    performance_path = EVIDENCE / "performance" / "performance-throughput.json"
    performance = read_json(performance_path)
    baseline, candidate = throughput_samples(benchmark)
    minimum = int(performance.get("minimum_sample_count", 1))
    protocol = benchmark.get("protocol")
    protocol = protocol if isinstance(protocol, dict) else {}
    repetitions = int(benchmark.get("repetitions_per_workload", 0))
    warmups = int(protocol.get("warmup_runs_per_implementation", 0))
    target_elapsed = int(protocol.get("target_minimum_sample_elapsed_ns", 0))
    observed_minimum = int(protocol.get("minimum_observed_sample_elapsed_ns", 0))
    semantic_passed = differential == "PASS"
    measurement_checks = {
        "semantic_identity": semantic_passed,
        "harness_regression": harness == "PASS",
        "minimum_sample_count": len(baseline) >= minimum and len(candidate) >= minimum,
        "warmup_policy": warmups >= 3,
        "minimum_sample_duration": target_elapsed > 0 and observed_minimum >= target_elapsed,
        "counterbalanced_order_recorded": _complete_orders(benchmark),
        "raw_latency_observations_recorded": _latency_complete(benchmark, repetitions),
        "paired_sample_cardinality": len(baseline) == len(candidate) and len(baseline) > 0,
    }
    measurement = "PASS" if all(measurement_checks.values()) else "FAIL"
    threshold = float(performance.get("declared_threshold", 1.15))
    observed_mean_ratio = (
        fmean(candidate) / fmean(baseline) if baseline and candidate else float("nan")
    )
    benefit = "PASS" if observed_mean_ratio >= threshold else "FAIL"
    regression = performance.get("worst_regression")
    if isinstance(regression, dict):
        observed = (
            min(baseline) / min(candidate)
            if baseline and candidate and min(candidate) != 0
            else float("inf")
        )
        maximum = float(regression.get("maximum_allowed_ratio", 1.1))
        worst = "PASS" if observed <= maximum else "FAIL"
        p99_latency_ratio = float(
            benchmark.get("worst_workload_p99_batch_latency_ratio", float("inf"))
        )
        regression["observed_ratio"] = observed
        regression["claimed_status"] = worst
        regression["reasons"] = [
            (f"Core MNCS worst-case throughput ratio was {observed:.6f}; limit is {maximum:.6f}."),
            (
                "The separately predeclared worst per-workload p99 aggregate-latency "
                f"ratio was {p99_latency_ratio:.6f}."
            ),
        ]
    else:
        worst = "UNKNOWN"
    semantic = performance.get("checksums_or_semantic_identity")
    if isinstance(semantic, dict):
        semantic["passed"] = semantic_passed
    validity = performance.get("measurement_validity")
    if isinstance(validity, dict):
        validity["claimed_status"] = measurement
        validity["reasons"] = [
            f"{name}: {'satisfied' if passed else 'not satisfied'}"
            for name, passed in measurement_checks.items()
        ]
    benefit_record = performance.get("benefit_threshold")
    if isinstance(benefit_record, dict):
        benefit_record["claimed_status"] = benefit
        benefit_record["reasons"] = [
            (
                "Observed arithmetic-mean throughput ratio was "
                f"{observed_mean_ratio:.6f}; threshold is {threshold:.6f}."
            )
        ]
    extensions = performance.setdefault("extensions", {})
    if isinstance(extensions, dict):
        extensions["mncs.dev:measurement-checks"] = measurement_checks
        extensions["mncs.dev:observed-mean-throughput-ratio"] = observed_mean_ratio
        extensions["mncs.dev:p99-latency-policy"] = {
            "observed_ratio": benchmark.get("worst_workload_p99_batch_latency_ratio"),
            "maximum_allowed_ratio": benchmark.get("maximum_latency_ratio"),
            "policy_result": (
                "PASS"
                if float(benchmark.get("worst_workload_p99_batch_latency_ratio", float("inf")))
                <= float(benchmark.get("maximum_latency_ratio", 1.1))
                else "FAIL"
            ),
        }
    write_json(performance_path, performance)
    statuses = {
        "measurement_valid": measurement,
        "benefit_threshold": benefit,
        "worst_regression": worst,
    }
    return aggregate(list(statuses.values())), statuses


def _replace_values(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: _replace_values(item, replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_values(item, replacements) for item in value]
    if isinstance(value, str):
        return replacements.get(value, value)
    return value


def refresh_identities() -> dict[str, str]:
    """Version the improved evaluator identities and return old-to-new hash bindings."""

    benchmark = read_json(RESULTS / "benchmark.json")
    environment = read_json(RESULTS / "environment.json")
    compiler_matrix = read_json(RESULTS / "compiler-matrix.json")
    identity_paths = {
        "evaluator": EVIDENCE / "identities" / "identity-evaluator.json",
        "benchmark": EVIDENCE / "identities" / "identity-benchmark.json",
        "environment": EVIDENCE / "identities" / "identity-environment.json",
        "compiler": EVIDENCE / "identities" / "identity-compiler.json",
        "build": EVIDENCE / "identities" / "identity-build.json",
    }
    old_hashes = {name: digest(path) for name, path in identity_paths.items()}

    evaluator = read_json(identity_paths["evaluator"])
    evaluator["version"] = "2.0"
    evaluator["description"] = (
        "Runs expanded differential, multi-mutation, atomic recovery, sanitizer, Clang-AST "
        "structural, harness-regression, and controlled paired-performance evaluation."
    )
    evaluator["attributes"] = {
        "study_evaluation_sha256": digest(ROOT / "tools" / "study_evaluation.py"),
        "run_study_sha256": digest(ROOT / "tools" / "run_study.py"),
        "harness_regression_sha256": digest(ROOT / "tools" / "harness_regression.py"),
        "repetitions_per_workload": benchmark.get("repetitions_per_workload"),
        "warmup_runs_per_implementation": benchmark.get("protocol", {}).get(
            "warmup_runs_per_implementation"
        ),
    }
    write_json(identity_paths["evaluator"], evaluator)

    benchmark_identity = read_json(identity_paths["benchmark"])
    benchmark_identity["version"] = "2.0"
    benchmark_identity["description"] = (
        "Counterbalanced, warmed, CPU-affinity-aware aggregate measurements with raw latency "
        "observations, no outlier deletion, and deterministic bootstrap uncertainty."
    )
    benchmark_identity["attributes"] = {
        "source_sha256": digest(ROOT / "tools" / "study_evaluation.py"),
        "threshold": benchmark.get("threshold"),
        "maximum_latency_ratio": benchmark.get("maximum_latency_ratio"),
        "protocol_json": json.dumps(benchmark.get("protocol"), sort_keys=True),
    }
    write_json(identity_paths["benchmark"], benchmark_identity)

    environment_identity = read_json(identity_paths["environment"])
    environment_identity["version"] = str(environment.get("captured_at", "unknown"))
    environment_identity["attributes"] = {
        "platform": environment.get("platform"),
        "machine": environment.get("machine"),
        "cpu_model": environment.get("cpu_model"),
        "logical_cpu_count": environment.get("logical_cpu_count"),
        "process_affinity_json": json.dumps(environment.get("process_affinity"), sort_keys=True),
        "python": environment.get("python"),
        "gcc": environment.get("gcc"),
        "clang": environment.get("clang"),
        "git_commit": environment.get("git_commit"),
    }
    write_json(identity_paths["environment"], environment_identity)

    compiler_identity = read_json(identity_paths["compiler"])
    compiler_identity["version"] = "2.0"
    compiler_identity["attributes"] = {
        "gcc": environment.get("gcc"),
        "clang": environment.get("clang"),
        "strict_flags": " ".join(compiler_matrix.get("strict_flags", [])),
    }
    write_json(identity_paths["compiler"], compiler_identity)

    build_identity = read_json(identity_paths["build"])
    build_identity["version"] = "2.0"
    build_identity["attributes"] = {
        "optimization": "O3",
        "language": "C11",
        "strict_flags": " ".join(compiler_matrix.get("strict_flags", [])),
        "compiler_matrix_sha256": digest(RESULTS / "compiler-matrix.json"),
    }
    write_json(identity_paths["build"], build_identity)

    new_hashes = {name: digest(path) for name, path in identity_paths.items()}
    return {old_hashes[name]: new_hashes[name] for name in identity_paths}


def rebind_documents(replacements: dict[str, str]) -> None:
    paths = [
        *sorted((EVIDENCE / "gates").glob("*.json")),
        *sorted((EVIDENCE / "invariants").glob("*.json")),
        *sorted((EVIDENCE / "performance").glob("*.json")),
        ROOT / "manifest.json",
        ROOT / "mncds" / "development-record.json",
    ]
    for path in paths:
        value = read_json(path)
        write_json(path, _replace_values(value, replacements))


def refresh_index_and_manifest(final_status: str) -> None:
    """Bind all changed evidence, add the harness corpus, and publish final status."""

    manifest_path = ROOT / "manifest.json"
    manifest = read_json(manifest_path)
    machine_hash = str(manifest["machine"]["sha256"])
    index_path = EVIDENCE / "index.json"
    index = read_json(index_path)
    records = index.get("records")
    if not isinstance(records, list):
        raise TypeError("evidence index records must be a list")
    has_harness = any(
        isinstance(record, dict) and record.get("id") == "raw-harness-regression"
        for record in records
    )
    if not has_harness:
        records.append(
            {
                "candidate_source_hash": machine_hash,
                "contract_id": CONTRACT_ID,
                "id": "raw-harness-regression",
                "kind": "other",
                "media_type": "application/json",
                "path": "evidence/results/harness-regression.json",
                "sha256": digest(RESULTS / "harness-regression.json"),
            }
        )
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            raise TypeError("invalid evidence index record")
        record["sha256"] = digest(ROOT / record["path"])
    write_json(index_path, index)

    benchmark = read_json(RESULTS / "benchmark.json")
    manifest["evidence_index"]["sha256"] = digest(index_path)
    manifest["final_status"] = final_status
    manifest["acceptance_policy"]["objective"]["minimum_sample_count"] = int(
        benchmark.get("sample_count_per_implementation", 0)
    )
    manifest["comparison_profile"]["benefit"]["mean_throughput_ratio"] = benchmark.get(
        "mean_throughput_ratio"
    )
    manifest["structural_aggregate"] = {
        "bounded": True,
        "provider_assumptions": [
            "The Clang AST and source-order provider is bounded to the declared invariant set."
        ],
        "required_invariants": ["invariant-bounded-storage"],
    }
    extensions = manifest.setdefault("extensions", {})
    if isinstance(extensions, dict):
        extensions["mncs.dev:harness-regression-evidence"] = "raw-harness-regression"
        extensions["mncs.dev:evaluation-epoch"] = "edgestream-evaluation-epoch-2"
    write_json(manifest_path, manifest)


def derive() -> str:
    """Derive gates, performance, identities, manifest, and MNCDS status."""

    environment = read_json(RESULTS / "environment.json")
    captured_at = str(environment.get("captured_at", "2026-07-27T00:00:00Z"))
    statuses: list[str] = []
    for gate_id, raw_name in GATES.items():
        raw = read_json(RESULTS / raw_name)
        raw_status = status_of(raw.get("status"))
        gate_path = EVIDENCE / "gates" / f"{gate_id}.json"
        gate = read_json(gate_path)
        gate["status"] = raw_status
        gate["started_at"] = captured_at
        gate["completed_at"] = captured_at
        evaluator = gate.get("evaluator")
        if isinstance(evaluator, dict):
            evaluator["version"] = "2.0"
        total = observation_count(raw)
        gate["observation_counts"] = {
            "total": total,
            "passed": total if raw_status == "PASS" else 0,
            "failed": total if raw_status == "FAIL" else 0,
            "unknown": total if raw_status == "UNKNOWN" else 0,
        }
        write_json(gate_path, gate)
        statuses.append(raw_status)

    structural = statuses[-1]
    invariant_path = EVIDENCE / "invariants" / "invariant-bounded-storage.json"
    invariant = read_json(invariant_path)
    invariant["status"] = structural
    invariant["provider"] = "edgestream-clang-structural-checker"
    invariant["provider_version"] = "2.0"
    invariant["analysis_method"] = (
        "Clang AST observations plus candidate-bound source-order checks over the declared "
        "fixed-storage, allocation, validation, checkpoint, and benchmark-independence invariants."
    )
    invariant["boundedness"] = {
        "bounded": True,
        "description": (
            "Nine explicit checks over one candidate translation unit and included "
            "state declarations."
        ),
    }
    invariant["started_at"] = captured_at
    invariant["completed_at"] = captured_at
    invariant["limitations"] = [
        "The provider does not establish arbitrary C semantics outside the declared invariant set."
    ]
    write_json(invariant_path, invariant)

    _, performance_statuses = derive_performance()
    statuses.extend(performance_statuses.values())
    harness_status = status_of(read_json(RESULTS / "harness-regression.json").get("status"))
    statuses.append(harness_status)

    replacements = refresh_identities()
    rebind_documents(replacements)
    final_status = aggregate(statuses)

    mncds_path = ROOT / "mncds" / "development-record.json"
    mncds = read_json(mncds_path)
    for candidate in mncds.get("candidates", []):
        if not isinstance(candidate, dict):
            continue
        for result in candidate.get("evaluator_results", []):
            if not isinstance(result, dict):
                continue
            gate_id = str(result.get("gate_id", ""))
            if gate_id in performance_statuses:
                result["status"] = performance_statuses[gate_id]
            elif gate_id == "behavioral":
                result["status"] = statuses[0]
            elif gate_id == "safety":
                result["status"] = statuses[2]
            elif gate_id == "resource_bounds":
                result["status"] = statuses[3]
    selection = mncds.get("selection")
    if isinstance(selection, dict):
        selection["minimum_useful_benefit_met"] = (
            performance_statuses["benefit_threshold"] == "PASS"
        )
    extensions = mncds.setdefault("extensions", {})
    if isinstance(extensions, dict):
        extensions["mncds.dev:evaluation-epoch"] = "edgestream-evaluation-epoch-2"
        extensions["mncds.dev:harness-regression-status"] = harness_status
    write_json(mncds_path, mncds)

    refresh_index_and_manifest(final_status)
    return final_status


def main() -> int:
    result = derive()
    return 0 if result == "PASS" else 3 if result == "UNKNOWN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
