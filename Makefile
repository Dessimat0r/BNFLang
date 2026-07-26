# Disable built-in rules that compile .c files directly
.SUFFIXES:
MAKEFLAGS += --no-builtin-rules

.PHONY: all test clean

GTIMEOUT := $(shell command -v gtimeout 2>/dev/null || echo "gtimeout")

# ── Programs ────────────────────────────────────────────────────────────────

PROGRAMS := examples/counter examples/scope

# Each program's .s depends on the grammar + its .c source
examples/counter.s: examples/c-to-asm.sbnf examples/counter.c
	python -m engine examples/c-to-asm.sbnf examples/counter.c examples/counter.s

examples/scope.s: examples/c-to-asm.sbnf examples/scope.c
	python -m engine examples/c-to-asm.sbnf examples/scope.c examples/scope.s

# Assemble .s → .o
%.o: %.s
	clang -arch x86_64 -c $< -o $@

# Link .o → executable
%: %.o
	clang -arch x86_64 $< -o $@ -lSystem

.PRECIOUS: examples/counter.o examples/scope.o

# ── Targets ─────────────────────────────────────────────────────────────────

all: $(PROGRAMS)

asm: examples/counter.s examples/scope.s

clean:
	rm -f examples/*.s examples/*.bin examples/*.o examples/counter examples/scope

# ── Tests ───────────────────────────────────────────────────────────────────

test-c-to-asm: examples/counter.s
	@echo "=== c-to-asm: check ==="
	grep -q '_main:' examples/counter.s || (echo "FAIL: missing _main"; exit 1)
	grep -q 'push rbp' examples/counter.s || (echo "FAIL: missing push rbp"; exit 1)
	grep -q 'call _printf' examples/counter.s || (echo "FAIL: missing call printf"; exit 1)
	@echo "PASS"

test-counter: examples/counter
	@echo "=== counter: run ==="
	$(GTIMEOUT) 2 ./examples/counter > /tmp/counter-out.txt 2>&1; \
	printf "0\n1\n2\n3\n4\n" > /tmp/counter-expected.txt; \
	diff /tmp/counter-out.txt /tmp/counter-expected.txt && echo "PASS" || echo "FAIL"

test-scope: examples/scope
	@echo "=== scope: run ==="
	$(GTIMEOUT) 2 ./examples/scope > /tmp/scope-out.txt 2>&1; \
	printf "10\n0\n1\n2\n" > /tmp/scope-expected.txt; \
	diff /tmp/scope-out.txt /tmp/scope-expected.txt && echo "PASS" || echo "FAIL"

test-full: test-c-to-asm test-counter test-scope
	@echo "=== all tests pass ==="

test: test-full
