#!/usr/bin/env python3
"""Bounded structured adapters for declared MNCS Forge development workflows."""

# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
import json
import os
import re
import selectors
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_CAP = 256 * 1024
ENVIRONMENT_ALLOWLIST = (
    "PATH",
    "LANG",
    "LC_ALL",
    "CC",
    "CFLAGS",
    "RUSTFLAGS",
    "CARGO_HOME",
    "RUSTUP_HOME",
)
SECRET_PATTERN = re.compile(
    r"(?i)(token|secret|password|authorization|api[_-]?key)([\"'=:\s]+)([^\s,\"']+)"
)


@dataclass(frozen=True)
class Workflow:
    argv: tuple[str, ...]
    timeout_seconds: float
    result_class: str
    limitations: tuple[str, ...] = ()


WORKFLOWS = {
    "tooling-inspect": Workflow(
        (".venv/bin/mncs", "version", "--json"),
        30,
        "tooling_inspection",
    ),
    "release-candidate-check": Workflow(
        ("make", "release-candidate-check"),
        1800,
        "release_candidate_development_check",
    ),
    "release-candidate-corpus": Workflow(
        ("make", "release-candidate-corpus"),
        300,
        "release_candidate_corpus",
    ),
    "python-rust-comparison": Workflow(
        (
            "python",
            "scripts/compare-release-candidate-consumers",
            "--json",
        ),
        900,
        "release_candidate_consumer_comparison",
        (
            "independent implementation/executable diversity does not establish "
            "independent operation or organizational independence",
        ),
    ),
    "recursive-analyzer-study": Workflow(
        ("make", "recursive-study"),
        600,
        "recursive_analyzer_study",
        (
            "internal study selection does not establish MNCS/MNCDS conformance, "
            "protected custody, or independent evaluation",
        ),
    ),
    "core-check": Workflow(
        ("make", "check"),
        3600,
        "core_development_check",
    ),
    "ravel-0.4-check": Workflow(
        ("make", "ravel-0.4-check"),
        900,
        "optional_case_study_check",
        ("RAVEL 0.4 is an optional case-study regression check, not a release gate",),
    ),
}


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _file_identity(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _redact(text: str, limit: int = 4096) -> str:
    return SECRET_PATTERN.sub(r"\1\2<redacted>", text[:limit])


def _terminate(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        process.wait(timeout=1)
    except (OSError, subprocess.TimeoutExpired):
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
        except OSError:
            pass
        process.wait(timeout=2)


def _resolve_executable(argv: tuple[str, ...]) -> Path:
    value = argv[0]
    if "/" in value:
        path = Path(value)
        if path.is_absolute():
            resolved = path.resolve(strict=True)
        else:
            resolved = (ROOT / path).resolve(strict=True)
            if not resolved.is_relative_to(ROOT):
                raise ValueError("relative executable escaped the repository root")
    else:
        found = shutil_which(value, os.environ.get("PATH", ""))
        if found is None:
            raise FileNotFoundError(value)
        resolved = Path(found).resolve(strict=True)
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise PermissionError(f"not an executable file: {resolved}")
    return resolved


def shutil_which(command: str, path: str) -> str | None:
    for directory in path.split(os.pathsep):
        if not directory:
            continue
        candidate = Path(directory) / command
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def _base_result(name: str, workflow: Workflow) -> dict[str, object]:
    return {
        "workflow": name,
        "result_class": workflow.result_class,
        "conformance_status": "UNKNOWN",
        "command": list(workflow.argv),
        "environment": {
            "allowlisted_keys": sorted(key for key in ENVIRONMENT_ALLOWLIST if key in os.environ),
            "values_disclosed": False,
        },
        "wrapper_identity": _file_identity(Path(__file__).resolve()),
        "limitations": [
            *workflow.limitations,
            "workflow PASS is a bounded development-check outcome, not MNCS or MNCDS "
            "conformance PASS",
            "the wrapper does not create independence, protected custody, witnessing, "
            "governance approval, certification, or promotion",
        ],
        "unsupported_constructs": [],
    }


def run_workflow(
    name: str,
    workflow: Workflow,
    *,
    output_cap: int = OUTPUT_CAP,
) -> dict[str, object]:
    result = _base_result(name, workflow)
    try:
        executable = _resolve_executable(workflow.argv)
    except (FileNotFoundError, OSError, PermissionError, ValueError) as exc:
        result.update(
            {
                "status": "UNKNOWN",
                "outcome": "unsupported",
                "executable": None,
                "executable_identity": None,
                "exit_code": None,
                "limitations": [*result["limitations"], _redact(str(exc))],
                "output_references": {},
            }
        )
        result["witnesses"] = [
            {
                "kind": "workflow_execution",
                "outcome": result["outcome"],
                "command": result["command"],
                "environment": result["environment"],
                "wrapper_identity": result["wrapper_identity"],
                "executable_identity": result["executable_identity"],
                "output_references": result["output_references"],
                "conformance_status": result["conformance_status"],
            }
        ]
        return result

    environment = {key: os.environ[key] for key in ENVIRONMENT_ALLOWLIST if key in os.environ}
    argv = [str(executable), *workflow.argv[1:]]
    process = subprocess.Popen(
        argv,
        cwd=ROOT,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        start_new_session=os.name == "posix",
    )
    assert process.stdout is not None
    assert process.stderr is not None
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    outputs = {"stdout": bytearray(), "stderr": bytearray()}
    deadline = time_monotonic() + workflow.timeout_seconds
    outcome = "completed"
    try:
        while selector.get_map():
            remaining = deadline - time_monotonic()
            if remaining <= 0:
                outcome = "timeout"
                _terminate(process)
                break
            events = selector.select(min(remaining, 0.1))
            if not events and process.poll() is not None:
                events = [(key, selectors.EVENT_READ) for key in selector.get_map().values()]
            for key, _ in events:
                chunk = os.read(key.fd, 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                target = outputs[str(key.data)]
                target.extend(chunk)
                if len(target) > output_cap:
                    outcome = "output_limit"
                    _terminate(process)
                    break
            if outcome == "output_limit":
                break
    finally:
        selector.close()
        if process.poll() is None:
            _terminate(process)
    returncode = process.returncode
    if outcome == "completed" and returncode is not None:
        if returncode < 0:
            outcome = "crash"
        elif returncode != 0:
            outcome = "failed"
    status = (
        "PASS"
        if outcome == "completed" and returncode == 0
        else "FAIL"
        if outcome == "failed"
        else "UNKNOWN"
    )
    stdout = bytes(outputs["stdout"][:output_cap])
    stderr = bytes(outputs["stderr"][:output_cap])
    result.update(
        {
            "status": status,
            "outcome": outcome,
            "executable": str(executable),
            "executable_identity": _file_identity(executable),
            "exit_code": returncode,
            "output_references": {
                "stdout": {
                    "identity": _sha256(stdout),
                    "bytes": len(stdout),
                    "excerpt": _redact(stdout.decode("utf-8", errors="replace")),
                },
                "stderr": {
                    "identity": _sha256(stderr),
                    "bytes": len(stderr),
                    "excerpt": _redact(stderr.decode("utf-8", errors="replace")),
                },
            },
        }
    )
    if outcome in {"timeout", "crash", "output_limit"}:
        result["limitations"] = [
            *result["limitations"],
            f"workflow ended with {outcome}; required facts remain UNKNOWN",
        ]
    result["witnesses"] = [
        {
            "kind": "workflow_execution",
            "outcome": result["outcome"],
            "command": result["command"],
            "environment": result["environment"],
            "wrapper_identity": result["wrapper_identity"],
            "executable_identity": result["executable_identity"],
            "output_references": result["output_references"],
            "exit_code": result["exit_code"],
            "conformance_status": result["conformance_status"],
        }
    ]
    return result


def time_monotonic() -> float:
    import time

    return time.monotonic()


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 1 or arguments[0] not in WORKFLOWS:
        payload = {
            "status": "UNKNOWN",
            "outcome": "unsupported",
            "conformance_status": "UNKNOWN",
            "limitations": ["expected one declared workflow name"],
            "supported_workflows": sorted(WORKFLOWS),
        }
    else:
        name = arguments[0]
        payload = run_workflow(name, WORKFLOWS[name])
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
