#!/usr/bin/env python3
"""Offline integrity and mechanism checks for the dSense Desk Pet case study."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import struct
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HASH_INDEX = ROOT / "evidence" / "results" / "artifact-hashes.json"
ANALYSIS = ROOT / "evidence" / "results" / "epoch-1-analysis.json"
COMPILE = ROOT / "evidence" / "results" / "compile-observations.json"
ASSURANCE = ROOT / "assurance-case.json"
PREREGISTRATION = ROOT / "preregistration.json"


class VerificationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path} must contain a JSON object")
    return value


def load_module(path: Path, name: str) -> ModuleType:
    specification = importlib.util.spec_from_file_location(name, path)
    require(specification is not None and specification.loader is not None, f"load {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def materializer() -> ModuleType:
    return load_module(ROOT / "tools" / "materialize.py", "dsense_materialize")


def verify_hashes() -> None:
    index = load_json(HASH_INDEX)
    artifacts = index.get("artifacts")
    require(isinstance(artifacts, list) and artifacts, "artifact hash index is empty")
    for artifact in artifacts:
        require(isinstance(artifact, dict), "invalid artifact hash entry")
        relative = artifact.get("path")
        expected = artifact.get("sha256")
        require(isinstance(relative, str), "artifact path must be a string")
        require(isinstance(expected, str), "artifact SHA-256 must be a string")
        path = ROOT / relative
        require(path.is_file(), f"missing artifact: {relative}")
        require(sha256(path.read_bytes()) == expected, f"SHA-256 mismatch: {relative}")


def normalize_debug_line(source: str) -> str:
    return re.sub(
        r"constexpr bool DEBUG_SERIAL = (?:true|false);",
        "constexpr bool DEBUG_SERIAL = <MODE>;",
        source,
        count=1,
    )


def verify_materialized_artifacts() -> dict[str, bytes]:
    module = materializer()
    artifacts = module.materialized_artifacts()
    for name, content in artifacts.items():
        module.verify_identity(name, content)
    return artifacts


def verify_firmware_pair(artifacts: dict[str, bytes]) -> None:
    module = materializer()
    telemetry = artifacts[module.TELEMETRY_NAME].decode("utf-8")
    production = artifacts[module.PRODUCTION_NAME].decode("utf-8")
    baseline = artifacts[module.BASELINE_NAME].decode("utf-8")

    require("constexpr bool DEBUG_SERIAL = true;" in telemetry, "telemetry mode is not enabled")
    require("constexpr bool DEBUG_SERIAL = false;" in production, "production mode is not disabled")
    require(
        normalize_debug_line(telemetry) == normalize_debug_line(production),
        "production and telemetry sketches differ outside DEBUG_SERIAL",
    )

    for expected in (
        "constexpr uint8_t BUTTON_PIN = 2;",
        "constexpr uint8_t UP_BUTTON_PIN = 3;",
        "constexpr uint8_t DOWN_BUTTON_PIN = 4;",
        "constexpr uint8_t PIEZO_MIC_PIN = A1;",
        "Serial.write((uint8_t)0xA5);",
        "Serial.write((uint8_t)0x5A);",
        "uint8_t v[4]={5,sizeof(FastPacket),sizeof(ModelPacket),sizeof(EventPacket)};",
        "EEPROM.get(EEPROM_SETTINGS_ADDRESS, settings);",
        "analogRead(PIEZO_MIC_PIN);",
    ):
        require(expected in telemetry, f"missing firmware invariant: {expected}")

    require("Serial.print" not in telemetry, "human-formatted serial output returned")
    require("malloc(" not in telemetry and "new " not in telemetry, "heap allocation detected")
    require(
        not re.findall(r'"(?:\\.|[^"\\])*"', telemetry),
        "V5 machine firmware contains C/C++ string literals",
    )
    require(len(telemetry.encode()) < len(baseline.encode()), "candidate source is not smaller")


def verify_binary_protocol() -> None:
    decoder = load_module(ROOT / "tools" / "capture_dsense_binary_v5.py", "dsense_decoder")
    require(decoder.expected_packet_sizes() == (49, 37, 20), "unexpected packet sizes")

    version_payload = struct.pack("<4B", 5, 49, 37, 20)
    valid = decoder.frame_bytes(127, version_payload)
    buffer = bytearray(b"noise" + valid[:3])
    require(list(decoder.parse_frames(buffer)) == [], "partial frame was emitted")
    buffer.extend(valid[3:])
    require(
        list(decoder.parse_frames(buffer)) == [(127, version_payload)],
        "valid version frame was not recovered after noise and fragmentation",
    )

    corrupt = bytearray(decoder.frame_bytes(3, bytes(20)))
    corrupt[-1] ^= 0xFF
    joined = bytearray(corrupt + decoder.frame_bytes(127, version_payload))
    require(
        list(decoder.parse_frames(joined)) == [(127, version_payload)],
        "decoder did not reject corruption and resynchronize",
    )


def verify_evidence(artifacts: dict[str, bytes]) -> None:
    module = materializer()
    analyzer = load_module(ROOT / "tools" / "analyze_epoch1.py", "dsense_analyzer")
    extract = json.loads(artifacts[module.EVIDENCE_NAME])
    regenerated = analyzer.canonical_json(analyzer.build_summary(extract))
    require(ANALYSIS.read_text(encoding="utf-8") == regenerated, "epoch-1 evidence drift")

    analysis = load_json(ANALYSIS)
    observations = analysis["observations"]
    require(observations["acoustic_counter_delta"] == 552, "unexpected event delta")
    require(observations["learned_noise_floor"]["minimum"] == 4, "noise-floor finding drift")
    require(
        observations["novelty"]["fraction_at_or_above_1000"] > 0.99,
        "novelty saturation finding drift",
    )
    require(analysis["result"]["development_status"] == "FAIL", "epoch-1 must remain FAIL")

    compile_data = load_json(COMPILE)
    baseline = compile_data["observations"][0]
    require(baseline["program_bytes"] == 34676, "baseline compile observation drift")
    require(baseline["program_headroom_bytes"] == -2420, "baseline headroom drift")
    require(compile_data["result"]["development_status"] == "UNKNOWN", "V5 compile is not known")

    preregistration = load_json(PREREGISTRATION)
    require(preregistration["hard_gates"]["quiet_event_rate_hz_max"] == 0.1, "quiet gate drift")
    require(
        preregistration["formal_status_if_development_passes"]["mncs"] == "UNKNOWN",
        "status drift",
    )

    assurance = load_json(ASSURANCE)
    require(assurance["formal_mncs_status"] == "UNKNOWN", "MNCS status must be UNKNOWN")
    require(assurance["formal_mncds_status"] == "UNKNOWN", "MNCDS status must be UNKNOWN")
    require(assurance["promotion_authorized"] is False, "promotion must remain unauthorized")


def main() -> int:
    try:
        verify_hashes()
        artifacts = verify_materialized_artifacts()
        verify_firmware_pair(artifacts)
        verify_binary_protocol()
        verify_evidence(artifacts)
    except (OSError, ValueError, KeyError, VerificationError) as error:
        print(f"FAIL: {error}")
        return 1
    print("PASS: dSense case-study integrity and offline mechanism checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
