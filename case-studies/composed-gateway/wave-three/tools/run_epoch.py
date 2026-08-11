#!/usr/bin/env python3
from __future__ import annotations

# Source layout is frozen for evidence identity; embedded fixtures may exceed line length.
# ruff: noqa: E501
# fmt: off

import argparse
import hashlib
import json
import os
import pathlib
import platform
import resource
import shutil
import statistics
import subprocess
import sys
import time
from typing import Any

WAVE = pathlib.Path(__file__).resolve().parents[1]
COMPOSED = WAVE.parent
REPO = WAVE.parents[2]
BUILD = WAVE / "build"
HOST = BUILD / "composed-host-wave3"
AUTHORITY = WAVE / "rust-authority/target/release/mncs-rust-authority-wave3"
WORKLOAD = "12\n30\n7\n9\n100\n5\n"
WARMUPS = 2
REPETITIONS = 9


def run(
    args: list[str],
    *,
    cwd: pathlib.Path | None = None,
    input_text: str = "",
    env: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(
        args,
        cwd=cwd,
        input=input_text,
        text=True,
        capture_output=True,
        env=merged,
        timeout=timeout,
        check=False,
    )


def must(completed: subprocess.CompletedProcess[str], label: str) -> subprocess.CompletedProcess[str]:
    if completed.returncode != 0:
        raise RuntimeError(f"{label} failed ({completed.returncode}): {completed.stderr or completed.stdout}")
    return completed


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def version(command: list[str]) -> str | None:
    try:
        completed = run(command, timeout=5)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    text = (completed.stdout or completed.stderr).strip().splitlines()
    return text[0] if completed.returncode == 0 and text else None


def parse_record(completed: subprocess.CompletedProcess[str], label: str) -> dict[str, Any]:
    must(completed, label)
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"{label} emitted invalid JSON: {error}") from error


def host_env(**extra: str) -> dict[str, str]:
    value = {
        "MNCS_RUST_AUTHORITY": str(AUTHORITY),
        "MNCS_TIMEOUT_MS": "2000",
    }
    value.update(extra)
    return value


def build(require_rust: bool) -> dict[str, Any]:
    BUILD.mkdir(parents=True, exist_ok=True)
    generator = WAVE / "tools/generate_binding.py"
    before = must(run([sys.executable, str(generator), "--print-identity"]), "binding identity before").stdout.strip()
    must(run([sys.executable, str(generator)]), "binding regeneration")
    must(run([sys.executable, str(generator), "--check"]), "binding drift check")
    after = must(run([sys.executable, str(generator), "--print-identity"]), "binding identity after").stdout.strip()
    if before != after:
        raise RuntimeError("binding regeneration identity changed")

    c_object = BUILD / "parser.o"
    must(
        run(
            [
                os.environ.get("CC", "cc"),
                "-std=c11",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-pedantic",
                "-c",
                str(COMPOSED / "c/parser.c"),
                "-o",
                str(c_object),
            ]
        ),
        "strict C11 build",
    )
    must(run(["go", "test", "./..."], cwd=WAVE / "go-host"), "Go unit tests")
    must(run(["go", "vet", "./..."], cwd=WAVE / "go-host"), "Go vet")
    must(run(["go", "test", "-race", "./..."], cwd=WAVE / "go-host"), "Go race tests")
    must(
        run(["go", "test", "-run=^$", "-fuzz=FuzzParseNative", "-fuzztime=2s", "./..."], cwd=WAVE / "go-host", timeout=20),
        "Go fuzz smoke",
    )
    must(run(["go", "build", "-trimpath", "-o", str(HOST), "."], cwd=WAVE / "go-host"), "Go host build")
    benchmark = must(
        run(
            [
                "go",
                "test",
                "-run=^$",
                "-bench=Benchmark(NativeParse|CheckpointDigest)$",
                "-benchmem",
                "-count=5",
                "./...",
            ],
            cwd=WAVE / "go-host",
        ),
        "Go component benchmarks",
    )

    cargo = shutil.which("cargo")
    rust_status = "UNKNOWN"
    if cargo:
        must(run([cargo, "fmt", "--check"], cwd=WAVE / "rust-authority"), "Rust fmt")
        must(run([cargo, "clippy", "--locked", "--", "-D", "warnings"], cwd=WAVE / "rust-authority", timeout=60), "Rust clippy")
        must(run([cargo, "test", "--locked"], cwd=WAVE / "rust-authority", timeout=60), "Rust tests")
        must(run([cargo, "build", "--locked", "--release"], cwd=WAVE / "rust-authority", timeout=60), "Rust release build")
        rust_status = "PASS"
    elif require_rust:
        raise RuntimeError("Rust toolchain is required for this epoch")

    return {
        "binding_regeneration": "PASS",
        "binding_identity_before": before,
        "binding_identity_after": after,
        "c11_build": "PASS",
        "go_tests": "PASS",
        "go_vet": "PASS",
        "go_race": "PASS",
        "go_fuzz_smoke": "PASS",
        "go_component_benchmarks": "PASS",
        "go_component_benchmark_output": benchmark.stdout[-16384:],
        "rust_toolchain": rust_status,
    }


def checkpoint_drills(rust_available: bool, output: pathlib.Path) -> dict[str, Any]:
    readable = parse_record(
        run([str(HOST)], input_text=WORKLOAD, env=host_env(MNCS_ROLLBACK="1")),
        "readable uninterrupted",
    )
    result: dict[str, Any] = {
        "readable_uninterrupted": "PASS",
        "readable_output_digest": readable["output_digest"],
        "recovery": "UNKNOWN",
        "replacement": "UNKNOWN",
        "identity_rejection": "PASS",
    }
    checkpoint = output / "checkpoint.json"

    # Identity rejection is exercised without Rust.
    failed = run(
        [str(HOST)],
        input_text=WORKLOAD,
        env=host_env(
            MNCS_ROLLBACK="1",
            MNCS_CHECKPOINT_PATH=str(checkpoint),
            MNCS_FAIL_AFTER="2",
        ),
    )
    if failed.returncode != 3 or not checkpoint.exists():
        raise RuntimeError("failed to create readable checkpoint")
    tampered = json.loads(checkpoint.read_text(encoding="utf-8"))
    tampered["binding_header"] = "0" * 64
    checkpoint.write_text(json.dumps(tampered), encoding="utf-8")
    rejected = run(
        [str(HOST)],
        input_text=WORKLOAD,
        env=host_env(
            MNCS_ROLLBACK="1",
            MNCS_RESUME="1",
            MNCS_CHECKPOINT_PATH=str(checkpoint),
        ),
    )
    if rejected.returncode != 3:
        raise RuntimeError("tampered checkpoint identity was accepted")

    if not rust_available:
        return result

    clean = parse_record(run([str(HOST)], input_text=WORKLOAD, env=host_env()), "composed uninterrupted")
    result["composed_uninterrupted"] = "PASS"
    result["composed_output_digest"] = clean["output_digest"]
    if clean["output_digest"] != readable["output_digest"]:
        raise RuntimeError("composed output differs from readable authority")

    checkpoint.unlink(missing_ok=True)
    interrupted = run(
        [str(HOST)],
        input_text=WORKLOAD,
        env=host_env(MNCS_CHECKPOINT_PATH=str(checkpoint), MNCS_FAIL_AFTER="3"),
    )
    if interrupted.returncode != 3 or not checkpoint.exists():
        raise RuntimeError("component failure did not retain checkpoint")
    started = time.perf_counter()
    recovered = parse_record(
        run(
            [str(HOST)],
            input_text=WORKLOAD,
            env=host_env(MNCS_CHECKPOINT_PATH=str(checkpoint), MNCS_RESUME="1"),
        ),
        "checkpoint recovery",
    )
    recovery_seconds = time.perf_counter() - started
    if recovered["output_digest"] != clean["output_digest"] or not recovered["recovered"]:
        raise RuntimeError("checkpoint recovery diverged")
    result.update(
        {
            "recovery": "PASS",
            "recovery_output_digest": recovered["output_digest"],
            "recovery_seconds": recovery_seconds,
        }
    )

    checkpoint.unlink(missing_ok=True)
    replaced = parse_record(
        run(
            [str(HOST)],
            input_text=WORKLOAD,
            env=host_env(
                MNCS_CHECKPOINT_PATH=str(checkpoint),
                MNCS_AUTHORITY_CRASH_AFTER="2",
                MNCS_FALLBACK="1",
                MNCS_ALLOW_READABLE_REPLACEMENT="1",
            ),
        ),
        "readable replacement drill",
    )
    if replaced["output_digest"] != clean["output_digest"] or not replaced["replaced"]:
        raise RuntimeError("replacement drill diverged")
    result.update(
        {
            "replacement": "PASS",
            "replacement_output_digest": replaced["output_digest"],
            "replacement_mode": replaced["mode"],
        }
    )
    return result


def measured_run(env: dict[str, str], checkpoint_path: pathlib.Path | None = None) -> dict[str, Any]:
    if checkpoint_path:
        env = dict(env)
        env["MNCS_CHECKPOINT_PATH"] = str(checkpoint_path)
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.perf_counter()
    completed = run([str(HOST)], input_text=WORKLOAD, env=env)
    elapsed = time.perf_counter() - started
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    record = parse_record(completed, "measurement")
    return {
        "wall_seconds": elapsed,
        "child_user_seconds": max(0.0, after.ru_utime - before.ru_utime),
        "child_system_seconds": max(0.0, after.ru_stime - before.ru_stime),
        "max_rss_observation": after.ru_maxrss,
        "output_digest": record["output_digest"],
        "mode": record["mode"],
    }


def summarize(values: list[dict[str, Any]]) -> dict[str, Any]:
    walls = [float(value["wall_seconds"]) for value in values]
    users = [float(value["child_user_seconds"]) for value in values]
    systems = [float(value["child_system_seconds"]) for value in values]
    return {
        "count": len(values),
        "wall_median_seconds": statistics.median(walls),
        "wall_min_seconds": min(walls),
        "wall_max_seconds": max(walls),
        "wall_mad_seconds": statistics.median([abs(value - statistics.median(walls)) for value in walls]),
        "child_user_median_seconds": statistics.median(users),
        "child_system_median_seconds": statistics.median(systems),
        "max_rss_observation_max": max(int(value["max_rss_observation"]) for value in values),
        "output_digests": sorted({str(value["output_digest"]) for value in values}),
        "throughput_messages_per_second": len(WORKLOAD.strip().splitlines()) / statistics.median(walls),
    }


def measurements(rust_available: bool, output: pathlib.Path, repetitions: int) -> dict[str, Any]:
    modes: dict[str, list[dict[str, Any]]] = {"readable": [], "readable_checkpoint": []}
    if rust_available:
        modes["composed"] = []
    for _ in range(WARMUPS):
        measured_run(host_env(MNCS_ROLLBACK="1"))
        if rust_available:
            measured_run(host_env())
    for index in range(repetitions):
        order = ["readable", "composed"] if index % 2 == 0 else ["composed", "readable"]
        if not rust_available:
            order = ["readable"]
        for name in order:
            modes[name].append(measured_run(host_env(MNCS_ROLLBACK="1") if name == "readable" else host_env()))
        checkpoint = output / f"measurement-checkpoint-{index}.json"
        modes["readable_checkpoint"].append(measured_run(host_env(MNCS_ROLLBACK="1"), checkpoint))
        checkpoint.unlink(missing_ok=True)
    summaries = {name: summarize(values) for name, values in modes.items()}
    if rust_available:
        summaries["derived"] = {
            "process_boundary_wall_overhead_seconds": summaries["composed"]["wall_median_seconds"] - summaries["readable"]["wall_median_seconds"],
            "process_to_readable_ratio": summaries["composed"]["wall_median_seconds"] / summaries["readable"]["wall_median_seconds"],
        }
    summaries["derived_checkpoint"] = {
        "checkpoint_wall_overhead_seconds": summaries["readable_checkpoint"]["wall_median_seconds"] - summaries["readable"]["wall_median_seconds"],
    }
    return {
        "warmups": WARMUPS,
        "repetitions": repetitions,
        "ordering": "alternating readable/composed; checkpoint measured after each pair",
        "outlier_policy": "none removed",
        "uncertainty": "median, range, and MAD; no global language comparison",
        "rss_note": "ru_maxrss units are platform dependent and retained as an environment observation",
        "summaries": summaries,
        "raw": modes,
        "events": {
            "fallback_attempts": 1 if rust_available else 0,
            "fallback_successes": 1 if rust_available else 0,
            "rejected_generated_proposals": 0,
            "valid_workload_protocol_rejections": 0,
            "configured_max_messages": 64,
        },
    }


def environment() -> dict[str, Any]:
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "go": version(["go", "version"]),
        "rustc": version(["rustc", "--version"]),
        "cargo": version(["cargo", "--version"]),
        "cc": version([os.environ.get("CC", "cc"), "--version"]),
        "github_sha": os.environ.get("GITHUB_SHA"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_runner_os": os.environ.get("RUNNER_OS"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--require-rust", action="store_true")
    parser.add_argument("--repetitions", type=int, default=REPETITIONS)
    args = parser.parse_args()
    if args.repetitions < 3:
        raise SystemExit("repetitions must be at least three")
    args.output.mkdir(parents=True, exist_ok=True)

    build_result = build(args.require_rust)
    rust_available = build_result["rust_toolchain"] == "PASS"
    drills = checkpoint_drills(rust_available, args.output)
    measurement = measurements(rust_available, args.output, args.repetitions)

    mutation_output = args.output / "mutations"
    mutation_status = "UNKNOWN"
    mutation_summary: dict[str, Any] | None = None
    if rust_available:
        completed = run([sys.executable, str(WAVE / "tools/run_mutations.py"), "--output", str(mutation_output)], timeout=120)
        must(completed, "mutation campaign")
        mutation_summary = json.loads((mutation_output / "summary.json").read_text(encoding="utf-8"))
        mutation_status = str(mutation_summary["status"])

    required_statuses = [
        build_result["c11_build"],
        build_result["go_tests"],
        build_result["go_vet"],
        build_result["go_race"],
        build_result["go_fuzz_smoke"],
        build_result["rust_toolchain"],
        drills["recovery"],
        drills["replacement"],
        mutation_status,
        "UNKNOWN",  # protected holdout requires external custody
        "UNKNOWN",  # independent evaluation requires an external evaluator
        "UNKNOWN",  # cross-host status requires aggregation of separate artifacts
    ]
    propagated = "PASS"
    if "FAIL" in required_statuses:
        propagated = "FAIL"
    elif "UNKNOWN" in required_statuses:
        propagated = "REVIEW_REQUIRED"

    result = {
        "schema_version": "0.3-experimental",
        "epoch_id": "composed-gateway-wave3-epoch-2",
        "system_contract_id": "contract:composed-gateway-wave3-0.2",
        "environment": environment(),
        "partitions": {
            "development": "PASS",
            "public_reproduction": "PASS" if rust_available else "UNKNOWN",
            "protected_holdout": "UNKNOWN",
        },
        "identities": {
            "go_host_source": "sha256:" + sha256(WAVE / "go-host/main.go"),
            "go_binding": "sha256:" + sha256(WAVE / "go-host/binding_gen.go"),
            "c_header": "sha256:" + sha256(COMPOSED / "c/parser.h"),
            "rust_authority_source": "sha256:" + sha256(WAVE / "rust-authority/src/main.rs"),
            "preregistration": "sha256:" + sha256(WAVE / "preregistration.json"),
        },
        "build_results": build_result,
        "recovery_drill": drills,
        "mutation_campaign": {
            "status": mutation_status,
            "summary": mutation_summary,
        },
        "measurements": measurement,
        "d4_regeneration_replacement_subclaim": "PASS" if drills["replacement"] == "PASS" and build_result["binding_regeneration"] == "PASS" else "UNKNOWN",
        "independent_evaluation": "UNKNOWN",
        "cross_host_reproduction": "UNKNOWN",
        "propagated_result": propagated,
        "formal_mncs_status": "UNKNOWN",
        "formal_mncds_status": "UNKNOWN",
        "promotion_authorized": False,
        "known_limitations": [
            "protected holdout is not available in the public repository",
            "the evaluator is structurally separate but not organizationally independent",
            "cross-host agreement is established only after hosted matrix artifacts are reviewed",
            "ru_maxrss units are platform dependent",
            "race, fuzz, and scheduler observations remain bounded",
        ],
    }
    result_path = args.output / "wave-three-epoch.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"epoch": result["epoch_id"], "result": propagated, "output": str(result_path)}, indent=2))
    return 1 if propagated == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
# fmt: on
