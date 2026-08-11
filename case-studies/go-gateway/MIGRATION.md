# Migration record: Go Gateway

- Source repository: `https://github.com/epi13/machine-native-complexity-standard`
- Frozen source commit: `80f08d312dce963265c7f69ac5b4bae8245bd692`
- Last source commit touching this study: `6a4a77c8178fd43384ca858f2d51826ece8146d7`
- Original source path: `case-studies/go-gateway/`
- Destination path: `case-studies/go-gateway/`
- Migration date: `2026-08-10`
- History: copied normally across repositories; Git file history is not implicitly preserved.
- Path/build changes: study-local Go commands are retained and exposed through destination compatibility targets.
- Relocated dependencies: none.
- Evidence-bearing artifact changed: no.
- Experiment rerun for migration: no. Unit, race, and bounded fuzz checks were run after copying.
- Validation after migration: `make -C case-studies/go-gateway check` passed.

