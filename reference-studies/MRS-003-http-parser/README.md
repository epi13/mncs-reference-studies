# MRS-003 — HTTP/1 parser

**Tier:** 1  
**Status:** PLANNED  
**Formal MNCS/MNCDS status:** UNKNOWN

## Question

Does an MNCS-style parser architecture improve explicit state reasoning, adversarial-input resistance, and agent modification reliability for an incremental protocol parser without unacceptable throughput or complexity costs?

## Why HTTP/1 parsing

HTTP/1 parsing adds protocol state, partial buffers, delimiters, header limits, framing rules, malformed traffic, and security-sensitive ambiguity while remaining small enough for controlled differential testing. It is a stronger state-machine test than JSON and a more adversarial surface than a pure codec.

## Planned arms

- frozen mature HTTP/1 parser/reference — **TBD after license/provenance review**;
- conventional idiomatic Rust implementation;
- MNCS-style Rust implementation;
- future MNCS-Language implementation.

## Initial metric families

- valid request/response parse equivalence within the frozen scope;
- partial/incremental input behavior;
- malformed and ambiguous input handling;
- header/line/resource limits;
- fuzzing and mutation-test outcomes;
- throughput and allocation behavior;
- verifier coverage of state transitions;
- controlled agent maintenance and security-fix tasks.

## Candidate agent tasks

Potential tasks include adding a header-count limit, preserving exact error offsets across incremental reads, or implementing a narrowly scoped framing-rule change against hidden regression tests.

## Claim boundary

This study is not a general HTTP-server security benchmark. Its claims must remain limited to the frozen parser surface, corpus, environment, and evaluation protocol.
