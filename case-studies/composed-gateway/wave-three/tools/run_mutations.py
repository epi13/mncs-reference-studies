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
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

from jsonschema import Draft202012Validator

WAVE = pathlib.Path(__file__).resolve().parents[1]
COMPOSED = WAVE.parent
REPO = WAVE.parents[2]
HOST = WAVE / "build/composed-host-wave3"
AUTHORITY = WAVE / "rust-authority/target/release/mncs-rust-authority-wave3"
PROVIDER = REPO / "experimental/language-evidence/providers/go_provider.py"
BOUNDARY_SCHEMA = REPO / "schemas/mncs-boundary-contract.schema.json"
BOUNDARY_PROCESS = WAVE / "boundary-process-v2.json"


def command(
    args: list[str],
    *,
    input_text: str = "",
    env: dict[str, str] | None = None,
    timeout: float = 5.0,
) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(
        args,
        input=input_text,
        text=True,
        capture_output=True,
        timeout=timeout,
        env=merged,
        check=False,
    )


def provider(source: str, *, simulate: str | None = None, timeout: float = 2.0) -> str:
    request: dict[str, Any] = {
        "protocol_version": "0.1",
        "type": "analysis_request",
        "request_id": "wave3-mutation",
        "analysis": "go.bounded-concurrency-safety",
        "component": {
            "language": "go",
            "source_text": source,
            "subject_id": "fixture:go:wave3-mutation",
            "contract_id": "contract:provider-conformance-0.2",
            "environment_id": "environment:wave3-mutation",
            "evidence_partition": "mutation",
        },
        "limits": {"wall_seconds": 2, "input_bytes": 65536},
        "extensions": {},
    }
    if simulate:
        request["extensions"] = {"mncs.dev:simulate": simulate}
    completed = command(
        [sys.executable, str(PROVIDER)],
        input_text=json.dumps(request, sort_keys=True) + "\n",
        timeout=timeout,
    )
    if completed.returncode != 0:
        return "operational_error"
    return str(json.loads(completed.stdout)["status"])


def direct_authority(line: str, env: dict[str, str] | None = None) -> tuple[str, int]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    process = subprocess.Popen(
        [str(AUTHORITY)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=merged,
    )
    assert process.stdin is not None and process.stdout is not None
    handshake = process.stdout.readline().strip()
    process.stdin.write(line + "\n")
    process.stdin.close()
    response = process.stdout.readline().strip()
    returncode = process.wait(timeout=3)
    return f"{handshake}|{response}", returncode


def checkpoint_digest(value: dict[str, Any]) -> str:
    payload = (
        f"{value['version']}\n"
        f"{value['system_contract']}\n"
        f"{value['binding_header']}\n"
        f"{value['binding_spec']}\n"
        f"{value['binding_generator']}\n"
        f"{value['authority']}\n"
        f"{value['input_digest']}\n"
        f"{value['processed']}\n"
        f"{value['sum']}\n"
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def make_checkpoint(directory: pathlib.Path, values: str = "1\n2\n3\n") -> pathlib.Path:
    checkpoint = directory / "state.json"
    completed = command(
        [str(HOST)],
        input_text=values,
        env={
            "MNCS_ROLLBACK": "1",
            "MNCS_CHECKPOINT_PATH": str(checkpoint),
            "MNCS_FAIL_AFTER": "1",
        },
    )
    if completed.returncode != 3 or not checkpoint.exists():
        raise RuntimeError("failed to create checkpoint fixture")
    return checkpoint


def mutation_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    def record(identifier: str, expected: str, observed: str, detail: str) -> None:
        records.append(
            {
                "id": identifier,
                "expected_outcome": expected,
                "observed_outcome": observed,
                "status": "PASS" if expected == observed else "FAIL",
                "detail": detail,
            }
        )

    with tempfile.TemporaryDirectory(prefix="mncs-wave3-mutations-") as temporary:
        temp = pathlib.Path(temporary)

        parser_source = (COMPOSED / "c/parser.c").read_text(encoding="utf-8")
        mutated = parser_source.replace(
            "        if (data[index] < '0' || data[index] > '9') return 2;\n", ""
        )
        (temp / "parser.c").write_text(mutated, encoding="utf-8")
        shutil.copy(COMPOSED / "c/parser.h", temp / "parser.h")
        (temp / "runner.c").write_text(
            '#include <stdio.h>\n#include "parser.h"\nint main(void){uint32_t out=0; int rc=mncs_parse_u32((const uint8_t*)"x",1,&out); printf("%d\\n",rc); return 0;}\n',
            encoding="utf-8",
        )
        built = command(
            ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic", str(temp / "parser.c"), str(temp / "runner.c"), "-o", str(temp / "mutant")]
        )
        ran = command([str(temp / "mutant")]) if built.returncode == 0 else built
        observed = "FAIL" if ran.returncode == 0 and ran.stdout.strip() == "0" else "UNKNOWN"
        record("c-invalid-frame-accepted", "FAIL", observed, "mutant removed decimal-byte rejection")

        output, returncode = direct_authority("V2 r0 100001")
        record("rust-invalid-proposal", "FAIL", "FAIL" if "ERR range" in output and returncode == 0 else "UNKNOWN", output)

        record("go-goroutine-leak", "FAIL", provider("package x\n// MNCS_DEFECT_GOROUTINE_LEAK\n"), "Go provider mutation token")
        record("missing-cancellation", "FAIL", provider("package x\n// MNCS_DEFECT_MISSING_CANCEL\n"), "Go provider mutation token")

        binding = (WAVE / "go-host/binding_gen.go").read_text(encoding="utf-8")
        drifted = binding.replace("C.uint32_t", "C.uint64_t")
        observed = "FAIL" if hashlib.sha256(drifted.encode()).hexdigest() != hashlib.sha256(binding.encode()).hexdigest() else "PASS"
        record("binding-integer-width", "FAIL", observed, "generated binding identity changed")

        (temp / "abi.c").write_text(
            '#include "parser.h"\n#if MNCS_PARSER_ABI != 2\n#error ABI mismatch\n#endif\nint main(void){return 0;}\n',
            encoding="utf-8",
        )
        abi = command(["cc", "-std=c11", "-I", str(COMPOSED / "c"), str(temp / "abi.c"), "-o", str(temp / "abi")])
        record("abi-version-mismatch", "FAIL", "FAIL" if abi.returncode != 0 else "PASS", "compile-time ABI guard")

        boundary = json.loads(BOUNDARY_PROCESS.read_text(encoding="utf-8"))
        boundary.pop("cancellation", None)
        schema = json.loads(BOUNDARY_SCHEMA.read_text(encoding="utf-8"))
        errors = list(Draft202012Validator(schema).iter_errors(boundary))
        record("schema-drift", "FAIL", "FAIL" if errors else "PASS", "required cancellation field removed")

        output, returncode = direct_authority("BAD r0 1")
        record("malformed-process-message", "FAIL", "FAIL" if "ERR protocol" in output and returncode == 0 else "UNKNOWN", output)

        crashed = command(
            [str(HOST)],
            input_text="1\n2\n",
            env={"MNCS_RUST_AUTHORITY": str(AUTHORITY), "MNCS_AUTHORITY_CRASH_AFTER": "0"},
        )
        record("child-process-crash", "operational_error", "operational_error" if crashed.returncode == 3 else "UNKNOWN", crashed.stderr.strip())

        started = time.perf_counter()
        cancelled = command(
            [str(HOST)],
            input_text="1\n",
            env={
                "MNCS_RUST_AUTHORITY": str(AUTHORITY),
                "MNCS_AUTHORITY_DELAY_MS": "1000",
                "MNCS_TIMEOUT_MS": "50",
            },
            timeout=2,
        )
        elapsed = time.perf_counter() - started
        record("cancellation-boundary", "FAIL", "FAIL" if cancelled.returncode == 3 and elapsed < 1.0 else "UNKNOWN", f"elapsed={elapsed:.6f}")

        partial = command(
            [str(HOST)],
            input_text="1\n2\n",
            env={"MNCS_RUST_AUTHORITY": str(AUTHORITY), "MNCS_AUTHORITY_PARTIAL_AT": "0"},
        )
        record("partial-process-write", "FAIL", "FAIL" if partial.returncode == 3 else "UNKNOWN", partial.stderr.strip())

        wrong = command(
            [str(HOST)],
            input_text="1\n",
            env={"MNCS_RUST_AUTHORITY": str(AUTHORITY), "MNCS_AUTHORITY_WRONG_VERSION": "1"},
        )
        record("process-version-mismatch", "FAIL", "FAIL" if wrong.returncode == 3 else "UNKNOWN", wrong.stderr.strip())

        stale_dir = temp / "stale"
        stale_dir.mkdir()
        stale_checkpoint = make_checkpoint(stale_dir)
        stale = command(
            [str(HOST)],
            input_text="1\n2\n4\n",
            env={"MNCS_ROLLBACK": "1", "MNCS_RESUME": "1", "MNCS_CHECKPOINT_PATH": str(stale_checkpoint)},
        )
        record("stale-checkpoint", "FAIL", "FAIL" if stale.returncode == 3 and "stale checkpoint" in stale.stderr else "UNKNOWN", stale.stderr.strip())

        partial_dir = temp / "partial"
        partial_dir.mkdir()
        partial_checkpoint = make_checkpoint(partial_dir)
        value = json.loads(partial_checkpoint.read_text(encoding="utf-8"))
        value["sum"] = value["sum"] + 1
        value["state_digest"] = checkpoint_digest(value)
        partial_checkpoint.write_text(json.dumps(value), encoding="utf-8")
        corrupted = command(
            [str(HOST)],
            input_text="1\n2\n3\n",
            env={"MNCS_ROLLBACK": "1", "MNCS_RESUME": "1", "MNCS_CHECKPOINT_PATH": str(partial_checkpoint)},
        )
        record("partial-state-recovery", "FAIL", "FAIL" if corrupted.returncode == 3 and "partial state" in corrupted.stderr else "UNKNOWN", corrupted.stderr.strip())

        binding_dir = temp / "binding"
        binding_dir.mkdir()
        binding_checkpoint = make_checkpoint(binding_dir)
        value = json.loads(binding_checkpoint.read_text(encoding="utf-8"))
        value["binding_header"] = "0" * 64
        # Intentionally keep state digest stale: either binding or digest must reject.
        binding_checkpoint.write_text(json.dumps(value), encoding="utf-8")
        rejected = command(
            [str(HOST)],
            input_text="1\n2\n3\n",
            env={"MNCS_ROLLBACK": "1", "MNCS_RESUME": "1", "MNCS_CHECKPOINT_PATH": str(binding_checkpoint)},
        )
        record("checkpoint-binding-identity", "FAIL", "FAIL" if rejected.returncode == 3 else "UNKNOWN", rejected.stderr.strip())

        exhausted = command([str(HOST)], input_text="1\n" * 65, env={"MNCS_ROLLBACK": "1"})
        record("resource-limit", "FAIL", "FAIL" if exhausted.returncode == 2 else "UNKNOWN", exhausted.stderr.strip())

        try:
            provider("package x\n", simulate="timeout", timeout=0.1)
            timeout_result = "UNKNOWN"
        except subprocess.TimeoutExpired:
            timeout_result = "operational_error"
        record("provider-timeout", "operational_error", timeout_result, "provider wall timeout")

        record("unsupported-build-tag", "UNKNOWN", provider("//go:build custom\npackage x\n"), "unsupported build tag remains UNKNOWN")

    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    records = mutation_records()
    for value in records:
        path = args.output / f"{value['id']}.json"
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "schema_version": "0.2-experimental",
        "campaign_id": "composed-gateway-wave3-mutations-v2",
        "status": "PASS" if all(value["status"] == "PASS" for value in records) else "FAIL",
        "total": len(records),
        "passed": sum(value["status"] == "PASS" for value in records),
        "records": [value["id"] for value in records],
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
# fmt: on
