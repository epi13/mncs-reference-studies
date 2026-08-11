# dSense Desk Pet — recursive embedded cognition case study

dSense is a physical Arduino Uno desk pet used to study machine-native representation,
recursive sensor/output feedback, predictive state, adaptive reactivity, and evidence-guided
regeneration under a severe 8-bit resource envelope.

The pet reads light, a passive piezo vibration sensor, three buttons, and four asynchronous timing
probes. It drives an OLED face, RGB LED, buzzer, menus, persistent settings, a reaction game,
acoustic self-probes, and binary telemetry. Its own display, light, sound, timing, and state outputs
are fed back into bounded internal signals. A ten-channel online predictor, compact episodic memory,
learned output coupling, curiosity, coherence, agency, fatigue, novelty, and valence influence later
behavior.

The case study is valuable because the development evidence changed the architecture twice:

1. A real telemetry run showed that the first acoustic detector fired near its refractory limit in
   quiet and active conditions alike. Novelty therefore saturated and ceased to carry information.
2. The repaired three-button human-readable interface then compiled to 34,676 bytes on a board with
   only 32,256 bytes of program storage.
3. V5 relocated human labels and CSV formatting out of the microcontroller. The OLED uses compact
   icon/numeric semantics and the Uno emits native framed binary state. Human-readable decoding,
   contracts, thresholds, and evidence remain outside the machine execution plane.

This is a recursive MNCDS-style development example: the device's output became evidence, that
evidence changed the detector and evaluator, and the later resource failure changed the
representation itself. The changed candidate receives a new identity and must pass a fresh,
predeclared hardware protocol.

## Current result

| Evidence item | Result |
|---|---|
| Epoch-1 acoustic discrimination | **FAIL** — 552 events in 211.825 seconds, including 2.617 Hz during the marked quiet baseline |
| Epoch-1 novelty usefulness | **FAIL** — novelty was at or above 1000 in more than 99% of data snapshots |
| V4 Uno program storage | **FAIL** — 34,676 / 32,256 bytes, 2,420 bytes over budget |
| V5 offline framing/checksum tests | **PASS** |
| V5 source and evidence integrity checks | **PASS** |
| V5 checked-in AVR compile evidence | **UNKNOWN** — no machine-local capture is committed |
| V5 preregistered hardware response protocol | **UNKNOWN** |
| Formal MNCS status | **UNKNOWN** |
| Formal MNCDS status | **UNKNOWN** |
| Promotion authorized | **No** |

Source-size and string-literal reductions are mechanism observations only. They do not replace an
AVR linker report. The candidate cannot receive a development PASS until the compile, acoustic,
button, persistence, and rollback gates in `preregistration.json` are captured.

## Machine-native boundary

- **Human control plane:** `CONTRACT.md`, `HARDWARE.md`, evaluation thresholds, stimulus order,
  serial-device choice, firmware flashing, evidence interpretation, and promotion authority.
- **Machine execution plane:** fixed-width sensor state, predictive channels, learned couplings,
  episodic summaries, expression motor state, icon/numeric UI, generated timing relationships, and
  binary packets.
- **Evidence plane:** a canonical telemetry extract tied to the original capture hash, reproducible analysis, compile observations, artifact hashes,
  decoder tests, and future AVR/hardware results.
- **Development-control plane:** retained failing baseline, frozen V5 candidate, explicit epoch
  record, preregistered gates, and prohibition on evaluator self-modification.
- **Operational-control plane:** explicit firmware selection, power removal, EEPROM reset, and
  complete-image rollback.

Human readability is relocated, not eliminated. The machine representation is intentionally compact;
the contract and evidence remain readable and auditable.

## Run offline checks

From the repository root:

```bash
make dsense-check
```

Or from this directory:

```bash
make check
```

The check materializes artifacts in memory and:

- verifies SHA-256 identities;
- regenerates the epoch-1 analysis from the canonical telemetry extract;
- tests V5 binary framing, checksum rejection, fragmentation, and resynchronization;
- verifies the production and telemetry sketches differ only by `DEBUG_SERIAL`;
- confirms the candidate contains no C/C++ string literals or decimal `Serial.print()` path;
- confirms declared pin and protocol invariants; and
- enforces the `UNKNOWN` formal-status and non-promotion boundary.

These are host checks, not an AVR size measurement or physical-device certification.

## Capture AVR compile evidence

When Arduino CLI, `arduino:avr`, and the required libraries are available, capture both
frozen V5 compiles without enumerating ports, uploading, or writing serial data:

```bash
make avr-compile MACHINE_LABEL=fedora-a \
  AVR_COMPILE_OUTPUT=evidence/local/avr-compile-fedora-a.json
```

The ignored local record contains the Arduino CLI and AVR core identities, installed and
used library versions, complete compiler output and its hashes, source identities,
produced binary identities, flash/SRAM measurements, and headroom. An observed compile
or resource failure is retained as `FAIL`; missing tools or unparseable measurements
remain `UNKNOWN`. Formal MNCS/MNCDS and every physical protocol gate remain `UNKNOWN`.

## Capture V5 telemetry

Run `python3 tools/materialize.py` to restore the sketches, upload the binary telemetry sketch, and use one explicit device path:

```bash
python3 tools/capture_dsense_binary_v5.py /dev/ttyUSB1
```

The recorder never scans ports and never sends serial bytes. It writes both the exact `.dsb` stream
and a decoded `.csv`. Type experiment labels into the terminal to add host-side markers.

The native frame is:

```text
A5 5A TYPE LENGTH PAYLOAD XOR
```

Packet types are:

- `1`: fast sensor/cognitive state, 49-byte payload;
- `2`: predictive model state, 37-byte payload;
- `3`: immediate event, 20-byte payload; and
- `127`: protocol declaration.

## Repository layout

```text
artifacts/                retained V4 baseline, verified V5 delta, and canonical telemetry extract
tools/                    materializer, capture, analysis, and offline verifier
evidence/raw/             canonical-extract and original-capture identity description
evidence/results/         derived findings, compile observations, and hashes
CONTRACT.md               readable behavior, authority, and acceptance gates
HARDWARE.md               wiring, electrical limits, and capture safety
preregistration.json      frozen V5 compile and hardware protocol
threat-model.json         threats, mitigations, and residual unknowns
assurance-case.json       review-required non-promotion record
development-record.json   evidence-to-architecture epoch history
```

## Claim boundary

This study demonstrates a real feedback-driven development loop and a bounded machine-native
representation strategy on an 8-bit target. It does not yet establish that V5 fits the Uno, that the
repaired detector passes the declared physical protocol, that the behavior generalizes across
assemblies, or that any formal conformance level has been earned.
