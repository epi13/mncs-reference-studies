# Migration record: Recursive Analyzer

- Source repository: `https://github.com/epi13/machine-native-complexity-standard`
- Frozen source commit: `80f08d312dce963265c7f69ac5b4bae8245bd692`
- Last source commit touching this study: `27e2a26d29077c049379470c40501f11265468f4`
- Original source path: `studies/recursive-analyzer/`
- Destination path: `studies/recursive-analyzer/`
- Migration date: `2026-08-10`
- History: copied normally across repositories; Git file history is not implicitly preserved.
- Path/build changes: the study remains callable from the destination root; its source-relative imports require no change.
- Relocated dependencies: the study uses the destination's existing study metadata and does not move normative conformance machinery.
- Evidence-bearing artifact changed: no.
- Experiment rerun for migration: no. The study runner completed after copying.
- Validation after migration: `PYTHONPATH=src python studies/recursive-analyzer/run_study.py` passed.

