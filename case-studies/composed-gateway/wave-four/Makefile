OUTPUT ?= evidence/actual
STANDARDS_PYTHONPATH ?= ../../../src

.PHONY: service service-race custody-fixtures cross-host-fixtures readiness static check clean

service:
	cd service-host && go test ./...

service-race:
	cd service-host && go test -race ./...

custody-fixtures:
	PYTHONPATH=$(STANDARDS_PYTHONPATH) python3 tools/verify_custody.py fixtures/custody/valid-template.json
	! PYTHONPATH=$(STANDARDS_PYTHONPATH) python3 tools/verify_custody.py fixtures/custody/invalid-self-custody.json

cross-host-fixtures:
	mkdir -p $(OUTPUT)
	PYTHONPATH=$(STANDARDS_PYTHONPATH) python3 tools/reconcile_cross_host.py fixtures/cross-host/ubuntu.json fixtures/cross-host/macos.json --output $(OUTPUT)/cross-host-pass.json
	! PYTHONPATH=$(STANDARDS_PYTHONPATH) python3 tools/reconcile_cross_host.py fixtures/cross-host/ubuntu.json fixtures/cross-host/mismatch.json --output $(OUTPUT)/cross-host-fail.json
	PYTHONPATH=$(STANDARDS_PYTHONPATH) python3 tools/reconcile_cross_host.py fixtures/cross-host/ubuntu.json fixtures/cross-host/unknown.json --output $(OUTPUT)/cross-host-unknown.json

readiness:
	mkdir -p $(OUTPUT)
	PYTHONPATH=$(STANDARDS_PYTHONPATH) python3 tools/evaluate_readiness.py readiness-input.json --output $(OUTPUT)/claim-readiness.json

static:
	PYTHONPATH=$(STANDARDS_PYTHONPATH) python3 tools/verify_static.py

check: service service-race custody-fixtures cross-host-fixtures readiness static

clean:
	rm -rf $(OUTPUT) service-host/*.test
