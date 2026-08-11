#!/usr/bin/env python3
"""Capture non-uploading AVR compile and resource evidence for frozen dSense V5."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import re
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "evidence" / "local" / "avr-compile.json"
FQBN = "arduino:avr:uno"
PROGRAM_LIMIT = 32_256
SRAM_LIMIT = 2_048
PREFERRED_PROGRAM_HEADROOM = 512
MEMORY_PATTERN = re.compile(
    r"Sketch uses (?P<program>\d+) bytes .*?Maximum is (?P<program_max>\d+) bytes\.\s*"
    r"Global variables use (?P<sram>\d+) bytes .*?Maximum is (?P<sram_max>\d+) bytes\.",
    re.DOTALL,
)
USED_LIBRARY_PATTERN = re.compile(r"^Using library (.+?) at version (\S+) in folder:", re.MULTILINE)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_materializer() -> ModuleType:
    path = ROOT / "tools" / "materialize.py"
    specification = importlib.util.spec_from_file_location("dsense_materialize_avr", path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load materializer: {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def command_result(
    command: list[str],
    *,
    timeout: float,
) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout if isinstance(error.stdout, str) else ""
        stderr = error.stderr if isinstance(error.stderr, str) else ""
        return {
            "status": "UNKNOWN",
            "operational_error": f"timeout after {timeout:g} seconds",
            "returncode": None,
            "stdout": stdout,
            "stderr": stderr,
            "stdout_sha256": sha256(stdout.encode()),
            "stderr_sha256": sha256(stderr.encode()),
        }
    except OSError as error:
        return {
            "status": "UNKNOWN",
            "operational_error": str(error),
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "stdout_sha256": sha256(b""),
            "stderr_sha256": sha256(b""),
        }
    return {
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "operational_error": None,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "stdout_sha256": sha256(completed.stdout.encode()),
        "stderr_sha256": sha256(completed.stderr.encode()),
    }


def parse_memory(output: str) -> dict[str, int] | None:
    matches = list(MEMORY_PATTERN.finditer(output))
    if len(matches) != 1:
        return None
    values = {name: int(value) for name, value in matches[0].groupdict().items()}
    return {
        "program_bytes": values["program"],
        "program_limit_bytes": values["program_max"],
        "program_headroom_bytes": values["program_max"] - values["program"],
        "global_sram_bytes": values["sram"],
        "sram_limit_bytes": values["sram_max"],
        "sram_headroom_bytes": values["sram_max"] - values["sram"],
    }


def used_libraries(output: str) -> list[dict[str, str]]:
    return [
        {"name": name, "version": version} for name, version in USED_LIBRARY_PATTERN.findall(output)
    ]


def compile_command(
    arduino_cli: str,
    build_path: Path,
    sketch_path: Path,
) -> list[str]:
    return [
        arduino_cli,
        "compile",
        "--fqbn",
        FQBN,
        "--build-path",
        str(build_path),
        "--clean",
        "--verbose",
        "--no-color",
        str(sketch_path),
    ]


def memory_status(memory: dict[str, int] | None) -> str:
    if memory is None:
        return "UNKNOWN"
    if memory["program_limit_bytes"] != PROGRAM_LIMIT or memory["sram_limit_bytes"] != SRAM_LIMIT:
        return "UNKNOWN"
    if memory["program_headroom_bytes"] < 0 or memory["sram_headroom_bytes"] < 0:
        return "FAIL"
    return "PASS"


def preferred_headroom_status(memory: dict[str, int] | None) -> str:
    if memory is None:
        return "UNKNOWN"
    return "PASS" if memory["program_headroom_bytes"] >= PREFERRED_PROGRAM_HEADROOM else "FAIL"


def aggregate_status(statuses: list[str]) -> str:
    if "FAIL" in statuses:
        return "FAIL"
    if "UNKNOWN" in statuses:
        return "UNKNOWN"
    return "PASS"


def binary_identities(build_path: Path) -> list[dict[str, Any]]:
    identities: list[dict[str, Any]] = []
    for path in sorted(build_path.iterdir()):
        if not path.is_file() or path.suffix not in {".bin", ".eep", ".elf", ".hex"}:
            continue
        content = path.read_bytes()
        identities.append(
            {
                "name": path.name,
                "bytes": len(content),
                "sha256": sha256(content),
            }
        )
    return identities


def extract_board_properties(details: dict[str, Any]) -> dict[str, str]:
    properties: dict[str, str] = {}
    raw = details.get("build_properties")
    if not isinstance(raw, list):
        return properties
    for item in raw:
        if not isinstance(item, str) or "=" not in item:
            continue
        key, value = item.split("=", 1)
        if key in {
            "version",
            "compiler.path",
            "runtime.tools.avr-gcc.path",
            "runtime.tools.avrdude.path",
        }:
            properties[key] = value
    return properties


def executable_version(path: Path, argument: str = "--version") -> dict[str, Any]:
    result = command_result([str(path), argument], timeout=10)
    return {
        "path": str(path),
        "status": result["status"],
        "returncode": result["returncode"],
        "stdout": result["stdout"],
        "stderr": result["stderr"],
        "stdout_sha256": result["stdout_sha256"],
        "stderr_sha256": result["stderr_sha256"],
    }


def collect_toolchain(arduino_cli: str) -> dict[str, Any]:
    version = command_result([arduino_cli, "version"], timeout=10)
    cores = command_result([arduino_cli, "core", "list"], timeout=30)
    libraries = command_result([arduino_cli, "lib", "list", "--format", "json"], timeout=30)
    details = command_result(
        [arduino_cli, "board", "details", "--fqbn", FQBN, "--format", "json"],
        timeout=30,
    )

    installed_libraries: list[dict[str, str]] = []
    if libraries["status"] == "PASS":
        try:
            decoded = json.loads(libraries["stdout"])
            for item in decoded.get("installed_libraries", []):
                library = item.get("library", {})
                name = library.get("name")
                library_version = library.get("version")
                location = library.get("location")
                if isinstance(name, str) and isinstance(library_version, str):
                    installed_libraries.append(
                        {
                            "name": name,
                            "version": library_version,
                            "location": location if isinstance(location, str) else "UNKNOWN",
                        }
                    )
        except (AttributeError, json.JSONDecodeError):
            libraries["status"] = "UNKNOWN"
            libraries["operational_error"] = "Arduino library JSON was not parseable"

    board_properties: dict[str, str] = {}
    if details["status"] == "PASS":
        try:
            board_properties = extract_board_properties(json.loads(details["stdout"]))
        except (AttributeError, json.JSONDecodeError):
            details["status"] = "UNKNOWN"
            details["operational_error"] = "Arduino board-details JSON was not parseable"

    bundled_avr_gcc: dict[str, Any] | None = None
    compiler_path = board_properties.get("compiler.path")
    if compiler_path:
        bundled_avr_gcc = executable_version(Path(compiler_path) / "avr-gcc")

    bundled_avrdude: dict[str, Any] | None = None
    avrdude_root = board_properties.get("runtime.tools.avrdude.path")
    if avrdude_root:
        bundled_avrdude = executable_version(Path(avrdude_root) / "bin" / "avrdude", "-?")

    return {
        "arduino_cli": {
            "status": version["status"],
            "returncode": version["returncode"],
            "stdout": version["stdout"],
            "stderr": version["stderr"],
        },
        "core_list": {
            "status": cores["status"],
            "returncode": cores["returncode"],
            "stdout": cores["stdout"],
            "stderr": cores["stderr"],
        },
        "fqbn": FQBN,
        "avr_core_version": board_properties.get("version"),
        "installed_libraries": sorted(installed_libraries, key=lambda item: item["name"]),
        "board_details_status": details["status"],
        "board_details_error": details["operational_error"],
        "bundled_avr_gcc": bundled_avr_gcc,
        "bundled_avrdude": bundled_avrdude,
    }


def compile_sketch(
    arduino_cli: str,
    materializer: ModuleType,
    name: str,
    source: bytes,
    temporary_root: Path,
    timeout: float,
) -> dict[str, Any]:
    materializer.verify_identity(name, source)
    sketch_name = Path(name).stem
    sketch_path = temporary_root / sketch_name
    build_path = temporary_root / f"{sketch_name}-build"
    sketch_path.mkdir()
    build_path.mkdir()
    (sketch_path / name).write_bytes(source)

    command = compile_command(arduino_cli, build_path, sketch_path)
    raw = command_result(command, timeout=timeout)
    combined_output = raw["stdout"] + raw["stderr"]
    memory = parse_memory(combined_output)
    resource_status = memory_status(memory)
    headroom_status = preferred_headroom_status(memory)
    compile_status = raw["status"]
    result = aggregate_status([compile_status, resource_status, headroom_status])
    return {
        "artifact": name,
        "source_bytes": len(source),
        "source_sha256": sha256(source),
        "command": command,
        "compile_status": compile_status,
        "resource_envelope_status": resource_status,
        "preferred_program_headroom_status": headroom_status,
        "result": result,
        "returncode": raw["returncode"],
        "operational_error": raw["operational_error"],
        "memory": memory,
        "used_libraries": used_libraries(combined_output),
        "raw_stdout": raw["stdout"],
        "raw_stderr": raw["stderr"],
        "raw_stdout_sha256": raw["stdout_sha256"],
        "raw_stderr_sha256": raw["stderr_sha256"],
        "produced_binaries": binary_identities(build_path),
    }


def unavailable_report(machine_label: str, reason: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "study_id": "dsense.desk-pet.avr-compile-capture.v1",
        "captured_at": datetime.now(UTC).isoformat(),
        "machine_label": machine_label,
        "environment": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "fqbn": FQBN,
        "status": "UNKNOWN",
        "operational_error": reason,
        "compiles": [],
        "formal_mncs_status": "UNKNOWN",
        "formal_mncds_status": "UNKNOWN",
        "physical_protocol_status": "UNKNOWN",
        "promotion_authorized": False,
    }


def capture(machine_label: str, timeout: float) -> dict[str, Any]:
    arduino_cli = shutil.which("arduino-cli")
    if arduino_cli is None:
        return unavailable_report(machine_label, "arduino-cli is unavailable")

    materializer = load_materializer()
    artifacts = materializer.materialized_artifacts()
    names = [materializer.TELEMETRY_NAME, materializer.PRODUCTION_NAME]
    for name in names:
        materializer.verify_identity(name, artifacts[name])

    toolchain = collect_toolchain(arduino_cli)
    prerequisite_status = aggregate_status(
        [
            toolchain["arduino_cli"]["status"],
            toolchain["core_list"]["status"],
            toolchain["board_details_status"],
        ]
    )
    if prerequisite_status != "PASS" or toolchain["avr_core_version"] is None:
        report = unavailable_report(
            machine_label, "required Arduino toolchain identity unavailable"
        )
        report["toolchain"] = toolchain
        return report

    with tempfile.TemporaryDirectory(prefix="mncs-dsense-avr-") as temporary:
        temporary_root = Path(temporary)
        compiles = [
            compile_sketch(
                arduino_cli,
                materializer,
                name,
                artifacts[name],
                temporary_root,
                timeout,
            )
            for name in names
        ]

    return {
        "schema_version": "1.0",
        "study_id": "dsense.desk-pet.avr-compile-capture.v1",
        "captured_at": datetime.now(UTC).isoformat(),
        "machine_label": machine_label,
        "environment": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "fqbn": FQBN,
        "limits": {
            "program_bytes": PROGRAM_LIMIT,
            "global_sram_bytes": SRAM_LIMIT,
            "preferred_program_headroom_bytes": PREFERRED_PROGRAM_HEADROOM,
        },
        "toolchain": toolchain,
        "compiles": compiles,
        "status": aggregate_status([compile_result["result"] for compile_result in compiles]),
        "formal_mncs_status": "UNKNOWN",
        "formal_mncds_status": "UNKNOWN",
        "physical_protocol_status": "UNKNOWN",
        "promotion_authorized": False,
        "claim_boundary": (
            "This record resolves only local compile and resource-envelope observations. "
            "It does not establish physical behavior, independent evaluation, formal "
            "MNCS/MNCDS status, or promotion authority."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--machine-label", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout", type=float, default=300)
    arguments = parser.parse_args()
    if arguments.timeout <= 0:
        parser.error("--timeout must be positive")

    report = capture(arguments.machine_label, arguments.timeout)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": str(arguments.output),
                "status": report["status"],
                "formal_mncs_status": report["formal_mncs_status"],
                "formal_mncds_status": report["formal_mncds_status"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
