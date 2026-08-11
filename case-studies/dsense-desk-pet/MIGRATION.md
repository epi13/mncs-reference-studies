# Migration record: dSense Desk Pet

- Source repository: `https://github.com/epi13/machine-native-complexity-standard`
- Frozen source commit: `80f08d312dce963265c7f69ac5b4bae8245bd692`
- Last source commit touching this study: `d49e92358c2fd8f84207d2a8532c7f657aba71e9`
- Original source path: `case-studies/dsense-desk-pet/`
- Destination path: `case-studies/dsense-desk-pet/`
- Migration date: `2026-08-10`
- History: copied normally across repositories; Git file history is not implicitly preserved.
- Path/build changes: study-local offline checks are retained; AVR/device capture remains explicit and is not run by repository checks.
- Relocated dependencies: none; the study's authored artifacts and integrity tools are self-contained.
- Evidence-bearing artifact changed: no.
- Experiment rerun for migration: no. Offline materialization, analysis, and integrity checks were run after copying.
- Validation after migration: `make -C case-studies/dsense-desk-pet check` passed.

