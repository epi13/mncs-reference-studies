# Standards-tooling dependency boundary

Historical studies may consume normative MNCS/MNCDS schemas or validators for
full conformance-oriented checks. That implementation remains authoritative in
the core standards repository and is not copied into this empirical repository.

Set `MNCS_STANDARDS_ROOT` to a checkout of
`https://github.com/epi13/machine-native-complexity-standard` when invoking an
explicit target such as `make edgestream-validate`,
`make multilingual-standard-check`, `make composed-wave-four`, or
`make composed-wave-five`.

Ordinary `make check` runs destination-owned structural, behavioral, compiler,
and fixture checks that do not require the normative implementation or mutate
checked-in evidence. A missing standards checkout is therefore an explicit
dependency limitation, not a silently substituted validator.
