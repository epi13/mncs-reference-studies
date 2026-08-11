# Post-Wave-Five local evidence roadmap

> Historical note: this audit drove the MNCS 0.3-rc.1 / MNCDS 0.1-rc.1
> implementation iteration. The current gap matrix and release evidence index
> supersede its local-work recommendations; its external evidence record is preserved.

This roadmap records the repository audit performed on 2026-07-28 from commit
`0a5a1d0423c477749eec72be81b26a3b4ab07314`. It supersedes any earlier informal
sequence of future waves. It is an implementation and evidence plan, not a normative
change or an RFC acceptance record.

MNCS 0.2 remains the current specification. MNCDS 0.1-draft and RFCs 0004 through 0007
remain Draft. Nothing in this roadmap promotes a case study, RFC, MNCS, or MNCDS
claim.

## Current project-family reconciliation — 2026-08-08

This section is the current successor to older informal Codex next-step notes. The
named `docs/codex-next-steps.md`, `docs/networked-standard-evolution.md`, and
execution-assurance note paths are not present in this checkout; the existing roadmap,
release-candidate documents, Forge integration guide, and sibling repositories were
used instead. Historical roadmap text below is retained for provenance.

| Area | Current disposition | MNCS actionability |
|---|---|---|
| MNCS Forge | Consolidated micro-verifiers, versioned records/migrations, lifecycle state machine, transactional storage, application-service decomposition, unified CLI/MCP dispatch, and Python compatibility-boundary work are implemented or actively advanced in the sibling Forge repository. | Do not duplicate Forge here. A future small placement micro-verifier should consume this profile through the public interface. |
| RAVEL | Standalone sibling project now owns adaptive evidence selection, memory, causal attribution, and learning. Its authority model keeps raw evidence immutable, failures retained, confidence separate from status, and promotion governed outside RAVEL. | Reference RAVEL as an advisory consumer; retain historical in-repository RAVEL evidence and do not migrate or relabel it. |
| MNEL | Standalone sibling project has an executable learned-provider runtime with persistent admission, Rust-first hosting, identity-bound snapshots, resource ceilings, backend-neutral CPU/full-accelerator/sequential-offload placement, probes, precision checks, and bounded AUTO recovery. | Use its observations to shape a provider-neutral evidence vocabulary; MNEL cannot issue MNCS conformance. |
| GIMP Local MCP | Local vision runtime demonstrates sequential offload, host-RAM weight storage, transient accelerator execution, reserve/cap planning, real probes, OOM recovery, and allocation/RSS/offload witnesses. | Treat as generic implementation evidence, not a machine-independent requirement or benchmark claim. |
| Execution placement | New in this iteration as `0.1-experimental`, non-normative `execution-placement-evidence`. | Locally actionable in MNCS: schema, validator, CLI, fixtures, and documentation. |
| Typed execution receipts | EA-NEXT-001 is implemented as `0.1-experimental`, non-normative `mncs-execution-receipt`; it records immutable runner observations and optionally links placement evidence. | Locally actionable follow-ons are immutable bundles, isolation runners, replay, attestations, and future adapter integration; none are claimed complete here. |
| Immutable execution bundles | EA-NEXT-002 is implemented as `0.1-experimental`, non-normative `mncs-execution-bundle`; it binds deterministic manifest/content identity to a bounded ZIP transport and can be checked against receipt bundle identities. | Locally actionable follow-ons are the Linux isolation runner, replay, verity, and future Forge/Fabric adapters; bundle integrity is not execution assurance. |
| Execution challenges and replay | EA-NEXT-005 is implemented as `0.1-experimental`, non-normative verifier-issued challenges and local replay receipts. It binds fresh nonces to receipt scope and records single-use consumption with a persisted local time watermark. | Local replay detection does not establish host-root resistance, custody, independence, isolation, conformance, or promotion; signing and Linux isolation remain separate. |

Old Forge tasks are therefore marked `DONE in sibling Forge`, `ACTIVE in sibling Forge`,
or `NOT AN MNCS TASK` by the table above rather than left as stale local backlog. The
remaining local follow-on is a small Forge/public-interface hook, not a cross-repository
rewrite.

### Current MNCS backlog disposition

- **DONE in MNCS:** release-candidate schemas and validator, Forge integration boundary,
  provider-neutral capability policy, RAVEL historical evidence preservation, the
  experimental execution-placement profile, EA-NEXT-001 typed execution receipts,
  and EA-NEXT-002 immutable execution bundles.
- **DONE or active in sibling Forge:** verifier consolidation, versioned records and
  migrations, lifecycle transitions, transactional ledger writes, application services,
  unified dispatch, and compatibility stabilization.
- **STILL OPEN locally:** optional placement-evidence micro-verifier hook; generic
  integration examples from a future Fabric-style executor; and later placement
  comparison research.
- **SUPERSEDED:** old local Forge implementation tasks that assumed a monolithic
  coordinator or pre-state-machine dispatch surface.
- **EXTERNAL / GOVERNANCE BLOCKED:** independent evaluation, protected custody,
  external security/privacy review, governance approval, certification, release and
  signing authority, and promotion. Code in this repository does not resolve these.
- **FUTURE RESEARCH:** heterogeneous NPU placement, distributed execution,
  energy/power evidence, deterministic cross-machine placement studies, and provider
  isolation/sandbox evidence.

## Evidence classes

The next work must preserve these distinctions:

- **Local reproduction** repeats a declared process on one development host.
- **Operator-controlled reproduction** repeats a frozen artifact on distinct machines
  controlled by the same operator.
- **Independent evaluation** requires an evaluator outside the generation and ordinary
  ranking authority.
- **Protected evidence** requires preregistered custody and non-disclosure before the
  candidate freeze.
- **Witnessed evidence** requires a separately identified observer of the declared
  operation.
- **Operational evidence** comes from an exercised release, monitoring, rollback, or
  retirement control rather than a fixture.
- **Governance approval** is a project decision after the required review period and
  non-conflicted approvals. Executable evidence cannot create that approval.

A PASS in one class does not imply PASS in another. Missing evidence remains
`UNKNOWN`.

## Current repository assessment

| Area | Implemented and locally executable | Still required |
|---|---|---|
| MNCS 0.2 | Python validator, schemas, versioned corpus, packages, attestations, trust policy, Provider Protocol, and independent Rust agreement for the supported subset | No 0.3 promotion is proposed by this audit |
| MNCDS 0.1-draft / RFC 0004 | Schema, validator, D1-D4 reference record, mutations, and deterministic corpus | Independent corpus consumer, reproducible two-epoch study with fresh protected evidence, security/privacy review, governance approvals |
| RFC 0005 | Foundation records, experimental schemas, narrow Clang provider, analyzer documentation | Complete analyzer corpus, frozen epoch comparison, fresh protected holdout, independent schema consumers where normative use is proposed, security/privacy review, governance approvals |
| RFC 0006 | Experimental C11, Rust, Python, and Go profiles and provider corpora | Independent reproduction threshold and resolution of the RFC's open packaging/environment questions |
| RFC 0007 | Composed Gateway Waves Two through Five, custody and readiness fixtures, portable host schema and reconciler | Three physical host records, external protected custody/evaluation, witnessed operational controls, governance review |
| EdgeStream | Full local smoke and evidence regeneration, including GCC/Clang, sanitizers, recovery, mutations, bounded structural checks, and performance | Reproduction of the full study on independent hosts; protected/independent/lifecycle evidence for broader claims |
| Remote Water | Deterministic digital twin, tests, study, safety authority, recovery, and EdgeStream integration | Independently controlled holdout, independent evaluator/release authority, cross-host and cross-architecture runs, domain review, and any real PLC/SCADA/field evidence |
| CacheForge | Initial study and epoch-2 capacity sweep with deterministic local reproduction | Protected trace custody, independent evaluator, inference-server/GPU adapter evidence, and cross-host reproduction |
| RAVEL | Inference, training, and unified deterministic checks | Protected real-data evaluation, adversarial continual-learning studies, modality adapters, cross-host/accelerator/distributed evidence, and operational controls |
| dSense | Artifact identity, epoch-1 failure retention, binary framing, host checks, and non-uploading AVR compile capture | A new candidate epoch after the frozen V5 compile failures; then physical acoustic, button, persistence, power-cycle, and rollback evidence |
| Multilingual Stream / Go Gateway | Shared contract, provider corpora, language-specific builds/tests, FFI/process boundaries, and development experiments | Independent protected evaluation, broader compiler/host reproduction, and non-experimental governance decisions |
| Composed Gateway Waves Three and Four | Recovery, replacement, measurement, service boundary, custody/cross-host/readiness fixtures | Organizationally independent custody/evaluation, real cross-host records for the applicable full epoch, witnessed replacement, release monitoring, retirement exercise, and release authorization |
| Composed Gateway Wave Five | Deterministic frozen archive, sidecar, local smoke, schemas, reconciler, and valid Fedora-A and PiOS-ARM physical-host records | `windows-a`, `windows-b`, and `fedora-b`; the cohort remains `UNKNOWN` until all five records are present |

The 42 top-level schemas match the 42 packaged schemas. The audit also exercised the
MNCS corpus, the 11-case MNCDS corpus, and all current language-provider fixtures.
That historical count remains unchanged; EA-NEXT-002 adds two later experimental
execution-bundle schemas to the current registry/package resources without
relabeling the Wave Five audit.

## Fedora-A Wave Five record

The frozen transport created and verified during this audit is:

- archive:
  `mncs-wave-five-portable-evaluator.zip`
- archive SHA-256:
  `98a6d338b7a60067781cd7cb41d9a9458917dbe0b3c9b2348b926e122439f7e8`
- sidecar:
  `mncs-wave-five-portable-evaluator.zip.sha256`
- sidecar-file SHA-256:
  `b901504ffa5e3fe9b18eb8475857eb688a8ce3e59e2e0b6b9b597add8565835b`
- manifest SHA-256:
  `ca4053025b6cdc0b17ee910c0a09011eba18fd5774df891d87a7465277126402`
- candidate freeze SHA-256:
  `d858508276593494f9e8a255e07a2265954ac37424212f71f4bfa94aacbc4de9`

The ignored Fedora-A record is
`case-studies/composed-gateway/wave-five/evidence/hosts/fedora-a.json`.
Its file SHA-256 for this run is
`cf7dd02387e820b47d36d3fa6981fc6f34b16b1d0fe012e06fe7b501666a7e55`.
The host record passes bundle integrity, deterministic vectors, checkpoint resume,
stale-input rejection, semantic corruption rejection, environment classification,
and schema validation. It remains operator-controlled evidence with protected holdout
and independent evaluation `UNKNOWN`.

## PiOS-ARM Wave Five record

The ignored PiOS-ARM record is
`case-studies/composed-gateway/wave-five/evidence/hosts/pios-arm.json`.
Its file SHA-256 for this run is
`5e924e6c2a888a802eca1ef4ba108fcf5d0828a09bedacaff74df810150ce3d5`.
The record and separately captured physical-host facts are:

- record ID: `host:pios-arm:1785298643`;
- execution started: `2026-07-29T04:17:23.593847Z`;
- model: Raspberry Pi Zero 2 W Rev 1.0;
- distribution: Debian GNU/Linux 12 (bookworm);
- architecture: `arm64` in the record and `aarch64` from `uname -m`;
- Python: CPython 3.11.2;
- host result: `PASS`;
- semantic-output digest:
  `0bd3bcf6bc40caf9b15e9148972f822ef2a1afbe1a03a882ff765aba398ff2d4`;
- required gates: bundle integrity `PASS`, deterministic vectors `PASS`,
  checkpoint resume `PASS`, corruption rejection `PASS`, and offline capability
  `PASS`;
- frozen archive identity:
  `sha256:98a6d338b7a60067781cd7cb41d9a9458917dbe0b3c9b2348b926e122439f7e8`;
- manifest identity:
  `sha256:ca4053025b6cdc0b17ee910c0a09011eba18fd5774df891d87a7465277126402`;
- candidate-freeze identity:
  `sha256:d858508276593494f9e8a255e07a2265954ac37424212f71f4bfa94aacbc4de9`;
- evidence class: `OPERATOR_CONTROLLED`; and
- protected holdout and independent evaluation: `UNKNOWN`.

The record passes the checked-in host-execution schema and agrees with Fedora-A on
the semantic-output digest, bundle identity, manifest identity, and candidate-freeze
identity. Two records are not a five-machine cohort. Cohort reconciliation was not
performed, and the cohort remains `UNKNOWN`.

## Exact remaining-machine procedure

Build once on the repository host and transfer only the exact archive and sidecar:

```bash
make -C case-studies/composed-gateway/wave-five bundle-check
cd case-studies/composed-gateway/wave-five/dist
sha256sum -c mncs-wave-five-portable-evaluator.zip.sha256
sha256sum mncs-wave-five-portable-evaluator.zip \
  mncs-wave-five-portable-evaluator.zip.sha256
```

The archive check must report the archive SHA-256 above. The sidecar file itself must
have the sidecar-file SHA-256 above. Do not rebuild independently on each target and do
not copy a source-tree evaluator in place of the ZIP.

For `windows-a`, verify and run in PowerShell:

```powershell
(Get-FileHash .\mncs-wave-five-portable-evaluator.zip -Algorithm SHA256).Hash.ToLower()
(Get-FileHash .\mncs-wave-five-portable-evaluator.zip.sha256 -Algorithm SHA256).Hash.ToLower()
Expand-Archive .\mncs-wave-five-portable-evaluator.zip -DestinationPath .\mncs-wave-five
Set-Location .\mncs-wave-five
.\run.ps1 -MachineLabel windows-a -OperatorId operator:alexander `
  -ArchiveIdentity sha256:98a6d338b7a60067781cd7cb41d9a9458917dbe0b3c9b2348b926e122439f7e8 `
  -Output host-record-windows-a.json
```

Repeat on the distinct second Windows machine with label `windows-b` and output
`host-record-windows-b.json`.

For `fedora-b`, verify and run:

```bash
sha256sum -c mncs-wave-five-portable-evaluator.zip.sha256
printf '%s  %s\n' \
  b901504ffa5e3fe9b18eb8475857eb688a8ce3e59e2e0b6b9b597add8565835b \
  mncs-wave-five-portable-evaluator.zip.sha256 | sha256sum -c -
mkdir mncs-wave-five
unzip -q mncs-wave-five-portable-evaluator.zip -d mncs-wave-five
cd mncs-wave-five
sh ./run.sh fedora-b operator:alexander host-record-fedora-b.json \
  sha256:98a6d338b7a60067781cd7cb41d9a9458917dbe0b3c9b2348b926e122439f7e8
```

Copy the three remaining records back without editing them as:

```text
case-studies/composed-gateway/wave-five/evidence/hosts/windows-a.json
case-studies/composed-gateway/wave-five/evidence/hosts/windows-b.json
case-studies/composed-gateway/wave-five/evidence/hosts/fedora-b.json
```

After all five records validate, reconcile exactly once:

```bash
PYTHONPATH=src python \
  case-studies/composed-gateway/wave-five/tools/reconcile_cohort.py \
  case-studies/composed-gateway/wave-five/evidence/hosts/windows-a.json \
  case-studies/composed-gateway/wave-five/evidence/hosts/windows-b.json \
  case-studies/composed-gateway/wave-five/evidence/hosts/fedora-a.json \
  case-studies/composed-gateway/wave-five/evidence/hosts/fedora-b.json \
  case-studies/composed-gateway/wave-five/evidence/hosts/pios-arm.json \
  --plan case-studies/composed-gateway/wave-five/machine-plan.json \
  --output case-studies/composed-gateway/wave-five/evidence/operator-cohort.json
```

Even a cohort PASS establishes only
`OPERATOR_CONTROLLED_CROSS_HOST` public reproduction.

## dSense compile result and next epoch

The non-uploading Fedora-A capture used exact frozen sources:

| Frozen sketch | Source SHA-256 | Compile | Flash | SRAM | Headroom result |
|---|---|---|---:|---:|---|
| Binary telemetry | `8c413fb12cc5ff3333175ff20ff5093b7cf98d297983b1472aa71ece53411808` | FAIL | 33,308 / 32,256 | 1,159 / 2,048 | FAIL, flash exceeds limit by 1,052 bytes |
| Production | `bcaa5bb03a3d7b86001d45f7890003f6d82a8e982ebdc38163a84baa460fa74e` | PASS | 31,788 / 32,256 | 1,142 / 2,048 | FAIL, 468 bytes is below the preregistered preferred 512-byte headroom |

The local capture is ignored machine evidence at
`case-studies/dsense-desk-pet/evidence/local/avr-compile-fedora-a.json`.
Its SHA-256 for the final capture in this audit is recorded in the audit report rather
than treated as checked-in formal evidence.

Do not modify the frozen V5 sketches to obtain PASS. The next dSense work is a new
candidate and development epoch with new source, generator, evaluator, and evidence
identities. The telemetry candidate cannot be flashed to the Uno in its current form.

After a newly identified telemetry candidate passes the compile and headroom gates,
Alexander must perform the physical work:

1. verify the exact Uno, wiring, piezo protection, and explicit serial-device path;
2. flash the newly identified binary-telemetry candidate;
3. capture the full preregistered stimulus sequence without sending serial data;
4. test isolated taps, quiet rate, direct piezo contact, self-sound masking, and
   light-to-microphone carryover;
5. exercise all three buttons and verify cognition continues through menus;
6. power-cycle and verify EEPROM persistence; and
7. flash the identified rollback image and retain the witnessed result.

Acoustic, button, persistence, power-cycle, rollback, and all other physical gates
remain `UNKNOWN` until those operations occur.

## External and governance work

External actors are still required for:

- protected-corpus custody after preregistration and candidate freeze;
- independent final evaluation with separate executable and organizational authority;
- independent witnessing of replacement, rollback, and lifecycle drills;
- domain review for Remote Water controls/safety;
- protected trace and serving-system evaluation for CacheForge;
- protected real-data and adversarial evaluation for RAVEL; and
- security/privacy review of claim-broadening risks in RFCs 0004 and 0005.

Governance is still required for:

- the review periods and non-conflicted approvals for RFCs 0004 through 0007;
- the independent approvals specified by RFCs 0004 and 0005;
- bootstrap-governance completion records, including maintainer/editor rosters,
  succession, release/signing authority, reviewer-pool status, conflicts, and recusal;
  and
- any future MNCS 0.3 decision and migration policy.

## Optional later ecosystem work

The current open issues for Sigstore/in-toto mapping, multi-language SDKs,
reproducible-build profiles, energy and hardware-utilization profiles, external pilots,
transparency logs, hardware-backed signing, a third MNCS validator, and provider
sandboxing remain useful future work. None replaces the missing dSense candidate,
three physical Wave Five records, independent evidence, or governance approval, and none
is made an MNCS 0.3 blocker by this audit.
