"""Load bounded workflow policy from the committed Forge configuration."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "mncs-forge.toml"


@dataclass(frozen=True)
class ForgeWorkflowPolicy:
    environment_allowlist: tuple[str, ...]
    output_cap: int


def load_forge_workflow_policy(
    config_path: Path = DEFAULT_CONFIG,
) -> ForgeWorkflowPolicy:
    with config_path.open("rb") as stream:
        config = tomllib.load(stream)
    allowlist = config.get("environment_allowlist")
    limits = config.get("limits")
    if (
        not isinstance(allowlist, list)
        or not allowlist
        or not all(isinstance(key, str) and key for key in allowlist)
        or not isinstance(limits, dict)
        or not isinstance(limits.get("output_bytes"), int)
    ):
        raise ValueError("mncs-forge.toml does not contain bounded workflow policy")
    output_cap = int(limits["output_bytes"])
    if output_cap < 1024 or output_cap > 16 * 1024 * 1024:
        raise ValueError("Forge output_bytes is outside the supported policy range")
    return ForgeWorkflowPolicy(tuple(dict.fromkeys(allowlist)), output_cap)
