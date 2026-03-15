# TestSuite — Design Proposal

*boop class for structured test authoring and execution*

---

## Problem

The current test files (`test_box_cube`, `test_containers`, `test_math`,
`test_stress`) each define their own helper functions — `expect_ok`,
`expect_fail`, `expect_value`, `expect_stdout`, `__section`, `__timer_*`
— duplicated across four files with minor variations. Adding a new test
means copying boilerplate. Adding a new class means writing another
test file from scratch.

A `TestSuite` class centralizes the harness, standardizes the assertion
syntax, and lets boop test itself with boop.

---

## Design Goals

- Consistent assertion syntax across all test files
- Queue and immediate execution modes, switchable per-suite or per-call
- Section grouping with automatic timing
- Pass/fail accumulation with a clean summary
- Self-documenting — a test file should read like a spec
- No external dependencies — pure boop

---

## Execution Modes

### Immediate Mode (default)

Each assertion executes and reports as it's called. Results accumulate.
Good for interactive use and simple test files.

```bash
into=t TestSuite name="Box Tests"   # mode=immediate is default

$t.assert_eq "volume 5x3x7" "$vol" "105"    # runs immediately, prints result
$t.assert_ok "isa Box" $box.isa Box          # runs immediately, prints result
$t.summary                                   # prints final totals
```

### Queue Mode

Assertions are registered but not executed. `$t.run` executes the
queue in order, then clears it. Useful for organizing tests into
sections that run as a unit.

```bash
into=t TestSuite name="Box Tests" mode=queue

$t.section "Geometry"
$t.assert_eq "top area" "$top" "15"
$t.assert_eq "side area" "$side" "35"
$t.assert_eq "volume" "$vol" "105"
$t.run                              # executes section, prints results + timing

$t.section "Encoding"
$t.assert_eq "pipes round-trip" "$enc" "red|blue"
$t.run

$t.summary                          # final totals across all sections
```

### Per-Call Override

Regardless of the suite's default mode, individual assertions can
override via typecast:

```bash
queue=true $t.assert_eq "..."       # always queues
immediate=true $t.assert_eq "..."   # always runs now, clears nothing
```

---

## Assertion Methods

### `$t.assert_eq desc actual expected`

Passes if `actual == expected` (string comparison).

```bash
$t.assert_eq "volume" "$vol" "105"
$t.assert_eq "class name" "$cls" "Box"
```

### `$t.assert_ne desc actual expected`

Passes if `actual != expected`.

```bash
$t.assert_ne "not empty" "$result" ""
```

### `$t.assert_ok desc command [args...]`

Passes if the command returns exit code 0.
Runs in current shell — no subshell cost for non-crashing commands.

```bash
$t.assert_ok "isa Box" $box.isa Box
$t.assert_ok "file exists" test -f "$outfile"
```

### `$t.assert_fail desc command [args...]`

Passes if the command returns a non-zero exit code.
**Always runs in a subshell** — isolates commands that call
`__bashClass.crash` (which calls `exit`). No way around this.

```bash
$t.assert_fail "rejects zero dim" bash -c '. boop Box; Box length=0 width=1 height=1'
$t.assert_fail "invalid class name" bash -c '. boop; __bashClass.validate "bad-name"'
```

### `$t.assert_match desc value pattern`

Passes if `value` matches the glob pattern.

```bash
$t.assert_match "toString has class" "$str" "Box(*"
$t.assert_match "object ID format" "$id" "_*"
```

### `$t.assert_contains desc haystack needle`

Passes if `haystack` contains `needle` as a substring.

```bash
$t.assert_contains "error mentions class" "$err" "Box"
```

### `$t.info desc`

Prints an informational line without affecting pass/fail counts.
Replaces the `printf "  INFO: ..."` pattern in `test_stress`.

```bash
$t.info "duplicate prop → '$val' (documenting behavior)"
```

---

## Section and Timing

### `$t.section name`

In queue mode: labels the next batch, starts a section timer.
`$t.run` prints the section name, results, and elapsed time.

In immediate mode: prints a section header and starts a timer.
Subsequent assertions print under that header until the next
`$t.section` call.

```bash
$t.section "Return Modes"
# ... assertions ...
$t.run          # queue mode: executes + prints "  [0.123s]"
                # immediate mode: timer stops on next section call
```

---

## Summary

### `$t.summary`

Prints final totals across all sections:

```
=== Box Tests RESULTS ===
  Passed: 42
  Failed: 0
  Total:  42
  Time:   1.234s

  All tests passed.
```

Exits with code 1 if any assertions failed — compatible with CI.

---

## Internal Design

### Storage

Each queued assertion is a Map object stored in a List on the suite:

```
TestSuite object
  ├── name        "Box Tests"
  ├── mode        "queue" | "immediate"
  ├── passed      (integer, stored as property)
  ├── failed      (integer)
  └── queue       List of Map objects, each with:
                    type    "eq" | "ne" | "ok" | "fail" | "match" | "contains" | "info"
                    desc    human-readable label
                    actual  (for eq/ne/match/contains)
                    expect  (for eq/ne/match/contains)
                    cmd     (for ok/fail — encoded command + args)
```

The `cmd` field for `assert_ok`/`assert_fail` stores the command as
an encoded string. On execution, it's decoded and run via `"$@"` expansion.

### `$t.run` Execution Loop

```
for each assertion in queue:
  decode type and args
  execute the check
  print PASS or FAIL with description
  increment passed or failed
clear queue
stop section timer, print elapsed
```

### Subshell Boundary

`assert_fail` must always fork. The command it tests may call
`__bashClass.crash`, which calls `exit`. Running that in the current
shell kills the test runner. The subshell isolation is:

```bash
( "$@" ) 2>/dev/null; rc=$?
(( rc != 0 )) && PASS || FAIL
```

`assert_ok` *can* run in the current shell for most cases — the
caller's responsibility is not to pass crash-prone commands to it.
If they do, the test runner exits, which is its own kind of feedback.

---

## Conversion Plan

Once TestSuite is solid:

1. Rewrite `test_box_cube` first — smallest, easiest to verify
2. Then `test_containers`, `test_math`
3. `test_stress` last — most complex, most to gain

The old test files remain until the rewrites pass cleanly.
No flag days.

---

## Open Questions

- Should `assert_fail` accept a function name as an alternative to
  `bash -c '...'`? The `bash -c` form is portable but verbose.
  A function name form (`. boop; fn_to_test args`) would require
  the test environment to already have boop loaded, which it always does.
  **Tentative: support both. Function name if it's a declared function,
  `bash -c` string otherwise.**

- Should `$t.summary` be called automatically on process exit via a
  trap, or always explicit? Explicit is more predictable. **Tentative: explicit.**

- `TestSuite` needs a `Math` dependency for timing output (elapsed
  seconds with decimals). Or it can use the same raw `EPOCHREALTIME`
  arithmetic `test_stress` uses. **Tentative: raw arithmetic — no
  dependency on Math, keeps TestSuite self-contained.**

---

## Example: test_box_cube Rewritten

```bash
#!/bin/bash
. boop TestSuite Cube

into=t TestSuite name="Box and Cube Tests" mode=queue

# Setup
into=box Box length=5 width=3 height=7
into=cube Cube size=4 unit=cm

$t.section "Box Geometry"
into=top $box.top;    $t.assert_eq "top area"    "$top"    "15"
into=side $box.side;  $t.assert_eq "side area"   "$side"   "35"
into=vol $box.volume; $t.assert_eq "volume"      "$vol"    "105"
$t.run

$t.section "Type Checking"
$t.assert_ok "cube isa Cube"      $cube.isa Cube
$t.assert_ok "cube isa Box"       $cube.isa Box
$t.assert_ok "cube isa bashClass" $cube.isa bashClass
$t.assert_fail "cube isa Map"     $cube.isa Map
$t.run

$t.section "Encoding"
$box.set "notes" $'pipe|eq=pct%'
into=v $box.get "notes"
$t.assert_eq "special chars round-trip" "$v" $'pipe|eq=pct%'
$t.run

$t.summary
```

Clean. Readable. No boilerplate.
