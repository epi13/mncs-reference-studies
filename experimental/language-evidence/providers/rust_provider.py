#!/usr/bin/env python3
from provider_common import ProviderDefinition, run

DEFINITION = ProviderDefinition(
    language="rust",
    provider_id="mncs.experimental.rust-source-provider",
    version="0.1.0",
    analysis_id="rust.bounded-source-safety",
    configuration_id="cfg:rust-source-provider-0.1.0",
    fail_tokens=("unsafe {", ".unwrap()", "MNCS_FAIL"),
    unknown_tokens=("macro_rules!", "#[cfg(", "MNCS_UNSUPPORTED"),
    limitations=(
        "Macro expansion is not analyzed",
        "Conditional compilation is not exhaustively enumerated",
    ),
)

if __name__ == "__main__":
    raise SystemExit(run(DEFINITION))
