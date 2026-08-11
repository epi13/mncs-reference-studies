#!/usr/bin/env python3
from provider_common import ProviderDefinition, run

DEFINITION = ProviderDefinition(
    language="c11",
    provider_id="mncs.experimental.c11-source-provider",
    version="0.1.0",
    analysis_id="c11.bounded-source-safety",
    configuration_id="cfg:c11-source-provider-0.1.0",
    fail_tokens=("gets(", "strcpy(", "MNCS_FAIL"),
    unknown_tokens=("__asm__", "_Generic(", "MNCS_UNSUPPORTED"),
    limitations=(
        "No whole-program alias proof",
        "Preprocessor expansion is not modeled",
    ),
)

if __name__ == "__main__":
    raise SystemExit(run(DEFINITION))
