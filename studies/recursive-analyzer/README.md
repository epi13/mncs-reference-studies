# Two-epoch recursive analyzer study

This bounded study tests the MNCDS recursive-improvement controls. Epoch one is
frozen before its failures are examined. The epoch-two objective is to reduce
incorrect `PASS`, not to maximize an undifferentiated score. The evaluator and
threshold policy are fixed, all materially evaluated candidates are retained,
and prior disagreements become development regression fixtures.

The final partition was developer-withheld from the repair feedback process
until the epoch-two tool identity was frozen. It is now disclosed for
reproduction. This is not organizationally independent or externally protected
custody. Consequently, internal selection can pass while the associated MNCS
claim and external-independence facts remain `UNKNOWN`.

Run:

```console
PYTHONPATH=src python studies/recursive-analyzer/run_study.py
```

The runner checks pinned SHA-256 identities, executes three repetitions per
case with a timeout, and reports true positives, false positives, false
negatives, incorrect PASS, UNKNOWN, crashes, timeouts, unsupported cases,
runtime, resource use, and diagnostic utility.
