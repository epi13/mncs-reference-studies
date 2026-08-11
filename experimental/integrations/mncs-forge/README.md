# Project-owned MNCS Forge capabilities

This directory defines the MNCS repository's first bounded micro-verifier capability
registry and Provider Protocol 0.1 provider. The integration is experimental,
provider-neutral at the protocol boundary, and non-normative.

The registry records narrow claims, methods, input kinds, witnesses, assumptions,
limitations, unsupported constructs, uncertainty classes, dependency envelopes,
costs, timeouts, requirement policy, consumers, and escalation paths. It is not a
second control plane and does not replace MNCS/MNCDS validation.

The fixed provider command implements:

- `evidence-change-impact`;
- `artifact-manifest-identity`;
- `mncs-assurance-graph-impact`; and
- `mncs-record-dispatch`.

Every invocation accepts exactly one bounded JSON Lines request and emits exactly one
matching response. It accepts no caller executable, argv, environment, working
directory, or shell command. Paths must remain within configured visible roots;
protected, absolute, traversing, symlink, remote, oversized, or excessive inputs
remain `UNKNOWN` or a protocol error. Analysis `FAIL` is used for an established
narrow mismatch or invalid supplied record. A process failure is operational
`UNKNOWN`, never analysis `PASS`.

The graph-impact method deliberately calls the current public Python implementation.
It is useful same-family development evidence, not an independent validator. The
record-dispatch method calls the public validator façade rather than duplicating
conformance semantics. The manifest method proves byte identity only. The
change-impact method trusts a caller-declared incomplete path envelope and therefore
cannot prove semantic independence.

Forge currently enforces `required_capabilities` at project level. This configuration
does not claim unsupported per-workflow enforcement. Compiler/platform capabilities
remain optional until a normal supported development environment can guarantee them.

The project development configuration is kept at repository root because Forge requires
project paths to be relative without `..` traversal. It retains the EdgeStream read-only
compatibility workflows and adds bounded project workflows. The compatibility record pins
the exact implementation commits used for local validation. Historical EdgeStream and
Joern evidence is unchanged.
