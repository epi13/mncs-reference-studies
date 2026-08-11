# EdgeStream telemetry processor contract

Contract identifier: `mncs.edgestream.telemetry.v1`

EdgeStream consumes an arbitrary fragmentation of a byte stream and emits canonical JSON
Lines records. Observable behavior is deterministic for identical bytes, initial state,
checkpoint state, declared limits, and implementation environment.

## Frame contract

Every frame is exactly 32 bytes and uses little-endian integers:

| Offset | Width | Field |
|---:|---:|---|
| 0 | 2 | magic `e5 47` |
| 2 | 1 | protocol version, `1` or `2` |
| 3 | 1 | flags; bit 0 declares a device restart |
| 4 | 2 | frame length, exactly `32` |
| 6 | 4 | device identifier |
| 10 | 4 | sequence number |
| 14 | 8 | event timestamp in milliseconds |
| 22 | 2 | metric identifier |
| 24 | 4 | signed measurement |
| 28 | 4 | IEEE CRC-32 over bytes 0 through 27 |

Version 1 values are already milli-units. Version 2 values are centi-units and are
normalized by multiplying by ten. Metric `65535` is a watermark control record; its
timestamp advances silence evaluation and its measurement is ignored.

## Ordering and duplicate behavior

A sequence equal to the last accepted sequence for a device is a duplicate. A lower
sequence is late unless the previous sequence is at least `0xfffffff0` and the new
sequence is at most `0x0f`. A restart flag clears sequence and rolling metric state before
the event is evaluated. Duplicate and late records do not update rolling state.

## Rolling state and alarms

Each device has four metrics. Each metric retains the last eight accepted normalized
values and emits an integer-truncated rolling average. A high alarm activates above
`50000` milli-units and clears at or below `45000`. A silence alarm activates when a
watermark is more than 60000 milliseconds beyond a device's last accepted event and
clears on the next accepted event from that device.

## Canonical output

JSON object keys and integer rendering are fixed by the implementations. Record types are:
`event`, `reject`, `duplicate`, `late`, `alarm`, `resource_limit`, `checkpoint`, and
`recovery`. No floating-point number is externally observable.

## Resource limits

The processor is limited to 64 active devices, four metrics per device, eight retained
samples per metric, a 4096-byte parser buffer, and 32-byte frames. A 65th device emits an
`active_devices` resource-limit record and is not installed. Parser overflow, malformed
length, unknown version, checksum failure, invalid metric, junk, and truncation are
observable rejection outcomes. Events are never silently discarded.

## Checkpoints

A checkpoint contains a fixed header, the complete processor state, and a CRC-32 over the
state. It is written to a temporary path and renamed only after successful write and
flush. Four deterministic fault points cover header write, state write, flush, and rename.
An incomplete or corrupt checkpoint must not replace the last valid checkpoint and must
not be restored as valid state.

## Exclusions

This development contract does not claim network transport security, cryptographic
message authentication, concurrent access, durability across every filesystem, or
production suitability. CRC-32 is an integrity check, not an authenticity mechanism.
