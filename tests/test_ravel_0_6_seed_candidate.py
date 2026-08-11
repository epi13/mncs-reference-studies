from __future__ import annotations

import hashlib
import runpy
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest

ROOT = Path(__file__).resolve().parents[1]
RAVEL_DIR = ROOT / "case-studies" / "ravel"
TOOL = RAVEL_DIR / "tools" / "ravel_0_6_seed_candidate.py"
SOURCE = RAVEL_DIR / "ravel_0_5.c"
EXPECTED_FROZEN_SHA256 = "1a8466ea1805811873c461fb891aaeaec18f6c9e7491b5ea7bd09bf698be102d"


def load_tool() -> dict[str, Any]:
    return runpy.run_path(str(TOOL))


def build_candidate() -> str:
    namespace = load_tool()
    build = cast(Callable[[bytes], str], namespace["build_candidate_source"])
    return build(SOURCE.read_bytes())


def test_frozen_source_identity_is_unchanged() -> None:
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED_FROZEN_SHA256


def test_seed_candidate_resets_inherited_empirical_support() -> None:
    candidate = build_candidate()
    start = candidate.index("static void seed_adaptation_expert")
    end = candidate.index("\n}\n\nstatic int add_adaptation_experts", start)
    function = candidate[start:end]

    assert "seeded = m->e[parent]" not in function
    assert "memset(&seeded, 0, sizeof seeded);" in function
    assert "seeded.transition_target[action][k] = INVALID_EXPERT;" in function
    assert "seeded.labels[event->label] = 1u;" in function
    assert "seeded.action_count[event->action] = 1u;" in function
    assert "seeded.count = 1u;" in function


def test_seed_candidate_planner_traverses_every_supported_target() -> None:
    candidate = build_candidate()
    start = candidate.index("static int plan_actions")
    end = candidate.index("\n}\n\nstatic uint32_t optimal_world_path", start)
    function = candidate[start:end]

    assert "for (uint32_t k = 0; k < TRANSITION_TOP_K; ++k)" in function
    assert "for (uint32_t k = 0; k < 1u; ++k)" not in function


def test_seed_candidate_is_deterministic_and_marked_as_development() -> None:
    first = build_candidate()
    second = build_candidate()

    assert first == second
    assert "RAVEL 0.6 development seed" in first
    assert "No evaluation claim is implied." in first


def test_seed_candidate_cli_check_is_read_only(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(TOOL), "--check"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.startswith("ravel-0.6-candidate-001 sha256=")
    assert list(tmp_path.iterdir()) == []


def test_seed_candidate_compiles(tmp_path: Path) -> None:
    compiler = shutil.which("cc")
    if compiler is None:
        pytest.skip("C compiler unavailable")

    source = tmp_path / "ravel_0_6.c"
    binary = tmp_path / "ravel_0_6"
    subprocess.run(
        [sys.executable, str(TOOL), "--output", str(source)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            compiler,
            "-std=c11",
            "-O0",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-pedantic",
            str(source),
            "-lm",
            "-o",
            str(binary),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
