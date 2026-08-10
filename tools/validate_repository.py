#!/usr/bin/env python3
"""Validate repository-level structural invariants without third-party packages."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_ROOT = ROOT / "reference-studies"
ID_RE = re.compile(r"^MRS-\d{3}$")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
ALLOWED_STATUS = {
    "PLANNED",
    "SELECTING_REFERENCE",
    "IMPLEMENTING",
    "DEVELOPMENT_EVALUATION",
    "PROTECTED_EVALUATION",
    "REVIEW_REQUIRED",
    "COMPLETE",
    "ARCHIVED",
}
ALLOWED_FORMAL_STATUS = {"UNKNOWN", "REVIEW_REQUIRED", "ESTABLISHED", "NOT_APPLICABLE"}
REQUIRED = {
    "schema_version",
    "id",
    "slug",
    "title",
    "tier",
    "status",
    "subject",
    "upstream",
    "arms",
    "primary_questions",
    "metric_families",
    "formal_mncs_status",
    "formal_mncds_status",
    "promotion_authorized",
}
UPSTREAM_REQUIRED = {"name", "url", "version", "commit", "license", "frozen"}


def fail(errors: list[str], path: Path, message: str) -> None:
    errors.append(f"{path.relative_to(ROOT)}: {message}")


def validate_manifest(path: Path, errors: list[str]) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(errors, path, f"cannot parse JSON: {exc}")
        return

    missing = REQUIRED - data.keys()
    extra = data.keys() - REQUIRED
    if missing:
        fail(errors, path, f"missing keys: {sorted(missing)}")
    if extra:
        fail(errors, path, f"unexpected keys: {sorted(extra)}")
    if missing:
        return

    study_id = data["id"]
    slug = data["slug"]
    if not isinstance(study_id, str) or not ID_RE.fullmatch(study_id):
        fail(errors, path, "id must match MRS-NNN")
    if not isinstance(slug, str) or not SLUG_RE.fullmatch(slug):
        fail(errors, path, "slug must be lowercase kebab-case")

    expected_dir = f"{study_id}-{slug}"
    if path.parent.name != expected_dir:
        fail(errors, path, f"directory must be {expected_dir!r}")

    if data["schema_version"] != "0.1.0":
        fail(errors, path, "schema_version must be 0.1.0")
    if not isinstance(data["tier"], int) or isinstance(data["tier"], bool) or data["tier"] < 1:
        fail(errors, path, "tier must be an integer >= 1")
    if data["status"] not in ALLOWED_STATUS:
        fail(errors, path, f"unsupported status {data['status']!r}")

    for key in ("title", "subject"):
        if not isinstance(data[key], str) or not data[key].strip():
            fail(errors, path, f"{key} must be a non-empty string")

    for key in ("arms", "primary_questions", "metric_families"):
        value = data[key]
        if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
            fail(errors, path, f"{key} must be a non-empty string array")
        elif len(value) != len(set(value)):
            fail(errors, path, f"{key} must not contain duplicates")

    upstream = data["upstream"]
    if not isinstance(upstream, dict):
        fail(errors, path, "upstream must be an object")
    else:
        missing_upstream = UPSTREAM_REQUIRED - upstream.keys()
        extra_upstream = upstream.keys() - UPSTREAM_REQUIRED
        if missing_upstream:
            fail(errors, path, f"upstream missing keys: {sorted(missing_upstream)}")
        if extra_upstream:
            fail(errors, path, f"upstream unexpected keys: {sorted(extra_upstream)}")
        if "frozen" in upstream and not isinstance(upstream["frozen"], bool):
            fail(errors, path, "upstream.frozen must be boolean")
        if upstream.get("frozen"):
            for key in ("name", "url", "license"):
                if not isinstance(upstream.get(key), str) or not upstream[key].strip():
                    fail(errors, path, f"frozen upstream requires non-empty {key}")
            if not upstream.get("version") and not upstream.get("commit"):
                fail(errors, path, "frozen upstream requires version or commit")

    for key in ("formal_mncs_status", "formal_mncds_status"):
        if data[key] not in ALLOWED_FORMAL_STATUS:
            fail(errors, path, f"unsupported {key} {data[key]!r}")
    if not isinstance(data["promotion_authorized"], bool):
        fail(errors, path, "promotion_authorized must be boolean")

    if not (path.parent / "README.md").is_file():
        fail(errors, path, "study directory must contain README.md")


def main() -> int:
    errors: list[str] = []

    required_paths = [
        ROOT / "README.md",
        ROOT / "case-studies" / "README.md",
        ROOT / "studies" / "README.md",
        REFERENCE_ROOT / "README.md",
        ROOT / "methodology" / "experimental-protocol.md",
        ROOT / "schemas" / "study.schema.json",
    ]
    for required in required_paths:
        if not required.is_file():
            errors.append(f"missing required repository file: {required.relative_to(ROOT)}")

    manifests = sorted(REFERENCE_ROOT.glob("MRS-*/study.json"))
    if not manifests:
        errors.append("no MRS study manifests found")
    for manifest in manifests:
        validate_manifest(manifest, errors)

    try:
        json.loads((ROOT / "schemas" / "study.schema.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"schemas/study.schema.json: cannot parse JSON: {exc}")

    if errors:
        print("Repository validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"Repository validation passed: {len(manifests)} MRS manifest(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
