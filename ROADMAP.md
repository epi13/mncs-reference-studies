# Roadmap

This roadmap is intentionally evidence-first. Dates are not promises; phases describe dependency order.

## Phase 0 — repository foundation

- [x] Separate empirical studies from the core MNCS standards repository.
- [x] Establish `case-studies/`, `studies/`, and `reference-studies/` as distinct research lanes.
- [x] Define initial MRS metadata and repository validation.
- [x] Draft shared protocol, metrics, evidence, agent-evaluation, and reproducibility guidance.
- [x] Scaffold MRS-001, MRS-002, and MRS-003.

## Phase 1 — migrate existing MNCS research

The existing `case-studies/` and `studies/` bodies from `machine-native-complexity-standard` have been imported in reviewable batches. Source commit identity, evidence boundaries, commands, and study-local provenance notes are preserved. The standards repository now links here for empirical work.

Migration status: all nine historical case studies and all three historical research studies are present in this repository at frozen source commit `80f08d312dce963265c7f69ac5b4bae8245bd692`. The destination owns empirical checks; normative MNCS/MNCDS validation remains a separately declared dependency.

### Case-study migration inventory

- [CacheForge](case-studies/cacheforge/README.md) — VALIDATED
- [Composed Gateway](case-studies/composed-gateway/README.md) — VALIDATED
- [dSense Desk Pet](case-studies/dsense-desk-pet/README.md) — VALIDATED
- [EdgeStream](case-studies/edgestream/README.md) — VALIDATED
- [EdgeStream Remote Water Integration](case-studies/edgestream-remote-water-integration/README.md) — MIGRATED
- [Go Gateway](case-studies/go-gateway/README.md) — VALIDATED
- [Multilingual Stream](case-studies/multilingual-stream/README.md) — VALIDATED
- [RAVEL](case-studies/ravel/README.md) — VALIDATED_WITH_LIMITATION
- [Remote Water Control](case-studies/remote-water-control/README.md) — VALIDATED

### Study migration inventory

- [Recursive Analyzer](studies/recursive-analyzer/README.md) — VALIDATED
- [Recursive Architecture Comparison](studies/recursive-architecture-comparison/README.md) — VALIDATED
- [Recursive Experience Substrate](studies/recursive-experience-substrate/README.md) — VALIDATED

The destination `GNUmakefile` owns the empirical compatibility targets. Normative
validator dependencies remain explicit through `MNCS_STANDARDS_ROOT`; no sibling
checkout is required for the default destination check.

## Phase 2 — Tier 1 reference reimplementations

### MRS-001 — JSON parser

Freeze a mature reference implementation and behavioral corpus, build an idiomatic conventional Rust arm, then build an MNCS-style Rust arm. Emphasize malformed input, nesting/resource limits, differential behavior, fuzzing, mutation testing, and controlled agent maintenance tasks.

### MRS-002 — LZ4-style block codec

Use a deterministic codec surface to test whether stronger structural verification can coexist with competitive runtime and memory behavior. Emphasize bounds, integer arithmetic, buffer handling, round-trip correctness, corruption handling, and performance.

### MRS-003 — HTTP/1 parser

Use a protocol parser to stress incremental state, partial input, ambiguity, malformed framing, resource constraints, fuzzing, and security-oriented verifier behavior.

## Phase 3 — distributed and agent evaluation

Integrate the optional MNCS Harness and MNCS Fabric so study runs can be assigned across heterogeneous workers/models while preserving model, machine, tool, environment, and evidence identity. Add repeatable agent task packs and hidden verifier suites.

## Phase 4 — Forge and evidence automation

Use the Forge to strengthen verifier generation, threat-oriented checks, evidence manifests, mutation campaigns, and reproducibility gates. Avoid letting automation silently redefine the study protocol.

## Phase 5 — RAVEL / MNEL learning loop

Package labeled study trajectories for later RAVEL and Machine-Native Experimental Learning work. Retain failures as training/evaluation evidence rather than exporting only successful traces. Distinguish teacher-generated proposals from independently verified outcomes.

## Phase 6 — MNCS-Language reproduction

When MNCS-Language is mature enough, add a language-native arm to frozen studies. Reuse the same behavioral contracts and external corpora where possible so language results remain connected to the original experiment rather than becoming unrelated demos.

## Later tiers

Expand beyond small parsers/codecs into larger libraries and applications only after the protocol survives multiple Tier 1 studies. Later candidates may include concurrent bounded queues, allocators, image decoders, storage components, gateways, and eventually recognizable mature systems.
