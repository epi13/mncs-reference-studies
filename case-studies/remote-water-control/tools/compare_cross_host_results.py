#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    host_files = sorted(args.input.rglob("host-identity.json"))
    observations: list[dict[str, Any]] = []
    for host_path in host_files:
        summary_path = (
            host_path.parent
            / "case-studies"
            / "remote-water-control"
            / "evidence"
            / "results"
            / "study-summary.json"
        )
        if not summary_path.exists():
            candidates = list(host_path.parent.rglob("study-summary.json"))
            if len(candidates) != 1:
                raise SystemExit(f"unable to resolve one study summary beside {host_path}")
            summary_path = candidates[0]
        host = load(host_path)
        summary = load(summary_path)
        observations.append(
            {
                "declared_architecture": host.get("declared_architecture"),
                "machine": host.get("machine"),
                "platform": host.get("platform"),
                "python": host.get("python"),
                "study_sha256": canonical_sha256(summary),
                "development_result": summary.get("development_result"),
                "formal_mncs_status": summary.get("formal_mncs_status"),
                "formal_mncds_status": summary.get("formal_mncds_status"),
            }
        )

    architectures = {item["declared_architecture"] for item in observations}
    study_hashes = {item["study_sha256"] for item in observations}
    checks = {
        "two_hosts_present": len(observations) == 2,
        "x86_64_and_arm64_present": architectures == {"x86_64", "arm64"},
        "development_results_pass": all(
            item["development_result"] == "PASS" for item in observations
        ),
        "formal_claims_remain_unknown": all(
            item["formal_mncs_status"] == "UNKNOWN" and item["formal_mncds_status"] == "UNKNOWN"
            for item in observations
        ),
        "semantic_evidence_identical": len(study_hashes) == 1,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    result = {
        "schema_version": "0.1",
        "comparison_id": "mncs.remote-water.cross-host.development-1",
        "status": status,
        "checks": {key: "PASS" if value else "FAIL" for key, value in checks.items()},
        "hosts": observations,
        "limitations": [
            (
                "Matching hosted-runner evidence is cross-host development "
                "reproducibility, not independent protected holdout evidence."
            ),
            (
                "This comparison does not establish domain review, release binding, "
                "operational monitoring, or physical-system validity."
            ),
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
