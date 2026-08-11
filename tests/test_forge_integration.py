"""Static and executable tests for the non-normative MNCS Forge integration."""

from __future__ import annotations

import json
import subprocess
import tempfile
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

pytestmark = pytest.mark.experimental

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "experimental" / "integrations" / "mncs-forge"
PROVIDER = INTEGRATION / "providers" / "project_provider.py"
FORGE = ROOT.parent / "mncs-forge-mcp" / ".venv" / "bin" / "mncs-forge"
ARTIFACTS = [
    "experimental/integrations/mncs-forge/fixtures/artifact-a.txt",
    "experimental/integrations/mncs-forge/fixtures/artifact-b.txt",
]


def _request(method: str, parameters: Mapping[str, object]) -> dict[str, object]:
    return {
        "protocol_version": "0.1",
        "type": "analysis_request",
        "request_id": "pytest-request-1",
        "analysis": method,
        "component": {
            "candidate_identity": "sha256:" + "1" * 64,
            "changed_paths": [],
        },
        "extensions": {"mncs_forge": {"question_parameters": dict(parameters)}},
    }


def _provider_bytes(payload: bytes) -> tuple[subprocess.CompletedProcess[bytes], dict[str, Any]]:
    completed = subprocess.run(
        [str(PROVIDER)],
        cwd=ROOT,
        input=payload,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert completed.returncode == 0
    assert completed.stderr == b""
    assert completed.stdout.count(b"\n") == 1
    assert len(completed.stdout) <= 131_072
    return completed, json.loads(completed.stdout)


def _provider(request: Mapping[str, object]) -> dict[str, Any]:
    _, result = _provider_bytes(
        json.dumps(dict(request), sort_keys=True, separators=(",", ":")).encode() + b"\n"
    )
    return result


def _forge(*arguments: str, config: Path | None = None) -> dict[str, Any]:
    if not FORGE.is_file():
        pytest.skip("separate mncs-forge executable is unavailable")
    completed = subprocess.run(
        [str(FORGE), "--config", str(config or ROOT / "mncs-forge.toml"), *arguments],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_capability_registry_schema_and_unique_bindings() -> None:
    schema = json.loads((INTEGRATION / "capability-registry.schema.json").read_text())
    registry = json.loads((INTEGRATION / "capability-registry.json").read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(registry)
    identifiers = [item["id"] for item in registry["capabilities"]]
    methods = [item["provider_protocol_method"] for item in registry["capabilities"]]
    assert len(identifiers) == len(set(identifiers)) == 4
    assert len(methods) == len(set(methods)) == 4
    assert all(item["required"] for item in registry["capabilities"])


def test_forge_config_capability_workflow_and_verifier_consistency() -> None:
    config = tomllib.loads((ROOT / "mncs-forge.toml").read_text())
    registry = json.loads((INTEGRATION / "capability-registry.json").read_text())
    providers = {item["id"]: item for item in config["providers"]}
    workflows = {item["name"]: item for item in config["workflows"]}
    verifiers = {item["id"]: item for item in config["verifiers"]}
    provider = providers["mncs-project-micro-verifiers"]

    assert config["required_capabilities"]
    assert set(config["required_capabilities"]) <= set(provider["capabilities"])
    assert set(config["required_capabilities"]) == {
        item["provider_protocol_method"] for item in registry["capabilities"]
    }
    assert set(verifiers) == {item["id"] for item in registry["capabilities"]}
    for declaration in verifiers.values():
        workflow = workflows[declaration["workflow"]]
        assert declaration["method"] in provider["capabilities"]
        assert declaration["provider"] == provider["id"] == workflow["provider_id"]
        assert workflow["provider_protocol"] is True
        assert declaration["category"] == workflow["category"]
        assert set(declaration["modes"]) <= {workflow["mode"]}
        assert workflow["command"] == provider["command"]


def test_provider_capabilities_and_wrong_method() -> None:
    capability_request = {
        "protocol_version": "0.1",
        "type": "capabilities",
        "request_id": "pytest-capabilities",
    }
    capabilities = _provider(capability_request)
    assert capabilities["type"] == "capabilities"
    assert capabilities["analyses"] == [
        "evidence-change-impact",
        "artifact-manifest-identity",
        "mncs-assurance-graph-impact",
        "mncs-record-dispatch",
    ]
    unsupported = _provider(_request("not-declared", {}))
    assert unsupported["status"] == "UNKNOWN"
    assert unsupported["extensions"]["unsupported_constructs"] == ["unsupported-method"]


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (b"{}\n{}\n", "FRAMING"),
        (b"{}", "FRAMING"),
        (b"not-json\n", "MALFORMED_JSON"),
        (b"x" * 65_537, "REQUEST_LIMIT"),
    ],
)
def test_provider_rejects_malformed_or_oversized_framing(payload: bytes, code: str) -> None:
    _, result = _provider_bytes(payload)
    assert result["type"] == "error"
    assert result["code"] == code


def test_provider_rejects_traversal_as_unknown() -> None:
    result = _provider(
        _request(
            "mncs-record-dispatch",
            {
                "record_path": "../pyproject.toml",
                "kind": "contract",
                "expected_schema_version": "0.3-rc.1",
            },
        )
    )
    assert result["status"] == "UNKNOWN"
    assert "record-unavailable" in result["extensions"]["unsupported_constructs"]


def test_manifest_identity_pass_and_mismatch_fail() -> None:
    passing = _provider(
        _request(
            "artifact-manifest-identity",
            {
                "manifest_path": ("experimental/integrations/mncs-forge/fixtures/manifest.json"),
                "artifact_paths": ARTIFACTS,
            },
        )
    )
    failing = _provider(
        _request(
            "artifact-manifest-identity",
            {
                "manifest_path": (
                    "experimental/integrations/mncs-forge/fixtures/manifest-mismatch.json"
                ),
                "artifact_paths": ARTIFACTS,
            },
        )
    )
    assert passing["status"] == "PASS"
    assert passing["extensions"]["mncs_forge"]["dependency_envelope"]["complete"] is True
    assert failing["status"] == "FAIL"
    assert failing["witnesses"]


def test_graph_impact_returns_transitive_scope_and_missing_claims() -> None:
    base = {
        "record_path": "examples/release-candidate-0.3/assurance-case.json",
        "material_changes": [
            {
                "change_id": "change.component-v2",
                "material": True,
                "affected_claim_ids": ["claim.component"],
            }
        ],
    }
    passing = _provider(
        _request(
            "mncs-assurance-graph-impact",
            {**base, "proposed_scope_claim_ids": ["claim.component", "claim.system"]},
        )
    )
    failing = _provider(
        _request(
            "mncs-assurance-graph-impact",
            {**base, "proposed_scope_claim_ids": ["claim.component"]},
        )
    )
    assert passing["status"] == "PASS"
    assert passing["witnesses"][0]["transitive_affected_claim_ids"] == [
        "claim.component",
        "claim.system",
    ]
    assert failing["status"] == "FAIL"
    assert failing["witnesses"][0]["missing_claim_ids"] == ["claim.system"]


def test_record_dispatch_exact_version_and_no_upgrade_inference() -> None:
    base = {
        "record_path": "examples/release-candidate-0.3/contract-profile.json",
        "kind": "contract",
    }
    passing = _provider(
        _request("mncs-record-dispatch", {**base, "expected_schema_version": "0.3-rc.1"})
    )
    unsupported = _provider(
        _request("mncs-record-dispatch", {**base, "expected_schema_version": "0.3"})
    )
    assert passing["status"] == "PASS"
    assert unsupported["status"] == "UNKNOWN"
    assert (
        "unsupported-or-downgraded-version" in unsupported["extensions"]["unsupported_constructs"]
    )


def test_forge_config_valid_and_discovery_does_not_probe() -> None:
    assert _forge("config", "validate")["ok"] is True
    before = set((ROOT / ".mncs-forge" / "records" / "provider-probes").glob("*.json"))
    discovered = _forge("verifier", "list")
    after = set((ROOT / ".mncs-forge" / "records" / "provider-probes").glob("*.json"))
    assert discovered["configured_count"] == 4
    assert discovered["inspection_executed_providers"] is False
    assert after == before


def test_missing_required_and_optional_unavailable_are_unknown() -> None:
    original = (ROOT / "mncs-forge.toml").read_text()
    missing_required = original.replace(
        '"mncs-record-dispatch",\n]',
        '"mncs-record-dispatch",\n  "missing-required-capability",\n]',
        1,
    )
    optional = """

[[providers]]
id = "optional-unavailable-provider"
name = "Optional unavailable test provider"
command = ["definitely-unavailable-mncs-provider"]
transport = "stdio-jsonl"
required = false
capabilities = ["optional-unavailable-capability"]
limitations = ["test-only unavailable optional provider"]
"""
    with tempfile.NamedTemporaryFile(
        mode="w",
        prefix=".mncs-forge-test-",
        suffix=".toml",
        dir=ROOT,
        delete=False,
    ) as stream:
        stream.write(missing_required + optional)
        stream.flush()
        temporary = Path(stream.name)
    try:
        blockers = _forge("providers", "blockers", config=temporary)
        providers = _forge("providers", "list", config=temporary)
    finally:
        temporary.unlink(missing_ok=True)
    missing = [
        item
        for item in blockers["blockers"]
        if item.get("capability") == "missing-required-capability"
    ]
    optional_provider = next(
        item
        for item in providers["providers"]
        if item["provider_id"] == "optional-unavailable-provider"
    )
    assert blockers["status"] == "UNKNOWN"
    assert missing and missing[0]["status"] == "UNKNOWN"
    assert optional_provider["required"] is False
    assert optional_provider["status"] == "UNKNOWN"


def test_explicit_forge_run_records_ledger_entries() -> None:
    ledger = ROOT / ".mncs-forge" / "ledger.jsonl"
    before = len(ledger.read_text().splitlines()) if ledger.exists() else 0
    result = _forge(
        "verifier",
        "run",
        "artifact.manifest-identity",
        "--parameters",
        json.dumps(
            {
                "manifest_path": ("experimental/integrations/mncs-forge/fixtures/manifest.json"),
                "artifact_paths": ARTIFACTS,
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
    )
    after = len(ledger.read_text().splitlines())
    assert result["status"] == "PASS"
    assert result["evidence_class"] == "development_evidence"
    assert result["independent_evaluation"] is False
    assert after >= before + 2
