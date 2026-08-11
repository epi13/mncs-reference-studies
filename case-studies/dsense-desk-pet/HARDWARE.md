# Hardware and capture notes

## Wiring

| Function | Uno pin | Connection |
|---|---:|---|
| Pet / wake / enter | D2 | momentary button to GND |
| Up | D3 | momentary button to GND |
| Down | D4 | momentary button to GND |
| Buzzer | D8 | module signal pin |
| RGB red | D9 | LED leg through resistor |
| RGB green | D10 | LED leg through resistor |
| RGB blue | D11 | LED leg through resistor |
| Light sensor | A0 | photoresistor divider |
| Piezo sensor | A1 | protected passive piezo input |
| Random seed | A2 | left unconnected |
| OLED SDA/SCL | A4/A5 | I2C display |

Buttons use the Uno's internal pull-ups and therefore read LOW when pressed.

## Passive piezo protection

A passive piezo can generate a voltage spike when struck. The declared development wiring is:

```text
piezo lead 1 -> 100 kOhm series resistor -> A1
A1 -> 1 MOhm resistor -> GND
piezo lead 2 -> GND
```

The series resistor limits clamp-diode current. The input is for small vibration/acoustic
experiments only. Do not strike the piezo hard, connect an amplified source, or use the circuit as
a calibrated microphone.

## USB capture safety

The recorder requires an explicit serial path, for example:

```bash
python3 tools/capture_dsense_binary_v5.py /dev/ttyUSB1
```

It does not scan other ports and does not transmit serial commands. The operator must still verify
the port. Disconnecting unrelated serial equipment before capture is the safest procedure.

## Board variants

The case study targets the classic Uno / ATmega328P. Uno R4, Nano, clone bootloaders, alternate
OLED controllers, active-low RGB modules, and passive versus active buzzers change the environment
and require a new environment record before results are compared.
