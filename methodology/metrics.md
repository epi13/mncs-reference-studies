# Metrics

No single metric represents MNCS quality. Each study selects metrics that answer its frozen questions.

## Correctness

Examples: corpus pass rate, differential mismatches, known-vector compatibility, round-trip correctness, malformed-input classification, deterministic replay, state digest equality.

Correctness gates should usually be hard gates rather than values averaged with performance.

## Assurance and failure detection

Examples: fuzz failures, time-to-first failure, mutation survival/detection, sanitizer findings, static-analysis findings, contract violations, verifier rejection, invalid-state construction tests, recovery/fallback correctness.

Distinguish a property prevented by the language/type system from one detected by an MNCS-specific verifier.

## Resource behavior

Examples: peak resident memory, allocation counts, bounded-buffer compliance, maximum nesting/depth, output bounds, queue capacity, CPU work, disk/network use, binary size.

## Performance

Examples: throughput, latency distribution, operations per second, compile time, startup time. Record enough environment information to explain hardware/runtime differences.

Do not treat cross-language performance as universally normalized simply because input data is shared.

## Machine maintainability

Examples: task success rate, hidden-test pass rate, regressions introduced, attempts to success, context/tokens consumed, tool calls, wall-clock time, model size, number of files inspected, verifier feedback cycles.

These metrics are particularly important to MNCS because human readability and machine-operable structure may be different optimization targets.

## Structural measures

Possible study-local measures include runtime-check count, compile-time encoded invariants, unsafe-code surface, contract count, verifier coverage, generated/authored code ratio, dependency count, and implementation size. These are descriptive unless the study preregisters a causal question around them.

## Reporting

Report raw values and distributions before derived summaries. Label observations as directly comparable, normalized-but-imperfect, language-specific, or non-comparable when needed. Do not collapse unlike metrics into a universal score.
