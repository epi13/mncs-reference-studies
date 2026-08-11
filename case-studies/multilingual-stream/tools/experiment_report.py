from __future__ import annotations

import platform

from experiment_common import REPEATS, WARMUPS, tool_version


def build_report(
    gcc: str,
    cargo: str,
    implementations: dict[str, list[str]],
    direct: list[dict[str, object]],
    sanitizer_status: str,
    sanitizer_note: str,
    benchmark: dict[str, object],
) -> dict[str, object]:
    observations = {
        "directly_comparable": direct,
        "normalized_imperfect": [
            {
                "observation": "throughput",
                "status": benchmark["status"],
                "reason": (
                    "same workload and host; compiler, startup, and runtime differences remain"
                ),
                "measurements": benchmark["measurements"],
            }
        ],
        "language_specific": [
            {
                "observation": "c11-runtime-safety",
                "status": sanitizer_status,
                "method": sanitizer_note,
            },
            {
                "observation": "rust-safe-boundary",
                "status": "PASS",
                "method": ("crate contains no unsafe block; cargo clippy and tests pass"),
            },
            {
                "observation": "tooling-burden",
                "status": "OBSERVED",
                "c11": ["compiler", "optional sanitizers"],
                "rust": ["rustc", "cargo", "rustfmt", "clippy"],
            },
        ],
        "non_comparable": [
            {
                "observation": "source complexity score",
                "status": "NOT_DEFINED",
                "reason": ("language syntax and abstractions are not a common numerical scale"),
            }
        ],
        "unknown": [
            {"observation": "cross-host performance", "status": "UNKNOWN"},
            {
                "observation": "exhaustive C11 undefined behavior absence",
                "status": "UNKNOWN",
            },
            {
                "observation": "all Rust macro/cfg/FFI behavior",
                "status": "UNKNOWN",
            },
            {
                "observation": "independent protected holdout",
                "status": "UNKNOWN",
            },
        ],
    }
    direct_pass = all(item["status"] == "PASS" for item in direct)
    benefit_status = benchmark["benefit_gate"]["status"]
    subjects = [
        {
            "id": name,
            "language": "C11" if name.startswith("c11") else "Rust",
            "role": "candidate" if name.endswith("candidate") else "reference",
        }
        for name in implementations
    ]
    return {
        "schema_version": "0.1-experimental",
        "report_id": "multilingual-stream-wave1-development",
        "contract_id": "contract:multilingual-bounded-stream-0.1",
        "subjects": subjects,
        "environment": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "gcc": tool_version([gcc, "--version"]),
            "rustc": tool_version(["rustc", "--version"]),
            "cargo": tool_version([cargo, "--version"]),
        },
        "observations": observations,
        "benchmark_protocol": {
            "input_bytes": benchmark["input_bytes"],
            "repeats": REPEATS,
            "warmups": WARMUPS,
            "uncertainty": "median and median absolute deviation",
            "useful_benefit_threshold": (
                "candidate median wall time at least 5% better than its "
                "same-language reference without correctness regression"
            ),
            "benchmark": benchmark,
        },
        "claim_boundary": {
            "formal_mncs_status": "UNKNOWN",
            "formal_mncds_status": "UNKNOWN",
            "promotion_authorized": False,
            "development_result": (
                "PASS" if direct_pass and benefit_status == "PASS" else "REVIEW_REQUIRED"
            ),
            "useful_benefit_status": benefit_status,
        },
        "extensions": {
            "mncs.dev:profiles": [
                "c11-reference-v0.1",
                "rust-1.97.1-edition-2024-v0.1",
            ]
        },
    }
