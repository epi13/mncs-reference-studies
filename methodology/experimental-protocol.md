# Experimental protocol

## 1. Freeze the question before optimizing the answer

Each MRS study begins with a written question, scope, comparison arms, external behavior, corpus, resource envelope, metrics, and gates. The first implementation epoch must not be evaluated against a moving target.

If the protocol changes after results are observed, create a new epoch. Preserve the prior protocol and result.

## 2. Reference identity

Before candidate implementation depends on it, freeze:

- upstream project and component;
- version/tag/commit;
- retrieval location;
- license and attribution obligations;
- any patches required to build the reference;
- test corpus identity and exclusions.

The reference implementation is evidence, not truth in every possible sense. Known upstream bugs should be recorded rather than silently copied into a normative contract.

## 3. Separate language effects from MNCS effects

Where the study question includes MNCS benefit, retain a conventional implementation in the same target language whenever practical. For the initial series this means an idiomatic Rust arm distinct from the MNCS-style Rust arm.

The conventional arm must not be intentionally handicapped.

## 4. Shared external contract

Comparison arms should receive the same valid, malformed, adversarial, and benchmark inputs wherever their interfaces permit. Normalize only what is necessary to compare equivalent behavior, and record non-comparable observations rather than manufacturing equivalence.

## 5. Development and protected evaluation

Development corpora may be visible and used to improve implementations. Protected or held-out evaluation, when used, must have a separately recorded custody/eligibility boundary. A schema-valid external input is not automatically an independent holdout.

## 6. Repetitions and seeds

Use deterministic seeds for generated corpora and record them. Performance measurements should use repeated runs and report distributions rather than a single favorable number. Warmup, affinity, power mode, and background-load controls should be documented when they materially affect results.

## 7. Non-regression gates

A study can have primary benefit thresholds, but correctness and declared safety/resource gates remain independent. A performance win cannot compensate for a correctness failure unless the preregistered protocol explicitly defines that behavior as an accepted tradeoff.

## 8. Agent experiments

Freeze agent task packets and verification before comparing arms. The implementation given to the agent may differ, but the requested behavior and scoring rule must not silently change. See `agent-evaluation.md`.

## 9. Negative evidence

Record null results and regressions. The purpose of a reference study is to learn where MNCS helps, where it does not, and which costs it introduces.
