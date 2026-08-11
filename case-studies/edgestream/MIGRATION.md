# Migration record: EdgeStream

- Source repository: `https://github.com/epi13/machine-native-complexity-standard`
- Frozen source commit: `80f08d312dce963265c7f69ac5b4bae8245bd692`
- Last source commit touching this study: `d49e92358c2fd8f84207d2a8532c7f657aba71e9`
- Original source path: `case-studies/edgestream/`
- Destination path: `case-studies/edgestream/`
- Migration date: `2026-08-10`
- History: copied normally across repositories; Git file history is not implicitly preserved.
- Path/build changes: study-local generation, build, smoke, and evidence targets are retained. MNCS/MNCDS validator commands remain explicitly standards-tooling dependent and are not duplicated here.
- Relocated dependencies: none in this migration; the normative validator/conformance package remains in the standards repository.
- Evidence-bearing artifact changed: no.
- Experiment rerun for migration: no. The local study test passed after copying.
- Validation after migration: `make -C case-studies/edgestream test` passed.

