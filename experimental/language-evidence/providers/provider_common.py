"""Deterministic bounded Provider Protocol 0.1 helper."""

from __future__ import annotations

import hashlib
import json
import sys
import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProviderDefinition:
    language: str
    provider_id: str
    version: str
    analysis_id: str
    configuration_id: str
    fail_tokens: tuple[str, ...]
    unknown_tokens: tuple[str, ...]
    limitations: tuple[str, ...]


def identity(d: ProviderDefinition) -> dict[str, str]:
    return {"id": d.provider_id, "version": d.version, "configuration_id": d.configuration_id}


def error(d: ProviderDefinition, code: str, summary: str) -> dict[str, Any]:
    return {
        "protocol_version": "0.1",
        "type": "error",
        "request_id": "unknown",
        "provider": identity(d),
        "summary": summary,
        "extensions": {"mncs.dev:error_code": code},
    }


def witness(kind: str, token: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "summary": f"bounded provider matched {token!r}",
        "locations": ["component.source_text"],
        "data": {"token": token},
    }


def analyze(d: ProviderDefinition, request: dict[str, Any]) -> dict[str, Any]:
    component = request.get("component")
    if not isinstance(component, dict):
        return error(d, "invalid_request", "component must be an object")
    source = component.get("source_text")
    if not isinstance(source, str):
        return error(d, "invalid_request", "source_text must be a string")
    if component.get("language") != d.language:
        return error(d, "environment_mismatch", "language does not match provider")

    extensions = request.get("extensions", {})
    simulation = extensions.get("mncs.dev:simulate") if isinstance(extensions, dict) else None
    if simulation == "crash":
        raise RuntimeError("simulated provider crash")
    if simulation == "timeout":
        time.sleep(5)

    unknown = next((token for token in d.unknown_tokens if token in source), None)
    failure = next((token for token in d.fail_tokens if token in source), None)
    status = "UNKNOWN" if unknown else "FAIL" if failure else "PASS"
    unsupported = [f"unsupported token {unknown!r}"] if unknown else []
    counterexamples = [witness("detected_violation", failure)] if failure else []
    witnesses = [] if unknown or failure else [witness("bounded_absence", "fail tokens")]
    limits = list(d.limitations)
    if unknown:
        limits.append("unsupported construct prevents decision")
    if status == "PASS":
        limits.append("PASS is limited to the declared invariant")

    source_bytes = source.encode()
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    basis = {
        "provider": identity(d),
        "source": source_hash,
        "status": status,
        "subject": component.get("subject_id"),
        "contract": component.get("contract_id"),
        "environment": component.get("environment_id"),
    }
    canonical = json.dumps(basis, sort_keys=True, separators=(",", ":")).encode()
    evidence_hash = "sha256:" + hashlib.sha256(canonical).hexdigest()
    result = {
        "schema_version": "0.1-experimental",
        "result_id": f"result:{d.language}:{evidence_hash[7:23]}",
        "invariant_id": d.analysis_id,
        "status": status,
        "mode": "evaluator",
        "evidence_partition": str(component.get("evidence_partition", "development")),
        "subject_id": str(component.get("subject_id", "subject:unknown")),
        "contract_id": str(component.get("contract_id", "contract:unknown")),
        "analyzer_id": d.provider_id,
        "analyzer_version": d.version,
        "configuration_id": d.configuration_id,
        "environment_id": str(component.get("environment_id", "environment:unknown")),
        "method": "bounded deterministic source token scan",
        "bounded": True,
        "required_semantics_complete": status != "UNKNOWN",
        "facts_examined": [
            {
                "kind": "source_text",
                "identity": f"source:{source_hash[:24]}",
                "location": "component.source_text",
                "support": "unsupported" if unknown else "bounded",
            }
        ],
        "assumptions": ["source_text is the complete declared subject"],
        "unsupported_constructs": unsupported,
        "witnesses": witnesses,
        "counterexamples": counterexamples,
        "resource_usage": {
            "wall_seconds": 0.0,
            "peak_memory_bytes": None,
            "input_bytes": len(source_bytes),
        },
        "limitations": limits,
        "evidence_hash": evidence_hash,
        "extensions": {"mncs.dev:language": d.language},
    }
    return {
        "protocol_version": "0.1",
        "type": "analysis_response",
        "request_id": str(request.get("request_id", "unknown")),
        "provider": identity(d),
        "status": status,
        "summary": f"{status}: bounded {d.language} source analysis",
        "witnesses": [*witnesses, *counterexamples],
        "limitations": limits,
        "extensions": {"mncs.dev:analyzer_result": result},
    }


def dispatch(d: ProviderDefinition, request: dict[str, Any]) -> dict[str, Any]:
    request_type = request.get("type")
    if request_type == "capabilities":
        return {
            "protocol_version": "0.1",
            "type": "capabilities",
            "request_id": str(request.get("request_id", "unknown")),
            "provider": identity(d),
            "analyses": [d.analysis_id],
            "statuses": ["PASS", "FAIL", "UNKNOWN"],
            "cancellation": False,
            "health_checks": True,
            "extensions": {"mncs.dev:execution": "explicit-only"},
        }
    if request_type == "analysis_request" and request.get("analysis") == d.analysis_id:
        return analyze(d, request)
    if request_type == "analysis_request":
        return {
            "protocol_version": "0.1",
            "type": "analysis_response",
            "request_id": str(request.get("request_id", "unknown")),
            "provider": identity(d),
            "status": "UNKNOWN",
            "summary": "UNKNOWN: analysis is unsupported",
            "witnesses": [],
            "limitations": ["requested analysis is not declared"],
            "extensions": {"mncs.dev:unsupported_analysis": request.get("analysis")},
        }
    return error(d, "invalid_request", "unsupported request")


def run(d: ProviderDefinition) -> int:
    first = sys.stdin.buffer.readline()
    if not first or sys.stdin.buffer.readline():
        print(json.dumps(error(d, "invalid_invocation", "one request required")))
        return 0
    try:
        request = json.loads(first)
        if not isinstance(request, dict) or request.get("protocol_version") != "0.1":
            response = error(d, "invalid_request", "invalid protocol request")
        else:
            response = dispatch(d, request)
        print(json.dumps(response, sort_keys=True, separators=(",", ":")))
        return 0
    except Exception as exc:
        print(f"provider operational failure: {exc}", file=sys.stderr)
        return 70
