.PHONY: generate check-generated test smoke study epoch2 protected-evaluation clean

PYTHONPATH := src:machine
BUNDLE ?=
OUTPUT ?= evidence/results/protected-evaluation.json

generate:
	PYTHONPATH=$(PYTHONPATH) python tools/generate_policy.py

check-generated:
	PYTHONPATH=$(PYTHONPATH) python tools/generate_policy.py --check

test: check-generated
	PYTHONPATH=$(PYTHONPATH) pytest -q tests

smoke: check-generated
	PYTHONPATH=$(PYTHONPATH) python tools/run_study.py smoke

study: test
	PYTHONPATH=$(PYTHONPATH) python tools/run_study.py all

epoch2: test
	PYTHONPATH=$(PYTHONPATH) python tools/run_epoch2.py

protected-evaluation: check-generated
	test -n "$(BUNDLE)" || (echo "BUNDLE=/path/to/trace-bundle.json is required" && exit 2)
	PYTHONPATH=$(PYTHONPATH) python tools/run_protected_evaluation.py \
		--bundle "$(BUNDLE)" --output "$(OUTPUT)"

clean:
	rm -f evidence/results/study-summary.json
	rm -f evidence/results/epoch-2-development.json
	rm -f evidence/results/epoch-2-scenario-results.json
	rm -f evidence/results/protected-evaluation.json
