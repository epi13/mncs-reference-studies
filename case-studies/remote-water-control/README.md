# Remote Water Resilience Controller

This case study is an executable, development-only digital twin and supervisory controller
for a bounded remote water system. It is the first MNCS example in this repository centered
on composed decision authority rather than a single optimized component.

The system models one storage tank, a duty pump, a standby pump, variable demand, power
loss, degraded telemetry, checkpoint restoration, and an append-only intent journal. A
deterministically generated table planner may propose commands, but a compact readable
safety kernel owns authorization. The code has no industrial protocol or actuator output.
It must not be connected to live equipment.

## What is implemented

- Deterministic plant simulation with energy, pump-start, overflow, and unmet-demand metrics.
- A readable threshold baseline and a generated fixed-state decision-table candidate.
- A separately maintained safety kernel that can accept, modify, hold, or reject proposals.
- Expiring, monotonically sequenced actuator-intent records.
- A SHA-256 hash-chained intent journal with replay rejection.
- Digest-protected atomic checkpoints with planner-identity and sequence binding.
- Power-loss, stale-telemetry, conflicting-sensor, peak-demand, and restart scenarios.
- Deterministic replay, fault, corruption, objective, and invariant tests.
- An experimental contract profile and combined assurance case that truthfully remain
  `UNKNOWN` for formal MNCS and MNCDS claims.

## Architecture

```text
scenario / future EdgeStream adapter
               |
               v
         telemetry sample
               |
               v
       generated table planner
          proposal only
               |
               v
       readable safety kernel
               |
               v
 signed-shape, expiring intent
               |
       +-------+--------+
       |                |
       v                v
 hash-chained       digital twin
 audit journal      plant update
       |
       v
 checkpoint / restart continuity
```

EdgeStream is represented as an optional future data dependency in the assurance case. This
initial implementation uses a direct normalized telemetry sample so the controller contract
and authority boundary can be tested without coupling the study to one transport.

## Run

From the repository root:

```bash
make remote-water-test
make remote-water-study
```

Or from this directory:

```bash
make test
make study
```

`make study` regenerates the candidate identity check, runs the test suite, executes both
planners over all declared development scenarios, validates the experimental contract and
assurance records, and writes deterministic evidence to `evidence/results/`.

## Development result versus formal claim

The checked-in development run can pass its declared hard gates and selection objective.
That does **not** produce an MNCS-L5 or MNCDS-D3 claim. The assurance case intentionally
records both statuses as `UNKNOWN` because the following remain outstanding:

- independently controlled protected holdout scenarios;
- independent final evaluator and release authority;
- cross-host and cross-architecture reproduction;
- operational monitoring, replacement, and rollback evidence;
- independent water-utility, controls, and safety review;
- any evidence involving a real PLC, SCADA system, pump, valve, or field network.

See `preregistration.json`, `contract/contract-profile.json`, `threat-model.json`, and
`assurance-case.json` before interpreting any result.

## Repository layout

```text
contract/                 experimental contract adequacy record
generator/                readable generation specification
machine/                  deterministic generated planner table
src/water_control/        controller, safety kernel, journal, checkpoint, and simulator
tests/                    invariant, recovery, replay, and objective tests
tools/                    generator and controlled-study runner
evidence/results/         deterministic development observations
preregistration.json      frozen development protocol and future holdout requirements
threat-model.json         threat paths, mitigations, and residual UNKNOWNs
assurance-case.json       composed review-required assurance record
```
