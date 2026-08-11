from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "machine"))

from cacheforge.epoch2 import evaluate_epoch2  # noqa: E402
from cacheforge.identities import collect_artifact_identities  # noqa: E402
from generated_policy import GeneratedEvictionPolicy  # noqa: E402

SUMMARY_OUTPUT = ROOT / "evidence" / "results" / "epoch-2-development.json"
SCENARIO_OUTPUT = ROOT / "evidence" / "results" / "epoch-2-scenario-results.json"


def main() -> int:
    summary = evaluate_epoch2(GeneratedEvictionPolicy)
    observations = summary.pop("observations")
    scenario_record = {
        "schema_version": "0.1",
        "study_id": summary["study_id"],
        "scenario_count": len(observations),
        "observation_digest": summary["scenario_observation_digest"],
        "observations": observations,
    }
    scenario_text = json.dumps(scenario_record, indent=2, sort_keys=True) + "\n"
    scenario_file_digest = hashlib.sha256(scenario_text.encode()).hexdigest()

    summary["scenario_observations"] = {
        "path": "evidence/results/epoch-2-scenario-results.json",
        "scenario_count": len(observations),
        "observation_digest": summary["scenario_observation_digest"],
        "file_digest": f"sha256:{scenario_file_digest}",
    }
    summary["artifact_identities"] = collect_artifact_identities()

    SUMMARY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    SCENARIO_OUTPUT.write_text(scenario_text)
    SUMMARY_OUTPUT.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "development_result": summary["development_result"],
                "formal_mncs_status": summary["formal_mncs_status"],
                "scenario_output": str(SCENARIO_OUTPUT),
                "summary_output": str(SUMMARY_OUTPUT),
            },
            sort_keys=True,
        )
    )
    return 0 if summary["development_result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
