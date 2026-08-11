from __future__ import annotations

import hashlib
import json
import subprocess

from experiment_common import REPEATS, ROOT, WARMUPS, measure, oracle, run


def functional_observations(
    implementations: dict[str, list[str]],
) -> list[dict[str, object]]:
    valid = (ROOT / "corpus/valid.txt").read_bytes()
    expected = oracle(valid)
    observations: list[dict[str, object]] = []
    for name, command in implementations.items():
        first = run(command, data=valid)
        second = run(command, data=valid)
        passed = (
            first.returncode == 0
            and first.stdout == expected
            and first.stderr == b""
            and first.stdout == second.stdout
        )
        observations.append(
            {
                "observation": "correctness-and-replay",
                "subject": name,
                "status": "PASS" if passed else "FAIL",
                "output_sha256": hashlib.sha256(first.stdout).hexdigest(),
            }
        )
        if not passed:
            raise SystemExit(
                f"functional failure: {name}: {first.returncode} {first.stdout!r} {first.stderr!r}"
            )
    malformed = json.loads((ROOT / "corpus/malformed.json").read_text(encoding="utf-8"))
    for name, command in implementations.items():
        passed = all(
            (result := run(command, data=item.encode("utf-8"))).returncode == 2
            and result.stdout == b""
            and result.stderr == b"invalid input\n"
            for item in malformed
        )
        observations.append(
            {
                "observation": "malformed-input",
                "subject": name,
                "status": "PASS" if passed else "FAIL",
                "cases": len(malformed),
            }
        )
        if not passed:
            raise SystemExit(f"malformed-input failure: {name}")
    return observations


def provider_observations() -> list[dict[str, object]]:
    provider_root = ROOT.parents[1] / "experimental/language-evidence/providers"
    fixtures = {
        "c11": ROOT / "fixtures/c11/deliberately-defective.c",
        "rust": ROOT / "fixtures/rust/deliberately-defective.rs",
    }
    analyses = {
        "c11": "c11.bounded-source-safety",
        "rust": "rust.bounded-source-safety",
    }
    observations: list[dict[str, object]] = []
    for language, fixture in fixtures.items():
        request = {
            "protocol_version": "0.1",
            "type": "analysis_request",
            "request_id": f"multilingual-defect-{language}",
            "analysis": analyses[language],
            "component": {
                "language": language,
                "source_text": fixture.read_text(encoding="utf-8"),
                "subject_id": f"fixture:multilingual-stream:{language}:defective",
                "contract_id": "contract:multilingual-bounded-stream-0.1",
                "environment_id": ("environment:multilingual-stream-wave1-linux-x86_64"),
                "evidence_partition": "public-development",
            },
            "limits": {"wall_seconds": 2, "input_bytes": 65_536},
            "extensions": {},
        }
        completed = run(
            ["python3", str(provider_root / f"{language}_provider.py")],
            data=(json.dumps(request, sort_keys=True, separators=(",", ":")) + "\n").encode(),
            timeout=2,
        )
        response = json.loads(completed.stdout) if completed.returncode == 0 else {}
        status = "PASS" if response.get("status") == "FAIL" else "FAIL"
        observations.append(
            {
                "observation": "deliberately-defective-fixture-rejected",
                "subject": language,
                "status": status,
                "provider_status": response.get("status", "OPERATIONAL_ERROR"),
                "provider": response.get("provider"),
            }
        )
        if status != "PASS":
            raise SystemExit(f"defective fixture was not rejected: {language}")
    return observations


def regeneration_observation() -> dict[str, object]:
    completed = subprocess.run(
        ["python3", "generator/generate.py", "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=5,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.stdout + completed.stderr)
    return {
        "observation": "candidate-regeneration-identity",
        "subject": "c11-and-rust-candidates",
        "status": "PASS",
        "method": "deterministic retained-template materializer",
    }


def benchmark_report(
    implementations: dict[str, list[str]],
    *,
    skip: bool,
) -> dict[str, object]:
    data = ("\n".join(str((index * 7_919) % 100_001) for index in range(25_000)) + "\n").encode()
    report: dict[str, object] = {
        "status": "SKIPPED",
        "repeats": REPEATS,
        "warmups": WARMUPS,
        "workload_sha256": hashlib.sha256(data).hexdigest(),
        "input_bytes": len(data),
        "measurements": {},
        "benefit_gate": {
            "status": "UNKNOWN",
            "maximum_candidate_reference_ratio": 0.95,
            "passing_subjects": [],
        },
    }
    if skip:
        return report
    measurements = {name: measure(command, data) for name, command in implementations.items()}
    passing: list[str] = []
    ratios: dict[str, float] = {}
    for language in ("c11", "rust"):
        candidate = measurements[f"{language}-candidate"]["median_seconds"]
        reference = measurements[f"{language}-reference"]["median_seconds"]
        ratio = float(candidate) / float(reference)
        ratios[language] = ratio
        if ratio <= 0.95:
            passing.append(language)
    report.update(
        {
            "status": "MEASURED",
            "measurements": measurements,
            "benefit_gate": {
                "status": "PASS" if passing else "FAIL",
                "maximum_candidate_reference_ratio": 0.95,
                "ratios": ratios,
                "passing_subjects": passing,
            },
        }
    )
    return report
