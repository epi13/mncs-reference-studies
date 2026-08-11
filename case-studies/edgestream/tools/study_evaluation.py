#!/usr/bin/env python3
"""Correctness, safety, recovery, structural, and performance evaluation for EdgeStream."""

from __future__ import annotations

import binascii
import json
import math
import os
import platform
import random
import re
import shutil
import statistics
import struct
import subprocess
import time
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Any

from study_support import (
    BUILD,
    RESULTS,
    ROOT,
    WORKLOADS,
    compile_binary,
    compile_flags,
    compiler_version,
    encode_frame,
    execute,
    filter_control,
    program,
    run,
    sha256,
    sha256_bytes,
    write_json,
)

BENCHMARK_REPETITIONS = 15
BENCHMARK_WARMUPS = 3
BENCHMARK_TARGET_SAMPLE_NS = 100_000_000
BENCHMARK_MAX_BATCH_ITERATIONS = 64
THROUGHPUT_THRESHOLD = 1.15
MAXIMUM_P99_LATENCY_RATIO = 1.10


def parse_metric(stderr: str) -> dict[str, Any]:
    """Return the final JSON metric line while tolerating preceding diagnostics."""

    for line in reversed(stderr.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "elapsed_ns" in value:
            return value
    raise ValueError("program did not emit a parseable metric record")


def _output_hash(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def differential_tests() -> dict[str, Any]:
    reference = program("reference")
    candidate = program("candidate")
    cases: list[dict[str, Any]] = []
    status = "PASS"
    chunks = (1, 2, 3, 7, 15, 31, 32, 33, 257, 1024, 4096)
    for workload in sorted(WORKLOADS.glob("*.bin")):
        baseline = execute(reference, workload, 4096, check=False)
        baseline_hash = _output_hash(baseline.stdout)
        for chunk in chunks:
            ref = execute(reference, workload, chunk, check=False)
            cand = execute(candidate, workload, chunk, check=False)
            ref_hash = _output_hash(ref.stdout)
            cand_hash = _output_hash(cand.stdout)
            passed = (
                ref.stdout == baseline.stdout
                and cand.stdout == baseline.stdout
                and ref.returncode == baseline.returncode
                and cand.returncode == baseline.returncode
            )
            cases.append(
                {
                    "workload": workload.name,
                    "workload_sha256": sha256(workload),
                    "chunk": chunk,
                    "status": "PASS" if passed else "FAIL",
                    "reference_exit": ref.returncode,
                    "candidate_exit": cand.returncode,
                    "baseline_exit": baseline.returncode,
                    "baseline_output_sha256": baseline_hash,
                    "reference_output_sha256": ref_hash,
                    "candidate_output_sha256": cand_hash,
                    "outputs_equal": ref_hash == cand_hash == baseline_hash,
                    "output_bytes": len(cand.stdout.encode("utf-8")),
                }
            )
            if not passed:
                status = "FAIL"
    result = {
        "status": status,
        "chunk_sizes": list(chunks),
        "case_count": len(cases),
        "cases": cases,
    }
    write_json(RESULTS / "differential.json", result)
    return result


def _repair_crc(frame: bytearray) -> None:
    frame[28:32] = struct.pack("<I", binascii.crc32(bytes(frame[:28])) & 0xFFFFFFFF)


def mutation_test() -> dict[str, Any]:
    clean = bytearray(encode_frame(1, 0, 11, 1, 7_000_000, 1, 47000))
    payload_bit = bytearray(clean)
    payload_bit[9] ^= 0x80
    bad_version = bytearray(clean)
    bad_version[2] = 9
    _repair_crc(bad_version)
    bad_length = bytearray(clean)
    bad_length[4:6] = struct.pack("<H", 31)
    bad_metric = bytearray(encode_frame(1, 0, 11, 1, 7_000_000, 9, 47000))

    mutations = [
        ("payload-bit-with-stale-checksum", bytes(payload_bit), "checksum", 0),
        ("unsupported-version-with-valid-checksum", bytes(bad_version), "version", 0),
        ("invalid-frame-length", bytes(bad_length), "length", 0),
        ("truncated-frame", bytes(clean[:17]), "truncated", 0),
        ("junk-prefix-resynchronization", b"JUNK" + bytes(clean), "junk", 1),
        ("out-of-range-metric", bytes(bad_metric), "metric", 0),
    ]
    cases: list[dict[str, Any]] = []
    overall = "PASS"
    for mutation, payload, reason, expected_accepted in mutations:
        path = BUILD / f"mutation-{mutation}.bin"
        path.write_bytes(payload)
        for chunk in (1, 5, 31):
            ref = execute(program("reference"), path, chunk, check=False)
            cand = execute(program("candidate"), path, chunk, check=False)
            ref_metric = parse_metric(ref.stderr)
            cand_metric = parse_metric(cand.stderr)
            reason_token = f'"reason":"{reason}"'
            passed = (
                ref.stdout == cand.stdout
                and reason_token in cand.stdout
                and int(ref_metric["accepted"]) == expected_accepted
                and int(cand_metric["accepted"]) == expected_accepted
                and int(ref_metric["rejected"]) >= 1
                and int(cand_metric["rejected"]) >= 1
                and ref.returncode == cand.returncode
            )
            case = {
                "mutation": mutation,
                "chunk": chunk,
                "expected_rejection_reason": reason,
                "status": "PASS" if passed else "FAIL",
                "reference_exit": ref.returncode,
                "candidate_exit": cand.returncode,
                "reference_output_sha256": _output_hash(ref.stdout),
                "candidate_output_sha256": _output_hash(cand.stdout),
                "outputs_equal": ref.stdout == cand.stdout,
                "reference_metric": ref_metric,
                "candidate_metric": cand_metric,
                "rejection_reason_observed": reason_token in cand.stdout,
            }
            cases.append(case)
            if not passed:
                overall = "FAIL"
    result = {
        "status": overall,
        "mutation_count": len(mutations),
        "case_count": len(cases),
        "cases": cases,
    }
    write_json(RESULTS / "mutation.json", result)
    return result


def _checkpoint_corruptions(data: bytes) -> dict[str, bytes]:
    payload_flip = bytearray(data)
    payload_flip[-1] ^= 0x01
    bad_magic = bytearray(data)
    bad_magic[0:4] = b"FAIL"
    return {
        "payload-bit-flip": bytes(payload_flip),
        "bad-magic": bytes(bad_magic),
        "truncated-header": data[:8],
        "truncated-payload": data[:-17],
    }


def checkpoint_tests() -> dict[str, Any]:
    workload = WORKLOADS / "steady.bin"
    data = workload.read_bytes()
    split = (len(data) // 2 // 32) * 32
    first_path = BUILD / "recovery-first.bin"
    second_path = BUILD / "recovery-second.bin"
    first_path.write_bytes(data[:split])
    second_path.write_bytes(data[split:])
    full_outputs = {
        name: execute(program(name), workload, 37, check=False)
        for name in ("reference", "candidate")
    }
    cases: list[dict[str, Any]] = []
    status = "PASS"

    for producer in ("reference", "candidate"):
        producer_binary = program(producer)
        checkpoint = BUILD / f"{producer}.checkpoint"
        first = execute(
            producer_binary,
            first_path,
            11,
            ["--checkpoint-out", str(checkpoint)],
            check=False,
        )
        valid_checkpoint = checkpoint.exists() and first.returncode == 0
        checkpoint_hash = sha256(checkpoint) if checkpoint.exists() else None
        checkpoint_bytes = checkpoint.read_bytes() if checkpoint.exists() else b""

        for consumer in ("reference", "candidate"):
            restored = execute(
                program(consumer),
                second_path,
                19,
                ["--checkpoint-in", str(checkpoint)],
                check=False,
            )
            expected = filter_control(full_outputs[consumer].stdout)
            combined = filter_control(first.stdout) + filter_control(restored.stdout)
            passed = valid_checkpoint and restored.returncode in (0, 1) and combined == expected
            cases.append(
                {
                    "kind": "cross-implementation-restore",
                    "producer": producer,
                    "consumer": consumer,
                    "status": "PASS" if passed else "FAIL",
                    "checkpoint_sha256": checkpoint_hash,
                    "checkpoint_bytes": len(checkpoint_bytes),
                    "restored_output_sha256": _output_hash("\n".join(combined)),
                    "expected_output_sha256": _output_hash("\n".join(expected)),
                    "restore_exit": restored.returncode,
                }
            )
            if not passed:
                status = "FAIL"

        for step in range(1, 5):
            before_hash = sha256(checkpoint)
            failed = execute(
                producer_binary,
                first_path,
                23,
                ["--checkpoint-out", str(checkpoint), "--fail-checkpoint-step", str(step)],
                check=False,
            )
            after_hash = sha256(checkpoint)
            temporary = Path(str(checkpoint) + ".tmp")
            recover = execute(
                producer_binary,
                second_path,
                29,
                ["--checkpoint-in", str(checkpoint)],
                check=False,
            )
            combined = filter_control(first.stdout) + filter_control(recover.stdout)
            expected = filter_control(full_outputs[producer].stdout)
            passed = (
                failed.returncode != 0
                and before_hash == after_hash
                and not temporary.exists()
                and recover.returncode in (0, 1)
                and combined == expected
            )
            cases.append(
                {
                    "kind": "atomic-checkpoint-fault",
                    "implementation": producer,
                    "fault_step": step,
                    "status": "PASS" if passed else "FAIL",
                    "failure_exit": failed.returncode,
                    "recovery_exit": recover.returncode,
                    "prior_checkpoint_preserved": before_hash == after_hash,
                    "temporary_removed": not temporary.exists(),
                    "recovered_output_matches": combined == expected,
                }
            )
            if not passed:
                status = "FAIL"

        for corruption, corrupted_bytes in _checkpoint_corruptions(checkpoint_bytes).items():
            corrupted = BUILD / f"{producer}-{corruption}.checkpoint"
            corrupted.write_bytes(corrupted_bytes)
            for consumer in ("reference", "candidate"):
                restored = execute(
                    program(consumer),
                    second_path,
                    17,
                    ["--checkpoint-in", str(corrupted)],
                    check=False,
                )
                failure_record = '"type":"recovery","status":"FAIL"' in restored.stdout
                passed = restored.returncode == 3 and failure_record
                cases.append(
                    {
                        "kind": "corrupt-checkpoint-rejection",
                        "producer": producer,
                        "consumer": consumer,
                        "corruption": corruption,
                        "status": "PASS" if passed else "FAIL",
                        "restore_exit": restored.returncode,
                        "failure_record_observed": failure_record,
                        "corrupt_checkpoint_sha256": sha256(corrupted),
                    }
                )
                if not passed:
                    status = "FAIL"

    result = {
        "status": status,
        "case_count": len(cases),
        "cases": cases,
    }
    write_json(RESULTS / "checkpoint-recovery.json", result)
    return result


def sanitizer_tests() -> dict[str, Any]:
    compiler = "clang" if shutil.which("clang") else "gcc" if shutil.which("gcc") else None
    if compiler is None:
        result = {"status": "UNKNOWN", "reason": "No supported compiler available"}
        write_json(RESULTS / "sanitizers.json", result)
        return result

    sanitizer_env = {
        "ASAN_OPTIONS": "detect_leaks=1:halt_on_error=1:abort_on_error=1",
        "UBSAN_OPTIONS": "halt_on_error=1:print_stacktrace=1",
    }
    results: dict[str, Any] = {
        "compiler": compiler,
        "compiler_version": compiler_version(compiler),
        "compile_flags": compile_flags(sanitizers=True),
        "runtime_options": sanitizer_env,
        "implementations": {},
        "status": "PASS",
    }
    error_markers = (
        "ERROR: AddressSanitizer",
        "LeakSanitizer",
        "runtime error:",
        "SUMMARY: UndefinedBehaviorSanitizer",
    )
    for name, source in (
        ("reference", ROOT / "reference" / "edgestream_reference.c"),
        ("candidate", ROOT / "machine" / "edgestream_generated.c"),
    ):
        binary = BUILD / f"{name}-sanitized"
        implementation: dict[str, Any] = {"cases": [], "status": "PASS"}
        try:
            command = compile_binary(compiler, source, binary, sanitizers=True)
            implementation["compile_command"] = command
            implementation["binary_sha256"] = sha256(binary)
            for workload in sorted(WORKLOADS.glob("*.bin")):
                for chunk in (1, 17, 4096):
                    completed = execute(
                        binary,
                        workload,
                        chunk,
                        ["--quiet"],
                        check=False,
                        env=sanitizer_env,
                        timeout=240.0,
                    )
                    diagnostics = [marker for marker in error_markers if marker in completed.stderr]
                    metric: dict[str, Any] | None = None
                    try:
                        metric = parse_metric(completed.stderr)
                    except ValueError:
                        diagnostics.append("missing-metric-record")
                    passed = completed.returncode in (0, 1) and not diagnostics
                    implementation["cases"].append(
                        {
                            "workload": workload.name,
                            "chunk": chunk,
                            "status": "PASS" if passed else "FAIL",
                            "exit": completed.returncode,
                            "diagnostics": diagnostics,
                            "stderr_sha256": _output_hash(completed.stderr),
                            "metric": metric,
                        }
                    )
                    if not passed:
                        implementation["status"] = "FAIL"
                        results["status"] = "FAIL"
        except subprocess.CalledProcessError as error:
            implementation = {
                "status": "FAIL",
                "compile_stderr": error.stderr,
                "compile_stdout": error.stdout,
            }
            results["status"] = "FAIL"
        results["implementations"][name] = implementation
    write_json(RESULTS / "sanitizers.json", results)
    return results


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")
    ordered = sorted(values)
    index = min(len(ordered) - 1, math.ceil(fraction * len(ordered)) - 1)
    return ordered[index]


def _bootstrap_ci(values: list[float], *, samples: int = 4000) -> tuple[float, float]:
    if not values:
        raise ValueError("bootstrap requires observations")
    rng = random.Random(0xED63)
    estimates = [statistics.fmean(rng.choice(values) for _ in values) for _ in range(samples)]
    return percentile(estimates, 0.025), percentile(estimates, 0.975)


def _governor(cpu: int) -> str | None:
    path = Path(f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_governor")
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


@contextmanager
def _pinned_cpu() -> Iterator[dict[str, Any]]:
    control: dict[str, Any] = {
        "supported": hasattr(os, "sched_getaffinity") and hasattr(os, "sched_setaffinity"),
        "pinned": False,
        "cpu": None,
        "governor": None,
    }
    original: set[int] | None = None
    if control["supported"]:
        try:
            original = set(os.sched_getaffinity(0))
            cpu = min(original)
            os.sched_setaffinity(0, {cpu})
            control.update(pinned=True, cpu=cpu, governor=_governor(cpu))
        except (OSError, ValueError):
            original = None
    try:
        yield control
    finally:
        if original:
            with suppress(OSError):
                os.sched_setaffinity(0, original)


def _run_metric(binary: Path, workload: Path) -> dict[str, Any]:
    completed = execute(binary, workload, 4096, ["--quiet"], check=False, timeout=240.0)
    if completed.returncode not in (0, 1):
        raise RuntimeError(f"benchmark execution failed: {binary} {workload}")
    return parse_metric(completed.stderr)


def _batch_metric(binary: Path, workload: Path, iterations: int) -> dict[str, Any]:
    observations = [_run_metric(binary, workload) for _ in range(iterations)]
    signatures = {
        (int(item["bytes"]), int(item["accepted"]), int(item["rejected"])) for item in observations
    }
    if len(signatures) != 1:
        raise RuntimeError("benchmark semantics varied between repeated executions")
    bytes_per_run, accepted_per_run, rejected_per_run = signatures.pop()
    elapsed = [int(item["elapsed_ns"]) for item in observations]
    return {
        "implementation": str(observations[0]["implementation"]),
        "iterations": iterations,
        "bytes_per_run": bytes_per_run,
        "accepted_per_run": accepted_per_run,
        "rejected_per_run": rejected_per_run,
        "bytes": bytes_per_run * iterations,
        "accepted": accepted_per_run * iterations,
        "rejected": rejected_per_run * iterations,
        "elapsed_ns": sum(elapsed),
        "run_elapsed_ns": elapsed,
        "minimum_run_elapsed_ns": min(elapsed),
        "maximum_run_elapsed_ns": max(elapsed),
    }


def benchmark(
    repetitions: int = BENCHMARK_REPETITIONS,
    warmups: int = BENCHMARK_WARMUPS,
    target_sample_ns: int = BENCHMARK_TARGET_SAMPLE_NS,
) -> dict[str, Any]:
    reference = program("reference")
    candidate = program("candidate")
    workloads = [WORKLOADS / "steady.bin", WORKLOADS / "high-cardinality.bin"]
    samples: list[dict[str, Any]] = []
    ratios: list[float] = []
    latency_by_workload: dict[str, Any] = {}

    with _pinned_cpu() as cpu_control:
        for workload in workloads:
            for _ in range(warmups):
                _run_metric(reference, workload)
                _run_metric(candidate, workload)
            probes = {
                "reference": _run_metric(reference, workload),
                "candidate": _run_metric(candidate, workload),
            }
            fastest = min(int(item["elapsed_ns"]) for item in probes.values())
            iterations = max(1, math.ceil((target_sample_ns * 1.20) / max(fastest, 1)))
            iterations = min(iterations, BENCHMARK_MAX_BATCH_ITERATIONS)
            workload_latencies: dict[str, list[float]] = {"reference": [], "candidate": []}

            for repetition in range(repetitions):
                if repetition % 2 == 0:
                    order = (("reference", reference), ("candidate", candidate))
                else:
                    order = (("candidate", candidate), ("reference", reference))
                record: dict[str, Any] = {
                    "workload": workload.name,
                    "workload_sha256": sha256(workload),
                    "repetition": repetition + 1,
                    "execution_order": [label for label, _ in order],
                    "batch_iterations": iterations,
                }
                for label, binary in order:
                    metric = _batch_metric(binary, workload, iterations)
                    record[label] = metric
                    workload_latencies[label].append(float(metric["elapsed_ns"]))
                ratio = float(record["reference"]["elapsed_ns"]) / float(
                    record["candidate"]["elapsed_ns"]
                )
                record["throughput_ratio"] = ratio
                ratios.append(ratio)
                samples.append(record)

            latency_summary: dict[str, Any] = {
                "raw_batch_elapsed_ns": workload_latencies,
                "reference": {},
                "candidate": {},
            }
            for label in ("reference", "candidate"):
                values = workload_latencies[label]
                latency_summary[label] = {
                    "p50_ns": percentile(values, 0.50),
                    "p95_ns": percentile(values, 0.95),
                    "p99_ns": percentile(values, 0.99),
                    "minimum_ns": min(values),
                    "maximum_ns": max(values),
                }
            latency_summary["p99_ratio"] = (
                latency_summary["candidate"]["p99_ns"] / latency_summary["reference"]["p99_ns"]
            )
            latency_by_workload[workload.name] = latency_summary

    baseline_throughputs = [
        float(sample["reference"]["bytes"])
        * 1_000_000_000.0
        / float(sample["reference"]["elapsed_ns"])
        for sample in samples
    ]
    candidate_throughputs = [
        float(sample["candidate"]["bytes"])
        * 1_000_000_000.0
        / float(sample["candidate"]["elapsed_ns"])
        for sample in samples
    ]
    mean_ratio = statistics.fmean(candidate_throughputs) / statistics.fmean(baseline_throughputs)
    median_ratio = statistics.median(ratios)
    paired_mean = statistics.fmean(ratios)
    ci_low, ci_high = _bootstrap_ci(ratios)
    worst_latency_ratio = max(float(value["p99_ratio"]) for value in latency_by_workload.values())
    minimum_aggregate_elapsed = min(
        int(sample[label]["elapsed_ns"])
        for sample in samples
        for label in ("reference", "candidate")
    )
    passed = mean_ratio >= THROUGHPUT_THRESHOLD and worst_latency_ratio <= MAXIMUM_P99_LATENCY_RATIO
    result = {
        "status": "PASS" if passed else "FAIL",
        "protocol": {
            "repetitions_per_workload": repetitions,
            "warmup_runs_per_implementation": warmups,
            "target_minimum_sample_elapsed_ns": target_sample_ns,
            "minimum_observed_sample_elapsed_ns": minimum_aggregate_elapsed,
            "maximum_batch_iterations": BENCHMARK_MAX_BATCH_ITERATIONS,
            "order_policy": "deterministically counterbalanced by paired repetition",
            "outlier_policy": "retain every measured sample in execution order",
            "timer": "CLOCK_MONOTONIC inside each process; batch values sum raw runs",
            "cpu_affinity": cpu_control,
        },
        "repetitions_per_workload": repetitions,
        "sample_count_per_implementation": len(samples),
        "mean_throughput_ratio": mean_ratio,
        "mean_throughput_ratio_method": (
            "arithmetic mean candidate throughput divided by arithmetic mean reference throughput"
        ),
        "mean_paired_throughput_ratio": paired_mean,
        "median_paired_throughput_ratio": median_ratio,
        "paired_mean_ratio_bootstrap_ci95": {"lower": ci_low, "upper": ci_high},
        "worst_workload_p99_batch_latency_ratio": worst_latency_ratio,
        "latency_by_workload": latency_by_workload,
        "threshold": THROUGHPUT_THRESHOLD,
        "maximum_latency_ratio": MAXIMUM_P99_LATENCY_RATIO,
        "samples": samples,
    }
    write_json(RESULTS / "benchmark.json", result)
    return result


def _walk_ast(node: Any) -> Iterator[dict[str, Any]]:
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk_ast(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk_ast(value)


def _decl_ref_name(node: dict[str, Any]) -> str | None:
    for child in _walk_ast(node.get("inner", [])):
        if child.get("kind") == "DeclRefExpr":
            referenced = child.get("referencedDecl")
            if isinstance(referenced, dict) and isinstance(referenced.get("name"), str):
                return str(referenced["name"])
    return None


def _clang_ast(source: Path) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    if not shutil.which("clang"):
        return None, {"status": "UNKNOWN", "reason": "clang is unavailable"}
    source_argument = str(source.relative_to(ROOT)) if source.is_relative_to(ROOT) else str(source)
    command = [
        "clang",
        "-std=c11",
        "-D_POSIX_C_SOURCE=200809L",
        "-Iinclude",
        "-Xclang",
        "-ast-dump=json",
        "-fsyntax-only",
        source_argument,
    ]
    recorded_command = [
        *command[:-1],
        source_argument if source.is_relative_to(ROOT) else "<external-source>",
    ]
    try:
        completed = run(command, timeout=180.0)
        ast = json.loads(completed.stdout)
        if not isinstance(ast, dict):
            raise TypeError("clang AST root is not an object")
        return ast, {
            "status": "PASS",
            "command": recorded_command,
            "clang_version": compiler_version("clang"),
            "ast_sha256": _output_hash(completed.stdout),
        }
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        json.JSONDecodeError,
        TypeError,
    ) as error:
        return None, {"status": "UNKNOWN", "reason": str(error), "command": recorded_command}


def structural_checks(
    source_path: Path | None = None,
    *,
    write_result: bool = True,
) -> dict[str, Any]:
    source = source_path or ROOT / "machine" / "edgestream_generated.c"
    candidate = source.read_text(encoding="utf-8")
    ast, provider = _clang_ast(source)
    call_names: set[str] = set()
    field_types: dict[str, str] = {}
    table_type: str | None = None
    if ast is not None:
        for node in _walk_ast(ast):
            kind = node.get("kind")
            if kind == "CallExpr":
                name = _decl_ref_name(node)
                if name:
                    call_names.add(name)
            elif kind == "FieldDecl" and node.get("name") in {"buffer", "devices"}:
                type_value = node.get("type")
                if isinstance(type_value, dict):
                    field_types[str(node.get("name"))] = str(type_value.get("qualType", ""))
            elif kind == "VarDecl" and node.get("name") == "crc32_table":
                type_value = node.get("type")
                if isinstance(type_value, dict):
                    table_type = str(type_value.get("qualType", ""))

    checksum_index = candidate.find("if (expected != actual)")
    accept_index = candidate.find("accept_frame(p")
    checks: dict[str, bool | None] = {
        "generated_marker": "MNCS-GENERATED" in candidate,
        "bounded_storage_ast": (
            bool(re.search(r"\[4096(?:U)?\]", field_types.get("buffer", "")))
            and bool(re.search(r"\[64(?:U)?\]", field_types.get("devices", "")))
        )
        if ast is not None
        else None,
        "no_dynamic_allocation_in_processor_ast": not bool(
            {"malloc", "calloc", "realloc", "aligned_alloc"} & call_names
        )
        if ast is not None
        else None,
        "crc_table_shape_ast": bool(re.search(r"\[256(?:U)?\]", table_type or ""))
        if ast is not None
        else None,
        "frame_length_checked": "frame_length != ES_MAX_FRAME_SIZE" in candidate,
        "checksum_precedes_accept": 0 <= checksum_index < accept_index,
        "no_benchmark_workload_branch": (
            '"steady.bin"' not in candidate
            and '"high-cardinality.bin"' not in candidate
            and "getenv(" not in candidate
        ),
        "checkpoint_integrity": "header.crc != crc32_slow" in candidate,
        "candidate_identity_bound": source.exists(),
    }
    statuses = {
        name: "UNKNOWN" if passed is None else "PASS" if passed else "FAIL"
        for name, passed in checks.items()
    }
    if "FAIL" in statuses.values():
        status = "FAIL"
    elif "UNKNOWN" in statuses.values():
        status = "UNKNOWN"
    else:
        status = "PASS"
    ledger = [
        {
            "checker": "edgestream-clang-structural-checker",
            "version": "2.0",
            "invariant": name,
            "status": item_status,
            "finding": (
                "declared structural observation satisfied"
                if item_status == "PASS"
                else "declared structural observation failed"
                if item_status == "FAIL"
                else "provider could not establish the observation"
            ),
            "candidate": sha256(source),
            "analysis_scope": (
                "Clang AST plus candidate-bound source-order checks for the declared invariant set"
            ),
            "false_positive_assessment": "none specifically suspected",
            "false_negative_assessment": (
                "none specifically suspected within the declared invariant set"
            ),
            "caused_repair": False,
        }
        for name, item_status in statuses.items()
    ]
    result = {
        "status": status,
        "provider": provider,
        "checks": checks,
        "check_statuses": statuses,
        "ast_observations": {
            "call_names": sorted(call_names),
            "es_processor_field_types": field_types,
            "crc32_table_type": table_type,
        },
        "ledger": ledger,
        "candidate_sha256": sha256(source),
        "semantic_scope": (
            "Bounded proof obligations for fixed storage, allocation calls, validation order, "
            "checkpoint integrity, generated identity, and benchmark independence."
        ),
        "limitations": [
            (
                "This bounded provider does not prove arbitrary C semantics outside "
                "the declared invariant set."
            ),
            "Joern is optional for this study and is recorded separately when unavailable.",
        ],
    }
    if write_result:
        write_json(RESULTS / "structural.json", result)
    return result


def _cpu_model() -> str | None:
    try:
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return None


def parse_joern_version(stdout: str, stderr: str) -> str | None:
    """Extract a real Joern version without treating launcher warnings as identity."""

    combined = stdout + "\n" + stderr
    match = re.search(r"(?m)^Version:\s*([0-9][0-9A-Za-z.+-]*)\s*$", combined)
    return match.group(1) if match else None


def environment_record() -> dict[str, Any]:
    git = run(["git", "rev-parse", "HEAD"], check=False)
    affinity = sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None
    joern_path = shutil.which("joern")
    joern_version: str | None = None
    joern_status = "UNKNOWN"
    if joern_path:
        joern = run([joern_path, "--version"], check=False, timeout=30.0)
        joern_version = parse_joern_version(joern.stdout, joern.stderr)
        if joern.returncode == 0 and joern_version is not None:
            joern_status = "AVAILABLE"
    value = {
        "status": "PASS",
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_model": _cpu_model(),
        "logical_cpu_count": os.cpu_count(),
        "process_affinity": affinity,
        "python": platform.python_version(),
        "gcc": compiler_version("gcc") if shutil.which("gcc") else None,
        "clang": compiler_version("clang") if shutil.which("clang") else None,
        "strict_compile_flags": compile_flags(),
        "sanitizer_compile_flags": compile_flags(sanitizers=True),
        "joern": joern_version,
        "joern_status": joern_status,
        "git_commit": git.stdout.strip() if git.returncode == 0 else None,
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    write_json(RESULTS / "environment.json", value)
    return value
