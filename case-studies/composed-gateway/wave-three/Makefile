OUTPUT ?= evidence/actual
STANDARDS_PYTHONPATH ?= ../../../src

.PHONY: generate generated-check static local epoch evaluate check clean

generate:
	python3 tools/generate_binding.py

generated-check:
	python3 tools/generate_binding.py --check

static: generated-check
	PYTHONPATH=$(STANDARDS_PYTHONPATH) python3 tools/verify_static.py

local: static
	rm -rf $(OUTPUT)
	python3 tools/run_epoch.py --output $(OUTPUT) --repetitions 9
	python3 tools/evaluate_epoch.py $(OUTPUT)/wave-three-epoch.json --output $(OUTPUT)/evaluator.json

epoch: static
	rm -rf $(OUTPUT)
	python3 tools/run_epoch.py --require-rust --output $(OUTPUT) --repetitions 9

evaluate:
	python3 tools/evaluate_epoch.py $(OUTPUT)/wave-three-epoch.json --output $(OUTPUT)/evaluator.json

check: epoch evaluate

clean:
	rm -rf build $(OUTPUT) rust-authority/target
