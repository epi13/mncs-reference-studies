# MNCS research studies

This directory is the migration target for the non-`case-studies/` research studies currently stored under `epi13/machine-native-complexity-standard/studies`.

These are distinct from the new numbered MRS reference-reimplementation series and should retain their existing identities and experimental boundaries during migration.

## Source inventory

As of the repository bootstrap, the core MNCS repository contains:

| Source directory | Study | Migration status |
|---|---|---|
| [`recursive-analyzer/`](recursive-analyzer/README.md) | Recursive Analyzer study | VALIDATED |
| [`recursive-architecture-comparison/`](recursive-architecture-comparison/README.md) | Recursive Architecture Comparison | VALIDATED |
| [`recursive-experience-substrate/`](recursive-experience-substrate/README.md) | Recursive Experience Substrate | VALIDATED |

The core repository currently calls these studies from root Makefile targets such as `recursive-study`, `recursive-architecture-study-check`, and `recursive-experience-substrate-check`. Those root dependencies need to move or be replaced with links only after the target study migration is validated here.

## Migration rules

Use the same provenance rules as `case-studies/`:

1. record the source repository and source commit SHA;
2. preserve study-local inputs, validators, tests, expected results, and claim language;
3. repair root-relative commands without changing scientific thresholds;
4. avoid regenerating frozen evidence during migration unless explicitly required and recorded;
5. add a `MIGRATION.md` documenting source path and material build/path changes;
6. validate here before removing or redirecting the source copy.

See [`../methodology/migration.md`](../methodology/migration.md) and the study-local `MIGRATION.md` files.
