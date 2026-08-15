.PHONY: check validate study-integrity recursive-study recursive-architecture-study-check \
  recursive-experience-substrate-check cacheforge-smoke cacheforge-test cacheforge-study \
  cacheforge-epoch2 edgestream-smoke edgestream-evidence remote-water-smoke \
  remote-water-test remote-water-study edgestream-water-integration ravel-test \
  ravel-training-check ravel-unified-check ravel-0.4-check ravel-0.4-compiler-matrix \
  ravel-0.4-sanitizers ravel-0.5-test ravel-0.5-evidence ravel-0.5-check \
  ravel-0.5-development-gates ravel-0.5-negative-test ravel-0.5-manifest-negative-test \
  ravel-0.5-compiler-matrix ravel-0.5-sanitizers ravel-0.5-runtime ravel-0.5-clean \
  ravel-0.5-historical-limitation \
  dsense-check dsense-avr-compile multilingual-stream go-gateway composed-gateway \
  composed-wave-three composed-wave-four composed-wave-five edgestream-validate \
  multilingual-standard-check cacheforge-language-profile

PYTHON ?= python3
MNCS_STANDARDS_ROOT ?=

validate:
	$(PYTHON) tools/validate_repository.py

study-integrity:
	$(PYTHON) tools/validate_migration.py

# Repository-level validation deliberately covers checks that do not rewrite
# checked-in evidence. Historical evidence-producing targets remain explicit.
check: validate study-integrity recursive-study recursive-architecture-study-check \
  recursive-experience-substrate-check cacheforge-test composed-gateway dsense-check \
  edgestream-smoke go-gateway multilingual-stream ravel-0.4-check \
  ravel-0.5-historical-limitation remote-water-test

recursive-study:
	PYTHONPATH=src $(PYTHON) studies/recursive-analyzer/run_study.py >/dev/null

recursive-architecture-study-check:
	$(PYTHON) studies/recursive-architecture-comparison/validate_study.py
	$(PYTHON) studies/recursive-architecture-comparison/test_validate_study.py

recursive-experience-substrate-check:
	$(PYTHON) studies/recursive-experience-substrate/validate_substrate.py
	$(PYTHON) studies/recursive-experience-substrate/test_validate_substrate.py

cacheforge-smoke:
	$(MAKE) -C case-studies/cacheforge smoke
cacheforge-test:
	$(MAKE) -C case-studies/cacheforge test
cacheforge-study:
	$(MAKE) -C case-studies/cacheforge study
cacheforge-epoch2:
	$(MAKE) -C case-studies/cacheforge epoch2
cacheforge-language-profile:
	$(PYTHON) tools/validate_cacheforge_profile.py

edgestream-smoke:
	$(MAKE) -C case-studies/edgestream smoke
edgestream-evidence:
	$(MAKE) -C case-studies/edgestream evidence
edgestream-validate:
	@test -n "$(MNCS_STANDARDS_ROOT)" || (echo "MNCS_STANDARDS_ROOT is required for normative EdgeStream validation" >&2; exit 2)
	$(MAKE) -C case-studies/edgestream validate \
		MNCS_STANDARDS_ROOT="$(MNCS_STANDARDS_ROOT)"

remote-water-smoke:
	$(MAKE) -C case-studies/remote-water-control smoke
remote-water-test:
	$(MAKE) -C case-studies/remote-water-control test
remote-water-study:
	$(MAKE) -C case-studies/remote-water-control study
edgestream-water-integration:
	$(MAKE) -C case-studies/edgestream-remote-water-integration study

ravel-test:
	$(MAKE) -C case-studies/ravel test
ravel-training-check:
	$(MAKE) -C case-studies/ravel training-check
ravel-unified-check:
	$(MAKE) -C case-studies/ravel unified-check
ravel-0.4-check:
	$(MAKE) -C case-studies/ravel 0.4-check
ravel-0.5-historical-limitation:
	$(PYTHON) tools/ravel_0_5_historical_limitation.py
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
	$(MAKE) -C case-studies/dsense-desk-pet avr-compile

multilingual-stream:
	$(MAKE) -C case-studies/multilingual-stream generate c11 rust
	$(PYTHON) case-studies/multilingual-stream/tools/run_experiment.py \
		--skip-benchmark --output /tmp/mncs-cross-language-report.json
multilingual-standard-check:
	@test -n "$(MNCS_STANDARDS_ROOT)" || (echo "MNCS_STANDARDS_ROOT is required for normative multilingual record/profile validation" >&2; exit 2)
	$(MAKE) -C case-studies/multilingual-stream \
		MNCS_STANDARDS_ROOT="$(MNCS_STANDARDS_ROOT)" check

go-gateway:
	$(MAKE) -C case-studies/go-gateway check
composed-gateway:
	$(MAKE) -C case-studies/composed-gateway check
composed-wave-three:
	@test -n "$(MNCS_STANDARDS_ROOT)" || (echo "MNCS_STANDARDS_ROOT is required for composed Wave Three validation" >&2; exit 2)
	MNCS_STANDARDS_ROOT="$(MNCS_STANDARDS_ROOT)" $(MAKE) -C case-studies/composed-gateway/wave-three check
composed-wave-four:
	@test -n "$(MNCS_STANDARDS_ROOT)" || (echo "MNCS_STANDARDS_ROOT is required for composed Wave Four validation" >&2; exit 2)
	PYTHONPATH="$(MNCS_STANDARDS_ROOT)/src" $(MAKE) -C case-studies/composed-gateway/wave-four check
composed-wave-five:
	@test -n "$(MNCS_STANDARDS_ROOT)" || (echo "MNCS_STANDARDS_ROOT is required for composed Wave Five validation" >&2; exit 2)
	PYTHONPATH="$(MNCS_STANDARDS_ROOT)/src" $(MAKE) -C case-studies/composed-gateway/wave-five check
