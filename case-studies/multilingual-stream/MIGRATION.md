# Migration record: Multilingual Stream

- Source repository: `https://github.com/epi13/machine-native-complexity-standard`
- Frozen source commit: `80f08d312dce963265c7f69ac5b4bae8245bd692`
- Last source commit touching this study: `d49e92358c2fd8f84207d2a8532c7f657aba71e9`
- Original source path: `case-studies/multilingual-stream/`
- Destination path: `case-studies/multilingual-stream/`
- Migration date: `2026-08-10`
- History: copied normally across repositories; Git file history is not implicitly preserved.
- Path/build changes: local generator, C11, Rust, and experiment paths are retained. Core-only language-profile/provider and MNCDS validator steps are separated as optional standards-tooling checks.
- Relocated dependencies: destination empirical tooling owns local profile/provider fixtures where practical; normative schemas and validators remain in the standards repository.
- Evidence-bearing artifact changed: no.
- Experiment rerun for migration: no. Generation, C11, and Rust checks were run after copying.
- Validation after migration: `make -C case-studies/multilingual-stream generate c11 rust` passed.

