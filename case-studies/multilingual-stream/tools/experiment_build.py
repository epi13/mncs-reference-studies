from __future__ import annotations

import subprocess
from pathlib import Path

from experiment_common import ROOT, oracle, run


def compile_subjects(gcc: str, cargo: str, build: Path) -> dict[str, list[str]]:
    c_reference = build / "c-reference"
    c_candidate = build / "c-candidate"
    flags = ["-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-pedantic"]
    subprocess.run(
        [gcc, *flags, str(ROOT / "c11/reference.c"), "-o", str(c_reference)],
        check=True,
    )
    subprocess.run(
        [gcc, *flags, str(ROOT / "c11/candidate.c"), "-o", str(c_candidate)],
        check=True,
    )
    subprocess.run([cargo, "fmt", "--check"], cwd=ROOT, check=True)
    subprocess.run(
        [
            cargo,
            "clippy",
            "--locked",
            "--all-targets",
            "--",
            "-D",
            "warnings",
        ],
        cwd=ROOT,
        check=True,
    )
    subprocess.run([cargo, "test", "--locked"], cwd=ROOT, check=True)
    subprocess.run(
        [cargo, "build", "--release", "--locked"],
        cwd=ROOT,
        check=True,
    )
    rust_binary = ROOT / "target/release/mncs-multilingual-stream"
    return {
        "c11-reference": [str(c_reference)],
        "c11-candidate": [str(c_candidate)],
        "rust-reference": [str(rust_binary), "reference"],
        "rust-candidate": [str(rust_binary), "candidate"],
    }


def sanitizer_observation(gcc: str, build: Path) -> tuple[str, str]:
    sanitizer = build / "c-sanitized"
    command = [
        gcc,
        "-std=c11",
        "-O1",
        "-g",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-pedantic",
        "-fsanitize=address,undefined",
        "-fno-omit-frame-pointer",
        str(ROOT / "c11/candidate.c"),
        "-o",
        str(sanitizer),
    ]
    valid = (ROOT / "corpus/valid.txt").read_bytes()
    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
        )
        result = run([str(sanitizer)], data=valid)
    except (OSError, subprocess.SubprocessError):
        return "UNKNOWN", "sanitizer toolchain unavailable"
    status = "PASS" if result.returncode == 0 and result.stdout == oracle(valid) else "FAIL"
    return status, "ASan and UBSan execution on declared corpus"
