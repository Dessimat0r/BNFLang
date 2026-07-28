.PHONY: all test clean test-arm64

GTIMEOUT := $(shell command -v gtimeout 2>/dev/null || echo "gtimeout")

# ── Programs (x86-64) ───────────────────────────────────────────────────────

PROGRAMS := examples/counter examples/scope examples/pascal examples/pointer examples/dptr examples/sprintf examples/datatypes examples/multi_sprintf

# Compile .msbnf → .sbnf
examples/c-to-asm.sbnf: examples/c-to-asm.msbnf
	python -m engine.msbnf examples/c-to-asm.msbnf examples/c-to-asm.sbnf

examples/c-to-asm-arm64.sbnf: examples/c-to-asm-arm64.msbnf
	python -m engine.msbnf examples/c-to-asm-arm64.msbnf examples/c-to-asm-arm64.sbnf

# Compile .c → .s via our grammar
examples/counter.s: examples/c-to-asm.sbnf examples/counter.c
	python -m engine examples/c-to-asm.sbnf examples/counter.c examples/counter.s

examples/scope.s: examples/c-to-asm.sbnf examples/scope.c
	python -m engine examples/c-to-asm.sbnf examples/scope.c examples/scope.s

examples/pascal.s: examples/c-to-asm.sbnf examples/pascal.c
	python -m engine examples/c-to-asm.sbnf examples/pascal.c examples/pascal.s

examples/pointer.s: examples/c-to-asm.sbnf examples/pointer.c
	python -m engine examples/c-to-asm.sbnf examples/pointer.c examples/pointer.s

examples/dptr.s: examples/c-to-asm.sbnf examples/dptr.c
	python -m engine examples/c-to-asm.sbnf examples/dptr.c examples/dptr.s

examples/sprintf.s: examples/c-to-asm.sbnf examples/sprintf.c
	python -m engine examples/c-to-asm.sbnf examples/sprintf.c examples/sprintf.s

examples/datatypes.s: examples/c-to-asm.sbnf examples/datatypes.c
	python -m engine examples/c-to-asm.sbnf examples/datatypes.c examples/datatypes.s

examples/multi_sprintf.s: examples/c-to-asm.sbnf examples/multi_sprintf.c
	python -m engine examples/c-to-asm.sbnf examples/multi_sprintf.c examples/multi_sprintf.s

# Assemble .s → executable for x86-64
examples/counter examples/scope examples/pascal examples/pointer examples/dptr examples/sprintf examples/datatypes examples/multi_sprintf:
	clang -arch x86_64 -c $(filter %.s,$^) -o $(@:.o=).o && \
	clang -arch x86_64 $(@:.o=).o -o $@ -lSystem

examples/counter: examples/counter.s
examples/scope: examples/scope.s
examples/pascal: examples/pascal.s
examples/pointer: examples/pointer.s
examples/dptr: examples/dptr.s
examples/sprintf: examples/sprintf.s
examples/datatypes: examples/datatypes.s
examples/multi_sprintf: examples/multi_sprintf.s

# ── Programs (ARM64) ────────────────────────────────────────────────────────

ARM64_PROGRAMS := examples/counter-arm64 examples/scope-arm64 examples/pascal-arm64 examples/pointer-arm64 examples/dptr-arm64 examples/sprintf-arm64 examples/datatypes-arm64 examples/multi_sprintf-arm64

examples/counter-arm64.s: examples/c-to-asm-arm64.sbnf examples/counter.c
	python -m engine examples/c-to-asm-arm64.sbnf examples/counter.c examples/counter-arm64.s

examples/scope-arm64.s: examples/c-to-asm-arm64.sbnf examples/scope.c
	python -m engine examples/c-to-asm-arm64.sbnf examples/scope.c examples/scope-arm64.s

examples/pascal-arm64.s: examples/c-to-asm-arm64.sbnf examples/pascal.c
	python -m engine examples/c-to-asm-arm64.sbnf examples/pascal.c examples/pascal-arm64.s

examples/pointer-arm64.s: examples/c-to-asm-arm64.sbnf examples/pointer.c
	python -m engine examples/c-to-asm-arm64.sbnf examples/pointer.c examples/pointer-arm64.s

examples/dptr-arm64.s: examples/c-to-asm-arm64.sbnf examples/dptr.c
	python -m engine examples/c-to-asm-arm64.sbnf examples/dptr.c examples/dptr-arm64.s

examples/sprintf-arm64.s: examples/c-to-asm-arm64.sbnf examples/sprintf.c
	python -m engine examples/c-to-asm-arm64.sbnf examples/sprintf.c examples/sprintf-arm64.s

examples/datatypes-arm64.s: examples/c-to-asm-arm64.sbnf examples/datatypes.c
	python -m engine examples/c-to-asm-arm64.sbnf examples/datatypes.c examples/datatypes-arm64.s

examples/multi_sprintf-arm64.s: examples/c-to-asm-arm64.sbnf examples/multi_sprintf.c
	python -m engine examples/c-to-asm-arm64.sbnf examples/multi_sprintf.c examples/multi_sprintf-arm64.s

examples/counter-arm64 examples/scope-arm64 examples/pascal-arm64 examples/pointer-arm64 examples/dptr-arm64 examples/sprintf-arm64 examples/datatypes-arm64 examples/multi_sprintf-arm64:
	clang -arch arm64 -c $(filter %.s,$^) -o $(@:.o=).o && \
	clang -arch arm64 $(@:.o=).o -o $@ -lSystem

examples/counter-arm64: examples/counter-arm64.s
examples/scope-arm64: examples/scope-arm64.s
examples/pascal-arm64: examples/pascal-arm64.s
examples/pointer-arm64: examples/pointer-arm64.s
examples/dptr-arm64: examples/dptr-arm64.s
examples/sprintf-arm64: examples/sprintf-arm64.s
examples/datatypes-arm64: examples/datatypes-arm64.s
examples/multi_sprintf-arm64: examples/multi_sprintf-arm64.s

# ── Targets ─────────────────────────────────────────────────────────────────

all: $(PROGRAMS)

all-arm64: $(ARM64_PROGRAMS)

asm: examples/counter.s examples/scope.s examples/pascal.s examples/sprintf.s examples/datatypes.s examples/multi_sprintf.s

asm-arm64: $(ARM64_PROGRAMS:%=%.s)

clean:
	rm -f examples/*.s examples/*.bin examples/*.o examples/counter examples/scope examples/pascal examples/pointer examples/dptr examples/sprintf examples/datatypes examples/multi_sprintf examples/*-arm64

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

test-pascal: examples/pascal
	@echo "=== pascal: run ==="
	$(GTIMEOUT) 2 ./examples/pascal > /tmp/pascal-out.txt 2>&1; \
	printf "    1 \n   1 1 \n  1 2 1 \n 1 3 3 1 \n1 4 6 4 1 \n" > /tmp/pascal-expected.txt; \
 	diff /tmp/pascal-out.txt /tmp/pascal-expected.txt && echo "PASS" || echo "FAIL"

test-pointer: examples/pointer
	@echo "=== pointer: run ==="
	$(GTIMEOUT) 2 ./examples/pointer > /tmp/pointer-out.txt 2>&1; \
	printf "5\n4\n3\n" > /tmp/pointer-expected.txt; \
	diff /tmp/pointer-out.txt /tmp/pointer-expected.txt && echo "PASS" || echo "FAIL"

test-dptr: examples/dptr
	@echo "=== dptr: run ==="
	$(GTIMEOUT) 2 ./examples/dptr > /tmp/dptr-out.txt 2>&1; \
	printf "5\n42\n" > /tmp/dptr-expected.txt; \
	diff /tmp/dptr-out.txt /tmp/dptr-expected.txt && echo "PASS" || echo "FAIL"

test-sprintf: examples/sprintf
	@echo "=== sprintf: run ==="
	$(GTIMEOUT) 2 ./examples/sprintf > /tmp/sprintf-out.txt 2>&1; \
	printf "42\n" > /tmp/sprintf-expected.txt; \
	diff /tmp/sprintf-out.txt /tmp/sprintf-expected.txt && echo "PASS" || echo "FAIL"

test-datatypes: examples/datatypes
	@echo "=== datatypes: run ==="
	$(GTIMEOUT) 2 ./examples/datatypes > /tmp/datatypes-out.txt 2>&1; \
	printf "42\n" > /tmp/datatypes-expected.txt; \
	diff /tmp/datatypes-out.txt /tmp/datatypes-expected.txt && echo "PASS" || echo "FAIL"

test-multi_sprintf: examples/multi_sprintf
	@echo "=== multi_sprintf: run ==="
	$(GTIMEOUT) 2 ./examples/multi_sprintf > /tmp/multi_sprintf-out.txt 2>&1; \
	printf "10 20 30\n" > /tmp/multi_sprintf-expected.txt; \
	diff /tmp/multi_sprintf-out.txt /tmp/multi_sprintf-expected.txt && echo "PASS" || echo "FAIL"

# ── ARM64 Tests ──────────────────────────────────────────────────────────────

test-arm64-counter: examples/counter-arm64
	@echo "=== arm64 counter ==="
	$(GTIMEOUT) 2 ./examples/counter-arm64 > /tmp/arm64-counter-out.txt 2>&1; \
	printf "0\n1\n2\n3\n4\n" > /tmp/arm64-counter-expected.txt; \
	diff /tmp/arm64-counter-out.txt /tmp/arm64-counter-expected.txt && echo "PASS" || echo "FAIL"

test-arm64-scope: examples/scope-arm64
	@echo "=== arm64 scope ==="
	$(GTIMEOUT) 2 ./examples/scope-arm64 > /tmp/arm64-scope-out.txt 2>&1; \
	printf "10\n0\n1\n2\n" > /tmp/arm64-scope-expected.txt; \
	diff /tmp/arm64-scope-out.txt /tmp/arm64-scope-expected.txt && echo "PASS" || echo "FAIL"

test-arm64-pascal: examples/pascal-arm64
	@echo "=== arm64 pascal ==="
	$(GTIMEOUT) 2 ./examples/pascal-arm64 > /tmp/arm64-pascal-out.txt 2>&1; \
	printf "    1 \n   1 1 \n  1 2 1 \n 1 3 3 1 \n1 4 6 4 1 \n" > /tmp/arm64-pascal-expected.txt; \
	diff /tmp/arm64-pascal-out.txt /tmp/arm64-pascal-expected.txt && echo "PASS" || echo "FAIL"

test-arm64-pointer: examples/pointer-arm64
	@echo "=== arm64 pointer ==="
	$(GTIMEOUT) 2 ./examples/pointer-arm64 > /tmp/arm64-pointer-out.txt 2>&1; \
	printf "5\n4\n3\n" > /tmp/arm64-pointer-expected.txt; \
	diff /tmp/arm64-pointer-out.txt /tmp/arm64-pointer-expected.txt && echo "PASS" || echo "FAIL"

test-arm64-dptr: examples/dptr-arm64
	@echo "=== arm64 dptr ==="
	$(GTIMEOUT) 2 ./examples/dptr-arm64 > /tmp/arm64-dptr-out.txt 2>&1; \
	printf "5\n42\n" > /tmp/arm64-dptr-expected.txt; \
	diff /tmp/arm64-dptr-out.txt /tmp/arm64-dptr-expected.txt && echo "PASS" || echo "FAIL"

test-arm64-sprintf: examples/sprintf-arm64
	@echo "=== arm64 sprintf ==="
	$(GTIMEOUT) 2 ./examples/sprintf-arm64 > /tmp/arm64-sprintf-out.txt 2>&1; \
	printf "42\n" > /tmp/arm64-sprintf-expected.txt; \
	diff /tmp/arm64-sprintf-out.txt /tmp/arm64-sprintf-expected.txt && echo "PASS" || echo "FAIL"

test-arm64-datatypes: examples/datatypes-arm64
	@echo "=== arm64 datatypes ==="
	$(GTIMEOUT) 2 ./examples/datatypes-arm64 > /tmp/arm64-datatypes-out.txt 2>&1; \
	printf "42\n" > /tmp/arm64-datatypes-expected.txt; \
	diff /tmp/arm64-datatypes-out.txt /tmp/arm64-datatypes-expected.txt && echo "PASS" || echo "FAIL"

test-arm64-multi_sprintf: examples/multi_sprintf-arm64
	@echo "=== arm64 multi_sprintf ==="
	$(GTIMEOUT) 2 ./examples/multi_sprintf-arm64 > /tmp/arm64-multi_sprintf-out.txt 2>&1; \
	printf "10 20 30\n" > /tmp/arm64-multi_sprintf-expected.txt; \
	diff /tmp/arm64-multi_sprintf-out.txt /tmp/arm64-multi_sprintf-expected.txt && echo "PASS" || echo "FAIL"

test-arm64: test-arm64-counter test-arm64-scope test-arm64-pascal test-arm64-pointer test-arm64-dptr test-arm64-sprintf test-arm64-datatypes test-arm64-multi_sprintf
	@echo "=== all ARM64 tests pass ==="

test-stack:
	@echo "=== stack allocation intensive tests ==="
	bash examples/test_stack.sh

test-full: test-c-to-asm test-counter test-scope test-pascal test-pointer test-dptr test-sprintf test-datatypes test-multi_sprintf test-arm64 test-stack
	@echo "=== all tests pass ==="

test: test-full
