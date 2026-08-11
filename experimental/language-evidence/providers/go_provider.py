#!/usr/bin/env python3
from provider_common import ProviderDefinition, run

DEFINITION = ProviderDefinition(
    language="go",
    provider_id="mncs.experimental.go-source-provider",
    version="0.2.0",
    analysis_id="go.bounded-concurrency-safety",
    configuration_id="cfg:go-source-provider-0.2.0",
    fail_tokens=(
        "MNCS_DEFECT_GOROUTINE_LEAK",
        "MNCS_DEFECT_MISSING_CANCEL",
        "MNCS_DEFECT_SHARED_STATE",
        "MNCS_DEFECT_CHANNEL_MISUSE",
        "MNCS_DEFECT_UNBOUNDED_WORKERS",
        "MNCS_DEFECT_PANIC_PATH",
        "MNCS_DEFECT_MALFORMED_INPUT",
    ),
    unknown_tokens=('import "C"', "//go:build", "MNCS_UNSUPPORTED_GENERATED"),
    limitations=(
        "bounded source markers and declared fixture structure only",
        "go test, vet, race, and fuzz remain separate runtime evidence",
    ),
)

if __name__ == "__main__":
    raise SystemExit(run(DEFINITION))
