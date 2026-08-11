# Migration record: CacheForge

- Source repository: `https://github.com/epi13/machine-native-complexity-standard`
- Frozen source commit: `80f08d312dce963265c7f69ac5b4bae8245bd692`
- Last source commit touching this study: `a95d70be42f366c41a0cb1142ad3c6cc519ac193`
- Original source path: `case-studies/cacheforge/`
- Destination path: `case-studies/cacheforge/`
- Migration date: `2026-08-10`
- History: copied normally across repositories; Git file history is not implicitly preserved.
- Path/build changes: study-local Makefile retained; destination compatibility targets call it from the destination root. The source-only language-profile helper is replaced by a destination-owned bounded profile check.
- Relocated dependencies: no normative validator code; CacheForge study code and its checked-in fixtures/evidence are self-contained.
- Evidence-bearing artifact changed: no.
- Experiment rerun for migration: no. Study-local non-evidence tests were run after copying.
- Validation after migration: `make -C case-studies/cacheforge test` passed.

