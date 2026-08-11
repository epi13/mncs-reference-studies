from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "case-studies" / "edgestream" / "tools"


def study_evaluation():
    sys.path.insert(0, str(TOOLS))
    try:
        return importlib.import_module("study_evaluation")
    finally:
        sys.path.remove(str(TOOLS))


def study_support():
    sys.path.insert(0, str(TOOLS))
    try:
        return importlib.import_module("study_support")
    finally:
        sys.path.remove(str(TOOLS))


def test_joern_version_ignores_launcher_warnings() -> None:
    module = study_evaluation()
    stdout = """Jul 28, 2026 org.jline.utils.Log logr
WARNING: Unable to create a system terminal
Version: 4.0.583
joern>
"""
    stderr = "Warning: Unknown option --version\n"
    assert module.parse_joern_version(stdout, stderr) == "4.0.583"


def test_joern_version_is_unknown_without_a_version_line() -> None:
    module = study_evaluation()
    assert module.parse_joern_version("launcher warning", "") is None


def test_compile_command_records_repository_relative_paths(monkeypatch) -> None:
    module = study_support()
    commands: list[list[str]] = []
    monkeypatch.setattr(module, "run", lambda command: commands.append(command))
    command = module.compile_binary(
        "cc",
        module.ROOT / "machine" / "edgestream_generated.c",
        module.BUILD / "candidate-test",
    )
    assert command == commands[0]
    assert "machine/edgestream_generated.c" in command
    assert "build/candidate-test" in command
    assert all(not item.startswith(str(module.ROOT)) for item in command)


def test_structural_provider_redacts_external_fixture_path(monkeypatch, tmp_path: Path) -> None:
    module = study_evaluation()
    completed = type("Completed", (), {"stdout": "{}", "stderr": ""})()
    monkeypatch.setattr(module, "run", lambda command, timeout: completed)
    monkeypatch.setattr(module, "compiler_version", lambda compiler: "clang test")
    _, provider = module._clang_ast(tmp_path / "fixture.c")
    assert provider["status"] == "PASS"
    assert provider["command"][-1] == "<external-source>"
