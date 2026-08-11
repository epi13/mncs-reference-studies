#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import subprocess
import sys
import tempfile
import zlib
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parents[1]
EDGESTREAM_ROOT = REPOSITORY_ROOT / "case-studies" / "edgestream"
WATER_ROOT = REPOSITORY_ROOT / "case-studies" / "remote-water-control"
sys.path.insert(0, str(WATER_ROOT / "src"))
sys.path.insert(0, str(WATER_ROOT / "machine"))

from water_control.controller import Controller  # noqa: E402
from water_control.model import TelemetryQuality, TelemetrySample  # noqa: E402
from water_control.planner import GeneratedTablePlanner  # noqa: E402

QUALITY_CODES = {
    0: TelemetryQuality.GOOD,
    1: TelemetryQuality.STALE,
    2: TelemetryQuality.CONFLICT,
}


def sha256_bytes(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def build_frame(
    *,
    device_id: int,
    sequence: int,
    timestamp_ms: int,
    metric: int,
    value: int,
) -> bytes:
    payload = struct.pack(
        "<2sBBHIIQHi",
        b"\xe5G",
        1,
        0,
        32,
        device_id,
        sequence,
        timestamp_ms,
        metric,
        value,
    )
    return payload + struct.pack("<I", zlib.crc32(payload) & 0xFFFFFFFF)


class EdgeStreamTelemetryAdapter:
    def __init__(self, device_id: int) -> None:
        self.device_id = device_id
        self.last_sequence = 0
        self.pending: dict[int, dict[int, int]] = defaultdict(dict)

    def accept(self, record: dict[str, Any]) -> TelemetrySample | None:
        if record.get("type") != "event":
            return None
        if int(record["device"]) != self.device_id:
            raise ValueError("mixed-device telemetry is outside this adapter contract")
        sequence = int(record.get("sequence", 0))
        if sequence <= self.last_sequence:
            raise ValueError("EdgeStream sequence must increase strictly")
        self.last_sequence = sequence
        metric = int(record["metric"])
        if metric not in {0, 1, 2, 3}:
            raise ValueError(f"unsupported EdgeStream metric {metric}")
        timestamp_ms = int(record["timestamp"])
        values = self.pending[timestamp_ms]
        if metric in values:
            raise ValueError("duplicate metric for one telemetry timestamp")
        values[metric] = int(record["value_milli"])
        if set(values) != {0, 1, 2, 3}:
            return None
        quality_code = values[3]
        if quality_code not in QUALITY_CODES:
            raise ValueError(f"unsupported telemetry quality code {quality_code}")
        if values[2] not in {0, 1}:
            raise ValueError(f"unsupported power code {values[2]}")
        del self.pending[timestamp_ms]
        observed_at_s = timestamp_ms // 1000
        return TelemetrySample(
            observed_at_s=observed_at_s,
            received_at_s=observed_at_s,
            tank_level_pct=values[0] / 1000.0,
            demand_lps=values[1] / 1000.0,
            power_available=values[2] == 1,
            quality=QUALITY_CODES[quality_code],
        )


def build_edgestream(binary: Path) -> list[str]:
    command = [
        "cc",
        "-std=c11",
        "-D_POSIX_C_SOURCE=200809L",
        "-Wall",
        "-Wextra",
        "-Wpedantic",
        "-Wconversion",
        "-Wshadow",
        "-Wformat=2",
        "-Wstrict-prototypes",
        "-Werror",
        "-Iinclude",
        "runner/edgestream_cli.c",
        "machine/edgestream_generated.c",
        "-o",
        str(binary),
    ]
    subprocess.run(command, cwd=EDGESTREAM_ROOT, check=True, capture_output=True, text=True)
    return [*command[:-1], "<temporary-binary>"]


def rejection_checks() -> dict[str, bool]:
    base = {
        "type": "event",
        "device": 7,
        "sequence": 1,
        "timestamp": 1_000_000,
        "metric": 0,
        "value_milli": 45_000,
    }

    replay = EdgeStreamTelemetryAdapter(7)
    replay.accept(base)
    try:
        replay.accept({**base, "metric": 1})
        replay_rejected = False
    except ValueError:
        replay_rejected = True

    mixed = EdgeStreamTelemetryAdapter(7)
    try:
        mixed.accept({**base, "device": 8})
        mixed_device_rejected = False
    except ValueError:
        mixed_device_rejected = True

    duplicate_metric = EdgeStreamTelemetryAdapter(7)
    duplicate_metric.accept(base)
    try:
        duplicate_metric.accept({**base, "sequence": 2})
        duplicate_metric_rejected = False
    except ValueError:
        duplicate_metric_rejected = True

    invalid_power = EdgeStreamTelemetryAdapter(7)
    power_records = [
        {**base, "sequence": 1, "metric": 0, "value_milli": 45_000},
        {**base, "sequence": 2, "metric": 1, "value_milli": 3_000},
        {**base, "sequence": 3, "metric": 2, "value_milli": 2},
        {**base, "sequence": 4, "metric": 3, "value_milli": 0},
    ]
    try:
        for record in power_records:
            invalid_power.accept(record)
        invalid_power_rejected = False
    except ValueError:
        invalid_power_rejected = True

    invalid_quality = EdgeStreamTelemetryAdapter(7)
    quality_records = [
        {**base, "sequence": 1, "metric": 0, "value_milli": 45_000},
        {**base, "sequence": 2, "metric": 1, "value_milli": 3_000},
        {**base, "sequence": 3, "metric": 2, "value_milli": 1},
        {**base, "sequence": 4, "metric": 3, "value_milli": 9},
    ]
    try:
        for record in quality_records:
            invalid_quality.accept(record)
        invalid_quality_rejected = False
    except ValueError:
        invalid_quality_rejected = True

    return {
        "replayed_sequence_rejected": replay_rejected,
        "mixed_device_rejected": mixed_device_rejected,
        "duplicate_metric_rejected": duplicate_metric_rejected,
        "invalid_power_rejected": invalid_power_rejected,
        "invalid_quality_rejected": invalid_quality_rejected,
    }


def run(output: Path) -> dict[str, Any]:
    boundary = json.loads((ROOT / "boundary-manifest.json").read_text())
    samples = (
        TelemetrySample(1_000, 1_000, 45.0, 3.0, True, TelemetryQuality.GOOD),
        TelemetrySample(1_060, 1_060, 38.0, 5.0, True, TelemetryQuality.GOOD),
        TelemetrySample(1_120, 1_120, 38.0, 5.0, True, TelemetryQuality.STALE),
        TelemetrySample(1_180, 1_180, 92.0, 2.0, True, TelemetryQuality.GOOD),
    )
    frames: list[bytes] = []
    sequence = 1
    quality_values = {
        TelemetryQuality.GOOD: 0,
        TelemetryQuality.STALE: 1,
        TelemetryQuality.CONFLICT: 2,
    }
    for sample in samples:
        encoded_values = (
            round(sample.tank_level_pct * 1000),
            round(sample.demand_lps * 1000),
            int(sample.power_available),
            quality_values[sample.quality],
        )
        for metric, value in enumerate(encoded_values):
            frames.append(
                build_frame(
                    device_id=7,
                    sequence=sequence,
                    timestamp_ms=sample.observed_at_s * 1000,
                    metric=metric,
                    value=value,
                )
            )
            sequence += 1

    with tempfile.TemporaryDirectory(prefix="mncs-integration-") as temporary:
        temporary_path = Path(temporary)
        binary = temporary_path / "edgestream-integration"
        input_path = temporary_path / "telemetry.bin"
        input_path.write_bytes(b"".join(frames))
        compile_command = build_edgestream(binary)
        completed = subprocess.run(
            [str(binary), "--chunk", "7", str(input_path)],
            cwd=EDGESTREAM_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        records = [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]
        event_records = [record for record in records if record.get("type") == "event"]
        adapter = EdgeStreamTelemetryAdapter(device_id=7)
        adapted_samples = [sample for record in event_records if (sample := adapter.accept(record))]
        if adapter.pending:
            raise RuntimeError("EdgeStream output ended with incomplete telemetry sample state")

        direct_controller = Controller(GeneratedTablePlanner())
        adapted_controller = Controller(GeneratedTablePlanner())
        direct_intents = [
            direct_controller.decide(sample, sample.received_at_s).as_dict() for sample in samples
        ]
        adapted_intents = [
            adapted_controller.decide(sample, sample.received_at_s).as_dict()
            for sample in adapted_samples
        ]
        checks = {
            "edge_events_complete": len(event_records) == len(samples) * 4,
            "adapter_sample_count": len(adapted_samples) == len(samples),
            "adapted_samples_equal_direct_samples": adapted_samples == list(samples),
            "authorized_intents_equal": adapted_intents == direct_intents,
            "journal_tail_equal": adapted_controller.journal.tail_hash
            == direct_controller.journal.tail_hash,
            "component_evidence_separate": all(
                not item["copied_or_rewritten_by_integration"]
                for item in boundary["component_boundaries"]
            ),
            "distinct_component_identities": len(
                {item["component_id"] for item in boundary["component_boundaries"]}
            )
            == len(boundary["component_boundaries"]),
            "claim_promotion_forbidden": not boundary["claim_boundary"][
                "integration_pass_promotes_component_claims"
            ],
            **rejection_checks(),
        }
        result = {
            "schema_version": "0.2",
            "study_id": boundary["integration_id"],
            "status": "PASS" if all(checks.values()) else "FAIL",
            "formal_mncs_status": "UNKNOWN",
            "formal_mncds_status": "UNKNOWN",
            "checks": {key: "PASS" if value else "FAIL" for key, value in checks.items()},
            "compile_command": compile_command,
            "chunk_size": 7,
            "frame_count": len(frames),
            "edge_record_count": len(records),
            "edge_event_count": len(event_records),
            "adapted_sample_count": len(adapted_samples),
            "intervention_counts": adapted_controller.intervention_counts,
            "identities": {
                "boundary_manifest": sha256_file(ROOT / "boundary-manifest.json"),
                "integration_runner": sha256_file(Path(__file__)),
                "edgestream_manifest": sha256_file(EDGESTREAM_ROOT / "manifest.json"),
                "edgestream_candidate": sha256_file(
                    EDGESTREAM_ROOT / "machine" / "edgestream_generated.c"
                ),
                "remote_water_assurance": sha256_file(WATER_ROOT / "assurance-case.json"),
                "remote_water_controller": sha256_file(
                    WATER_ROOT / "src" / "water_control" / "controller.py"
                ),
                "remote_water_planner": sha256_file(
                    WATER_ROOT / "machine" / "generated_planner.py"
                ),
                "remote_water_safety_kernel": sha256_file(
                    WATER_ROOT / "src" / "water_control" / "safety.py"
                ),
                "input_frames": sha256_file(input_path),
                "canonical_edge_output": sha256_bytes(completed.stdout.encode()),
                "authorized_intents": sha256_bytes(
                    json.dumps(adapted_intents, sort_keys=True, separators=(",", ":")).encode()
                ),
            },
            "component_boundaries": boundary["component_boundaries"],
            "limitations": [
                (
                    "This study exercises a local file and process boundary, not a "
                    "network transport or live SCADA path."
                ),
                (
                    "An integration PASS does not promote either component claim or "
                    "authorize production control."
                ),
                "The adapter contract is limited to one device and four declared metric mappings.",
            ],
        }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "evidence" / "results" / "study-summary.json",
    )
    args = parser.parse_args()
    result = run(args.output)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
