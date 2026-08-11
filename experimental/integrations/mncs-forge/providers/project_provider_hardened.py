#!/usr/bin/env python3
"""Deletion-aware entrypoint for the project-owned Forge provider.

The underlying provider remains the implementation authority for every method. This
entrypoint narrows one integration defect: change-impact questions may name deleted or
renamed paths whose old bytes no longer exist after the change.
"""

from __future__ import annotations

from typing import Any

import project_provider as base


def evidence_change_impact(request: dict[str, Any]) -> dict[str, object]:
    """Compare changed paths, including deleted paths, with a declared envelope."""

    component = request.get("component")
    changed = component.get("changed_paths") if isinstance(component, dict) else None
    dependency_values = base.parameters(request).get("dependency_paths")
    if (
        not isinstance(changed, list)
        or not isinstance(dependency_values, list)
        or not dependency_values
        or len(changed) > base.MAX_FILES
        or len(dependency_values) > base.MAX_FILES
    ):
        return base.response(
            request,
            "UNKNOWN",
            "the declared dependency envelope is missing or outside bounds",
            unsupported=["missing-or-unbounded-dependency-envelope"],
            limitations=["dependency_paths must be a non-empty bounded list"],
        )
    try:
        changed_paths = [base.safe_relative_path(item, must_exist=False)[0] for item in changed]
        dependency_paths = [
            base.safe_relative_path(item, must_exist=False)[0] for item in dependency_values
        ]
    except base.ProviderInputError as exc:
        return base.response(
            request,
            "UNKNOWN",
            "path impact could not be established",
            unsupported=["unsupported-path"],
            limitations=[str(exc)],
        )
    overlap = sorted(
        path
        for path in changed_paths
        if any(base.path_overlap(path, dependency) for dependency in dependency_paths)
    )
    assumptions = ["dependency_paths names the caller's intended bounded envelope"]
    if overlap:
        return base.response(
            request,
            "FAIL",
            "a changed path intersects the declared evidence dependency envelope",
            witnesses=[{"affected_path": item} for item in overlap],
            dependency_paths=dependency_paths,
            complete=False,
            assumptions=assumptions,
        )
    return base.response(
        request,
        "PASS",
        "no changed path intersects the declared evidence dependency envelope",
        limitations=[
            "path separation does not prove semantic or whole-program independence",
            "an incomplete caller envelope cannot prove evidence independence",
            "deleted-path identity binds the canonical path and absent state, not old bytes",
        ],
        dependency_paths=dependency_paths,
        complete=False,
        assumptions=assumptions,
    )


def main() -> int:
    base.evidence_change_impact = evidence_change_impact
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
