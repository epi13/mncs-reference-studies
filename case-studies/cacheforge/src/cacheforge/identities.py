from __future__ import annotations

import hashlib
from pathlib import Path

CASE_ROOT = Path(__file__).resolve().parents[2]
IDENTITY_PATHS = (
    "epoch-2-evidence-amendment.json",
    "epoch-2-preregistration.json",
    "generator/policy-spec.json",
    "machine/generated_policy.py",
    "protected-trace-bundle.schema.json",
    "src/cacheforge/authority.py",
    "src/cacheforge/epoch2.py",
    "src/cacheforge/identities.py",
    "src/cacheforge/model.py",
    "src/cacheforge/policies.py",
    "src/cacheforge/scenarios.py",
    "src/cacheforge/simulator.py",
    "src/cacheforge/study.py",
    "src/cacheforge/trace_bundle.py",
    "tools/run_epoch2.py",
    "tools/run_protected_evaluation.py",
)


def collect_artifact_identities() -> dict[str, object]:
    artifacts = {}
    for relative_path in IDENTITY_PATHS:
        payload = (CASE_ROOT / relative_path).read_bytes()
        artifacts[relative_path] = f"sha256:{hashlib.sha256(payload).hexdigest()}"
    return {
        "algorithm": "sha256",
        "artifacts": artifacts,
        "runtime_contract": {
            "language": "Python",
            "minimum_version": "3.11",
            "random_protocol": "integer-seeded random.Random workload generation",
            "serialization": "UTF-8 JSON with sorted keys and two-space indentation",
        },
    }
