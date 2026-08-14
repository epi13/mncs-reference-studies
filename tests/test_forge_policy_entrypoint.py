"""Tests for the policy-bound Forge workflow entrypoint."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def test_hardened_entrypoint_passes_configured_output_cap(monkeypatch: Any, capsys: Any) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import forge_policy
        import forge_workflow
        import forge_workflow_hardened

        policy = forge_policy.load_forge_workflow_policy()
        captured: dict[str, object] = {}

        def fake_run_workflow(name: str, workflow: object, *, output_cap: int) -> dict[str, object]:
            captured.update({"name": name, "workflow": workflow, "output_cap": output_cap})
            return {"status": "PASS"}

        monkeypatch.setattr(forge_workflow, "run_workflow", fake_run_workflow)
        monkeypatch.setattr(sys, "argv", ["forge_workflow_hardened.py", "tooling-inspect"])
        assert forge_workflow_hardened.main() == 0
    finally:
        sys.path.pop(0)
    assert captured["name"] == "tooling-inspect"
    assert captured["output_cap"] == policy.output_cap
    assert json.loads(capsys.readouterr().out)["status"] == "PASS"


def test_tooling_inspect_does_not_require_a_repo_local_venv() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import forge_workflow
    finally:
        sys.path.pop(0)
    argv = forge_workflow.resolve_tooling_inspect_argv()
    assert argv[0] != ".venv/bin/mncs"
    assert argv[-2:] == ("version", "--json")
    assert Path(argv[0]).is_file() or argv[1:3] == ("-m", "mncs_validator.cli")
