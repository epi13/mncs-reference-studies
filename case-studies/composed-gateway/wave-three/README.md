# Composed Gateway Wave Three

Wave Three is a measured development epoch for the C11/Go/Rust composed gateway. It does not rewrite the Wave Two component or boundary records. New host, authority, binding, process-protocol, preregistration, and evidence identities are used throughout.

## Scope

The epoch evaluates:

- deterministic generated-binding regeneration and drift detection;
- strict C11 parsing through the existing allocation-free ABI;
- a new Go host with atomic checkpoints and identity-bound restore;
- a pinned Rust 1.97.1 authority using the new `V2` process protocol;
- uninterrupted, interrupted/restarted, and readable-replacement execution;
- rejection of stale, partial, incompatible, and binding-mismatched checkpoints;
- eighteen retained fault and limitation outcomes;
- repeated latency, child CPU, RSS observation, process-boundary, checkpoint, and recovery measurements;
- a second implementation of evidence aggregation;
- Ubuntu and macOS hosted reproduction artifact jobs.

## Run

```bash
make static
make local          # Records Rust-dependent evidence as UNKNOWN when Rust is unavailable.
make check          # Requires pinned Rust and runs the full epoch.
```

The full CI result is written beneath `evidence/actual/` and uploaded as a workflow artifact. Generated runtime artifacts are intentionally not committed automatically.

## Recovery and replacement

Checkpoints bind the system contract, source header, binding specification, binding generator, input digest, authority identity, processed count, accumulated state, and a state digest. Restore rejects any mismatch. The only replacement allowed by this epoch is an explicitly authorized transition from `rust-authority-v2` to `go-readable-authority-v2`; the final digest must match uninterrupted execution.

A successful hosted run supports the narrow regeneration/replacement drill subclaim. It does **not** establish full MNCDS-D4 because release approval, production monitoring, retirement triggers, independent witnessing, and protected evidence custody remain absent.

## Claim boundary

The checked-in local development record is `REVIEW_REQUIRED` because Rust was unavailable in the recorded local environment. Formal MNCS and MNCDS statuses remain `UNKNOWN`, promotion is prohibited, protected holdout remains `UNKNOWN`, and the structurally separate evaluator is not organizationally independent.
