# Holdout boundary

The public repository contains only a commitment to the Wave Three preregistration and the interface for supplying a protected corpus. It intentionally does not contain a protected seed or private trace. A hosted run without `MNCS_PROTECTED_HOLDOUT` records the holdout result as `UNKNOWN`; it may not substitute the development corpus or public reproduction corpus and call the result protected.

An independent evaluator may provide a newline-delimited decimal workload through `MNCS_PROTECTED_HOLDOUT`. The evaluator must separately retain the corpus identity, custody record, disclosure time, and result artifact. Repository maintainers cannot self-assert independent custody merely by setting the variable.
