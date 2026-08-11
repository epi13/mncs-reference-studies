#!/usr/bin/env python3
"""Shared build, execution, workload, and environment support for EdgeStream."""

from __future__ import annotations

import binascii
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
WORKLOADS = ROOT / "workloads"
RESULTS = ROOT / "evidence" / "results"

STRICT_FLAGS = [
    "-std=c11",
    "-D_POSIX_C_SOURCE=200809L",
    "-Wall",
    "-Wextra",
    "-Wpedantic",
    "-Wconversion",
    "-Wshadow",
    "-Wformat=2",
    "-Wstrict-prototypes",
    "-Wcast-align",
    "-Wnull-dereference",
    "-Werror",
    "-fno-common",
    "-Iinclude",
    "-O3",
]
SANITIZER_FLAGS = [
    "-std=c11",
    "-D_POSIX_C_SOURCE=200809L",
    "-Wall",
    "-Wextra",
    "-Wpedantic",
    "-Wconversion",
    "-Wshadow",
    "-Wformat=2",
    "-Wstrict-prototypes",
    "-Wcast-align",
    "-Wnull-dereference",
    "-Werror",
    "-fno-common",
    "-Iinclude",
    "-O1",
    "-g",
    "-fsanitize=address,undefined",
    "-fno-omit-frame-pointer",
]


def sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(
    command: list[str],
    *,
    check: bool = True,
    capture: bool = True,
    env: Mapping[str, str] | None = None,
    timeout: float = 180.0,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        command,
        cwd=ROOT,
        check=check,
        text=True,
        capture_output=capture,
        env=merged_env,
        timeout=timeout,
    )


def encode_frame(
    version: int,
    flags: int,
    device: int,
    sequence: int,
    timestamp: int,
    metric: int,
    value: int,
) -> bytes:
    prefix = struct.pack(
        "<2sBBHIIQHi",
        b"\xe5G",
        version,
        flags,
        32,
        device,
        sequence & 0xFFFFFFFF,
        timestamp,
        metric,
        value,
    )
    return prefix + struct.pack("<I", binascii.crc32(prefix) & 0xFFFFFFFF)


def generate_workloads() -> dict[str, dict[str, Any]]:
    WORKLOADS.mkdir(parents=True, exist_ok=True)
    metadata: dict[str, dict[str, Any]] = {}

    steady = bytearray()
    for round_id in range(1200):
        for device in range(1, 33):
            version = 1 if (round_id + device) % 2 == 0 else 2
            metric = (round_id + device) % 4
            normalized = 42000 + ((round_id * 37 + device * 101) % 16000)
            raw = normalized if version == 1 else normalized // 10
            steady += encode_frame(
                version,
                0,
                device,
                round_id,
                1_000_000 + round_id * 1000,
                metric,
                raw,
            )
    steady += encode_frame(1, 0, 0, 0, 1_000_000 + 1_300_000, 0xFFFF, 0)
    (WORKLOADS / "steady.bin").write_bytes(steady)

    hostile = bytearray(b"JUNK")
    for index in range(2500):
        frame = bytearray(
            encode_frame(
                1 + index % 2,
                0,
                1 + index % 20,
                index // 20,
                2_000_000 + index * 73,
                index % 4,
                35000 + index % 20000,
            )
        )
        if index % 17 == 0:
            hostile += b"\x00\xff"
        if index % 23 == 0:
            frame[7] ^= 0x20
        if index % 29 == 0:
            frame[2] = 9
            prefix = bytes(frame[:28])
            frame[28:] = struct.pack("<I", binascii.crc32(prefix) & 0xFFFFFFFF)
        if index % 31 == 0:
            hostile += frame
        hostile += frame
        if index % 37 == 0:
            hostile += frame[:11]
    (WORKLOADS / "hostile.bin").write_bytes(hostile)

    high = bytearray()
    sequence = 0
    for round_id in range(800):
        for device in range(1, 65):
            high += encode_frame(
                1,
                0,
                device,
                round_id,
                3_000_000 + sequence * 10,
                round_id % 4,
                30000 + ((device * 91 + round_id * 13) % 30000),
            )
            sequence += 1
    for device in range(65, 73):
        high += encode_frame(1, 0, device, 0, 4_000_000, 0, 40000)
    (WORKLOADS / "high-cardinality.bin").write_bytes(high)

    edge = bytearray()
    edge += encode_frame(1, 0, 7, 0xFFFFFFFE, 5_000_000, 0, 51000)
    edge += encode_frame(1, 0, 7, 0xFFFFFFFF, 5_001_000, 0, 52000)
    edge += encode_frame(1, 0, 7, 0, 5_002_000, 0, 53000)
    edge += encode_frame(1, 0, 7, 0, 5_002_000, 0, 53000)
    edge += encode_frame(1, 0, 7, 0xFFFFFFFF, 5_003_000, 0, 10000)
    edge += encode_frame(2, 1, 7, 1, 5_004_000, 0, 4000)
    edge += encode_frame(1, 0, 0, 0, 5_100_001, 0xFFFF, 0)
    edge += encode_frame(1, 0, 7, 2, 5_101_000, 0, 41000)
    (WORKLOADS / "edge-cases.bin").write_bytes(edge)

    for path in sorted(WORKLOADS.glob("*.bin")):
        metadata[path.name] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    write_json(WORKLOADS / "manifest.json", metadata)
    return metadata


def generate_candidate() -> dict[str, Any]:
    output = ROOT / "machine" / "edgestream_generated.c"
    command = [
        sys.executable,
        "generator/generate_candidate.py",
        "--reference",
        "reference/edgestream_reference.c",
        "--output",
        str(output.relative_to(ROOT)),
    ]
    run(command)
    first = output.read_bytes()
    with tempfile.TemporaryDirectory() as directory:
        second_path = Path(directory) / "candidate.c"
        run([*command[:-1], str(second_path)])
        second = second_path.read_bytes()
    result = {
        "status": "PASS" if first == second else "FAIL",
        "candidate_sha256": sha256(output),
        "reference_sha256": sha256(ROOT / "reference" / "edgestream_reference.c"),
        "generator_sha256": sha256(ROOT / "generator" / "generate_candidate.py"),
        "bytes": len(first),
        "byte_identical_regeneration": first == second,
    }
    write_json(RESULTS / "generation.json", result)
    return result


def compiler_version(compiler: str) -> str:
    completed = run([compiler, "--version"])
    return completed.stdout.splitlines()[0]


def compile_flags(*, sanitizers: bool = False) -> list[str]:
    return list(SANITIZER_FLAGS if sanitizers else STRICT_FLAGS)


def compile_binary(
    compiler: str,
    implementation: Path,
    output: Path,
    sanitizers: bool = False,
) -> list[str]:
    flags = compile_flags(sanitizers=sanitizers)
    command = [
        compiler,
        *flags,
        "runner/edgestream_cli.c",
        str(implementation.relative_to(ROOT)),
        "-o",
        str(output.relative_to(ROOT)),
    ]
    run(command)
    return command


def build_all() -> dict[str, Any]:
    BUILD.mkdir(parents=True, exist_ok=True)
    compilers = [name for name in ("gcc", "clang") if shutil.which(name)]
    results: dict[str, Any] = {
        "compilers": {},
        "status": "PASS",
        "strict_flags": compile_flags(),
    }
    for compiler in compilers:
        compiler_result: dict[str, Any] = {
            "version": compiler_version(compiler),
            "builds": {},
        }
        for name, source in (
            ("reference", ROOT / "reference" / "edgestream_reference.c"),
            ("candidate", ROOT / "machine" / "edgestream_generated.c"),
        ):
            output = BUILD / f"{name}-{compiler}"
            try:
                command = compile_binary(compiler, source, output)
                compiler_result["builds"][name] = {
                    "status": "PASS",
                    "binary_sha256": sha256(output),
                    "command": command,
                }
            except subprocess.CalledProcessError as error:
                compiler_result["builds"][name] = {
                    "status": "FAIL",
                    "stderr": error.stderr,
                }
                results["status"] = "FAIL"
        results["compilers"][compiler] = compiler_result
    if not compilers:
        results["status"] = "UNKNOWN"
    write_json(RESULTS / "compiler-matrix.json", results)
    return results


def program(name: str) -> Path:
    preferred = BUILD / f"{name}-gcc"
    if preferred.exists():
        return preferred
    return BUILD / f"{name}-clang"


def execute(
    binary: Path,
    workload: Path,
    chunk: int,
    extra: list[str] | None = None,
    check: bool = True,
    *,
    env: Mapping[str, str] | None = None,
    timeout: float = 180.0,
) -> subprocess.CompletedProcess[str]:
    command = [str(binary), "--chunk", str(chunk)]
    if extra:
        command.extend(extra)
    command.append(str(workload))
    return run(command, check=check, env=env, timeout=timeout)


def filter_control(text: str) -> list[str]:
    return [
        line
        for line in text.splitlines()
        if '"type":"checkpoint"' not in line and '"type":"recovery"' not in line
    ]
