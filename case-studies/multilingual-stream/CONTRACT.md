# Multilingual bounded-stream contract

## Purpose

Process a bounded line-oriented stream of unsigned decimal integers and return one deterministic
summary. The useful benefit is throughput improvement by the generated Rust candidate relative to
the readable Rust baseline while preserving the same correctness, malformed-input, resource, and
recovery envelope. C11 is the controlled cross-language anchor, not the optimization baseline.

## Input

- UTF-8/ASCII bytes only.
- Zero or more records, one unsigned decimal integer per line.
- Values are in `0..=100000`.
- LF and CRLF are accepted; a final newline is optional.
- Empty records, signs, spaces, non-digits, out-of-range values, NUL bytes, and input above 1 MiB
  are malformed.

## Output

Successful execution writes exactly one JSON line:

```json
{"count":3,"sum":6,"checksum":1883237471}
```

`count` and `sum` are exact unsigned values. `checksum` starts at zero and, for every input value
`x`, becomes `((checksum * 16777619) XOR x) mod 2^32`.

Malformed input exits with code 2, writes no stdout, and writes exactly `invalid input\n` to stderr.

## Resource and recovery envelope

- Maximum input: 1,048,576 bytes.
- No network, filesystem write, subprocess, thread, clock, random source, or environment-dependent
  behavior in the subject implementations.
- Recovery is deterministic replay: rerunning the same complete input after interruption must
  produce the same output.
- Benchmarks use the same generated workload, process invocation method, warmup count, repeat count,
  and host observation record. Cross-language timings are normalized but imperfect comparisons.

## Claim boundary

A successful development run establishes only this contract on the declared host and toolchains.
It does not establish universal safety, all C undefined-behavior absence, Rust macro or FFI proof,
cross-host superiority, or formal MNCS/MNCDS conformance.
