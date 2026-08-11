#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import stat
import tempfile
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "bundle-src"
DEFAULT_OUTPUT = ROOT / "dist"
FIXED_DATE_TIME = (1980, 1, 1, 0, 0, 0)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def manifest_for(files: list[Path]) -> dict[str, Any]:
    entries = []
    for path in files:
        relative = path.relative_to(SOURCE).as_posix()
        entries.append(
            {
                "path": relative,
                "identity": "sha256:" + sha256_file(path),
                "size": path.stat().st_size,
            }
        )
    freeze = SOURCE / "candidate-freeze.json"
    evaluator = SOURCE / "evaluator.py"
    vectors = SOURCE / "vectors.json"
    return {
        "schema_version": "0.5-experimental",
        "bundle_id": "composed-gateway-wave5-portable-evaluator-v1",
        "bundle_format": "mncs-portable-evaluator-v1",
        "candidate_freeze_identity": "sha256:" + sha256_file(freeze),
        "evaluator_identity": "sha256:" + sha256_file(evaluator),
        "workload_identity": "sha256:" + sha256_file(vectors),
        "created_at": "2026-07-28T00:00:00Z",
        "minimum_python": "3.9",
        "entrypoint": "evaluator.py",
        "network_policy": "offline-no-network-required",
        "supported_platforms": ["Windows", "Linux/Fedora", "Linux/Pi OS", "other Python 3.9+"],
        "result_schema": "mncs-host-execution-record-0.5-experimental",
        "claim_boundary": (
            "Host PASS establishes only portable evaluator execution on the recorded "
            "machine. Cohort PASS may establish operator-controlled public reproduction, "
            "never protected holdout or independent evaluation."
        ),
        "files": entries,
        "extensions": {"mncs.dev:wave": "five"},
    }


def zip_entry(name: str, data: bytes, executable: bool = False) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, FIXED_DATE_TIME)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    mode = 0o755 if executable else 0o644
    info.external_attr = (stat.S_IFREG | mode) << 16
    return info


def build(output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    files = sorted(path for path in SOURCE.iterdir() if path.is_file())
    manifest = manifest_for(files)
    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode() + b"\n"
    archive = output / "mncs-wave-five-portable-evaluator.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        for path in files:
            bundle.writestr(
                zip_entry(
                    path.name,
                    path.read_bytes(),
                    executable=path.name in {"evaluator.py", "run.sh"},
                ),
                path.read_bytes(),
            )
        bundle.writestr(zip_entry("manifest.json", manifest_bytes), manifest_bytes)
    manifest_path = output / "manifest.json"
    manifest_path.write_bytes(manifest_bytes)
    lock = {
        "schema_version": "0.5-experimental",
        "bundle_id": manifest["bundle_id"],
        "manifest_identity": "sha256:" + sha256_bytes(manifest_bytes),
        "archive_identity": "sha256:" + sha256_file(archive),
        "archive_size": archive.stat().st_size,
        "candidate_freeze_identity": manifest["candidate_freeze_identity"],
    }
    (output / "bundle-lock.json").write_text(
        json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "mncs-wave-five-portable-evaluator.zip.sha256").write_text(
        sha256_file(archive) + "  " + archive.name + "\n", encoding="utf-8"
    )
    return lock


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check-lock", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as temporary:
        first = build(Path(temporary) / "first")
        second = build(Path(temporary) / "second")
        if first != second:
            raise SystemExit("deterministic bundle build failed")
        if (Path(temporary) / "first/mncs-wave-five-portable-evaluator.zip").read_bytes() != (
            Path(temporary) / "second/mncs-wave-five-portable-evaluator.zip"
        ).read_bytes():
            raise SystemExit("deterministic archive bytes differ")
    lock = build(args.output)
    if args.check_lock:
        expected = json.loads(args.check_lock.read_text(encoding="utf-8"))
        if lock != expected:
            print(json.dumps({"status": "FAIL", "expected": expected, "actual": lock}, indent=2))
            return 1
    print(json.dumps({"status": "PASS", **lock}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
