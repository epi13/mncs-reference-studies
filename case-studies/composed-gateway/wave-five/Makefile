DIST ?= dist
OUTPUT ?= evidence/actual
STANDARDS_PYTHONPATH ?= ../../../src

.PHONY: bundle bundle-check local-smoke static cohort check clean

bundle:
	python3 tools/build_bundle.py --output $(DIST)

bundle-check:
	python3 tools/build_bundle.py --output $(DIST) --check-lock bundle-lock.json

local-smoke: bundle-check
	python3 tools/run_ci_bundle.py \
		--archive $(DIST)/mncs-wave-five-portable-evaluator.zip \
		--lock $(DIST)/bundle-lock.json \
		--machine-label local-smoke \
		--operator-id operator:repository \
		--output $(OUTPUT)/host-record-local-smoke.json

static:
	PYTHONPATH=$(STANDARDS_PYTHONPATH) python3 tools/verify_static.py

cohort:
	PYTHONPATH=../../../src python3 tools/reconcile_cohort.py \
		$(HOST_RECORDS) \
		--plan machine-plan.json \
		--output $(OUTPUT)/operator-cohort.json

check: bundle-check local-smoke static

clean:
	rm -rf $(DIST) $(OUTPUT)
