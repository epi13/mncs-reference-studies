# Multilingual bounded-stream case study

This Wave One study gives C11 and Rust the same readable contract, valid corpus, malformed corpus,
resource envelope, recovery rule, benchmark workload, useful-benefit threshold, and result schema.
It compares a readable and candidate implementation in each language while preserving compiler,
build, runtime, and language differences in the environment record.

The generated-style Rust candidate uses one bounded byte-state parser rather than the readable
record-slice parser. Its operational objective is at least 5% better median throughput than the
Rust reference on the declared workload without any correctness, malformed-input, or replay
regression. The C11 programs are a controlled anchor, not a universal performance baseline.

Run from the repository root:

```bash
make multilingual-stream
```

The experiment runs strict C11 builds, Rust formatting, Clippy, tests, a locked release build,
malformed-input fixtures, deterministic replay, optional C sanitizers, and seven benchmark repeats.
The emitted report separates directly comparable, normalized-but-imperfect, language-specific,
non-comparable, and UNKNOWN observations. It never produces a universal cross-language complexity
score.

Formal MNCS and MNCDS status remain `UNKNOWN`; promotion is not authorized. The report is a bounded
development observation only.
