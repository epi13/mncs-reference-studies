# Threat model

Threats include malformed and oversized input, integer overflow, parser disagreement, accidental
acceptance of whitespace or signs, compiler/runtime mismatch, panic or crash, benchmark noise,
provider overclaim, and result identity drift.

Mitigations include fixed-width arithmetic, checked sum/count bounds, a 1 MiB cap, shared corpus,
exact exit/output rules, strict C diagnostics, ASan/UBSan execution, locked Rust builds, Clippy,
rustfmt, deterministic replay, repeated measurements, profile/provider identity, and explicit
UNKNOWN handling.

Residual UNKNOWNs include exhaustive C11 undefined behavior, every Rust conditional compilation or
macro expansion, cross-host performance, microarchitectural side channels, and independent evidence
custody.
