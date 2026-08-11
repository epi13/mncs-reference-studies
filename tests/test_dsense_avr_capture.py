from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "case-studies" / "dsense-desk-pet" / "tools" / "capture_avr_compile.py"


def load_tool() -> ModuleType:
    specification = importlib.util.spec_from_file_location("dsense_avr_capture", TOOL)
    assert specification is not None
    assert specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def test_memory_parser_preserves_overflow_and_headroom() -> None:
    tool = load_tool()
    output = """
Sketch uses 33308 bytes (103%) of program storage space. Maximum is 32256 bytes.
Global variables use 1159 bytes (56%) of dynamic memory, leaving 889 bytes for local variables.
Maximum is 2048 bytes.
"""
    memory = tool.parse_memory(output)
    assert memory == {
        "program_bytes": 33308,
        "program_limit_bytes": 32256,
        "program_headroom_bytes": -1052,
        "global_sram_bytes": 1159,
        "sram_limit_bytes": 2048,
        "sram_headroom_bytes": 889,
    }
    assert tool.memory_status(memory) == "FAIL"
    assert (
        tool.aggregate_status(
            [
                "PASS",
                tool.memory_status(memory),
                tool.preferred_headroom_status(memory),
            ]
        )
        == "FAIL"
    )


def test_memory_parser_is_conservative() -> None:
    tool = load_tool()
    assert tool.parse_memory("Sketch uses 1 bytes. Maximum is 32256 bytes.") is None
    assert tool.memory_status(None) == "UNKNOWN"
    assert tool.preferred_headroom_status(None) == "UNKNOWN"


def test_compile_command_cannot_upload_or_select_a_port(tmp_path: Path) -> None:
    tool = load_tool()
    command = tool.compile_command(
        "/opt/arduino-cli",
        tmp_path / "build",
        tmp_path / "sketch",
    )
    assert command[0] == "/opt/arduino-cli"
    assert "compile" in command
    assert "--upload" not in command
    assert "--port" not in command
    assert "-p" not in command


def test_used_library_versions_and_status_precedence() -> None:
    tool = load_tool()
    output = """
Using library Wire at version 1.0 in folder: /ignored/Wire
Using library EEPROM at version 2.0 in folder: /ignored/EEPROM
"""
    assert tool.used_libraries(output) == [
        {"name": "Wire", "version": "1.0"},
        {"name": "EEPROM", "version": "2.0"},
    ]
    assert tool.aggregate_status(["PASS", "UNKNOWN"]) == "UNKNOWN"
    assert tool.aggregate_status(["PASS", "UNKNOWN", "FAIL"]) == "FAIL"
