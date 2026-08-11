# Structural-harness feedback

Evaluation epoch 2 replaces the original pattern-only ledger with a candidate-bound Clang
AST and source-order provider. The revised provider records a narrow semantic scope instead
of marking every passing observation as a suspected false negative.

The regression corpus now preserves representative disagreement and failure cases for:

1. missing generated identity markers;
2. processor-path dynamic allocation;
3. missing frame-length validation;
4. checksum validation not established before state mutation;
5. workload-aware benchmark branches; and
6. bypassed checkpoint CRC validation.

The evaluator must report `FAIL` when a declared invariant is contradicted and `UNKNOWN`
when Clang cannot establish an AST-dependent observation. Joern remains a separate optional
provider and is never inferred from the Clang result.

Machine-readable provider observations are written to `evidence/results/structural.json`.
The provider regression result is written to `evidence/results/harness-regression.json`.
