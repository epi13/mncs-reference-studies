# MRS reference reimplementation studies

MRS studies compare a mature reference behavior against deliberately separated implementation arms. Their purpose is to isolate where benefits and costs come from rather than simply demonstrating a successful MNCS implementation.

## Identifier policy

`MRS-NNN` identifiers are stable once published. Directory names use the identifier plus a short subject slug, for example `MRS-001-json`.

## Intended comparison arms

A typical study contains:

1. **reference** — frozen upstream implementation or authoritative behavioral fixture;
2. **conventional-rust** — idiomatic Rust without deliberate MNCS architecture;
3. **mncs-rust** — Rust structured around the MNCS hypotheses being tested;
4. **mncs-language** — future arm, added only when the language can implement the frozen contract credibly.

Not every study must implement every arm immediately, but omitted arms must be visible in the study manifest.

## Standard lifecycle

```text
PLANNED
  -> SELECTING_REFERENCE
  -> IMPLEMENTING
  -> DEVELOPMENT_EVALUATION
  -> PROTECTED_EVALUATION (when applicable)
  -> REVIEW_REQUIRED / COMPLETE
```

A lifecycle state is not a claim of superiority.

## Minimum study surface

Every MRS directory must contain `README.md` and `study.json`. The manifest is validated at repository level. Implementation, corpus, evidence, and tooling directories are added as the study enters implementation.

Use `templates/reference-study/` for new work.
