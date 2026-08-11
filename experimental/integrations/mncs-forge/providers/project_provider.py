#!/usr/bin/env python3
"""Project-owned bounded Provider Protocol 0.1 micro-verifiers.

The provider answers four narrow development questions. It is non-normative,
operator-controlled, and not an independent MNCS/MNCDS validator or custody system.
"""

# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any, cast

from mncs_validator.assurance import (
    RecordKind,
    material_change_impact,
    parse_time,
    validate_rc_file,
)

PROVIDER = {
    "id": "mncs-project-micro-verifiers",
    "name": "mncs-project-micro-verifiers",
    "identity": "mncs-project-micro-verifiers-v0.1",
    "version": "0.1",
}
METHODS = [
    "evidence-change-impact",
    "artifact-manifest-identity",
    "mncs-assurance-graph-impact",
    "mncs-record-dispatch",
]
MAX_REQUEST_BYTES = 65_536
MAX_OUTPUT_BYTES = 131_072
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_FILES = 64
MAX_TOTAL_FILE_BYTES = 4 * 1024 * 1024
MAX_DEPTH = 8
REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
ALLOWED_ROOTS = (
    "case-studies/edgestream/machine",
    "case-studies/edgestream/build",
    "case-studies/edgestream/evidence",
    "case-studies/edgestream/mncds",
    "examples/release-candidate-0.3",
    "examples/mncds-0.1-rc",
    "experimental/integrations/mncs-forge/fixtures",
)
PROTECTED_ROOTS = (
    "case-studies/edgestream/specification",
    "case-studies/edgestream/reference",
    "case-studies/edgestream/tools",
    "case-studies/edgestream/preregistration.json",
)


class ProviderInputError(ValueError):
    """A bounded caller input is malformed or outside provider authority."""


def _within(path: str, roots: tuple[str, ...]) -> bool:
    return any(path == root or path.startswith(root + "/") for root in roots)


def safe_relative_path(value: object, *, must_exist: bool = True) -> tuple[str, Path]:
    """Normalize one contained, non-protected, regular non-symlink path."""

    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ProviderInputError("path must be a non-empty canonical POSIX relative path")
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or "." in pure.parts:
        raise ProviderInputError("absolute, traversal, and non-canonical paths are forbidden")
    normalized = pure.as_posix()
    if _within(normalized, PROTECTED_ROOTS):
        raise ProviderInputError("protected authority paths are forbidden")
    if not _within(normalized, ALLOWED_ROOTS):
        raise ProviderInputError("path is outside the provider's declared visible roots")
    root = Path.cwd().resolve()
    candidate = root.joinpath(*pure.parts)
    current = root
    for part in pure.parts:
        current /= part
        if current.is_symlink():
            raise ProviderInputError("symlink paths are forbidden")
    try:
        resolved = candidate.resolve(strict=must_exist)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise ProviderInputError("path is unavailable or escapes the provider workspace") from exc
    if must_exist and not resolved.is_file():
        raise ProviderInputError("path must identify a regular file")
    return normalized, resolved


def bounded_json_value(value: object, *, depth: int = 0) -> None:
    """Reject excessive question-parameter depth or collection size."""

    if depth > MAX_DEPTH:
        raise ProviderInputError("JSON input exceeds the depth bound")
    if value is None or isinstance(value, (bool, int, float)):
        return
    if isinstance(value, str):
        if len(value) > 4096:
            raise ProviderInputError("JSON string exceeds the length bound")
        return
    if isinstance(value, list):
        if len(value) > 128:
            raise ProviderInputError("JSON array exceeds the item bound")
        for item in value:
            bounded_json_value(item, depth=depth + 1)
        return
    if isinstance(value, dict):
        if len(value) > 128 or not all(
            isinstance(key, str) and 0 < len(key) <= 128 for key in value
        ):
            raise ProviderInputError("JSON object exceeds the key bound")
        for item in value.values():
            bounded_json_value(item, depth=depth + 1)
        return
    raise ProviderInputError("question parameters must be JSON values")


def load_json_path(value: object) -> tuple[str, Path, dict[str, Any]]:
    """Read one bounded JSON object from an allowed path."""

    relative, path = safe_relative_path(value)
    size = path.stat().st_size
    if size > MAX_JSON_BYTES:
        raise ProviderInputError("JSON record exceeds the byte bound")
    try:
        result = json.loads(path.read_bytes())
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProviderInputError("JSON record is unreadable or malformed") from exc
    if not isinstance(result, dict):
        raise ProviderInputError("JSON record root must be an object")
    bounded_json_value(result)
    return relative, path, cast(dict[str, Any], result)


def parameters(request: dict[str, Any]) -> dict[str, Any]:
    """Return the Forge question-parameter object."""

    extensions = request.get("extensions")
    forge = extensions.get("mncs_forge") if isinstance(extensions, dict) else None
    result = forge.get("question_parameters") if isinstance(forge, dict) else None
    if not isinstance(result, dict):
        raise ProviderInputError("mncs_forge.question_parameters must be an object")
    bounded_json_value(result)
    return cast(dict[str, Any], result)


def response(
    request: dict[str, Any],
    status: str,
    summary: str,
    *,
    witnesses: list[object] | None = None,
    limitations: list[str] | None = None,
    unsupported: list[str] | None = None,
    dependency_paths: list[str] | None = None,
    dependency_identities: dict[str, str] | None = None,
    complete: bool = False,
    assumptions: list[str] | None = None,
) -> dict[str, object]:
    """Build one strict analysis response with an explicit dependency envelope."""

    return {
        "protocol_version": "0.1",
        "type": "analysis_response",
        "request_id": request["request_id"],
        "provider": PROVIDER,
        "status": status,
        "summary": summary,
        "witnesses": witnesses or [],
        "limitations": limitations or [],
        "extensions": {
            "unsupported_constructs": unsupported or [],
            "mncs_forge": {
                "assumptions": assumptions or [],
                "dependency_envelope": {
                    "paths": dependency_paths or [],
                    "identities": dependency_identities or {},
                    "complete": complete,
                },
            },
        },
    }


def error_response(request_id: str, code: str, message: str) -> dict[str, object]:
    """Build a protocol error for malformed framing or request authority."""

    return {
        "protocol_version": "0.1",
        "type": "error",
        "request_id": request_id,
        "provider": PROVIDER,
        "code": code,
        "message": message,
        "extensions": {},
    }


def path_overlap(first: str, second: str) -> bool:
    """Return whether either normalized path contains the other."""

    return first == second or first.startswith(second + "/") or second.startswith(first + "/")


def evidence_change_impact(request: dict[str, Any]) -> dict[str, object]:
    """Compare explicit changed paths with a caller-declared bounded envelope."""

    component = request.get("component")
    changed = component.get("changed_paths") if isinstance(component, dict) else None
    dependency_values = parameters(request).get("dependency_paths")
    if (
        not isinstance(changed, list)
        or not isinstance(dependency_values, list)
        or not dependency_values
        or len(changed) > MAX_FILES
        or len(dependency_values) > MAX_FILES
    ):
        return response(
            request,
            "UNKNOWN",
            "the declared dependency envelope is missing or outside bounds",
            unsupported=["missing-or-unbounded-dependency-envelope"],
            limitations=["dependency_paths must be a non-empty bounded list"],
        )
    try:
        changed_paths = [safe_relative_path(item)[0] for item in changed]
        dependency_paths = [safe_relative_path(item)[0] for item in dependency_values]
    except ProviderInputError as exc:
        return response(
            request,
            "UNKNOWN",
            "path impact could not be established",
            unsupported=["unsupported-path"],
            limitations=[str(exc)],
        )
    overlap = sorted(
        path
        for path in changed_paths
        if any(path_overlap(path, dependency) for dependency in dependency_paths)
    )
    if overlap:
        return response(
            request,
            "FAIL",
            "a changed path intersects the declared evidence dependency envelope",
            witnesses=[{"affected_path": item} for item in overlap],
            dependency_paths=dependency_paths,
            complete=False,
            assumptions=["dependency_paths names the caller's intended bounded envelope"],
        )
    return response(
        request,
        "PASS",
        "no changed path intersects the declared evidence dependency envelope",
        limitations=[
            "path separation does not prove semantic or whole-program independence",
            "an incomplete caller envelope cannot prove evidence independence",
        ],
        dependency_paths=dependency_paths,
        complete=False,
        assumptions=["dependency_paths names the caller's intended bounded envelope"],
    )


def ordered_manifest_digest(artifacts: list[dict[str, object]]) -> str:
    """Digest ordered manifest identity tuples deterministically."""

    payload = json.dumps(artifacts, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def artifact_manifest_identity(request: dict[str, Any]) -> dict[str, object]:
    """Compare bounded artifact bytes and order with a declared manifest."""

    values = parameters(request)
    try:
        manifest_relative, _, manifest = load_json_path(values.get("manifest_path"))
    except ProviderInputError as exc:
        return response(
            request,
            "UNKNOWN",
            "the artifact manifest is unavailable or unsupported",
            unsupported=["manifest-unavailable"],
            limitations=[str(exc)],
        )
    artifacts = manifest.get("artifacts")
    supplied = values.get("artifact_paths")
    if (
        manifest.get("schema_version") != "0.1"
        or not isinstance(artifacts, list)
        or not artifacts
        or len(artifacts) > MAX_FILES
        or not isinstance(supplied, list)
        or len(supplied) != len(artifacts)
    ):
        return response(
            request,
            "UNKNOWN",
            "the manifest structure or supplied artifact set is unsupported",
            unsupported=["unsupported-manifest-shape"],
            dependency_paths=[manifest_relative],
            limitations=["version 0.1 and one to 64 ordered artifacts are required"],
        )
    actual: list[dict[str, object]] = []
    dependency_paths = [manifest_relative]
    total = 0
    try:
        for index, raw in enumerate(artifacts):
            if not isinstance(raw, dict):
                raise ProviderInputError("manifest artifact entry must be an object")
            relative, path = safe_relative_path(raw.get("path"))
            supplied_relative, _ = safe_relative_path(supplied[index])
            if relative != supplied_relative:
                raise ProviderInputError("supplied artifact order differs from the manifest")
            size = path.stat().st_size
            total += size
            if total > MAX_TOTAL_FILE_BYTES:
                raise ProviderInputError("artifact bytes exceed the aggregate bound")
            digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
            actual.append({"path": relative, "size": size, "sha256": digest})
            dependency_paths.append(relative)
    except (OSError, ProviderInputError) as exc:
        return response(
            request,
            "UNKNOWN",
            "artifact identity material is unavailable or unsupported",
            unsupported=["artifact-unavailable"],
            dependency_paths=dependency_paths,
            limitations=[str(exc)],
        )
    declared = [
        {
            "path": item.get("path"),
            "size": item.get("size"),
            "sha256": item.get("sha256"),
        }
        for item in cast(list[dict[str, Any]], artifacts)
    ]
    actual_ordered_digest = ordered_manifest_digest(actual)
    declared_ordered_digest = manifest.get("ordered_digest")
    mismatches = [
        {"index": index, "declared": declared_item, "actual": actual_item}
        for index, (declared_item, actual_item) in enumerate(zip(declared, actual, strict=True))
        if declared_item != actual_item
    ]
    if declared_ordered_digest != actual_ordered_digest:
        mismatches.append(
            {
                "field": "ordered_digest",
                "declared": declared_ordered_digest,
                "actual": actual_ordered_digest,
            }
        )
    if mismatches:
        return response(
            request,
            "FAIL",
            "artifact identities do not agree with the declared manifest",
            witnesses=mismatches[:16],
            dependency_paths=dependency_paths,
            complete=True,
            limitations=["identity agreement would not establish artifact truth or adequacy"],
        )
    return response(
        request,
        "PASS",
        "ordered artifact paths, sizes, digests, and manifest digest agree",
        witnesses=[{"ordered_digest": actual_ordered_digest, "artifact_count": len(actual)}],
        dependency_paths=dependency_paths,
        complete=True,
        limitations=["identity agreement does not establish artifact truth or adequacy"],
    )


def assurance_graph_impact(request: dict[str, Any]) -> dict[str, object]:
    """Compute current-Python-family graph impact, not a second validator."""

    values = parameters(request)
    try:
        relative, path, record = load_json_path(values.get("record_path"))
    except ProviderInputError as exc:
        return response(
            request,
            "UNKNOWN",
            "the assurance record is unavailable or unsupported",
            unsupported=["assurance-record-unavailable"],
            limitations=[str(exc)],
        )
    if record.get("schema_version") != "0.3-rc.1":
        return response(
            request,
            "UNKNOWN",
            "the assurance record version is unsupported",
            unsupported=["unsupported-assurance-version"],
            dependency_paths=[relative],
        )
    report = validate_rc_file(path, "assurance")
    if not report.valid:
        return response(
            request,
            "FAIL",
            "the supplied assurance record is invalid",
            witnesses=[
                {
                    "category": report.category,
                    "issue_codes": sorted({item.code for item in report.issues + report.warnings}),
                }
            ],
            dependency_paths=[relative],
            complete=True,
            limitations=["invalid input is an analysis FAIL, not MNCS conformance FAIL"],
        )
    changes = values.get("material_changes")
    proposed = values.get("proposed_scope_claim_ids")
    if (
        not isinstance(changes, list)
        or not isinstance(proposed, list)
        or len(changes) > 64
        or len(proposed) > 128
        or not all(isinstance(item, dict) for item in changes)
        or not all(isinstance(item, str) for item in proposed)
    ):
        return response(
            request,
            "UNKNOWN",
            "material changes or proposed scope are unsupported",
            unsupported=["unsupported-change-scope-shape"],
            dependency_paths=[relative],
        )
    dependencies = record.get("dependencies")
    if not isinstance(dependencies, list) or not all(
        isinstance(item, dict) for item in dependencies
    ):
        return response(
            request,
            "UNKNOWN",
            "the assurance dependency graph is unsupported",
            unsupported=["unsupported-dependency-graph"],
            dependency_paths=[relative],
        )
    direct, closure = material_change_impact(
        cast(list[dict[str, Any]], changes),
        cast(list[dict[str, Any]], dependencies),
    )
    proposed_set = set(cast(list[str], proposed))
    missing = closure - proposed_set
    witness = {
        "direct_affected_claim_ids": sorted(direct),
        "transitive_affected_claim_ids": sorted(closure),
        "proposed_scope_claim_ids": sorted(proposed_set),
        "missing_claim_ids": sorted(missing),
    }
    if missing:
        return response(
            request,
            "FAIL",
            "the proposed revalidation scope omits graph-affected claims",
            witnesses=[witness],
            dependency_paths=[relative],
            complete=True,
            limitations=[
                "same Python implementation family; this is development evidence, "
                "not independent verification",
                "undeclared real dependencies remain outside the computed closure",
            ],
        )
    return response(
        request,
        "PASS",
        "the proposed scope covers the bounded required graph-impact closure",
        witnesses=[witness],
        dependency_paths=[relative],
        complete=True,
        limitations=[
            "same Python implementation family; this is development evidence, "
            "not independent verification",
            "this method does not perform a second MNCS validation",
        ],
    )


def record_dispatch(request: dict[str, Any]) -> dict[str, object]:
    """Check exact public-validator kind/version dispatch without upgrading."""

    values = parameters(request)
    kind = values.get("kind")
    if kind not in {"contract", "assurance", "threat", "measurement"}:
        return response(
            request,
            "UNKNOWN",
            "the requested record kind is unsupported",
            unsupported=["unsupported-record-kind"],
        )
    try:
        relative, path, record = load_json_path(values.get("record_path"))
    except ProviderInputError as exc:
        return response(
            request,
            "UNKNOWN",
            "the record is unavailable or unsupported",
            unsupported=["record-unavailable"],
            limitations=[str(exc)],
        )
    expected = values.get("expected_schema_version", "0.3-rc.1")
    actual = record.get("schema_version")
    if actual != expected or expected != "0.3-rc.1":
        return response(
            request,
            "UNKNOWN",
            "the exact schema version is unsupported or a downgrade substitution",
            witnesses=[{"kind": kind, "expected_version": expected, "actual_version": actual}],
            unsupported=["unsupported-or-downgraded-version"],
            dependency_paths=[relative],
            complete=True,
            limitations=["a changed version string is never inferred to be an upgrade"],
        )
    evaluation_time = parse_time(values.get("evaluation_time"))
    report = validate_rc_file(path, cast(RecordKind, kind), at=evaluation_time)
    witness = {
        "kind": kind,
        "schema_version": actual,
        "dispatch_category": report.category,
        "issue_codes": sorted({item.code for item in report.issues + report.warnings}),
    }
    if report.category == "UNSUPPORTED":
        return response(
            request,
            "UNKNOWN",
            "public validator dispatch reports unsupported",
            witnesses=[witness],
            unsupported=["public-validator-unsupported"],
            dependency_paths=[relative],
            complete=True,
        )
    if report.category == "INVALID":
        return response(
            request,
            "FAIL",
            "public validator dispatch reports invalid input",
            witnesses=[witness],
            dependency_paths=[relative],
            complete=True,
            limitations=["dispatch FAIL means invalid input, not an MNCS conformance FAIL"],
        )
    return response(
        request,
        "PASS",
        "the record uses an exact supported kind and schema version",
        witnesses=[witness],
        dependency_paths=[relative],
        complete=True,
        limitations=[
            "dispatch support does not establish record adequacy, independence, or promotion"
        ],
    )


def capabilities(request: dict[str, Any]) -> dict[str, object]:
    """Return deterministic provider capabilities without analysis."""

    return {
        "protocol_version": "0.1",
        "type": "capabilities",
        "request_id": request["request_id"],
        "provider": PROVIDER,
        "analyses": METHODS,
        "statuses": ["PASS", "FAIL", "UNKNOWN"],
        "cancellation": False,
        "health_checks": False,
        "extensions": {
            "supported_constructs": [
                "bounded-path-envelope",
                "bounded-manifest-identity",
                "mncs-0.3-required-graph-impact",
                "mncs-0.3-exact-record-dispatch",
            ],
            "unsupported_constructs": [
                "whole-program-semantic-independence",
                "organizational-independence",
                "protected-custody",
                "arbitrary-executables",
                "network-evidence",
            ],
            "limitations": [
                "project-owned non-normative development provider",
                "no method establishes MNCS/MNCDS conformance or promotion",
            ],
        },
    }


def handle(request: dict[str, Any]) -> dict[str, object]:
    """Validate request identity/type/method and dispatch exactly one operation."""

    request_id = request.get("request_id")
    if request.get("protocol_version") != "0.1":
        return error_response(
            str(request_id or "invalid"), "UNSUPPORTED_PROTOCOL", "protocol_version must be 0.1"
        )
    if not isinstance(request_id, str) or REQUEST_ID.fullmatch(request_id) is None:
        return error_response("invalid", "INVALID_REQUEST_ID", "request_id is invalid")
    request_type = request.get("type")
    if request_type == "capabilities":
        return capabilities(request)
    if request_type != "analysis_request":
        return error_response(request_id, "UNSUPPORTED_REQUEST", "request type is unsupported")
    method = request.get("analysis")
    functions = {
        "evidence-change-impact": evidence_change_impact,
        "artifact-manifest-identity": artifact_manifest_identity,
        "mncs-assurance-graph-impact": assurance_graph_impact,
        "mncs-record-dispatch": record_dispatch,
    }
    function = functions.get(method)
    if function is None:
        return response(
            request,
            "UNKNOWN",
            "the requested analysis method is unsupported",
            unsupported=["unsupported-method"],
        )
    try:
        return function(request)
    except ProviderInputError as exc:
        return response(
            request,
            "UNKNOWN",
            "the request is outside the provider's bounded input subset",
            unsupported=["unsupported-input"],
            limitations=[str(exc)],
        )
    except (OSError, UnicodeError, ValueError) as exc:
        return response(
            request,
            "UNKNOWN",
            "the provider encountered a bounded operational input error",
            limitations=[type(exc).__name__],
            unsupported=["operational-input-error"],
        )


def emit(result: dict[str, object]) -> int:
    """Emit exactly one bounded canonical response line."""

    encoded = json.dumps(result, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
    if len(encoded) > MAX_OUTPUT_BYTES:
        encoded = (
            json.dumps(
                error_response(
                    str(result.get("request_id", "invalid")),
                    "OUTPUT_LIMIT",
                    "provider response exceeded its output bound",
                ),
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            + b"\n"
        )
    sys.stdout.buffer.write(encoded)
    return 0


def main() -> int:
    """Read exactly one newline-terminated request and emit exactly one response."""

    raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
    if len(raw) > MAX_REQUEST_BYTES:
        return emit(error_response("invalid", "REQUEST_LIMIT", "request exceeds byte bound"))
    if not raw.endswith(b"\n") or raw.count(b"\n") != 1:
        return emit(
            error_response(
                "invalid",
                "FRAMING",
                "exactly one newline-terminated JSON request is required",
            )
        )
    try:
        request = json.loads(raw)
    except (UnicodeError, json.JSONDecodeError):
        return emit(error_response("invalid", "MALFORMED_JSON", "request is not valid JSON"))
    if not isinstance(request, dict):
        return emit(error_response("invalid", "MALFORMED_REQUEST", "request must be an object"))
    try:
        bounded_json_value(request)
        result = handle(cast(dict[str, Any], request))
    except ProviderInputError as exc:
        result = error_response("invalid", "REQUEST_LIMIT", str(exc))
    return emit(result)


if __name__ == "__main__":
    raise SystemExit(main())
