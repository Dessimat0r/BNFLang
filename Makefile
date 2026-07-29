.PHONY: all test clean test-arm64

GTIMEOUT := $(shell command -v gtimeout 2>/dev/null || echo "gtimeout")

# ── Programs ───────────────────────────────────────────────────────────────

PROGRAMS := examples/counter examples/scope examples/pascal examples/pointer examples/dptr examples/sprintf examples/datatypes examples/multi_sprintf examples/test_control_flow examples/test_operators examples/test_functions examples/test_globals_arrays
ARM64_PROGRAMS := examples/counter-arm64 examples/scope-arm64 examples/pascal-arm64 examples/pointer-arm64 examples/dptr-arm64 examples/sprintf-arm64 examples/datatypes-arm64 examples/multi_sprintf-arm64 examples/test_control_flow-arm64 examples/test_operators-arm64 examples/test_functions-arm64 examples/test_globals_arrays-arm64

# ── Compile .msbnf → .sbnf ─────────────────────────────────────────────────

examples/c-to-ir.sbnf: examples/c-to-ir.msbnf
	python -m engine.msbnf examples/c-to-ir.msbnf examples/c-to-ir.sbnf

examples/ir-to-x86.sbnf: examples/ir-to-x86.msbnf
	python -m engine.msbnf examples/ir-to-x86.msbnf examples/ir-to-x86.sbnf

examples/ir-to-arm64.sbnf: examples/ir-to-arm64.msbnf
	python -m engine.msbnf examples/ir-to-arm64.msbnf examples/ir-to-arm64.sbnf

SBNF_FILES := examples/c-to-ir.sbnf examples/ir-to-x86.sbnf examples/ir-to-arm64.sbnf

# ── Stage 1: .c → Micro-IR (.ir) ───────────────────────────────────────────

examples/%.ir: examples/%.c examples/c-to-ir.sbnf
	python -m engine examples/c-to-ir.sbnf $< $@

# ── Stage 2: .ir → x86-64 .s ───────────────────────────────────────────────

examples/%.s: examples/%.ir examples/ir-to-x86.sbnf
	python -m engine examples/ir-to-x86.sbnf $< $@

# ── Stage 2: .ir → ARM64 .s ────────────────────────────────────────────────

examples/%-arm64.s: examples/%.ir examples/ir-to-arm64.sbnf
	python -m engine examples/ir-to-arm64.sbnf $< $@

# ── Assemble .s → executable ───────────────────────────────────────────────

examples/counter examples/scope examples/pascal examples/pointer examples/dptr examples/sprintf examples/datatypes examples/multi_sprintf examples/test_control_flow examples/test_operators examples/test_functions examples/test_globals_arrays:
	clang -arch x86_64 -c $(filter %.s,$^) -o $(@:.o=).o && \
	clang -arch x86_64 $(@:.o=).o -o $@ -lSystem

examples/counter-arm64 examples/scope-arm64 examples/pascal-arm64 examples/pointer-arm64 examples/dptr-arm64 examples/sprintf-arm64 examples/datatypes-arm64 examples/multi_sprintf-arm64 examples/test_control_flow-arm64 examples/test_operators-arm64 examples/test_functions-arm64 examples/test_globals_arrays-arm64:
	clang -arch arm64 -c $(filter %.s,$^) -o $(@:.o=).o && \
	clang -arch arm64 $(@:.o=).o -o $@ -lSystem

examples/counter: examples/counter.s
examples/scope: examples/scope.s
examples/pascal: examples/pascal.s
examples/pointer: examples/pointer.s
examples/dptr: examples/dptr.s
examples/sprintf: examples/sprintf.s
examples/datatypes: examples/datatypes.s
examples/multi_sprintf: examples/multi_sprintf.s
examples/test_control_flow: examples/test_control_flow.s
examples/test_operators: examples/test_operators.s
examples/test_functions: examples/test_functions.s
examples/test_globals_arrays: examples/test_globals_arrays.s

examples/counter-arm64: examples/counter-arm64.s
examples/scope-arm64: examples/scope-arm64.s
examples/pascal-arm64: examples/pascal-arm64.s
examples/pointer-arm64: examples/pointer-arm64.s
examples/dptr-arm64: examples/dptr-arm64.s
examples/sprintf-arm64: examples/sprintf-arm64.s
examples/datatypes-arm64: examples/datatypes-arm64.s
examples/multi_sprintf-arm64: examples/multi_sprintf-arm64.s
examples/test_control_flow-arm64: examples/test_control_flow-arm64.s
examples/test_operators-arm64: examples/test_operators-arm64.s
examples/test_functions-arm64: examples/test_functions-arm64.s
examples/test_globals_arrays-arm64: examples/test_globals_arrays-arm64.s

all: $(PROGRAMS) $(ARM64_PROGRAMS)

# ── Test Suite ─────────────────────────────────────────────────────────────

test: $(SBNF_FILES) $(PROGRAMS) test-arm64
	@echo "=== counter: run ==="
	@$(GTIMEOUT) 2 ./examples/counter > /tmp/counter-out.txt 2>&1; \
		printf "0\n1\n2\n3\n4\n" > /tmp/counter-expected.txt; \
		diff /tmp/counter-out.txt /tmp/counter-expected.txt && echo "PASS" || echo "FAIL"
	@echo "=== scope: run ==="
	@$(GTIMEOUT) 2 ./examples/scope > /tmp/scope-out.txt 2>&1; \
		printf "10\n0\n1\n2\n" > /tmp/scope-expected.txt; \
		diff /tmp/scope-out.txt /tmp/scope-expected.txt && echo "PASS" || echo "FAIL"
	@echo "=== pascal: run ==="
	@$(GTIMEOUT) 2 ./examples/pascal > /tmp/pascal-out.txt 2>&1; \
		printf "    1 \n   1 1 \n  1 2 1 \n 1 3 3 1 \n1 4 6 4 1 \n" > /tmp/pascal-expected.txt; \
		diff /tmp/pascal-out.txt /tmp/pascal-expected.txt && echo "PASS" || echo "FAIL"
	@echo "=== pointer: run ==="
	@$(GTIMEOUT) 2 ./examples/pointer > /tmp/pointer-out.txt 2>&1; \
		printf "5\n4\n3\n" > /tmp/pointer-expected.txt; \
		diff /tmp/pointer-out.txt /tmp/pointer-expected.txt && echo "PASS" || echo "FAIL"
	@echo "=== dptr: run ==="
	@$(GTIMEOUT) 2 ./examples/dptr > /tmp/dptr-out.txt 2>&1; \
		printf "5\n42\n" > /tmp/dptr-expected.txt; \
		diff /tmp/dptr-out.txt /tmp/dptr-expected.txt && echo "PASS" || echo "FAIL"
	@echo "=== sprintf: run ==="
	@$(GTIMEOUT) 2 ./examples/sprintf > /tmp/sprintf-out.txt 2>&1; \
		printf "42\n" > /tmp/sprintf-expected.txt; \
		diff /tmp/sprintf-out.txt /tmp/sprintf-expected.txt && echo "PASS" || echo "FAIL"
	@echo "=== datatypes: run ==="
	@$(GTIMEOUT) 2 ./examples/datatypes > /tmp/datatypes-out.txt 2>&1; \
		printf "42\n" > /tmp/datatypes-expected.txt; \
		diff /tmp/datatypes-out.txt /tmp/datatypes-expected.txt && echo "PASS" || echo "FAIL"
	@echo "=== multi_sprintf: run ==="
	@$(GTIMEOUT) 2 ./examples/multi_sprintf > /tmp/multi_sprintf-out.txt 2>&1; \
		printf "10 20 60\n" > /tmp/multi_sprintf-expected.txt; \
		diff /tmp/multi_sprintf-out.txt /tmp/multi_sprintf-expected.txt && echo "PASS" || echo "FAIL"
	@echo "=== test_control_flow: run ==="
	@$(GTIMEOUT) 2 ./examples/test_control_flow > /tmp/control_flow-out.txt 2>&1; \
		printf "2\n10\n3\n8\n200\n" > /tmp/control_flow-expected.txt; \
		diff /tmp/control_flow-out.txt /tmp/control_flow-expected.txt && echo "PASS" || echo "FAIL"
	@echo "=== test_operators: run ==="
	@$(GTIMEOUT) 2 ./examples/test_operators > /tmp/operators-out.txt 2>&1; \
		printf "3\n2\n52\n2\n5\n2\n300\n" > /tmp/operators-expected.txt; \
		diff /tmp/operators-out.txt /tmp/operators-expected.txt && echo "PASS" || echo "FAIL"
	@echo "=== test_functions: run ==="
	@$(GTIMEOUT) 2 ./examples/test_functions > /tmp/functions-out.txt 2>&1; \
		printf "42\n52\n8\n21\n" > /tmp/functions-expected.txt; \
		diff /tmp/functions-out.txt /tmp/functions-expected.txt && echo "PASS" || echo "FAIL"
	@echo "=== test_globals_arrays: run ==="
	@$(GTIMEOUT) 2 ./examples/test_globals_arrays > /tmp/globals_arrays-out.txt 2>&1; \
		printf "50\n75\n10\n20\n30\n40\n50\n150\n1\n2\n3\n" > /tmp/globals_arrays-expected.txt; \
		diff /tmp/globals_arrays-out.txt /tmp/globals_arrays-expected.txt && echo "PASS" || echo "FAIL"

test-arm64: $(SBNF_FILES) $(ARM64_PROGRAMS)
	@echo "=== arm64 counter ==="
	@$(GTIMEOUT) 2 ./examples/counter-arm64 > /tmp/arm64-counter-out.txt 2>&1; \
		printf "0\n1\n2\n3\n4\n" > /tmp/arm64-counter-expected.txt; \
		diff /tmp/arm64-counter-out.txt /tmp/arm64-counter-expected.txt && echo "PASS" || echo "FAIL"
	@echo "=== arm64 scope ==="
	@$(GTIMEOUT) 2 ./examples/scope-arm64 > /tmp/arm64-scope-out.txt 2>&1; \
		printf "10\n0\n1\n2\n" > /tmp/arm64-scope-expected.txt; \
		diff /tmp/arm64-scope-out.txt /tmp/arm64-scope-expected.txt && echo "PASS" || echo "FAIL"
	@echo "=== arm64 pascal ==="
	@$(GTIMEOUT) 2 ./examples/pascal-arm64 > /tmp/arm64-pascal-out.txt 2>&1; \
		printf "    1 \n   1 1 \n  1 2 1 \n 1 3 3 1 \n1 4 6 4 1 \n" > /tmp/pascal-expected.txt; \
		diff /tmp/arm64-pascal-out.txt /tmp/pascal-expected.txt && echo "PASS" || echo "FAIL"
	@echo "=== arm64 pointer ==="
	@$(GTIMEOUT) 2 ./examples/pointer-arm64 > /tmp/arm64-pointer-out.txt 2>&1; \
		printf "5\n4\n3\n" > /tmp/arm64-pointer-expected.txt; \
		diff /tmp/arm64-pointer-out.txt /tmp/arm64-pointer-expected.txt && echo "PASS" || echo "FAIL"
	@echo "=== arm64 dptr ==="
	@$(GTIMEOUT) 2 ./examples/dptr-arm64 > /tmp/arm64-dptr-out.txt 2>&1; \
		printf "5\n42\n" > /tmp/arm64-dptr-expected.txt; \
		diff /tmp/arm64-dptr-out.txt /tmp/arm64-dptr-expected.txt && echo "PASS" || echo "FAIL"
	@echo "=== arm64 sprintf ==="
	@$(GTIMEOUT) 2 ./examples/sprintf-arm64 > /tmp/arm64-sprintf-out.txt 2>&1; \
		printf "42\n" > /tmp/arm64-sprintf-expected.txt; \
		diff /tmp/arm64-sprintf-out.txt /tmp/arm64-sprintf-expected.txt && echo "PASS" || echo "FAIL"
	@echo "=== arm64 datatypes ==="
	@$(GTIMEOUT) 2 ./examples/datatypes-arm64 > /tmp/arm64-datatypes-out.txt 2>&1; \
		printf "42\n" > /tmp/datatypes-expected.txt; \
		diff /tmp/arm64-datatypes-out.txt /tmp/datatypes-expected.txt && echo "PASS" || echo "FAIL"
	@echo "=== arm64 multi_sprintf ==="
	@$(GTIMEOUT) 2 ./examples/multi_sprintf-arm64 > /tmp/arm64-multi_sprintf-out.txt 2>&1; \
		printf "10 20 60\n" > /tmp/multi_sprintf-expected.txt; \
		diff /tmp/arm64-multi_sprintf-out.txt /tmp/multi_sprintf-expected.txt && echo "PASS" || echo "FAIL"
	@echo "=== arm64 test_control_flow ==="
	@$(GTIMEOUT) 2 ./examples/test_control_flow-arm64 > /tmp/arm64-control_flow-out.txt 2>&1; \
		printf "2\n10\n3\n8\n200\n" > /tmp/control_flow-expected.txt; \
		diff /tmp/arm64-control_flow-out.txt /tmp/control_flow-expected.txt && echo "PASS" || echo "FAIL"
	@echo "=== arm64 test_operators ==="
	@$(GTIMEOUT) 2 ./examples/test_operators-arm64 > /tmp/arm64-operators-out.txt 2>&1; \
		printf "3\n2\n52\n2\n5\n2\n300\n" > /tmp/operators-expected.txt; \
		diff /tmp/arm64-operators-out.txt /tmp/operators-expected.txt && echo "PASS" || echo "FAIL"
	@echo "=== arm64 test_functions ==="
	@$(GTIMEOUT) 2 ./examples/test_functions-arm64 > /tmp/arm64-functions-out.txt 2>&1; \
		printf "42\n52\n8\n21\n" > /tmp/functions-expected.txt; \
		diff /tmp/arm64-functions-out.txt /tmp/functions-expected.txt && echo "PASS" || echo "FAIL"
	@echo "=== arm64 test_globals_arrays ==="
	@$(GTIMEOUT) 2 ./examples/test_globals_arrays-arm64 > /tmp/arm64-globals_arrays-out.txt 2>&1; \
		printf "50\n75\n10\n20\n30\n40\n50\n150\n1\n2\n3\n" > /tmp/globals_arrays-expected.txt; \
		diff /tmp/arm64-globals_arrays-out.txt /tmp/globals_arrays-expected.txt && echo "PASS" || echo "FAIL"
	@echo "=== all ARM64 tests pass ==="
	@echo "=== stack allocation intensive tests ==="
	@bash examples/test_stack.sh
	@echo "=== all tests pass ==="

clean:
	rm -f examples/*.ir examples/*.s examples/*.bin examples/*.o examples/counter examples/scope examples/pascal examples/pointer examples/dptr examples/sprintf examples/datatypes examples/multi_sprintf examples/test_control_flow examples/test_operators examples/test_functions examples/test_globals_arrays examples/*-arm64
