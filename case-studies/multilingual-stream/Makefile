.PHONY: profiles providers generate c11 rust records experiment check clean

PYTHON ?= python3

profiles:
	$(PYTHON) ../../tools/validate_language_profile.py ../../experimental/language-evidence/profiles/c11-reference-v0.1.json
	$(PYTHON) ../../tools/validate_language_profile.py ../../experimental/language-evidence/profiles/rust-1.97.1-edition-2024-v0.1.json

providers:
	@test -n "$(MNCS_STANDARDS_ROOT)" || (echo "MNCS_STANDARDS_ROOT is required for the complete Provider Protocol corpus" >&2; exit 2)
	PYTHONPATH="$(MNCS_STANDARDS_ROOT)/src" $(PYTHON) "$(MNCS_STANDARDS_ROOT)/scripts/run-language-provider-corpus"

generate:
	$(PYTHON) generator/generate.py --check

c11:
	$(CC) -std=c11 -O2 -Wall -Wextra -Werror -pedantic c11/reference.c -o /tmp/mncs-stream-c-reference
	$(CC) -std=c11 -O2 -Wall -Wextra -Werror -pedantic c11/candidate.c -o /tmp/mncs-stream-c-candidate

rust:
	cargo fmt --check
	cargo clippy --locked --all-targets -- -D warnings
	cargo test --locked
	cargo build --release --locked

records:
	@test -n "$(MNCS_STANDARDS_ROOT)" || (echo "MNCS_STANDARDS_ROOT is required for MNCDS record validation" >&2; exit 2)
	PYTHONPATH="$(MNCS_STANDARDS_ROOT)/src" mncds validate mncds/development-record.json

experiment:
	$(PYTHON) tools/run_experiment.py --output /tmp/mncs-cross-language-report.json

check: profiles providers generate c11 rust records experiment

clean:
	rm -rf target /tmp/mncs-stream-c-reference /tmp/mncs-stream-c-candidate /tmp/mncs-cross-language-report.json
