# EdgeStream protocol notes

The fixed frame deliberately keeps parsing bounded while retaining versioning, malformed
input behavior, ordering state, time state, and recovery. The workload generator produces
all multi-byte fields with Python `struct` little-endian encodings and computes CRC-32 over
the first 28 bytes.

Version 2 changes only the measurement scale. This isolates normalization behavior from
transport framing and makes exact reference-versus-candidate comparison possible.

Arbitrary transport fragmentation is not part of the semantic input. Splitting or joining
chunks must not change canonical records. The evaluator checks chunks of 1, 3, 7, 31, 32,
257, and 4096 bytes.
