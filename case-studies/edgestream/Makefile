.PHONY: generate build test benchmark harness-regression evidence validate smoke thorough clean

generate:
	python tools/run_study.py generate

build:
	python tools/run_study.py build

test:
	python tools/run_study.py test

benchmark:
	python tools/run_study.py benchmark

harness-regression:
	python tools/run_study.py harness-regression

evidence:
	python tools/run_study.py all
	python tools/package_evidence.py

validate:
	mncs validate-bundle . --require-pass
	mncds validate mncds/development-record.json --require-pass

smoke:
	python tools/smoke.py

thorough: evidence validate

clean:
	rm -rf build
	rm -f workloads/*.bin
