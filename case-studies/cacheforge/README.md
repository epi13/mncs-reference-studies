# CacheForge LLM KV-cache case study

CacheForge is a bounded, trace-driven MNCS research case study for an AI/ML
infrastructure component: LLM key-value cache allocation, prefix reuse, and eviction.
It compares readable conventional policies with a generated 64-state eviction table
under the same deterministic hybrid-cache simulator.

The machine-generated policy can only propose victims. A compact readable authority
validates that every proposed block exists, is unique, has no live owners, and can be
evicted without exceeding the declared memory envelope. Invalid proposals are rejected
and routed through a readable LRU fallback before state mutation.

## Initial development result

The initial checked-in development study passes its declared gates:

- **12.844% fewer recomputed blocks than LRU** across the declared traces;
- no recomputation regression in the low-reuse control workload;
- deterministic planning work below the declared 1.50 baseline ratio;
- duplicate and unknown-victim mutation policies rejected without corruption;
- checkpointed and uninterrupted execution converge on the same final state digest.

The initial benefit is concentrated in the alternating-tenant workload. It remains useful
as a bounded demonstration, but it is not evidence of general KV-cache superiority.

## Evaluation epoch 2

Epoch 2 broadens the repository-visible development protocol before any protected claim:

- 16 independent deterministic traces;
- four paired cache capacities: 16, 24, 32, and 48 blocks;
- 64 capacity-repeated evaluations and 3,072 total requests;
- varied prefix reuse, cancellation, and generated-token lengths;
- comparison against both LRU and readable segmented LRU;
- per-evaluation comparison against whichever conventional baseline performs best.

The frozen candidate passes the preregistered epoch-2 development gates:

- 39,654 candidate recomputations versus 41,167 for the per-evaluation strongest baseline;
- **3.675% aggregate reduction** in recomputed blocks;
- improvement in 53 of 64 evaluations;
- median candidate-to-baseline ratio of 0.966886;
- p95 ratio of 1.035928 and worst observed ratio of 1.051546;
- no candidate fallback use or rejected candidate proposals;
- every capacity aggregate is non-regressive.

The distribution also exposes a real weakness: at 48 blocks, the candidate regresses in
9 of 16 evaluations and has a median scenario ratio above 1.0, although the capacity
aggregate remains slightly favorable. The high-capacity regressions cluster in workloads
with only one or two hot system-prefix families. Epoch 2 therefore remains
`REVIEW_REQUIRED`; formal MNCS and MNCDS status remain `UNKNOWN`.

## Evidence integrity amendment

A post-run review added evidence-integrity controls without changing the candidate,
workload, or performance thresholds:

- all 64 scenario observations are written to
  `evidence/results/epoch-2-scenario-results.json`;
- the summary includes seed-clustered, capacity, and hot-prefix-regime diagnostics;
- SHA-256 identities bind the candidate, generator, simulator, authority, baselines,
  evaluator, preregistration, and protected-input schema;
- `epoch-2-evidence-amendment.json` records that the performance protocol was not changed.

## Protected evaluation boundary

The repository includes a strict external trace-bundle schema and evaluator. The loader
validates every bundle against the published JSON Schema before constructing simulator
objects. Unknown properties and invalid types are rejected rather than ignored or coerced.

Protected traces are not committed to the repository. The evaluator records the bundle
digest, compares the frozen candidate with both conventional baselines, and reports:

- `schema_valid: true` only after full schema validation;
- `protocol_eligible: NOT_ESTABLISHED`;
- `custody_verified: NOT_ESTABLISHED`;
- `formal_mncs_status: UNKNOWN`;
- `formal_mncds_status: UNKNOWN`;
- `evaluation_result: REVIEW_REQUIRED`;
- `promotion_authorized: false`.

This prevents a schema-valid or numerically favorable bundle from silently becoming a
formal claim. Trace custody, independence, protocol eligibility, and release decisions
remain separate review obligations.

## Architecture

```text
model cache groups + request trace
                |
                v
      generated eviction table
           proposal only
                |
                v
      readable allocation authority
       validate / reject / fallback
                |
                v
 deterministic hybrid-cache simulator
                |
       +--------+---------+
       |                  |
       v                  v
 evidence metrics     checkpoint digest
```

The simulator includes one full-attention cache group and one sliding-window group. It
models exact prefix identities, request ownership, cancellation, block pressure, eviction,
checkpoint restore, and deterministic final-state hashing. It processes requests
sequentially and does not yet model continuous batching or overlapping live sequences.

## Run

From the repository root:

```bash
make cacheforge-test
make cacheforge-study
make cacheforge-epoch2
```

Or from this directory:

```bash
make test
make study
make epoch2
```

To evaluate an externally held trace bundle without committing the traces:

```bash
make protected-evaluation \
  BUNDLE=/path/to/protected-traces.json \
  OUTPUT=/path/to/protected-result.json
```

`make epoch2` verifies the generated candidate, runs the tests, evaluates every seed and
capacity against LRU and segmented LRU, and deterministically rewrites both
`evidence/results/epoch-2-development.json` and
`evidence/results/epoch-2-scenario-results.json`.

## Repository layout

```text
contract/                          readable scope, authority, and invariant contract
generator/                         frozen generated-policy specification
machine/                           generated 64-state eviction table
src/cacheforge/                    simulator, authority, policy, and evaluation code
tests/                             invariant, recovery, epoch-2, and bundle tests
tools/                             deterministic study and protected-evaluation runners
evidence/results/                  checked-in summaries and scenario observations
preregistration.json               initial thresholds and selection rule
epoch-2-preregistration.json       frozen broader evaluation protocol
epoch-2-evidence-amendment.json    post-run evidence-integrity amendment
protected-trace-bundle.schema.json enforced external trace input contract
assurance-case.json                initial development assurance record
epoch-2-assurance-case.json        epoch-2 review-required assurance record
threat-model.json                  threats, mitigations, and residual UNKNOWNs
```

## Claim boundary

A development `PASS` means only that the frozen candidate passed the declared deterministic
simulator protocol. It does not establish GPU correctness, production performance,
protected-holdout independence, inference-server compatibility, tenant isolation,
continuous-batching behavior, or formal MNCS/MNCDS conformance.
