.PHONY: test evidence materialize avr-compile check clean

PYTHON ?= python3
MACHINE_LABEL ?= local-host
AVR_COMPILE_OUTPUT ?= evidence/local/avr-compile.json

# Offline mechanism, identity, and evidence checks. This does not replace AVR compilation.
test:
	$(PYTHON) tools/verify_case_study.py

evidence:
	$(PYTHON) tools/analyze_epoch1.py

materialize:
	$(PYTHON) tools/materialize.py

avr-compile:
	$(PYTHON) tools/capture_avr_compile.py \
		--machine-label "$(MACHINE_LABEL)" \
		--output "$(AVR_COMPILE_OUTPUT)"

check:
	$(PYTHON) tools/materialize.py --check
	$(PYTHON) tools/analyze_epoch1.py --check
	$(PYTHON) tools/verify_case_study.py

clean:
	rm -rf .materialized dsense_v5_*.csv dsense_v5_*.dsb
