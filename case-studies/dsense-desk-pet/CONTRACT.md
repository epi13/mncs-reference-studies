# dSense Desk Pet readable contract

## Intended use

The dSense Desk Pet is an educational embedded-systems research artifact for an Arduino Uno.
It explores bounded predictive processing, sensor/output feedback, adaptive acoustic reaction,
episodic state, expressive rendering, and machine-native representation under the
ATmega328P resource envelope.

It is not a medical, safety, security, access-control, surveillance, industrial-control, or
animal-care device. It has no network stack and no authority beyond its OLED, RGB LED, buzzer,
EEPROM settings, and telemetry output.

## Human control plane

Humans retain authority over:

- hardware wiring and electrical limits;
- intended and prohibited uses;
- firmware selection and flashing;
- evaluation protocol and stimulus labels;
- acceptance thresholds;
- serial-device selection;
- evidence custody and interpretation;
- formal MNCS/MNCDS status;
- rollback to a previously known firmware image; and
- physical disconnection or power removal.

The firmware may adapt internal baselines, associations, expression state, reaction timing, and
bounded episodic summaries. It may not alter this contract, the evaluator, acceptance gates,
telemetry framing, hardware pin authority, or promotion decision.

## Hardware contract

Target hardware:

- Arduino Uno / ATmega328P;
- 32,256 bytes available program storage;
- 2,048 bytes SRAM;
- 128x64 I2C OLED at `0x3C` or `0x3D`;
- RGB LED on D9, D10, and D11 through one resistor per color leg;
- buzzer module on D8;
- pet/wake/enter button from D2 to ground;
- up button from D3 to ground;
- down button from D4 to ground;
- light divider on A0;
- passive two-pin piezo sensor on A1 through the protection network in `HARDWARE.md`; and
- unused analog input A2 as a non-cryptographic random seed source.

All buttons use `INPUT_PULLUP`. The firmware assumes active-low button presses.

## Required invariants

1. The candidate must compile for `arduino:avr:uno` without exceeding program or SRAM limits.
2. The firmware must use no heap allocation, recursion, filesystem, network, or external actuator.
3. Sensor and cognitive values must remain in fixed-width bounded integer representations.
4. Acoustic reactions must use adaptive baseline, onset, hysteresis, rearming, and self-sound
   masking; sustained energy alone must not retrigger at the refractory limit.
5. Light-to-microphone ADC carryover must be mitigated by discarding the first A1 conversion
   after cross-channel access.
6. OLED observation must be rate-limited so displaying a diagnostic graph cannot dominate the
   timing model it is observing.
7. Telemetry firmware must emit only framed V5 binary packets. It must not require incoming
   serial commands.
8. The host recorder must open only the explicit port supplied by the operator and must not write
   to that device.
9. Production and telemetry firmware must differ only in the compile-time `DEBUG_SERIAL` value.
10. EEPROM settings must be guarded by a magic value and version before use.
11. Menu navigation must not suspend the underlying sensor, prediction, mood, or timing model.
12. A failed, corrupt, unknown, or incomplete observation must not be promoted to PASS.

## Observable behavior

The expressive face is the normal home screen. Up and down open and navigate machine-native icon
menus. The pet/wake button selects items, pets or wakes the device on the face, starts the reaction
game when held, and backs out of menus when held.

Sound is represented as distinct bounded concepts:

- adaptive background level;
- onset;
- sustained presence;
- external or unexplained energy;
- self-produced sound;
- event class; and
- event confidence.

A single physical impulse should produce one reaction, not a repeated stream of events. Sustained
vibration may remain visible as presence without repeatedly increasing novelty.

## Epoch-2 acceptance gates

The frozen V5 candidate is eligible for a development PASS only when all of these are observed:

- AVR compile succeeds within the Uno flash and SRAM limits;
- binary protocol packet sizes are 49, 37, and 20 bytes for data, model, and event packets;
- offline decoder framing and checksum tests pass;
- quiet acoustic-event rate is at most 0.10 Hz after a 10-second settling period;
- each isolated desk tap produces one event and no second event within 500 ms;
- direct piezo contact is classified at least as strongly as a soft desk tap;
- self-generated probe sound does not become an external event;
- covering and uncovering A0 without touching the piezo does not create a persistent acoustic
  level shift greater than the preregistered bound;
- all three buttons navigate and return without blocking cognition updates;
- settings survive a power cycle; and
- rollback to the prior known image is demonstrated.

Repository-visible development evidence alone does not establish independent hardware
replication, protected holdout, production reliability, or formal conformance.

## Replacement and rollback

The machine execution plane is stored as a content-addressed compressed text envelope and replaced as a complete materialized firmware image. The readable contract,
hardware map, evaluator, and evidence remain outside that image. Rollback consists of flashing a
previously identified sketch and, when needed, resetting EEPROM settings through the tool menu or
an explicit maintenance sketch.
