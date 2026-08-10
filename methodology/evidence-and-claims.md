# Evidence and claims

This repository separates experimental outcomes from formal claims.

## Default states

New studies begin with:

```text
formal_mncs_status: UNKNOWN
formal_mncds_status: UNKNOWN
promotion_authorized: false
```

A favorable benchmark must not silently change those values.

## Suggested result vocabulary

- `PASS` — the frozen candidate passed the declared bounded protocol.
- `FAIL` — one or more declared gates failed.
- `REVIEW_REQUIRED` — evidence is informative but cannot be promoted without review or has material mixed results.
- `UNKNOWN` — the evidence does not establish the property/status.
- `NOT_APPLICABLE` — the property is outside the study scope.

`PASS` is deliberately narrower than “MNCS is better.”

## Development evidence

Development inputs may have influenced implementation decisions. Development evidence can guide engineering and hypothesis refinement, but it must be labeled as such.

## Protected evidence

Protected evaluation requires more than unseen bytes. Record who/what selected the input, when it was frozen, content identity, whether implementers had access, and whether the evaluator itself was frozen. If custody or independence is not established, say so.

## Promotion boundary

Any broader MNCS/MNCDS claim should identify the exact evidence set and the reasoning that connects bounded observations to the claim. That promotion should be independently reviewable and should not be performed automatically by a study runner.

## Failure is useful

A study that shows no MNCS benefit, or shows a cost, is successful research if the protocol is sound. Preserve it.
