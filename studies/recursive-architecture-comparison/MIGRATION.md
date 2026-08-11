# Migration record: Recursive Architecture Comparison

- Source repository: `https://github.com/epi13/machine-native-complexity-standard`
- Frozen source commit: `80f08d312dce963265c7f69ac5b4bae8245bd692`
- Last source commit touching this study: `d65f32dc61580694915e89bb6b62eb624fc23398`
- Original source path: `studies/recursive-architecture-comparison/`
- Destination path: `studies/recursive-architecture-comparison/`
- Migration date: `2026-08-10`
- History: copied normally across repositories; Git file history is not implicitly preserved.
- Path/build changes: root compatibility targets call the existing validators from the destination root.
- Relocated dependencies: none; this bounded study remains distinct from numbered MRS studies.
- Evidence-bearing artifact changed: no.
- Experiment rerun for migration: no. Validator and fixture checks passed after copying.
- Validation after migration: `validate_study.py` and `test_validate_study.py` passed.

