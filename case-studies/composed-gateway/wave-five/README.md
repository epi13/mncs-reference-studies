# Composed Gateway Wave Five

Wave Five packages the frozen composed-gateway semantics into a portable, offline evaluator that can be run unchanged on machines outside GitHub Actions. It is designed for the machines currently available to the project: two Windows computers, two Fedora computers, and one Raspberry Pi OS ARM computer.

## What those five machines establish

A passing five-host cohort is meaningful evidence. It can establish:

- repeated execution on distinct physical machines;
- Windows and Linux OS-family coverage;
- Windows, Fedora, and Raspberry Pi OS distribution coverage;
- x86-64 and ARM architecture coverage when the Pi reports ARM;
- deterministic bundle integrity and semantic-output agreement;
- operator-controlled public reproduction.

It does **not** establish independent evaluation, protected holdout, independent custody, or an independent witness because the same project operator controls the machines and execution. Wave Five records that distinction rather than discarding the useful evidence or overstating it.

## Portable evaluator

The bundle uses only Python 3.9 or later and the standard library. It performs no network operation and evaluates:

- bundle-file identities;
- bounded decimal-frame behavior;
- malformed and out-of-range rejection;
- deterministic uninterrupted output;
- checkpoint and resume equivalence;
- stale-input rejection;
- semantic checkpoint-corruption rejection;
- environment and optional toolchain observations.

The ZIP is deterministic and uses stored entries rather than platform-dependent compression. The checked-in `bundle-lock.json` freezes the manifest and transport identities.

## Build once

```bash
make bundle-check
```

Copy the exact ZIP and `.sha256` sidecar from `dist/` to every machine. Verify the ZIP before extraction.

## Run on the five machines

Use these exact labels:

| Machine | Label |
|---|---|
| Windows computer 1 | `windows-a` |
| Windows computer 2 | `windows-b` |
| Fedora computer 1 | `fedora-a` |
| Fedora computer 2 | `fedora-b` |
| Raspberry Pi OS computer | `pios-arm` |

Windows PowerShell:

```powershell
.\run.ps1 -MachineLabel windows-a -OperatorId operator:alexander
```

Fedora or Pi OS:

```bash
./run.sh fedora-a operator:alexander
```

Rename each generated file to include its machine label and copy all five records back into one directory without editing them.

## Reconcile the cohort

```bash
PYTHONPATH=../../../src python3 tools/reconcile_cohort.py \
  evidence/hosts/*.json \
  --plan machine-plan.json \
  --output evidence/operator-cohort.json
```

The preregistered physical-machine cohort requires all five labels, at least two OS families, three distribution classes, two normalized architectures, identical bundle and candidate identities, all required gates PASS, and one semantic output digest.

## Claim boundary

The checked-in cohort is `UNKNOWN` until the physical records are collected. When the five records pass, `public_reproduction_status` may become `PASS` under the evidence class `OPERATOR_CONTROLLED_CROSS_HOST`. `independent_evaluation_status`, protected holdout, formal MNCS, formal MNCDS, and promotion remain `UNKNOWN` or prohibited until external actors supply the missing evidence.
