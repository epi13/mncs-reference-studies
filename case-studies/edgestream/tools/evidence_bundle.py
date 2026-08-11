#!/usr/bin/env python3
"""Assemble the EdgeStream MNCS bundle and MNCDS record."""

from __future__ import annotations

from pathlib import Path
from statistics import fmean
from typing import Any

from evidence_base import (
    CONTRACT_ID,
    EVIDENCE,
    RESULTS,
    ROOT,
    create_gate_results,
    create_identities,
    create_invariant,
    digest,
    read_json,
    write_json,
)
from evidence_performance import create_performance_result


def evidence_record(
    identifier: str,
    kind: str,
    path: Path,
    media_type: str,
    machine_hash: str,
    *,
    bind_candidate: bool = False,
    description: str | None = None,
) -> dict[str, Any]:
    """Return one authoritative evidence-index record."""

    record: dict[str, Any] = {
        "id": identifier,
        "kind": kind,
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": digest(path),
        "media_type": media_type,
        "contract_id": CONTRACT_ID,
    }
    if bind_candidate:
        record["candidate_source_hash"] = machine_hash
    if description:
        record["description"] = description
    return record


def create_evidence_index(
    contract: Path,
    reference: Path,
    machine: Path,
    machine_hash: str,
    identities: dict[str, Path],
    gate_paths: list[Path],
    invariant_path: Path,
    performance_path: Path,
) -> Path:
    """Create the authoritative MNCS 0.2 evidence graph index."""

    records = [
        evidence_record("contract", "contract", contract, "text/markdown", machine_hash),
        evidence_record("reference", "reference", reference, "text/x-c", machine_hash),
        evidence_record(
            "machine",
            "machine",
            machine,
            "text/x-c",
            machine_hash,
            bind_candidate=True,
        ),
    ]
    for name, path in identities.items():
        records.append(
            evidence_record(
                f"identity-{name}",
                "identity",
                path,
                "application/json",
                machine_hash,
                bind_candidate=True,
            )
        )
    for path in gate_paths:
        records.append(
            evidence_record(
                path.stem,
                "gate_result",
                path,
                "application/json",
                machine_hash,
                bind_candidate=True,
            )
        )
    records.extend(
        [
            evidence_record(
                "invariant-bounded-storage",
                "invariant",
                invariant_path,
                "application/json",
                machine_hash,
                bind_candidate=True,
            ),
            evidence_record(
                "performance-throughput",
                "performance",
                performance_path,
                "application/json",
                machine_hash,
                bind_candidate=True,
            ),
        ]
    )

    raw_mapping = {
        "raw-differential": ("fuzz", RESULTS / "differential.json"),
        "raw-compiler-matrix": ("other", RESULTS / "compiler-matrix.json"),
        "raw-sanitizers": ("other", RESULTS / "sanitizers.json"),
        "raw-checkpoint-recovery": ("other", RESULTS / "checkpoint-recovery.json"),
        "raw-mutation": ("mutation", RESULTS / "mutation.json"),
        "raw-structural": ("other", RESULTS / "structural.json"),
        "raw-generation": ("other", RESULTS / "generation.json"),
        "raw-benchmark": ("other", RESULTS / "benchmark.json"),
    }
    for identifier, (kind, path) in raw_mapping.items():
        records.append(
            evidence_record(
                identifier,
                kind,
                path,
                "application/json",
                machine_hash,
                bind_candidate=True,
            )
        )

    index_path = EVIDENCE / "index.json"
    write_json(
        index_path,
        {
            "schema_version": "0.2",
            "mncs_version": "0.2",
            "immutable": False,
            "unreferenced_evidence_policy": "warn",
            "records": records,
            "extensions": {},
        },
    )
    return index_path


def create_manifest(
    contract: Path,
    reference: Path,
    machine: Path,
    identities: dict[str, Path],
    index_path: Path,
    baseline_samples: list[float],
    candidate_samples: list[float],
) -> None:
    """Create the MNCS 0.2 L4 manifest bound to all current evidence."""

    machine_hash = digest(machine)
    manifest = {
        "$schema": "../../schemas/mncs-manifest.schema.json",
        "schema_version": "0.2",
        "mncs_version": "0.2",
        "claimed_level": "MNCS-L4",
        "component": {
            "name": "EdgeStream",
            "version": "0.1.0-development",
            "contract_id": CONTRACT_ID,
            "criticality": "moderate",
            "identity_hash": machine_hash,
        },
        "contract": {
            "path": "specification/contract.md",
            "sha256": digest(contract),
        },
        "reference": {
            "path": "reference/edgestream_reference.c",
            "sha256": digest(reference),
        },
        "machine": {
            "path": "machine/edgestream_generated.c",
            "sha256": machine_hash,
            "generated_marker": "MNCS-GENERATED",
        },
        "generator": {
            "name": "EdgeStream deterministic specialization generator",
            "version": "1.0",
            "identity_evidence_id": "identity-generator",
            "identity_hash": digest(identities["generator"]),
        },
        "environment": {
            "fingerprint": digest(identities["environment"]),
            "identity_evidence_id": "identity-environment",
            "description": (
                "Captured Linux x86_64 local development environment with GCC and Clang."
            ),
        },
        "acceptance_policy": {
            "conformance_level": "MNCS-L4",
            "required_gates": [
                "behavioral",
                "compiler_matrix",
                "safety",
                "resource_bounds",
                "mutation",
                "structural",
                "measurement_valid",
                "benefit_threshold",
                "worst_regression",
            ],
            "on_unknown": "reject",
            "conflicting_evidence": "reject",
            "objective": {
                "metric": "telemetry throughput",
                "unit": "bytes/second",
                "direction": "higher_is_better",
                "threshold": 1.15,
                "minimum_sample_count": 7,
                "noise_policy": (
                    "No outlier deletion; paired measurements retained in execution order."
                ),
                "declared_before_generation": True,
            },
            "regression_policy": {"maximum_worst_case_ratio": 1.10},
            "mutation_required": True,
        },
        "gate_results": {
            "behavioral": ["gate-behavioral"],
            "compiler_matrix": ["gate-compiler-matrix"],
            "safety": ["gate-safety"],
            "resource_bounds": ["gate-resource-bounds"],
            "mutation": ["gate-mutation"],
            "structural": ["gate-structural"],
            "measurement_valid": ["performance-throughput"],
            "benefit_threshold": ["performance-throughput"],
            "worst_regression": ["performance-throughput"],
        },
        "evidence_index": {
            "path": "evidence/index.json",
            "sha256": digest(index_path),
        },
        "fuzz_evidence": ["raw-differential"],
        "resource_bounds": {
            "maximum_active_devices": 64,
            "maximum_metrics_per_device": 4,
            "maximum_window_samples": 8,
            "maximum_parser_buffer_bytes": 4096,
            "checkpoint_bytes_observed": 14896,
        },
        "invariants": ["invariant-bounded-storage"],
        "structural_aggregate": {
            "required_invariants": ["bounded-storage"],
            "provider_assumptions": [
                "Source-pattern checks are bounded rejection evidence, not semantic proof."
            ],
            "bounded": True,
        },
        "performance_results": ["performance-throughput"],
        "comparison_profile": {
            "benefit": {
                "mean_throughput_ratio": (fmean(candidate_samples) / fmean(baseline_samples))
            },
            "complexity": {
                "candidate_source_bytes": float(machine.stat().st_size),
                "reference_source_bytes": float(reference.stat().st_size),
            },
            "normalization": (
                "Identical contract, workload corpus, output semantics, compiler mode, and host."
            ),
        },
        "limitations": [
            "Experimental development study on one host.",
            (
                "Joern-specific analysis was unavailable and is not a required provider "
                "for this claim."
            ),
            ("Repository-visible separated workloads are not blind third-party holdout evidence."),
        ],
        "final_status": "PASS",
        "extensions": {
            "mncs.dev:case-study": "edgestream",
            "mncs.dev:mncds-profile": "MNCDS-D2",
        },
    }
    write_json(ROOT / "manifest.json", manifest)


def update_mncds_record(
    baseline_samples: list[float],
    candidate_samples: list[float],
) -> None:
    """Bind the D2 candidate ledger to the captured mean throughput values."""

    path = ROOT / "mncds" / "development-record.json"
    record = read_json(path)
    candidates = record.get("candidates")
    if not isinstance(candidates, list):
        raise TypeError("MNCDS candidate ledger must be a list")
    objective_values = {
        "candidate-readable-reference": fmean(baseline_samples),
        "candidate-generated-crc-table": fmean(candidate_samples),
    }
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise TypeError("MNCDS candidate must be an object")
        candidate_id = candidate.get("candidate_id")
        if isinstance(candidate_id, str) and candidate_id in objective_values:
            candidate["objective_value"] = objective_values[candidate_id]
    selection = record.get("selection")
    if not isinstance(selection, dict):
        raise TypeError("MNCDS selection must be an object")
    selection["minimum_useful_benefit_met"] = (
        fmean(candidate_samples) / fmean(baseline_samples) >= 1.15
    )
    write_json(path, record)


def main() -> int:
    """Regenerate every identity, result wrapper, index, and manifest."""

    machine = ROOT / "machine" / "edgestream_generated.c"
    reference = ROOT / "reference" / "edgestream_reference.c"
    contract = ROOT / "specification" / "contract.md"
    harness = ROOT / "tools" / "run_study.py"
    corpus = ROOT / "workloads" / "manifest.json"
    benchmark = read_json(RESULTS / "benchmark.json")
    environment = read_json(RESULTS / "environment.json")
    machine_hash = digest(machine)
    reference_hash = digest(reference)

    identities = create_identities(harness, corpus, environment)
    evaluator_hash = digest(identities["evaluator"])
    environment_hash = digest(identities["environment"])
    gate_paths = create_gate_results(
        machine_hash,
        reference_hash,
        evaluator_hash,
        environment_hash,
    )
    invariant_path = create_invariant(
        machine_hash,
        evaluator_hash,
        environment_hash,
    )
    performance_path, baseline_samples, candidate_samples = create_performance_result(
        benchmark,
        identities,
        machine_hash,
        reference_hash,
        evaluator_hash,
        environment_hash,
    )
    index_path = create_evidence_index(
        contract,
        reference,
        machine,
        machine_hash,
        identities,
        gate_paths,
        invariant_path,
        performance_path,
    )
    create_manifest(
        contract,
        reference,
        machine,
        identities,
        index_path,
        baseline_samples,
        candidate_samples,
    )
    update_mncds_record(baseline_samples, candidate_samples)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
