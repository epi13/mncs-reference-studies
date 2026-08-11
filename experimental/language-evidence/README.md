# Experimental language evidence profiles

This directory is a non-normative evidence layer for MNCS and MNCDS. It describes how a
particular language environment can supply bounded evidence without redefining MNCS levels,
MNCDS development profiles, or validator interoperability.

Four different statements remain separate:

1. **Candidate conformance** is an MNCS result for one declared implementation and evidence bundle.
2. **MNCDS process conformance** is a development-record result for one controlled lifecycle.
3. **Provider conformance** means a provider obeys Provider Protocol 0.1 and preserves PASS, FAIL,
   UNKNOWN, identity, and operational-error semantics.
4. **Profile validity** means a language evidence profile conforms to the experimental schema.

A language, compiler, interpreter, analyzer, or provider is never “MNCS certified.” A profile may
be profile-valid, a provider may be provider-conformant, and a capability may be evidence-supported.
Those statements do not establish an MNCS or MNCDS claim.

Wave One contains compact profiles for C11, Rust 1.97.1 edition 2024, and CPython 3.11. C11 remains
the controlled anchor because the existing EdgeStream evidence, strict compiler diagnostics,
sanitisers, Clang AST analysis, mutation work, and performance protocols are already bounded and
well understood. Rust adds a statically safe, macro-capable, Cargo-locked comparison. Python binds
the existing CacheForge AI/ML study while explicitly separating Python behavior from native
extensions and dynamic metaprogramming.

Run:

```bash
make language-profile-schema
make language-provider-corpus
make multilingual-stream
make cacheforge-language-profile
make multilingual-wave-one
```

Provider execution is always explicit. Ordinary `mncs validate`, bundle validation, packaging, and
MNCDS record validation never launch these providers.
