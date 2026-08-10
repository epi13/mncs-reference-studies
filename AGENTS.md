# Agent instructions

This repository is the empirical research and validation companion to the Machine-Native Complexity Standard (MNCS).

## Prime directive

Do not optimize a study to make MNCS look favorable. Preserve the declared comparison, record negative evidence, and distinguish observations from claims.

## Repository lanes

- `reference-studies/` contains numbered MRS controlled reimplementation studies.
- `case-studies/` contains MNCS experimental case studies migrated from the core standards repository.
- `methodology/` contains shared protocol rules.
- `schemas/` defines machine-readable study metadata.

Do not merge these lanes casually. Existing migrated case studies may have their own historical protocols; new MRS studies must follow the shared MRS protocol unless an explicit deviation is recorded.

## Required behavior for MRS work

1. Freeze and identify the upstream reference before implementation work that depends on it.
2. Record upstream license, version/commit, source URL, and provenance.
3. Preserve an independent conventional implementation arm when the study is intended to isolate MNCS effects from language effects.
4. Use the same external behavioral contract and corpus across arms wherever technically meaningful.
5. Never weaken a gate, remove a failing fixture, or change a benchmark workload after seeing a candidate result without recording a new evaluation epoch.
6. Keep generated artifacts distinguishable from authored contracts and readable authority code.
7. Record environment details sufficient to explain compiler, runtime, CPU, accelerator, OS, and dependency differences.
8. Prefer deterministic seeds and content hashes for evidence-bearing inputs.
9. Treat UNKNOWN and REVIEW_REQUIRED as legitimate outcomes.
10. Never promote a bounded development PASS into a general MNCS or MNCDS claim.

## Agent evaluation

Agent-maintenance experiments must freeze the task packet before comparing implementations. Hidden/verifier tests must not be exposed to the agent being evaluated. Record model identity, serving configuration, tools, context, attempts, token/compute data when available, wall-clock data when meaningful, and the exact pass/fail criterion.

Do not silently give one comparison arm more information or stronger tools.

## MNCS family integration

When the MNCS Forge or related MCPs are available, use them for evidence, verifier, and provenance work where they improve reproducibility. Harness/Fabric execution should preserve worker/model/environment identity rather than collapsing distributed runs into one anonymous result.

RAVEL/MNEL learning material derived from these studies must retain outcome labels, study/epoch identity, provenance, and whether a trajectory succeeded or failed.

## Validation

Run from the repository root:

```bash
make check
```

Study-specific checks belong inside each study and should be callable without modifying frozen evidence by default.
