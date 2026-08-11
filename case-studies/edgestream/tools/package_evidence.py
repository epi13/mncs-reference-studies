#!/usr/bin/env python3
"""Package EdgeStream evidence and derive conformance from raw observations."""

from derive_evidence import derive
from evidence_bundle import main as build_bundle


def main() -> int:
    """Build the evidence graph, then derive every acceptance status."""

    result = build_bundle()
    if result != 0:
        return result
    status = derive()
    if status == "PASS":
        return 0
    if status == "UNKNOWN":
        return 3
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
