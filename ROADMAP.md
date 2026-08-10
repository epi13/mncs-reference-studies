# Roadmap

This roadmap is intentionally evidence-first. Dates are not promises; phases describe dependency order.

## Phase 0 — repository foundation

- [x] Separate empirical studies from the core MNCS standards repository.
- [x] Establish `case-studies/`, `studies/`, and `reference-studies/` as distinct research lanes.
- [x] Define initial MRS metadata and repository validation.
- [x] Draft shared protocol, metrics, evidence, agent-evaluation, and reproducibility guidance.
- [x] Scaffold MRS-001, MRS-002, and MRS-003.

## Phase 1 — migrate existing MNCS research

Move the existing `case-studies/` and `studies/` bodies from `machine-native-complexity-standard` in reviewable batches. Preserve source commit identity, evidence boundaries, commands, and study-local history/provenance notes. Update the standards repository to link here only after target content is merged and validated.

### Case-study migration inventory

- CacheForge
- Composed Gateway
- dSense Desk Pet
- EdgeStream
- EdgeStream Remote Water Integration
- Go Gateway
- Multilingual Stream
- RAVEL
- Remote Water Control

### Study migration inventory

- Recursive Analyzer
- Recursive Architecture Comparison
- Recursive Experience Substrate

The source root Makefile currently couples these studies to targets including `recursive-study`, `recursive-architecture-study-check`, `recursive-experience-substrate-check`, `cacheforge-*`, `ravel-*`, `multilingual-*`, `go-gateway`, and `composed-gateway`. Migration PRs must repair those root/workflow dependencies deliberately rather than copying them blindly.

## Phase 2 — Tier 1 reference reimplementations

### MRS-001 — JSON parser

Freeze a mature reference implementation and behavioral corpus, build an idiomatic conventional Rust arm, then build an MNCS-style Rust arm. Emphasize malformed input, nesting/resource limits, differential behavior, fuzzing, mutation testing, and controlled agent maintenance tasks.

### MRS-002 — LZ4-style block codec

Use a deterministic codec surface to test whether stronger structural verification can coexist with competitive runtime and memory behavior. Emphasize bounds, integer arithmetic, buffer handling, round-trip correctness, corruption handling, and performance.

### MRS-003 — HTTP/1 parser

Use a protocol parser to stress incremental state, partial input, ambiguity, malformed framing, resource constraints, fuzzing, and security-oriented verifier behavior.

## Phase 3 — distributed and agent evaluation

Integrate the local harness and MNCS Fabric so study runs can be assigned across heterogeneous workers/models while preserving model, machine, tool, environment, and evidence identity. Add repeatable agent task packs and hidden verifier suites.

## Phase 4 — Forge and evidence automation

Use the Forge to strengthen verifier generation, threat-oriented checks, evidence manifests, mutation campaigns, and reproducibility gates. Avoid letting automation silently redefine the study protocol.

## Phase 5 — RAVEL / MNEL learning loop

Package labeled study trajectories for later RAVEL and Machine-Native Experimental Learning work. Retain failures as training/evaluation evidence rather than exporting only successful traces. Distinguish teacher-generated proposals from independently verified outcomes.

## Phase 6 — MNCS-Language reproduction

When MNCS-Language is mature enough, add a language-native arm to frozen studies. Reuse the same behavioral contracts and external corpora where possible so language results remain connected to the original experiment rather than becoming unrelated demos.

## Later tiers

Expand beyond small parsers/codecs into larger libraries and applications only after the protocol survives multiple Tier 1 studies. Later candidates may include concurrent bounded queues, allocators, image decoders, storage components, gateways, and eventually recognizable mature systems.
