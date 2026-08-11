from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from cacheforge.epoch2 import summarize_policy_results
from cacheforge.identities import collect_artifact_identities
from cacheforge.model import RequestTrace
from cacheforge.policies import EvictionPolicy, ReferenceLRU, SegmentedLRU
from cacheforge.scenarios import Scenario
from cacheforge.study import evaluate_policy

CASE_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = CASE_ROOT / "protected-trace-bundle.schema.json"
MAX_SCENARIOS = 256
MAX_REQUESTS = 10_000


@dataclass(frozen=True)
class TraceBundle:
    bundle_id: str
    input_digest: str
    scenarios: tuple[Scenario, ...]


def _require_mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return value


def _require_list(value: object, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be an array")
    return value


@lru_cache(maxsize=1)
def _trace_bundle_validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _validate_schema(payload: object) -> None:
    try:
        _trace_bundle_validator().validate(payload)
    except ValidationError as exc:
        location = ".".join(str(part) for part in exc.absolute_path) or "root"
        raise ValueError(
            f"trace bundle schema validation failed at {location}: {exc.message}"
        ) from exc


def load_trace_bundle(path: Path) -> TraceBundle:
    raw = path.read_bytes()
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"trace bundle is not valid JSON: {exc.msg}") from exc
    _validate_schema(decoded)
    payload = _require_mapping(decoded, "trace bundle")

    bundle_id = payload["bundle_id"]
    assert isinstance(bundle_id, str)
    raw_scenarios = _require_list(payload["scenarios"], "scenarios")
    if len(raw_scenarios) > MAX_SCENARIOS:
        raise ValueError("scenario count is outside the allowed range")

    scenarios: list[Scenario] = []
    seen_scenario_ids: set[str] = set()
    total_requests = 0

    for raw_scenario in raw_scenarios:
        scenario_payload = _require_mapping(raw_scenario, "scenario")
        scenario_id = scenario_payload["scenario_id"]
        assert isinstance(scenario_id, str)
        if scenario_id in seen_scenario_ids:
            raise ValueError(f"duplicate scenario_id: {scenario_id}")
        seen_scenario_ids.add(scenario_id)

        capacity_blocks = scenario_payload["capacity_blocks"]
        assert isinstance(capacity_blocks, int) and not isinstance(capacity_blocks, bool)
        raw_requests = _require_list(scenario_payload["requests"], "requests")

        requests: list[RequestTrace] = []
        seen_request_ids: set[str] = set()
        for raw_request in raw_requests:
            request_payload = _require_mapping(raw_request, "request")
            request_id = request_payload["request_id"]
            assert isinstance(request_id, str)
            if request_id in seen_request_ids:
                raise ValueError(f"duplicate request_id in scenario {scenario_id}: {request_id}")
            seen_request_ids.add(request_id)

            prompt_blocks = _require_list(request_payload["prompt_blocks"], "prompt_blocks")
            generated_blocks = request_payload["generated_blocks"]
            priority = request_payload.get("priority", 1)
            cancel_after = request_payload.get("cancel_after_generated")
            assert isinstance(generated_blocks, int) and not isinstance(generated_blocks, bool)
            assert isinstance(priority, int) and not isinstance(priority, bool)
            assert cancel_after is None or (
                isinstance(cancel_after, int) and not isinstance(cancel_after, bool)
            )

            requests.append(
                RequestTrace(
                    request_id=request_id,
                    prompt_blocks=tuple(str(block) for block in prompt_blocks),
                    generated_blocks=generated_blocks,
                    priority=priority,
                    cancel_after_generated=cancel_after,
                )
            )

        total_requests += len(requests)
        if total_requests > MAX_REQUESTS:
            raise ValueError("trace bundle exceeds the request limit")

        purpose = scenario_payload.get("purpose", "external protected evaluation")
        assert isinstance(purpose, str)
        scenarios.append(
            Scenario(
                scenario_id=scenario_id,
                capacity_blocks=capacity_blocks,
                requests=tuple(requests),
                purpose=purpose,
            )
        )

    digest = hashlib.sha256(raw).hexdigest()
    return TraceBundle(
        bundle_id=bundle_id,
        input_digest=f"sha256:{digest}",
        scenarios=tuple(scenarios),
    )


def evaluate_trace_bundle(
    bundle: TraceBundle,
    candidate_factory: Callable[[], EvictionPolicy],
) -> dict[str, object]:
    lru = evaluate_policy(ReferenceLRU, bundle.scenarios)
    segmented = evaluate_policy(SegmentedLRU, bundle.scenarios)
    candidate = evaluate_policy(candidate_factory, bundle.scenarios)
    observations = summarize_policy_results(
        bundle.scenarios,
        lru,
        segmented,
        candidate,
    )
    return {
        "schema_version": "0.3",
        "study_id": "mncs.cacheforge.kv-cache.protected-evaluation.v1",
        "mode": "external-trace-bundle",
        "bundle_id": bundle.bundle_id,
        "input_bundle_digest": bundle.input_digest,
        "schema_valid": True,
        "protocol_eligible": "NOT_ESTABLISHED",
        "custody_verified": "NOT_ESTABLISHED",
        "observed_development_gate_result": observations["status"],
        "observed_gate_result": observations["status"],
        "evaluation_result": "REVIEW_REQUIRED",
        "formal_mncs_status": "UNKNOWN",
        "formal_mncds_status": "UNKNOWN",
        "disposition": "REVIEW_REQUIRED",
        "promotion_authorized": False,
        "candidate_id": candidate.policy_id,
        "baseline_ids": [lru.policy_id, segmented.policy_id],
        "scenario_count": len(bundle.scenarios),
        "request_count": sum(len(scenario.requests) for scenario in bundle.scenarios),
        "distinct_capacity_count": len({scenario.capacity_blocks for scenario in bundle.scenarios}),
        "artifact_identities": collect_artifact_identities(),
        **observations,
        "limitations": [
            "The evaluator records numerical observations but cannot establish eligibility.",
            "Trace custody and independence must be reviewed outside this process.",
            "A schema-valid bundle is not automatically a protected protocol-qualified bundle.",
            "A real inference-server adapter and accelerator evidence remain outstanding.",
        ],
    }
