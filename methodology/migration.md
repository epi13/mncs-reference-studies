# Migrating studies from the core MNCS repository

The migration should reduce coupling without losing provenance.

## Recommended sequence

1. Freeze the source commit SHA in `machine-native-complexity-standard`.
2. Move/copy one coherent study (or tightly coupled study pair) into this repository on a dedicated PR.
3. Add `MIGRATION.md` inside the migrated study with source repository, source commit, original path, migration date, and any path/build changes.
4. Repair root-relative Makefile/workflow/document links here without changing scientific thresholds or regenerating frozen evidence unless required and explicitly recorded.
5. Run the study's existing tests and evidence-integrity checks.
6. Merge the target migration.
7. In a separate source-repository PR, replace the old study body with links or remove it as appropriate, and update root workflows/docs.

This order avoids a period where the only authoritative copy is half-migrated.

## Evidence preservation

Migration is not a new experimental epoch by itself. Do not rewrite preregistration files, expected results, hashes, or claim statuses merely because paths changed. If a build-system change alters produced evidence, record that explicitly and consider starting a new epoch.

## Git history

A normal cross-repository copy does not preserve Git history automatically. At minimum preserve source commit identity in `MIGRATION.md`. If full file history is important, perform a history-preserving import using appropriate Git tooling and review the resulting history before pushing.

## Workflows

Do not blindly copy root workflows from the standards repository. Adapt workflow triggers and paths so this repository owns study execution while the core MNCS repository retains standards/conformance work.
