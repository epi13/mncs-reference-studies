#!/usr/bin/env python3
from provider_common import ProviderDefinition, run

DEFINITION = ProviderDefinition(
    language="python",
    provider_id="mncs.experimental.python-source-provider",
    version="0.1.0",
    analysis_id="python.bounded-source-safety",
    configuration_id="cfg:python-source-provider-0.1.0",
    fail_tokens=("pickle.loads(", "yaml.load(", "MNCS_FAIL"),
    unknown_tokens=("exec(", "eval(", "__getattr__", "MNCS_UNSUPPORTED"),
    limitations=(
        "Reflection and monkey-patching are not resolved",
        "Native extension behavior is outside source-only coverage",
    ),
)

if __name__ == "__main__":
    raise SystemExit(run(DEFINITION))
