# MRS-002 — LZ4-style block codec

**Tier:** 1  
**Status:** PLANNED  
**Formal MNCS/MNCDS status:** UNKNOWN

## Question

Can MNCS-style structure increase assurance around buffer bounds, integer arithmetic, and corruption handling in a performance-sensitive codec while retaining competitive runtime and memory behavior relative to conventional Rust and a mature reference implementation?

## Why a block codec

A codec has an unusually objective core oracle: valid compressed data must decode correctly, and round trips must preserve the original bytes. The implementation also stresses hot loops, bounds, offsets, malformed streams, allocation strategy, and optimization choices, making it useful for testing whether stronger verification imposes measurable cost.

## Planned arms

- frozen mature LZ4-compatible/reference implementation — **TBD after license/provenance review**;
- conventional idiomatic Rust implementation;
- MNCS-style Rust implementation;
- future MNCS-Language implementation.

## Initial metric families

- known-vector compatibility;
- round-trip correctness;
- malformed/corrupt input handling;
- bounds and integer-safety evidence;
- fuzzing and mutation testing;
- compression/decompression throughput;
- memory and allocation behavior;
- binary/build cost where meaningful;
- controlled agent modification success.

## Candidate agent tasks

Potential frozen tasks include adding a configurable output bound, improving corruption diagnostics, or adding a streaming wrapper while preserving the block-format contract.

## Claim boundary

The study must not trade correctness for speed or treat language safety alone as an MNCS result. Conventional Rust exists specifically to expose that distinction.
