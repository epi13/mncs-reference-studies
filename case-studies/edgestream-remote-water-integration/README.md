# EdgeStream to Remote Water Integration Study

This development-only study compiles and executes the existing generated EdgeStream C
candidate, feeds it binary telemetry frames under the EdgeStream contract, adapts accepted
canonical event records into the Remote Water telemetry interface, and compares the resulting
authorized intents against direct Remote Water inputs.

The adapter is deliberately narrow: one device, four metrics, strictly increasing event
sequences, and complete timestamp groups. It rejects duplicate or replayed sequences,
mixed-device records, unsupported metrics, invalid power values, and invalid quality codes.

The component evidence boundaries remain separate. EdgeStream retains its own captured
`MNCS-L4` development result. Remote Water retains formal `MNCS-L5` and `MNCDS-D3` status as
`UNKNOWN`. An integration PASS cannot promote either component claim or authorize live control.

Run from the repository root:

```bash
make edgestream-water-integration
```

The result is written to `evidence/results/study-summary.json`. This exercises a local file and
process boundary only. It provides no network transport, authentication, SCADA connection,
industrial protocol, or actuator output.
