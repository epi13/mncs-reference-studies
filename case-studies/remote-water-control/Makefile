.PHONY: generate check-generated test smoke study clean

PYTHONPATH := src:machine

generate:
	PYTHONPATH=$(PYTHONPATH) python tools/generate_planner.py

check-generated:
	PYTHONPATH=$(PYTHONPATH) python tools/generate_planner.py --check

test: check-generated
	PYTHONPATH=$(PYTHONPATH) pytest -q

smoke: check-generated
	PYTHONPATH=$(PYTHONPATH) python tools/run_study.py smoke

study: test
	PYTHONPATH=$(PYTHONPATH) python tools/run_study.py all

clean:
	rm -f evidence/results/scenario-results.json evidence/results/study-summary.json
