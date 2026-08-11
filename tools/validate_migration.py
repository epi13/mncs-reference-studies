"""Validate the migrated-study inventory without modifying study evidence."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = "80f08d312dce963265c7f69ac5b4bae8245bd692"
CASE_STUDIES = (
    "cacheforge",
    "composed-gateway",
    "dsense-desk-pet",
    "edgestream",
    "edgestream-remote-water-integration",
    "go-gateway",
    "multilingual-stream",
    "ravel",
    "remote-water-control",
)
RESEARCH_STUDIES = (
    "recursive-analyzer",
    "recursive-architecture-comparison",
    "recursive-experience-substrate",
)


def check_study(path: Path, source_path: str, errors: list[str]) -> None:
    migration = path / "MIGRATION.md"
    if not migration.is_file():
        errors.append(f"missing migration record: {migration.relative_to(ROOT)}")
        return
    text = migration.read_text(encoding="utf-8")
    required = (
        "Source repository:",
        f"Frozen source commit: `{SOURCE_SHA}`",
        f"Original source path: `{source_path}/`",
        f"Destination path: `{source_path}/`",
        "Migration date:",
        "History:",
        "Path/build changes:",
        "Evidence-bearing artifact changed:",
        "Experiment rerun for migration:",
        "Validation after migration:",
    )
    for marker in required:
        if marker not in text:
            errors.append(f"{migration.relative_to(ROOT)} missing {marker}")


def main() -> int:
    errors: list[str] = []
    for name in CASE_STUDIES:
        check_study(ROOT / "case-studies" / name, f"case-studies/{name}", errors)
    for name in RESEARCH_STUDIES:
        check_study(ROOT / "studies" / name, f"studies/{name}", errors)

    if not (ROOT / "MIGRATION.md").is_file():
        errors.append("missing root MIGRATION.md")
    if not re.search(r"362.*tracked files|tracked files.*362", (ROOT / "MIGRATION.md").read_text(encoding="utf-8")):
        errors.append("root migration record does not bind the tracked-file inventory")

    if errors:
        print("Migration validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print("Migration validation passed: 9 case studies and 3 research studies recorded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

