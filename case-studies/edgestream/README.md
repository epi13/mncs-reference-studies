# EdgeStream MNCS case study

EdgeStream is a fault-tolerant, bounded C11 telemetry processor used as the second major
MNCS research example. It compares a readable reference with a deterministic generated
candidate across stateful parsing, malformed input, alarm transitions, resource pressure,
checkpoint recovery, compiler and sanitizer checks, bounded structural analysis, evaluator
regression fixtures, and controlled paired performance measurements.

The checked-in development evidence derives `MNCS-L4` status from raw observations rather
than self-asserted labels. The companion process record targets `MNCDS-D2`; it does not
claim independent protected holdout evidence or lifecycle release assurance. These are
experimental development results, not accredited certification or a production-safety
claim.

## Run the complete study

```bash
make thorough
```

This command regenerates the candidate and workloads, performs strict GCC and Clang builds,
runs the expanded correctness, mutation, checkpoint, sanitizer, structural, and harness
regression suites, executes the controlled benchmark, packages the evidence graph, and
validates both the MNCS bundle and MNCDS record.

The full study requires Python 3.11+, a C11 compiler, and preferably both GCC and Clang.
Generated binaries and workload byte streams are excluded from version control. Compact
workload identities and captured result records are committed.

## Evaluation epoch 2

The second evaluation epoch preserves the original 1.15 throughput threshold and 1.10
maximum p99 latency ratio while strengthening the evidence protocol:

- Eleven fragmentation sizes are compared across every workload, with separate reference,
  candidate, and baseline output hashes.
- Six mutation classes are tested at three fragmentation sizes with explicit rejection
  reasons, counters, and outputs.
- Checkpoint testing covers cross-implementation restore, atomic failure preservation, and
  four corruption classes.
- AddressSanitizer and UndefinedBehaviorSanitizer run across all workloads and multiple
  fragmentation sizes with recorded flags and runtime options.
- The structural provider uses Clang AST observations plus bounded source-order checks and
  is regression-tested against representative defective fixtures.
- Performance samples include warmups, counterbalanced order, CPU-affinity observations,
  aggregate durations of at least 100 ms, raw p99 inputs, and a deterministic bootstrap
  confidence interval.

See `preregistration.json`, `evidence/results/study-summary.json`, and
`evidence/results/benchmark.json` for the declared protocol and machine-readable results.
