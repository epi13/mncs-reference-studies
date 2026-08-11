# EdgeStream design

The readable reference uses bytewise little-endian decoding and a bitwise CRC-32. The
machine candidate is regenerated from the reference and replaces the CRC loop with a
specialized 256-entry table. The transformation is intentionally narrow: all state,
classification, JSON output, and checkpoint behavior remain shared and are tested for
byte-identical behavior.

The study is more demanding than the preliminary HTTP decoder because correctness spans
long-lived per-device state, rolling aggregation, sequence rollover, explicit event time,
alarm transitions, bounded admission, persistence, recovery, and injected checkpoint
failures.

The required structural provider is a bounded Clang-AST and source-order analyzer tied to
the generated candidate identity. It establishes only the declared invariant set and does
not claim complete C semantic proof. A versioned regression corpus confirms that the
provider rejects representative missing-marker, dynamic-allocation, validation-order,
benchmark-awareness, and checkpoint-integrity defects. Joern remains optional and is
recorded separately when unavailable; its absence is not silently converted to PASS.
