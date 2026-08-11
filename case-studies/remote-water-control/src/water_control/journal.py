# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

from water_control.model import AuthorizedIntent

GENESIS_HASH = "0" * 64


def canonical_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


@dataclass(frozen=True)
class JournalEntry:
    sequence: int
    previous_hash: str
    intent: dict[str, Any]
    entry_hash: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class IntentJournal:
    def __init__(self, *, last_sequence: int = 0, tail_hash: str = GENESIS_HASH) -> None:
        self.last_sequence = last_sequence
        self.tail_hash = tail_hash
        self.entries: list[JournalEntry] = []

    def append(self, intent: AuthorizedIntent) -> JournalEntry:
        if intent.sequence != self.last_sequence + 1:
            raise ValueError("intent sequence must advance exactly once")
        payload = {
            "previous_hash": self.tail_hash,
            "intent": intent.as_dict(),
        }
        entry_hash = hashlib.sha256(canonical_bytes(payload)).hexdigest()
        entry = JournalEntry(intent.sequence, self.tail_hash, intent.as_dict(), entry_hash)
        self.entries.append(entry)
        self.last_sequence = intent.sequence
        self.tail_hash = entry_hash
        return entry

    def verify(self) -> bool:
        expected_sequence = self.last_sequence - len(self.entries) + 1
        previous_hash = self.entries[0].previous_hash if self.entries else self.tail_hash
        for entry in self.entries:
            if entry.sequence != expected_sequence or entry.previous_hash != previous_hash:
                return False
            payload = {"previous_hash": previous_hash, "intent": entry.intent}
            if hashlib.sha256(canonical_bytes(payload)).hexdigest() != entry.entry_hash:
                return False
            previous_hash = entry.entry_hash
            expected_sequence += 1
        return previous_hash == self.tail_hash

    def snapshot(self) -> dict[str, Any]:
        return {"last_sequence": self.last_sequence, "tail_hash": self.tail_hash}
