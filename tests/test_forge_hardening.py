"""Regression tests for deletion-aware and policy-bound Forge entrypoints."""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROVIDER = (
    ROOT
    / "experimental"
    / "integrations"
    / "mncs-forge"
    / "providers"
    / "project_provider_hardened.py"
)


def request(changed_paths: list[str], dependency_paths: list[str]) -> dict[str, object]:
    return {
        "protocol_version": "0.1",
        "type": "analysis_request",
        "request_id": "deleted-path-regression",
        "analysis": "evidence-change-impact",
        "component": {
            "candidate_identity": "sha256:" + "1" * 64,
            "changed_paths": changed_paths,
        },
        "extensions": {
            "mncs_forge": {"question_parameters": {"dependency_paths": dependency_paths}}
        },
    }


def run_provider(payload: dict[str, object]) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(PROVIDER)],
        cwd=ROOT,
        input=json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stderr == ""
    assert completed.stdout.count("\n") == 1
    result = json.loads(completed.stdout)
    assert isinstance(result, dict)
    return result


def test_deleted_path_can_establish_bounded_overlap() -> None:
    deleted = "experimental/integrations/mncs-forge/fixtures/deleted-artifact.txt"
    result = run_provider(request([deleted], [deleted]))
    assert result["status"] == "FAIL"
    assert result["witnesses"] == [{"affected_path": deleted}]


def test_deleted_path_can_establish_bounded_non_overlap() -> None:
    deleted = "experimental/integrations/mncs-forge/fixtures/deleted-artifact.txt"
    dependency = "experimental/integrations/mncs-forge/fixtures/unrelated-artifact.txt"
    result = run_provider(request([deleted], [dependency]))
    assert result["status"] == "PASS"
    assert "old bytes" in " ".join(result["limitations"])


def test_workflow_policy_is_loaded_from_committed_config() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        from forge_policy import load_forge_workflow_policy

        policy = load_forge_workflow_policy()
    finally:
        sys.path.pop(0)
    with (ROOT / "mncs-forge.toml").open("rb") as stream:
        config = tomllib.load(stream)
    assert policy.environment_allowlist == tuple(config["environment_allowlist"])
    assert policy.output_cap == config["limits"]["output_bytes"]


def test_forge_config_uses_hardened_entrypoints() -> None:
    with (ROOT / "mncs-forge.toml").open("rb") as stream:
        config = tomllib.load(stream)
    provider = config["providers"][0]
    assert provider["command"][-1].endswith("project_provider_hardened.py")
    project_workflows = [
        item for item in config["workflows"] if item.get("provider_id") == provider["id"]
    ]
    assert project_workflows
    assert all(item["command"] == provider["command"] for item in project_workflows)
    bounded_workflows = [
        item
        for item in config["workflows"]
        if item["name"]
        in {
            "tooling-inspect",
            "release-candidate-check",
            "release-candidate-corpus",
            "python-rust-comparison",
            "recursive-analyzer-study",
            "core-check",
            "ravel-0.4-check",
        }
    ]
    assert bounded_workflows
    assert all(
        any(argument.endswith("forge_workflow_hardened.py") for argument in item["command"])
        for item in bounded_workflows
    )
