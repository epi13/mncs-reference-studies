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
import subprocess

WAVE = pathlib.Path(__file__).resolve().parents[1]
HOST = WAVE / "build/composed-host-wave3"
AUTHORITY = WAVE / "rust-authority/target/release/mncs-rust-authority-wave3"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("corpus", type=pathlib.Path)
    parser.add_argument("custody", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    corpus = args.corpus.read_bytes()
    custody = json.loads(args.custody.read_text(encoding="utf-8"))
    required = {"custodian_id", "evaluator_id", "disclosed_after_freeze", "corpus_private_before_disclosure"}
    missing = sorted(required - custody.keys())
    if missing:
        raise SystemExit(f"custody record missing: {', '.join(missing)}")
    completed = subprocess.run(
        [str(HOST)],
        input=corpus,
        capture_output=True,
        env={
            **os.environ,
            "MNCS_RUST_AUTHORITY": str(AUTHORITY),
            "MNCS_TIMEOUT_MS": "2000",
        },
        check=False,
    )
    status = "PASS" if completed.returncode == 0 else "FAIL"
    output_record = json.loads(completed.stdout) if completed.returncode == 0 else None
    record = {
        "schema_version": "0.3-experimental",
        "record_id": "composed-gateway-wave3-protected-holdout",
        "corpus_sha256": hashlib.sha256(corpus).hexdigest(),
        "custody_record": custody,
        "execution_status": status,
        "output_record": output_record,
        "stderr": completed.stderr.decode(errors="replace")[:4096],
        "independence_assertion": "External review is required; repository tooling does not authenticate organizational independence.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
# fmt: on
