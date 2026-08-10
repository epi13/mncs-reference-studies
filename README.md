# MNCS Reference Studies

Empirical case studies and reference reimplementations for evaluating the Machine-Native Complexity Standard (MNCS) against proven software architectures, using conventional, MNCS-style, and future MNCS-Language implementations.

This repository is the experimental and validation companion to the [Machine-Native Complexity Standard](https://github.com/epi13/machine-native-complexity-standard). The standard defines ideas and requirements; this repository is where those ideas are challenged against controlled workloads, mature software behavior, adversarial tests, and repeatable agent tasks.

## Study families

### Reference reimplementation studies (`reference-studies/`)

The MRS series starts from a proven or widely used implementation and holds behavior as constant as practical while changing representation and architecture.

The intended long-term comparison is:

```text
upstream/reference implementation
            |
            v
   conventional Rust port
            |
            v
       MNCS-style Rust
            |
            v
 future MNCS-Language implementation
```

The conventional Rust arm is important: it separates gains attributable to Rust itself from gains attributable to MNCS structure, contracts, verifier boundaries, and machine-oriented representation.

| Study | Tier | Subject | Status | Primary emphasis |
|---|---:|---|---|---|
| [MRS-001](reference-studies/MRS-001-json/README.md) | 1 | JSON parser | PLANNED | correctness, malformed input, agent modification |
| [MRS-002](reference-studies/MRS-002-lz4/README.md) | 1 | LZ4-style block codec | PLANNED | performance, bounds, memory behavior |
| [MRS-003](reference-studies/MRS-003-http-parser/README.md) | 1 | HTTP/1 parser | PLANNED | protocol state, adversarial input, streaming |

Exact upstream implementations are intentionally not frozen yet. Each study must record upstream identity, license, version/commit, provenance, and the reason it was selected before implementation begins.

### MNCS case studies (`case-studies/`)

The existing MNCS repository already contains research case studies such as CacheForge, EdgeStream, Remote Water Control, Multilingual Stream, Go Gateway, Composed Gateway, RAVEL, and dSense Desk Pet. They will migrate here in separate PRs so the core standards repository is not burdened with experimental code and generated evidence.

The migration landing zone and current inventory are in [`case-studies/README.md`](case-studies/README.md).

## What this repository is trying to measure

Runtime performance matters, but it is only one axis. Studies should capture, when applicable:

- behavioral correctness and differential equivalence;
- malformed/adversarial input handling;
- memory and resource bounds;
- compiler/type-system guarantees versus runtime checks;
- fuzzing and mutation-test outcomes;
- verifier and contract coverage;
- runtime, memory, binary size, and build cost;
- agent success rate on controlled maintenance tasks;
- regressions introduced by agent modifications;
- tokens/context/tool calls required for successful agent work;
- cross-model and cross-substrate reproducibility;
- evidence suitable for later harness, RAVEL, or MNEL learning experiments.

There is deliberately **no universal MNCS score**. A favorable result on one metric does not erase regressions on another metric.

## Evidence and claim boundary

A favorable development result is not automatically a formal MNCS or MNCDS claim. Every study must declare its evidence boundary and promotion status. `PASS` inside a bounded experiment means only that the frozen candidate passed the declared protocol for that experiment.

Negative and null results are first-class evidence. If conventional Rust performs better, if an MNCS construct adds cost without benefit, or if an agent performs worse against an MNCS representation, that result belongs in the record.

See [`methodology/evidence-and-claims.md`](methodology/evidence-and-claims.md).

## Repository layout

```text
case-studies/          existing MNCS experiments migrated from the standards repo
reference-studies/     numbered MRS reimplementation experiments
methodology/           shared experimental protocol and measurement rules
schemas/               machine-readable study metadata contracts
templates/             starting files for new studies
tools/                 repository-level validation and later comparison tooling
.github/                CI and contribution workflow
```

## Quick start

```bash
make check
```

The initial repository validator uses only the Python standard library. It checks the structural invariants of the MRS manifests so the repository can establish a stable machine-readable surface before heavier study tooling arrives.

## Relationship to the MNCS family

This repository is intended to become a repeatable workload and evidence source for the wider MNCS family. The local harness and Fabric can eventually distribute and reproduce study tasks; the Forge can contribute verifier/evidence machinery; and RAVEL/MNEL can consume carefully labeled successful and failed trajectories. Future MNCS-Language implementations can rerun the same frozen study contracts rather than inventing new demonstrations.

The goal is not to prove MNCS by construction. The goal is to make MNCS easier to falsify, measure, improve, and reproduce.
