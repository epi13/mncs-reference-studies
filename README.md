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

The historical case studies have migrated here from the core repository. They remain a separate lane from the numbered MRS series and retain their original protocols, evidence boundaries, and claim language. See the [complete case-study inventory](case-studies/README.md).

The migration landing zone and current inventory are in [`case-studies/README.md`](case-studies/README.md).

### Existing MNCS research studies (`studies/`)

The historical Recursive Analyzer, Recursive Architecture Comparison, and Recursive Experience Substrate studies have also migrated here. They are not the new MRS series, so this repository preserves a distinct [`studies/`](studies/README.md) lane rather than renaming them during the move.

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
case-studies/          existing MNCS case studies migrated from the standards repo
studies/               existing MNCS research studies migrated from the standards repo
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

The default `make` entrypoint is the destination-owned `GNUmakefile`. It validates migration provenance and MRS metadata, then runs non-evidence-writing checks across the migrated studies. The historical root `Makefile` is retained byte-identically because the frozen RAVEL 0.5 source manifest binds it; use the destination `GNUmakefile` through ordinary `make` commands.

Some historical checks intentionally depend on normative MNCS/MNCDS validator tooling that remains in the [standards repository](https://github.com/epi13/machine-native-complexity-standard). MNCDS itself is now a sibling specification, the [Machine-Native Complexity Development Specification](https://github.com/epi13/machine-native-complexity-development-specification). Those checks are exposed through explicit targets and require `MNCS_STANDARDS_ROOT`; the destination does not duplicate normative conformance code.

## Relationship to the MNCS family

This repository is intended to become a repeatable workload and evidence source for the wider MNCS family. The optional [MNCS Harness](https://github.com/epi13/mncs-harness) and Fabric can eventually distribute and reproduce study tasks; the Forge can contribute verifier/evidence machinery; and RAVEL/MNEL can consume carefully labeled successful and failed trajectories. Future MNCS-Language implementations can rerun the same frozen study contracts rather than inventing new demonstrations.

The goal is not to prove MNCS by construction. The goal is to make MNCS easier to falsify, measure, improve, and reproduce.

## Migration provenance

The complete migration record is in [`MIGRATION.md`](MIGRATION.md). Every migrated study contains a study-local `MIGRATION.md` recording the frozen source commit, source and destination paths, adaptation decisions, evidence status, and validation.
