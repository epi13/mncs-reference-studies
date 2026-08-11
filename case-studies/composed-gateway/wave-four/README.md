# Composed Gateway Wave Four

Wave Four is the evidence-custody and claim-readiness layer for the C11/Go/Rust composed gateway. It preserves all Wave Three evidence and identities. The public repository defines the contracts and reference verifiers needed for external evidence, but it does not claim that its own processes are independent.

## Scope

Wave Four adds:

- protected-holdout custody and disclosure records;
- developer, custodian, evaluator, witness, and release-authority separation;
- cross-host evidence reconciliation by system, epoch, component, tool, and semantic-output identities;
- separate MNCS implementation and MNCDS lifecycle readiness aggregation;
- a bounded Go loopback HTTP service boundary with cancellation, malformed-input, size, version, shutdown, and restart tests;
- release monitoring, rollback, and retirement policies;
- a witnessed release-drill record format;
- deterministic PASS, FAIL, and UNKNOWN fixtures.

## Run

```bash
make check
```

The fixture corpus proves that the reference logic preserves `FAIL > UNKNOWN > PASS`. Fixture PASS results are conformance tests for the tools; they are not evidence that an external custodian, evaluator, witness, or production environment exists.

## Independence boundary

A protected result can pass only when:

1. preregistration precedes candidate freeze;
2. candidate freeze precedes corpus disclosure;
3. disclosure precedes evaluation;
4. developer, custodian, and evaluator identities are distinct;
5. corpus, raw result, normalized result, and attestation are content-addressed;
6. development participants had no access to the corpus before disclosure.

Software can validate these records, but organizational independence remains an externally attested fact.

## Current result

The checked-in local readiness result is `REVIEW_REQUIRED`. The development epoch, deterministic regeneration, and loopback service-boundary tests pass. Cross-host agreement, protected holdout, independent evaluation, witnessed replacement, operational monitoring, retirement exercise, and release authorization remain `UNKNOWN`. Formal MNCS and MNCDS statuses remain `UNKNOWN`, and promotion is prohibited.
