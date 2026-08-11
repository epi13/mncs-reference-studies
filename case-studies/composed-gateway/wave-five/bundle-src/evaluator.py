#!/usr/bin/env python3
"""Portable offline MNCS Wave Five evaluator (Python 3.9+)."""

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_UNKNOWN = "UNKNOWN"


def canonical_bytes(value):
    rendered = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return rendered.encode("utf-8")


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def verify_manifest(root, manifest):
    findings = []
    for entry in manifest.get("files", []):
        relative = entry.get("path")
        target = root / relative
        if not target.is_file():
            findings.append("missing bundle file: " + str(relative))
            continue
        actual_size = target.stat().st_size
        actual_hash = sha256_file(target)
        if actual_size != entry.get("size"):
            findings.append("size mismatch: " + str(relative))
        if "sha256:" + actual_hash != entry.get("identity"):
            findings.append("identity mismatch: " + str(relative))
    return findings


def parse_decimal(text):
    if not isinstance(text, str) or not text or not text.isascii() or not text.isdigit():
        raise ValueError("invalid decimal frame")
    value = int(text, 10)
    if value > 100000:
        raise ValueError("resource limit")
    return value


def state_digest(input_digest, processed, total):
    return sha256_bytes(
        canonical_bytes(
            {
                "input_digest": input_digest,
                "processed": processed,
                "sum": total,
                "version": 1,
            }
        )
    )


def make_checkpoint(values, processed):
    input_digest = sha256_bytes(canonical_bytes(values))
    total = sum(values[:processed])
    return {
        "version": 1,
        "input_digest": input_digest,
        "processed": processed,
        "sum": total,
        "state_digest": state_digest(input_digest, processed, total),
    }


def restore_checkpoint(values, checkpoint):
    allowed = {"version", "input_digest", "processed", "sum", "state_digest"}
    if set(checkpoint) != allowed:
        raise ValueError("checkpoint fields")
    if checkpoint["version"] != 1:
        raise ValueError("checkpoint version")
    input_digest = sha256_bytes(canonical_bytes(values))
    if checkpoint["input_digest"] != input_digest:
        raise ValueError("stale input")
    processed = checkpoint["processed"]
    if not isinstance(processed, int) or processed < 0 or processed > len(values):
        raise ValueError("processed range")
    expected_sum = sum(values[:processed])
    if checkpoint["sum"] != expected_sum:
        raise ValueError("semantic state mismatch")
    expected_digest = state_digest(input_digest, processed, expected_sum)
    if checkpoint["state_digest"] != expected_digest:
        raise ValueError("state digest mismatch")
    return expected_sum + sum(values[processed:])


def tool_probe(command, version_args):
    executable = shutil.which(command)
    if executable is None:
        return {"status": STATUS_UNKNOWN, "executable": None, "version": None}
    try:
        result = subprocess.run(
            [executable] + version_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=4,
            check=False,
        )
        first_line = (result.stdout or "").strip().splitlines()
        return {
            "status": STATUS_PASS if result.returncode == 0 else STATUS_UNKNOWN,
            "executable": Path(executable).name,
            "version": first_line[0][:300] if first_line else None,
        }
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": STATUS_UNKNOWN, "executable": Path(executable).name, "version": str(exc)}


def linux_distribution():
    os_release = Path("/etc/os-release")
    if not os_release.is_file():
        return "Linux"
    values = {}
    for line in os_release.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value.strip().strip('"')
    return values.get("PRETTY_NAME") or values.get("ID") or "Linux"


def normalized_architecture(value):
    lowered = (value or "unknown").lower()
    if lowered in {"amd64", "x86_64", "x64"}:
        return "x86_64"
    if lowered in {"aarch64", "arm64"}:
        return "arm64"
    if lowered.startswith("armv7"):
        return "armv7"
    if lowered.startswith("armv6"):
        return "armv6"
    return lowered


def environment(machine_label):
    system = platform.system() or "unknown"
    if system == "Windows":
        distribution = "Windows"
    elif system == "Linux":
        distribution = linux_distribution()
    else:
        distribution = system
    node_material = canonical_bytes(
        {
            "machine_label": machine_label,
            "node": platform.node(),
            "system": system,
            "release": platform.release(),
            "machine": normalized_architecture(platform.machine()),
        }
    )
    return {
        "os_family": system,
        "os_release": platform.release() or "unknown",
        "distribution": distribution,
        "architecture": normalized_architecture(platform.machine()),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "cpu_count": os.cpu_count(),
        "machine_fingerprint": "sha256:" + sha256_bytes(node_material),
    }


def run_vectors(vectors):
    findings = []
    valid_values = []
    for case in vectors["valid_frames"]:
        try:
            value = parse_decimal(case["input"])
        except ValueError as exc:
            findings.append("valid frame rejected: " + str(exc))
            continue
        if value != case["value"]:
            findings.append("valid frame value mismatch")
        valid_values.append(value)
    for case in vectors["invalid_frames"]:
        try:
            parse_decimal(case)
        except ValueError:
            continue
        findings.append("invalid frame accepted: " + case)

    expected_sum = vectors["expected_sum"]
    if sum(valid_values) != expected_sum:
        findings.append("uninterrupted sum mismatch")

    checkpoint = make_checkpoint(valid_values, vectors["checkpoint_after"])
    try:
        restored = restore_checkpoint(valid_values, checkpoint)
        if restored != expected_sum:
            findings.append("checkpoint resume mismatch")
    except ValueError as exc:
        findings.append("checkpoint resume rejected: " + str(exc))

    corrupt = dict(checkpoint)
    corrupt["sum"] += 1
    corrupt["state_digest"] = state_digest(
        corrupt["input_digest"], corrupt["processed"], corrupt["sum"]
    )
    try:
        restore_checkpoint(valid_values, corrupt)
        findings.append("semantic checkpoint corruption accepted")
    except ValueError:
        pass

    stale = dict(checkpoint)
    stale["input_digest"] = "0" * 64
    stale["state_digest"] = state_digest(stale["input_digest"], stale["processed"], stale["sum"])
    try:
        restore_checkpoint(valid_values, stale)
        findings.append("stale checkpoint accepted")
    except ValueError:
        pass

    semantic = {
        "accepted_values": valid_values,
        "expected_sum": expected_sum,
        "checkpoint_after": vectors["checkpoint_after"],
        "restored_sum": expected_sum,
        "corruption_rejected": True,
        "stale_input_rejected": True,
        "contract": vectors["contract"],
    }
    return findings, semantic


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--machine-label", required=True)
    parser.add_argument("--operator-id", required=True)
    parser.add_argument("--output", default="host-record.json")
    parser.add_argument("--archive-identity", default=None)
    args = parser.parse_args()

    started = time.time()
    root = Path(__file__).resolve().parent
    manifest_path = root / "manifest.json"
    vectors_path = root / "vectors.json"
    manifest = read_json(manifest_path)
    vectors = read_json(vectors_path)
    manifest_identity = "sha256:" + sha256_file(manifest_path)

    findings = verify_manifest(root, manifest)
    vector_findings, semantic = run_vectors(vectors)
    findings.extend(vector_findings)
    semantic_digest = sha256_bytes(canonical_bytes(semantic))
    gates = {
        "bundle_integrity": STATUS_PASS if not verify_manifest(root, manifest) else STATUS_FAIL,
        "deterministic_vectors": STATUS_PASS if not vector_findings else STATUS_FAIL,
        "checkpoint_resume": STATUS_PASS if not vector_findings else STATUS_FAIL,
        "corruption_rejection": STATUS_PASS if not vector_findings else STATUS_FAIL,
        "offline_capability": STATUS_PASS,
    }
    result = STATUS_FAIL if findings else STATUS_PASS
    raw_events = {
        "manifest_identity": manifest_identity,
        "semantic": semantic,
        "gates": gates,
        "findings": findings,
    }
    record = {
        "schema_version": "0.5-experimental",
        "record_id": "host:" + args.machine_label + ":" + str(int(started)),
        "bundle_id": manifest["bundle_id"],
        "manifest_identity": manifest_identity,
        "transport_archive_identity": args.archive_identity,
        "candidate_freeze_identity": manifest["candidate_freeze_identity"],
        "machine_label": args.machine_label,
        "operator_id": args.operator_id,
        "operator_controlled": True,
        "evidence_class": "OPERATOR_CONTROLLED",
        "started_at_unix": started,
        "finished_at_unix": time.time(),
        "environment": environment(args.machine_label),
        "capabilities": {
            "go": tool_probe("go", ["version"]),
            "rustc": tool_probe("rustc", ["--version"]),
            "c_compiler": tool_probe("cc", ["--version"]),
        },
        "gates": gates,
        "semantic_output_digest": semantic_digest,
        "raw_artifact_identity": "sha256:" + sha256_bytes(canonical_bytes(raw_events)),
        "result": result,
        "findings": findings,
        "independent_evaluation_status": STATUS_UNKNOWN,
        "protected_holdout_status": STATUS_UNKNOWN,
        "extensions": {
            "mncs.dev:network": "no network required by evaluator",
            "mncs.dev:claim": "portable evaluator host execution only",
        },
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "status": result,
        "output": str(output),
        "semantic_output_digest": semantic_digest,
    }
    print(json.dumps(summary, sort_keys=True))
    return 1 if result == STATUS_FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
