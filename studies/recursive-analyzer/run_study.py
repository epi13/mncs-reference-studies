#!/usr/bin/env python3
"""Reproduce the bounded two-epoch analyzer study."""

# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
import json
import resource
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} is not an object")
    return value


def evaluate(
    tool: Path, corpus: dict[str, Any], repetitions: int, timeout: float
) -> dict[str, Any]:
    observations: list[dict[str, Any]] = []
    metrics = {
        "true_positives": 0,
        "false_positives": 0,
        "false_negatives": 0,
        "incorrect_pass": 0,
        "unknown": 0,
        "crashes": 0,
        "timeouts": 0,
        "unsupported": 0,
        "diagnostic_utility": 0,
    }
    runtimes: list[float] = []
    for case in corpus["cases"]:
        first: dict[str, Any] | None = None
        deterministic = True
        for _ in range(repetitions):
            started = time.perf_counter()
            try:
                process = subprocess.run(
                    [sys.executable, str(tool)],
                    input=json.dumps(case),
                    capture_output=True,
                    check=False,
                    text=True,
                    timeout=timeout,
                )
            except subprocess.TimeoutExpired:
                metrics["timeouts"] += 1
                deterministic = False
                continue
            runtimes.append(time.perf_counter() - started)
            if process.returncode != 0:
                metrics["crashes"] += 1
                deterministic = False
                continue
            result = json.loads(process.stdout)
            if first is None:
                first = result
            elif result != first:
                deterministic = False
        actual = "UNKNOWN" if first is None else first["status"]
        expected = case["expected"]
        metrics["true_positives"] += int(expected == "FAIL" and actual == "FAIL")
        metrics["false_positives"] += int(expected == "PASS" and actual == "FAIL")
        metrics["false_negatives"] += int(expected == "FAIL" and actual != "FAIL")
        metrics["incorrect_pass"] += int(expected != "PASS" and actual == "PASS")
        metrics["unknown"] += int(actual == "UNKNOWN")
        metrics["unsupported"] += int(expected == "UNKNOWN")
        metrics["diagnostic_utility"] += int(actual == expected)
        observations.append(
            {
                "case_id": case["case_id"],
                "expected": expected,
                "actual": actual,
                "diagnostic": None if first is None else first["diagnostic"],
                "deterministic": deterministic,
            }
        )
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    metrics["runtime_seconds_min"] = min(runtimes, default=0.0)
    metrics["runtime_seconds_max"] = max(runtimes, default=0.0)
    metrics["max_rss_kib"] = usage.ru_maxrss
    return {"metrics": metrics, "observations": observations}


def main() -> int:
    plan = load(ROOT / "study-plan.json")
    development = load(ROOT / "development-corpus.json")
    final = load(ROOT / "final-corpus.json")
    epoch_one = ROOT / "epoch-one" / "analyzer.py"
    epoch_two = ROOT / "epoch-two" / "analyzer.py"
    identities = {
        "epoch_one_tool": sha256(epoch_one),
        "epoch_one_corpus": sha256(ROOT / "development-corpus.json"),
        "epoch_two_tool": sha256(epoch_two),
        "epoch_two_development_corpus": sha256(ROOT / "development-corpus.json"),
        "epoch_two_final_corpus": sha256(ROOT / "final-corpus.json"),
    }
    expected_identities = {
        "epoch_one_tool": plan["epoch_one"]["tool_sha256"],
        "epoch_one_corpus": plan["epoch_one"]["corpus_sha256"],
        "epoch_two_tool": plan["epoch_two"]["tool_sha256"],
        "epoch_two_development_corpus": plan["epoch_two"]["development_corpus_sha256"],
        "epoch_two_final_corpus": plan["epoch_two"]["final_corpus_sha256"],
    }
    identity_match = identities == expected_identities
    repetitions = int(plan["repetitions"])
    timeout = float(plan["timeout_seconds"])
    results = {
        "epoch_one_development": evaluate(epoch_one, development, repetitions, timeout),
        "epoch_two_development": evaluate(epoch_two, development, repetitions, timeout),
        "epoch_one_final_comparator": evaluate(epoch_one, final, repetitions, timeout),
        "epoch_two_final": evaluate(epoch_two, final, repetitions, timeout),
    }
    before = results["epoch_one_final_comparator"]["metrics"]
    after = results["epoch_two_final"]["metrics"]
    comparison = {
        "incorrect_pass_delta": after["incorrect_pass"] - before["incorrect_pass"],
        "false_negative_delta": after["false_negatives"] - before["false_negatives"],
        "false_positive_delta": after["false_positives"] - before["false_positives"],
        "diagnostic_utility_delta": after["diagnostic_utility"] - before["diagnostic_utility"],
        "crash_delta": after["crashes"] - before["crashes"],
        "timeout_delta": after["timeouts"] - before["timeouts"],
    }
    selected = (
        identity_match
        and comparison["incorrect_pass_delta"] <= -int(plan["objective"]["minimum_useful_benefit"])
        and comparison["false_negative_delta"] <= 0
        and comparison["false_positive_delta"] <= 0
        and after["crashes"] == 0
        and after["timeouts"] == 0
    )
    output = {
        "study_id": plan["study_id"],
        "identity_match": identity_match,
        "identities": identities,
        "results": results,
        "comparison": comparison,
        "selection": {
            "selected_tool_id": "analyzer.epoch-two" if selected else None,
            "internal_selection_status": "PASS" if selected else "FAIL",
            "mncs_claim_status": "UNKNOWN",
            "external_independence": "UNKNOWN",
        },
        "non_promotion_boundary": plan["non_promotion_boundary"],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if selected else 1


if __name__ == "__main__":
    raise SystemExit(main())
