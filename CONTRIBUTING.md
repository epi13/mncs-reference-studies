# Contributing

MNCS Reference Studies welcomes experiments that can fail honestly.

## Choose the correct lane

Use `reference-studies/` for controlled reimplementations of a proven or mature implementation. Use `case-studies/` for bounded MNCS experiments that do not fit the reference-reimplementation design.

## New MRS study checklist

Before implementation begins, a study should define:

- a stable MRS identifier;
- the behavioral surface being compared;
- upstream identity, version/commit, license, and provenance;
- comparison arms;
- test and malformed/adversarial corpora;
- resource envelope;
- benchmark workload, if performance is in scope;
- primary and secondary metrics;
- agent task packets, if machine maintainability is in scope;
- preregistered success/non-regression gates;
- evidence and claim boundary;
- reproducibility/environment requirements.

Start from `templates/reference-study/` and validate with `make check`.

## Upstream licensing

Do not copy upstream source into this repository until its license and redistribution obligations are understood and recorded. Preserve required attribution and NOTICE material. When a study can use an upstream repository as an external fixture instead of vendoring source, document the frozen retrieval method and content identity.

## Experimental integrity

Do not tune thresholds after observing candidate performance and then present the new threshold as preregistered. If a protocol needs to change, start a new epoch and preserve the old result.

Negative evidence, regressions, failed agent attempts, and non-comparable measurements should be retained when they are relevant to the study question.

## Pull requests

PRs should state what experimental surface changed, whether a frozen protocol/evidence artifact changed, what validation was run, and whether the change alters any claim boundary. Migration PRs should also record the source repository and source commit.
