# Migration record: Composed Gateway

- Source repository: `https://github.com/epi13/machine-native-complexity-standard`
- Frozen source commit: `80f08d312dce963265c7f69ac5b4bae8245bd692`
- Last source commit touching this study: `d49e92358c2fd8f84207d2a8532c7f657aba71e9`
- Original source path: `case-studies/composed-gateway/`
- Destination path: `case-studies/composed-gateway/`
- Migration date: `2026-08-10`
- History: copied normally across repositories; Git file history is not implicitly preserved.
- Path/build changes: study-local Makefiles are retained. Destination wave targets use destination-local paths and do not copy the core standards package.
- Relocated dependencies: empirical wave checks remain with this study; normative schema validation remains an optional dependency on the standards repository/toolchain.
- Evidence-bearing artifact changed: no.
- Experiment rerun for migration: no. C, Go, Rust, generated-binding, and smoke checks were run after copying.
- Validation after migration: `make -C case-studies/composed-gateway check` passed.

