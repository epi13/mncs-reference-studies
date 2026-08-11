from __future__ import annotations

import json
import statistics
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_INPUT = 1_048_576
REPEATS = 7
WARMUPS = 2


def run(
    command: list[str],
    *,
    data: bytes = b"",
    timeout: float = 10.0,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        command,
        input=data,
        capture_output=True,
        timeout=timeout,
        check=False,
        cwd=ROOT,
    )


def oracle(data: bytes) -> bytes:
    if len(data) > MAX_INPUT or b"\x00" in data:
        raise ValueError("input is outside the declared envelope")
    if not data:
        values: list[int] = []
    else:
        records = data.replace(b"\r\n", b"\n").split(b"\n")
        if records[-1] == b"":
            records.pop()
        if any(not record or not record.isdigit() for record in records):
            raise ValueError("input record is malformed")
        values = [int(record) for record in records]
        if any(value > 100_000 for value in values):
            raise ValueError("input value is out of range")
    checksum = 0
    for value in values:
        checksum = ((checksum * 16_777_619) & 0xFFFFFFFF) ^ value
    result = {"count": len(values), "sum": sum(values), "checksum": checksum}
    return (json.dumps(result, separators=(",", ":")) + "\n").encode()


def measure(command: list[str], data: bytes) -> dict[str, float | list[float]]:
    for _ in range(WARMUPS):
        completed = run(command, data=data)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.decode())
    samples: list[float] = []
    for _ in range(REPEATS):
        start = time.perf_counter_ns()
        completed = run(command, data=data)
        elapsed = (time.perf_counter_ns() - start) / 1_000_000_000
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.decode())
        samples.append(elapsed)
    median = statistics.median(samples)
    mad = statistics.median(abs(sample - median) for sample in samples)
    return {
        "samples_seconds": samples,
        "median_seconds": median,
        "mad_seconds": mad,
    }


def tool_version(command: list[str]) -> str | None:
    try:
        result = subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=5,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return (result.stdout or result.stderr).splitlines()[0]
