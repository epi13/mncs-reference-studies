# Migration record: Remote Water Control

- Source repository: `https://github.com/epi13/machine-native-complexity-standard`
- Frozen source commit: `80f08d312dce963265c7f69ac5b4bae8245bd692`
- Last source commit touching this study: `2aaa68101786d5dabb214760fb8c60cf36943d2d`
- Original source path: `case-studies/remote-water-control/`
- Destination path: `case-studies/remote-water-control/`
- Migration date: `2026-08-10`
- History: copied normally across repositories; Git file history is not implicitly preserved.
- Path/build changes: study-local generation and test paths are retained; cross-host/protected evaluation remains explicit and is not run by ordinary checks.
- Relocated dependencies: none; normative validator/conformance tooling remains in the standards repository.
- Evidence-bearing artifact changed: no.
- Experiment rerun for migration: no. Generated-planner and test checks were run after copying.
- Validation after migration: `make -C case-studies/remote-water-control test` passed.

