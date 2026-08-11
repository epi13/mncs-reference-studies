#!/usr/bin/env python3
"""Capture and decode dSense V5 binary telemetry from one explicit serial port.

The recorder never scans ports and never writes to the serial device. It stores the
exact binary stream and a decoded CSV. Typed lines become host-side experiment markers.
"""

from __future__ import annotations

import csv
import datetime as dt
import os
import select
import struct
import sys
import time
from collections.abc import Iterator
from pathlib import Path

SYNC = b"\xA5\x5A"
FORMATS = {
    1: (
        "<I13HhH15B",
        [
            "device_ms",
            "events",
            "brightness",
            "ambient",
            "presence",
            "external",
            "threshold",
            "onset",
            "arousal",
            "novelty",
            "coherence",
            "agency",
            "curiosity",
            "fatigue",
            "valence",
            "jitter",
            "state",
            "result",
            "face",
            "face_intensity",
            "ui",
            "selection",
            "flags",
            "sfx",
            "red",
            "green",
            "blue",
            "event_class",
            "confidence",
            "armed",
            "presence_active",
        ],
    ),
    2: (
        "<I10B10B2B4H2Bb",
        [
            "device_ms",
            *[f"c{index}" for index in range(10)],
            *[f"p{index}" for index in range(10)],
            "rgb_coupling",
            "sound_coupling",
            "jitter_base",
            "jitter_model",
            "reaction_mean",
            "reaction_dev",
            "episodes",
            "familiarity",
            "recalled",
        ],
    ),
    3: (
        "<I4H8B",
        [
            "device_ms",
            "events",
            "presence",
            "onset",
            "external",
            "code",
            "state",
            "face",
            "ui",
            "selection",
            "event_class",
            "confidence",
            "sfx",
        ],
    ),
    127: ("<4B", ["version", "fast_size", "model_size", "event_size"]),
}

ALL_FIELDS = ["host_iso", "host_elapsed", "record", "marker"]
for _, names in FORMATS.values():
    for name in names:
        if name not in ALL_FIELDS:
            ALL_FIELDS.append(name)


def iso_now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="milliseconds")


def frame_bytes(packet_type: int, payload: bytes) -> bytes:
    """Build one valid frame for verifier tests; the recorder itself never transmits it."""
    if len(payload) > 255:
        raise ValueError("payload exceeds one-byte protocol length")
    checksum = packet_type ^ len(payload)
    for byte in payload:
        checksum ^= byte
    return SYNC + bytes((packet_type, len(payload))) + payload + bytes((checksum,))


def parse_frames(buffer: bytearray) -> Iterator[tuple[int, bytes]]:
    """Consume complete checksum-valid frames while retaining incomplete tail bytes."""
    while True:
        position = buffer.find(SYNC)
        if position < 0:
            if len(buffer) > 1:
                del buffer[:-1]
            return
        if position:
            del buffer[:position]
        if len(buffer) < 5:
            return
        packet_type = buffer[2]
        length = buffer[3]
        frame_length = 5 + length
        if len(buffer) < frame_length:
            return
        payload = bytes(buffer[4 : 4 + length])
        checksum = buffer[4 + length]
        expected = packet_type ^ length
        for byte in payload:
            expected ^= byte
        del buffer[:frame_length]
        if checksum == expected:
            yield packet_type, payload


def expected_packet_sizes() -> tuple[int, int, int]:
    return tuple(struct.calcsize(FORMATS[index][0]) for index in (1, 2, 3))


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {Path(sys.argv[0]).name} /dev/ttyUSB1", file=sys.stderr)
        return 2
    port = sys.argv[1]
    if not os.path.exists(port):
        print(f"Port does not exist: {port}", file=sys.stderr)
        return 2

    try:
        import serial
    except ImportError:
        print(
            "pyserial is required: python3 -m pip install --user pyserial",
            file=sys.stderr,
        )
        return 2

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = Path(f"dsense_v5_{stamp}.dsb")
    csv_path = Path(f"dsense_v5_{stamp}.csv")
    start = time.monotonic()
    buffer = bytearray()
    validated = False
    deadline = start + 12.0

    print(f"Opening exactly {port} at 115200 baud; no data will be sent.")
    with (
        serial.Serial(port, 115200, timeout=0.10) as device,
        raw_path.open("wb") as raw_file,
        csv_path.open("w", newline="", encoding="utf-8") as csv_file,
    ):
        writer = csv.DictWriter(csv_file, fieldnames=ALL_FIELDS)
        writer.writeheader()
        print("Waiting for dSense binary V5 sync...")

        try:
            while True:
                chunk = device.read(512)
                if chunk:
                    raw_file.write(chunk)
                    raw_file.flush()
                    buffer.extend(chunk)
                    for packet_type, payload in parse_frames(buffer):
                        specification = FORMATS.get(packet_type)
                        if specification is None:
                            continue
                        format_string, names = specification
                        if struct.calcsize(format_string) != len(payload):
                            continue
                        values = struct.unpack(format_string, payload)
                        row = {
                            "host_iso": iso_now(),
                            "host_elapsed": f"{time.monotonic() - start:.3f}",
                            "record": {1: "D", 2: "P", 3: "E", 127: "V"}[
                                packet_type
                            ],
                        }
                        row.update(zip(names, values, strict=True))
                        writer.writerow(row)
                        csv_file.flush()
                        if packet_type == 127:
                            version, fast_size, model_size, event_size = values
                            if version == 5 and (
                                fast_size,
                                model_size,
                                event_size,
                            ) == expected_packet_sizes():
                                if not validated:
                                    print(
                                        "dSense V5 confirmed: packet sizes "
                                        f"{fast_size}/{model_size}/{event_size}."
                                    )
                                    print(
                                        "Type experiment markers and press Enter. "
                                        "Ctrl+C stops."
                                    )
                                validated = True

                if not validated and time.monotonic() > deadline:
                    raise RuntimeError(
                        "No valid dSense V5 packet arrived. Confirm the UnoMax Binary "
                        "sketch is uploaded and this is the Uno's exact port."
                    )

                if select.select([sys.stdin], [], [], 0)[0]:
                    marker = sys.stdin.readline()
                    if marker == "":
                        continue
                    marker = marker.strip()
                    if marker:
                        writer.writerow(
                            {
                                "host_iso": iso_now(),
                                "host_elapsed": f"{time.monotonic() - start:.3f}",
                                "record": "MARK",
                                "marker": marker,
                            }
                        )
                        csv_file.flush()
                        print(f"MARK {marker}")
        except KeyboardInterrupt:
            pass
        except RuntimeError as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 1

    print(f"Decoded CSV: {csv_path.resolve()}")
    print(f"Raw binary:  {raw_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
