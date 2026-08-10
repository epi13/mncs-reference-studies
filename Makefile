.PHONY: check validate

check: validate

validate:
	python3 tools/validate_repository.py
