# MNCS empirical-study migration record

This repository migration imports the historical empirical material from
`epi13/machine-native-complexity-standard` at frozen source commit
`80f08d312dce963265c7f69ac5b4bae8245bd692`.

The source snapshot contained 362 tracked files across nine case studies and
three research studies. The tracked files were imported with `git archive` and
verified byte-identically against a SHA-256 inventory (`362` entries; inventory
digest `9cf429d4ff7255a70f21d00b3c915e699a4284fd300aaeac59d3d8894746974a`).

Ignored local build products, caches, binaries, and generated working outputs
were not part of the Git source snapshot and were not imported. Checked-in
evidence, fixtures, preregistrations, thresholds, seeds, and claim boundaries
were not regenerated or rewritten by the copy.

Seven authored build/path files were subsequently adapted to establish the
standards-tooling boundary for composed Waves Three–Five and the multilingual
profile/record targets. Those files are listed in the study-local migration
records and are not evidence-bearing artifacts. The checked-in evidence files
remain byte-identical to the frozen inventory after restoring a locally
generated EdgeStream scratch result.

The normal cross-repository copy does not preserve Git file history. Each
study has its own `MIGRATION.md` with the source path, destination path, last
source-touching commit, and study-specific adaptation record.

The historical case-study and research-study lanes remain separate from the
numbered `reference-studies/MRS-*` lane.
