.PHONY: format lint type test build examples corpus mncds-corpus interoperability release-candidate-schema release-candidate-corpus release-candidate-independent recursive-study recursive-architecture-study-check recursive-experience-substrate-check release-candidate-check docs edgestream-smoke edgestream-evidence remote-water-smoke remote-water-test remote-water-study edgestream-water-integration cacheforge-smoke cacheforge-test cacheforge-study cacheforge-epoch2 ravel-test ravel-training-check ravel-unified-check ravel-0.4-check ravel-0.4-compiler-matrix ravel-0.4-sanitizers ravel-0.5-test ravel-0.5-evidence ravel-0.5-check ravel-0.5-development-gates ravel-0.5-negative-test ravel-0.5-manifest-negative-test ravel-0.5-compiler-matrix ravel-0.5-sanitizers ravel-0.5-runtime ravel-0.5-clean dsense-check dsense-avr-compile language-profile-schema language-provider-corpus multilingual-stream cacheforge-language-profile multilingual-wave-one go-profile go-provider-corpus go-gateway composed-gateway multilingual-wave-two composed-wave-three multilingual-wave-three composed-wave-four multilingual-wave-four composed-wave-five multilingual-wave-five check

WAVE_THREE_OUTPUT ?= evidence/actual
WAVE_FOUR_OUTPUT ?= evidence/actual
WAVE_FIVE_OUTPUT ?= evidence/actual
DSENSE_MACHINE_LABEL ?= local-host
DSENSE_AVR_OUTPUT ?= evidence/local/avr-compile.json

format:
	ruff format .
lint:
	ruff format --check .
	ruff check .
type:
	mypy src
test:
	PYTHONPATH=src pytest
build:
	python -m build
examples:
	PYTHONPATH=src ./scripts/verify-examples
corpus:
	PYTHONPATH=src ./scripts/run-conformance-corpus
mncds-corpus:
	PYTHONPATH=src python scripts/run-mncds-corpus
interoperability:
	PYTHONPATH=src ./scripts/run-interoperability
release-candidate-schema:
	PYTHONPATH=src python -c "from mncs_validator.schemas import load_schema; [load_schema(name) for name in ('contract-profile-0.3','assurance-case-0.3','threat-record-0.3','measurement-profile-0.3','mncds-development-record-0.1')]"
release-candidate-corpus:
	PYTHONPATH=src ./scripts/run-release-candidate-corpus
release-candidate-independent:
	cargo test --manifest-path independent/rc-consumer/Cargo.toml
	cargo clippy --manifest-path independent/rc-consumer/Cargo.toml --all-targets -- -D warnings
	PYTHONPATH=src ./scripts/compare-release-candidate-consumers
recursive-study:
	PYTHONPATH=src python studies/recursive-analyzer/run_study.py >/dev/null
recursive-architecture-study-check:
	python studies/recursive-architecture-comparison/validate_study.py
	python studies/recursive-architecture-comparison/test_validate_study.py
recursive-experience-substrate-check:
	python studies/recursive-experience-substrate/validate_substrate.py
	python studies/recursive-experience-substrate/test_validate_substrate.py
release-candidate-check: release-candidate-schema release-candidate-corpus release-candidate-independent recursive-study
docs:
	./scripts/build-docs
edgestream-smoke:
	$(MAKE) -C case-studies/edgestream smoke
edgestream-evidence:
	$(MAKE) -C case-studies/edgestream evidence
remote-water-smoke:
	$(MAKE) -C case-studies/remote-water-control smoke
remote-water-test:
	$(MAKE) -C case-studies/remote-water-control test
remote-water-study:
	$(MAKE) -C case-studies/remote-water-control study
edgestream-water-integration:
	$(MAKE) -C case-studies/edgestream-remote-water-integration study
cacheforge-smoke:
	$(MAKE) -C case-studies/cacheforge smoke
cacheforge-test:
	$(MAKE) -C case-studies/cacheforge test
cacheforge-study:
	$(MAKE) -C case-studies/cacheforge study
cacheforge-epoch2:
	$(MAKE) -C case-studies/cacheforge epoch2
ravel-test:
	$(MAKE) -C case-studies/ravel test
ravel-training-check:
	$(MAKE) -C case-studies/ravel training-check
ravel-unified-check:
	$(MAKE) -C case-studies/ravel unified-check
ravel-0.4-check:
	$(MAKE) -C case-studies/ravel 0.4-check
ravel-0.4-compiler-matrix:
	$(MAKE) -C case-studies/ravel 0.4-compiler-matrix
ravel-0.4-sanitizers:
	$(MAKE) -C case-studies/ravel 0.4-sanitizers
ravel-0.5-test:
	$(MAKE) -C case-studies/ravel 0.5-test
ravel-0.5-evidence:
	$(MAKE) -C case-studies/ravel 0.5-evidence
ravel-0.5-check:
	$(MAKE) -C case-studies/ravel 0.5-check
ravel-0.5-development-gates:
	$(MAKE) -C case-studies/ravel 0.5-development-gates
ravel-0.5-negative-test:
	$(MAKE) -C case-studies/ravel 0.5-negative-test
ravel-0.5-manifest-negative-test:
	$(MAKE) -C case-studies/ravel 0.5-manifest-negative-test
ravel-0.5-compiler-matrix:
	$(MAKE) -C case-studies/ravel 0.5-compiler-matrix
ravel-0.5-sanitizers:
	$(MAKE) -C case-studies/ravel 0.5-sanitizers
ravel-0.5-runtime:
	$(MAKE) -C case-studies/ravel 0.5-runtime
ravel-0.5-clean:
	$(MAKE) -C case-studies/ravel 0.5-clean
dsense-check:
	$(MAKE) -C case-studies/dsense-desk-pet check
dsense-avr-compile:
	$(MAKE) -C case-studies/dsense-desk-pet avr-compile \
		MACHINE_LABEL=$(DSENSE_MACHINE_LABEL) \
		AVR_COMPILE_OUTPUT=$(DSENSE_AVR_OUTPUT)
language-profile-schema:
	PYTHONPATH=src ./scripts/validate-language-profile experimental/language-evidence/profiles/c11-reference-v0.1.json
	PYTHONPATH=src ./scripts/validate-language-profile experimental/language-evidence/profiles/rust-1.97.1-edition-2024-v0.1.json
	PYTHONPATH=src ./scripts/validate-language-profile experimental/language-evidence/profiles/python-cpython-3.11-v0.1.json
language-provider-corpus:
	./scripts/run-language-provider-corpus
multilingual-stream:
	$(MAKE) -C case-studies/multilingual-stream check
cacheforge-language-profile:
	./scripts/verify-cacheforge-language-profile
multilingual-wave-one:
	./scripts/run-multilingual-wave-one
go-profile:
	PYTHONPATH=src ./scripts/validate-language-profile experimental/language-evidence/profiles/go-1.23-v0.2.json
go-provider-corpus:
	./scripts/run-wave-two-provider-corpus
go-gateway:
	$(MAKE) -C case-studies/go-gateway check
composed-gateway:
	$(MAKE) -C case-studies/composed-gateway check
multilingual-wave-two: go-profile go-provider-corpus
	PYTHONPATH=src ./scripts/verify-wave-two
	$(MAKE) go-gateway
	$(MAKE) composed-gateway
composed-wave-three:
	$(MAKE) -C case-studies/composed-gateway/wave-three OUTPUT=$(WAVE_THREE_OUTPUT) check
multilingual-wave-three: go-profile go-provider-corpus
	PYTHONPATH=src ./scripts/verify-wave-three
	$(MAKE) composed-wave-three WAVE_THREE_OUTPUT=$(WAVE_THREE_OUTPUT)
composed-wave-four:
	$(MAKE) -C case-studies/composed-gateway/wave-four OUTPUT=$(WAVE_FOUR_OUTPUT) check
multilingual-wave-four:
	PYTHONPATH=src ./scripts/verify-wave-four
	$(MAKE) composed-wave-four WAVE_FOUR_OUTPUT=$(WAVE_FOUR_OUTPUT)
composed-wave-five:
	$(MAKE) -C case-studies/composed-gateway/wave-five OUTPUT=$(WAVE_FIVE_OUTPUT) check
multilingual-wave-five:
	PYTHONPATH=src ./scripts/verify-wave-five
	$(MAKE) composed-wave-five WAVE_FIVE_OUTPUT=$(WAVE_FIVE_OUTPUT)
check: lint type test build examples corpus mncds-corpus interoperability release-candidate-check recursive-architecture-study-check recursive-experience-substrate-check docs
