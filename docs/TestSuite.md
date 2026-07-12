# Testing.TestSuite

Test runner with section grouping, assertion helpers, and a summary report.
Used by all boop test suites and available for any bash project.

## Contents

- [Dependencies](#dependencies)
- [Quick Start](#quick-start)
- [Constructor](#constructor)
- [Sections](#sections)
- [Assertions](#assertions)
  - [`assert_ok` — command exits 0](#assert_ok-command-exits-0)
  - [`assert_fail` — command exits non-zero](#assert_fail-command-exits-non-zero)
  - [`assert_eq` — string equality](#assert_eq-string-equality)
  - [`assert_ne` — string inequality](#assert_ne-string-inequality)
  - [`assert_match` — glob pattern](#assert_match-glob-pattern)
  - [`assert_contains` — substring](#assert_contains-substring)
  - [`run` — execute queued assertions (queue mode)](#run-execute-queued-assertions-queue-mode)
- [Info Lines](#info-lines)
- [Summary](#summary)
- [Full Example — Unit Test File](#full-example-unit-test-file)
- [Design Notes](#design-notes)

---

## Dependencies

```bash
. boop TestSuite    # alias resolves to Testing.TestSuite
```

---

## Quick Start

```bash
#!/bin/bash
set -uo pipefail
. boop TestSuite MyClass

into=t TestSuite name="MyClass Tests"

$t.section "construction"
into=obj MyClass name="Alice"
$t.assert_ok "creates object"  test -n "$obj"

$t.section "methods"
into=n $obj.name
$t.assert_eq "name round-trips"  "$n"  "Alice"

$t.assert_fail "bad input crashes"  MyClass name=""

$t.summary
```

---

## Constructor

```bash
into=t TestSuite name="Suite Name"
into=t TestSuite name="Suite Name" mode=queue verbose=1
```

**Constructor arguments:**

| Argument | Default | Effect |
|----------|---------|--------|
| `name=` | (required) | Suite name shown in output |
| `mode=` | `immediate` | `immediate` — run assertions as called; `queue` — store and batch-execute via `$t.run` |
| `verbose=` | `0` | `1` prints every PASS line, section headers, and timing |

`verbose` can also be set via the environment variable `TESTSUITE_VERBOSE=1`
before creating the suite. The constructor reads it at creation time:

```bash
TESTSUITE_VERBOSE=1 ./tests/test_all
```

---

## Sections

Sections group related assertions for readability. The section name appears
in failure output.

```bash
$t.section "construction"
$t.section "arithmetic"
$t.section "error cases"
```

There is no `end section` — each `section` call closes the previous one.

---

## Assertions

All assertions take a **label** as their first argument. The label appears in
`PASS`/`FAIL` output.

### `assert_ok` — command exits 0

```bash
$t.assert_ok "label"  command [args...]
$t.assert_ok "file exists"   test -f /tmp/myfile
$t.assert_ok "length is set" test -n "$length"
$t.assert_ok "isa check"     $obj.isa Collection.List
```

Passes if the command exits 0. Fails if non-zero.

### `assert_fail` — command exits non-zero

```bash
$t.assert_fail "label"  command [args...]
$t.assert_fail "empty input crashes"  MyClass name=""
$t.assert_fail "underflow crashes"    $stack.pop
$t.assert_fail "bad color crashes"    $r.fg notacolor
```

Passes if the command exits non-zero. Fails if it exits 0.
Use this to confirm that invalid input produces a crash.

### `assert_eq` — string equality

```bash
$t.assert_eq "label"  actual  expected
$t.assert_eq "val correct"  "$v"  "3.14"
$t.assert_eq "class name"   "$c"  "Collection.List"
```

Passes if `actual == expected` (exact string comparison).

### `assert_ne` — string inequality

```bash
$t.assert_ne "label"  actual  unexpected
$t.assert_ne "IDs differ"  "$obj1"  "$obj2"
```

Passes if `actual != expected`.

### `assert_match` — glob pattern

```bash
$t.assert_match "label"  actual  pattern
$t.assert_match "has brackets"  "$json"  "*[*"
$t.assert_match "starts with v"  "$ver"  "v*"
```

Uses bash `[[ "$actual" == $pattern ]]`. Pattern is a glob, not a regex.

### `assert_contains` — substring

```bash
$t.assert_contains "label"  actual  substring
$t.assert_contains "has error msg"  "$output"  "required"
$t.assert_contains "has key"        "$s"        "port"
```

Passes if `actual` contains `substring` (uses `[[ "$actual" == *"$substring"* ]]`).

### `run` — execute queued assertions (queue mode)

```bash
$t.run
```

Executes all assertions that have been stored in the queue (queue mode only).
Each stored assertion is run in sequence, results are recorded, and the
queue is cleared. Call after a batch of assertions to report the results
and free the queue.

In immediate mode the queue is always empty, so `$t.run` is a no-op.

**Queue mode example:**

```bash
into=t TestSuite name="Batch Tests" mode=queue

$t.section "basics"
$t.assert_eq "one is one" "1" "1"
$t.assert_ok "true is true" true
$t.assert_fail "false is false" false

# Nothing has run yet — all stored in the queue.
$t.run    # Execute the batch; clears the queue.

$t.section "more"
$t.assert_ne "distinct values" "a" "b"
$t.run    # Execute this batch.

$t.summary
```

---

## Info Lines

Print informational output (not counted as a test):

```bash
$t.info "Testing against version $ver"
$t.info "Skipping GPU tests — no GPU detected"
```

---

## Summary

```bash
$t.summary
```

Prints the final counts and exits nonzero if any failures occurred:

```
  --- Suite Name ---
  PASS: 24   FAIL: 0
```

Always call `$t.summary` at the end of each test file. The `test_all` runner
checks the exit code of each test suite.

---

## Full Example — Unit Test File

```bash
#!/bin/bash
set -uo pipefail

. boop TestSuite Math

into=t TestSuite name="Math Tests"

# ── construction ──────────────────────────────────────────────────────────────

$t.section "construction"

into=n Math.new 3.14
$t.assert_ok "creates object"     test -n "$n"
into=v $n.val
$t.assert_eq "value round-trips"  "$v"  "3.14"

into=z Math.new
into=v $z.val
$t.assert_eq "default is zero"    "$v"  "0"

# ── arithmetic ────────────────────────────────────────────────────────────────

$t.section "arithmetic"

into=r Math.add "1.5" "2.5"
$t.assert_eq "add"            "$r"  "4"

into=r Math.multiply "3" "4"
$t.assert_eq "multiply"       "$r"  "12"

into=r Math.divide "10" "3"
$t.assert_match "divide prec" "$r"  "3.333*"

# ── comparison ───────────────────────────────────────────────────────────────

$t.section "comparison"

into=a Math.new "5"
into=b Math.new "3"
$t.assert_ok   "5 > 3"  $a.gt "$b"
$t.assert_fail "5 < 3"  $a.lt "$b"
$t.assert_ok   "5 >= 5" $a.ge "$a"

$t.summary
```

---

## Design Notes

**Exit code propagates.** `$t.summary` exits nonzero if any assertion failed.
When `test_all` runs each suite with `"$file" || rc=1`, a single failure in
any suite marks the whole run as failed.

**No output buffering.** Results print in real time as assertions run. In
verbose mode every PASS appears immediately; in normal mode only failures print
until `summary`.

**Crash isolation.** `assert_fail` runs the command in a subshell `()`.
This means a crashed command (non-zero exit) counts as a non-zero exit and
the assertion passes. The subshell isolates the failure from the test runner.
