# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from water_control.journal import canonical_bytes


class CheckpointError(ValueError):
    pass


def encode_checkpoint(payload: dict[str, Any]) -> bytes:
    digest = hashlib.sha256(canonical_bytes(payload)).hexdigest()
    envelope = {"payload": payload, "sha256": digest}
    return canonical_bytes(envelope)


def decode_checkpoint(data: bytes) -> dict[str, Any]:
    try:
        envelope = json.loads(data)
        payload = envelope["payload"]
        expected = envelope["sha256"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise CheckpointError("checkpoint envelope is malformed") from exc
    actual = hashlib.sha256(canonical_bytes(payload)).hexdigest()
    if actual != expected:
        raise CheckpointError("checkpoint digest mismatch")
    if not isinstance(payload, dict):
        raise CheckpointError("checkpoint payload must be an object")
    return payload


def write_checkpoint(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(encode_checkpoint(payload))
    os.replace(temporary, path)


def read_checkpoint(path: Path) -> dict[str, Any]:
    return decode_checkpoint(path.read_bytes())
