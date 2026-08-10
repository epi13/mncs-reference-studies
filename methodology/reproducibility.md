# Reproducibility

A result without environment identity is difficult to interpret and difficult for Fabric or outside contributors to reproduce.

## Record at minimum

When applicable, record:

- operating system and kernel/build;
- architecture;
- CPU model and logical/physical core information;
- RAM;
- accelerator/GPU and driver/runtime;
- compiler/interpreter/toolchain versions;
- dependency lockfile identities;
- build profile and relevant flags;
- benchmark affinity/power settings;
- model identity, quantization, serving runtime, and context settings for agent runs;
- random seeds;
- input/corpus digests;
- implementation commit/digest;
- study protocol/epoch identity.

## Heterogeneous Fabric runs

Cross-machine execution is useful, but do not average away substrate identity. Results from a Fedora CPU node, Windows GPU node, Raspberry Pi, or other worker should retain worker/environment labels.

## Determinism

Prefer deterministic generators and replayable fixtures. When nondeterminism is intrinsic, record repetition count and distribution. A deterministic final digest is valuable when it can be produced without hiding meaningful state.

## Generated evidence

Study runners should write evidence to explicit output paths. Protected/private inputs should not be committed accidentally; `.gitignore` provides default landing exclusions, but study-specific controls may be stricter.
