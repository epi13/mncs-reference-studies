.PHONY: generate generated-check c-check go-check rust-check smoke wave-three check

generate:
	python3 tools_generate.py
generated-check:
	python3 tools_generate.py --check
c-check:
	$${CC:-cc} -std=c11 -Wall -Wextra -Werror -pedantic -c c/parser.c -o /tmp/mncs-parser.o
go-check: generated-check
	cd go-host && go test ./... && go build ./...
rust-check:
	cd rust-authority && cargo fmt --check && cargo clippy --locked -- -D warnings && cargo test --locked && cargo build --locked --release
smoke: c-check go-check
	printf '12\n30\n' | MNCS_ROLLBACK=1 go-host/composed-host
wave-three:
	$(MAKE) -C wave-three check
check: c-check go-check rust-check smoke
