# Migration record: RAVEL

- Source repository: `https://github.com/epi13/machine-native-complexity-standard`
- Frozen source commit: `80f08d312dce963265c7f69ac5b4bae8245bd692`
- Last source commit touching this study: `a434b98acfdba312355790072164325109137ce6`
- Original source path: `case-studies/ravel/`
- Destination path: `case-studies/ravel/`
- Migration date: `2026-08-10`
- History: copied normally across repositories; Git file history is not implicitly preserved.
- Path/build changes: the historical root `Makefile` and RAVEL 0.5 workflow are retained byte-identically because the frozen 0.5 source manifest binds them. `GNUmakefile` is the destination operational entrypoint for study targets; the historical files are provenance-bound authorities.
- Relocated dependencies: RAVEL study code and evaluators remain local; no normative standards implementation is copied.
- Evidence-bearing artifact changed: no.
- Experiment rerun for migration: no. RAVEL 0.4 verification passed. The frozen source snapshot's RAVEL 0.5 canonical artifacts are already stale/missing when verified against its evaluator, so migration does not regenerate or relabel them.
- Validation after migration: training, unified, and RAVEL 0.4 checks passed; RAVEL 0.5 remains an explicit historical limitation with the source-baseline stale-artifact failure preserved.
