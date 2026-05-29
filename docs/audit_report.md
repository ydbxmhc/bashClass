# Codebase Audit Report

**Date:** 2026-05-29  
**Branch:** `claude/pull-and-evaluate-j9DlJ`  
**Scope:** Full codebase sweep — deviations from best practices (bash, OOP, framework conventions), security risks, and speed/maintainability opportunities.  
**Reference standards:** `docs/STANDARDS.md`, `docs/GOTCHAS.md`, `docs/bash_style.md`, `.kiro/steering/*.md`

No code was changed during this audit.

---

## Severity Legend

| Severity | Meaning |
|---|---|
| **CRITICAL** | Silent misbehavior or data corruption in production |
| **HIGH** | Security risk or hard crash under reachable conditions |
| **MEDIUM** | Correctness hazard that currently doesn't trigger due to surrounding conditions |
| **LOW** | Style, maintainability, or minor standards deviation |

---

## CRITICAL — Silent Misbehavior

### C1 · `Collection/List/List` — `$Class` vs `$_Class` typo in every method

**File:** `Collection/List/List`  
**Affected:** Every public method (`Collection.List.new`, `Collection.List.push`, `Collection.List.pop`, etc.)

Every method contains:

```bash
local _Self="${_Self:-${Class:-Collection.List}}"
```

The fallback references `$Class` (no underscore). The framework variable is `$_Class` (with underscore). `$Class` is never set by the dispatch machinery, so it is always empty, causing the inner fallback to always expand to the literal string `Collection.List`.

**Consequence:** In any calling context where `_Self` is not already set (e.g., static calls, or any call made before the dispatch chain sets `_Self`), every method silently operates on the hardcoded identity `Collection.List` instead of the actual receiver. Object identity is broken.

**Fix:** Change every occurrence to:

```bash
local _Self="${_Self:-${_Class:-Collection.List}}"
```

---

## HIGH — Security

### H1 · `Stream` — `eval "exec ${fd}>&-"` uses unvalidated FD value

**File:** `Stream/Stream`, methods `Stream.close` and `Stream._destroy`

```bash
eval "exec ${__boop_static[${_Self}.fd]}>&-"
```

The FD value is pulled from `__boop_static` (internal associative array). In normal operation this is an integer assigned during `Stream.new`. However, if the internal state were ever corrupted (e.g., by a bug in another method writing to `__boop_static`, or by a nameref collision), the `eval` would execute arbitrary shell code.

**Fix:** Validate that the FD value is a plain integer before the `eval`:

```bash
local __Stream_close_fd="${__boop_static[${_Self}.fd]}"
[[ "$__Stream_close_fd" =~ ^[0-9]+$ ]] || { boop.throw "Stream.close: invalid fd '${__Stream_close_fd}'"; return 1; }
eval "exec ${__Stream_close_fd}>&-"
```

Or use the validated-integer exec form directly if your bash version supports it.

### H2 · `boop` — Tmpfiles have no crash-cleanup trap

**File:** `boop`, functions `__boop.backfillMethods`, `__boop.registerClass`, `__boop.createAlias`

All three follow the pattern:

```bash
local tmpfile="${TMPDIR:-/tmp}/__boop_{bf,rc,alias}_$$"
# ... write to tmpfile ...
source "$tmpfile"
rm -f "$tmpfile"
```

If the script crashes (or `_Crash` fires) during the `source` step, `rm -f` never runs and the tmpfile leaks in `/tmp`. Because the name includes `$$` (PID), files from different runs don't overwrite each other, so they accumulate indefinitely.

**Fix:** Add a `trap` immediately after creating the file:

```bash
local tmpfile="${TMPDIR:-/tmp}/__boop_bf_$$"
trap 'rm -f "$tmpfile"' RETURN
```

`RETURN` fires when the function exits for any reason, including abnormal exits.

---

## MEDIUM — Correctness Hazards

### M1 · `lens` — `--not` flag silently ignored in `--fields` and `--chars` modes

**File:** `lens`, function `_lens_run`

The `--not` flag is documented as inverting selection. In position (`--match`) mode it is correctly applied. In `--fields` and `--chars` modes, `_lens_emit_rec` is called unconditionally; the `not` variable is never checked in those branches.

**Example of broken behavior:**

```bash
echo "foo:bar:baz" | lens --fields 1 -d: --not
# Should emit: bar:baz  (all fields except field 1)
# Actually emits: foo    (not flag silently ignored)
```

**Fix:** In `_lens_run`, before calling `_lens_emit_rec` in the fields/chars branches, add the `not`-inversion logic parallel to what exists in the match branch.

### M2 · `Args` — `read -ra` splits on ambient IFS in Phases 4b and 4d

**File:** `Args/Args`

Phase 4b (Exclusive group validation):

```bash
read -ra __Args_parse_gmembers <<< "$__Args_parse_gpart"
```

Phase 4d (Together group validation):

```bash
read -ra __Args_parse_tog_members <<< "$__Args_parse_tog"
```

Neither line sets `local IFS` first. If the calling script has set `IFS` to anything other than the default (`$' \t\n'`), `read -ra` will use that IFS to split the string, silently producing wrong member lists and causing group validation to fail or pass incorrectly.

**GOTCHAS.md** calls this out explicitly: "The user may have set IFS to anything before sourcing boop."

**Fix:** Add `local IFS=$' \t\n'` before each of these `read -ra` calls.

### M3 · `lens` — multiple standalone `(( n++ ))` statements are errexit hazards

**File:** `lens`, functions `_lens_run` and `_lens_emit_rec`

**GOTCHAS.md** explicitly documents this: `(( count++ ))` when count is 0 evaluates to 0 (false) and returns exit code 1. Under `set -e`, that kills the script.

Affected statements include (illustrative — grep `(( _n++` and `(( _lens_sel_count++`):

```bash
(( _n++ ))             # kills when _n == 0
(( _lens_sel_count++ ))  # kills when count == 0
```

`lens` currently runs without `set -e` so these don't crash today. But STANDARDS.md mandates errexit-safe code, and anyone who sources lens into a `set -e` context will be surprised.

**Fix:** Replace all standalone post-increments with pre-increment or addition form:

```bash
(( ++_n ))           # safe: evaluates to new value (>= 1)
(( _n += 1 ))        # also safe
```

Note: `(( _i++ > 0 ))` in the fields separator logic is **not** a bug — the `> 0` comparison means the exit code is based on the comparison, not the arithmetic. This one is fine.

---

## LOW — Standards Deviations and Style

### L1 · `lens` — local variables do not use triple-prefix naming

**File:** `lens`  
**Reference:** `docs/STANDARDS.md` §"Naming Conventions", `docs/bash_style.md`

STANDARDS requires that all locals inside any function use the triple-prefix form `__ClassName_methodName_varname`. `lens` is a script (not a class), but it defines internal functions and the same nameref-collision risk applies.

Current naming:

```bash
local _n _s _ws _we _spec _part _ofs _fi _out _i _rec _r _c _field _hit _dl _len
```

These single-character or two-character names will silently collide with nameref variables (`local -n`) if any of `_lens_run`'s callers or callees use a nameref to a variable with one of these names.

**Fix:** Adopt a consistent prefix, e.g., `__lens_run_n`, `__lens_run_i`, etc.

### L2 · `lens` — EOL and fdelim mutex not using group `[Exclusive]` form

**File:** `lens`, the Args schema at the top of the script

The EOL exclusivity is expressed as three pairwise constraint lines:

```
eolChar | eolString
eolChar | eolClass
eolString | eolClass
```

The fdelim exclusivity is also expressed as three pairwise lines:

```
fdelimSet | fdelimStr
fdelimSet | fdelimCol
fdelimStr | fdelimCol
```

The group `[Exclusive]` form was added to Args specifically for this case. These should be:

```
(eolChar eolString eolClass)
(fdelimSet fdelimStr fdelimCol)
```

Two lines instead of six; semantically clearer; fewer constraints to keep in sync if new options are added to the group.

### L3 · `lens` — function headers are incomplete

**File:** `lens`, all internal functions

STANDARDS requires full function header comments with `what`, `args`, `returns`, and `gotchas` sections. `_lens_run`, `_lens_emit_rec`, `_lens_parse_spec`, and `_lens_split_fields` have one-line descriptions at most.

### L4 · `Stream._scrubCharClass` — local variable naming violation

**File:** `Stream/Stream`, function `__Stream._scrubCharClass`

```bash
for c in ...; do
  local __Stream_bc_tmp=...
```

- `c` is a bare single-character variable name (not triple-prefix)
- `__Stream_bc_tmp` uses `bc` as the method-name segment, but the function is `_scrubCharClass`; it should be `__Stream_scrubCharClass_tmp`

### L5 · `blackjack` shuffle — variables don't follow script's own prefix convention

**File:** `blackjack`, function `BJ.shuffle` (or equivalent)

The shuffle function uses `__i`, `__j`, `__tmp` as loop variables. The rest of the script uses the `__BJ_` prefix convention. These should be `__BJ_shuffle_i`, `__BJ_shuffle_j`, `__BJ_shuffle_tmp` for consistency.

### L6 · `Collection.List.clear` — non-idiomatic array emptiness check

**File:** `Collection/List/List`, `Collection.List.clear`

```bash
[[ -n "${!__Collection_List_clear_arr[@]}" ]]
```

This uses indirect-expansion key enumeration inside `[[ -n ]]`, which is both non-standard and inconsistent with how other methods check for empty arrays (`(( ${#arr[@]} ))`). The intent is to check whether the array is non-empty; the idiomatic form is:

```bash
(( ${#__Collection_List_clear_arr[@]} > 0 ))
```

---

## Speed / Maintainability Opportunities

### S1 · `_lens_split_fields` fdelimSet branch — O(n·m) per record

**File:** `lens`, function `_lens_split_fields`

The fdelimSet branch (multi-character delimiter set) uses nested loops: outer over each character in the record, inner over each character in the delimiter set. For a record of length *n* and a delimiter set of size *m*, this is O(n·m) per record.

**Faster alternative:** Replace the inner loop with a glob test:

```bash
if [[ "${fdelimSet}" == *"${_c}"* ]]; then
```

This is still O(n·m) in worst-case terms but the constant factor is much smaller because the glob test runs inside bash's C layer rather than the shell dispatch loop.

An even faster approach for large inputs would be `tr` with the delimiter set, processing the whole record in one external call.

### S2 · `__boop.classResolve` — PATH/BOOPPATH scanned on every call

**File:** `boop`, function `__boop.classResolve`

Every class resolution call rebuilds the list of root directories from `$PATH` and `$BOOPPATH`. For scripts that instantiate many objects, this adds up.

**Improvement:** Cache the computed root list in a global array and invalidate (or re-scan) only when `$PATH` or `$BOOPPATH` changes (compare against a stored hash or stored value).

### S3 · `boop` nested helper functions — survive crash if `unset -f` doesn't run

**File:** `boop`, functions `__boop.loader` and `__boop.classResolve`

Both define inner helper functions (`__boop_loader_addRoot`, `__boop_classResolve_addRoot`, `__boop_classResolve_r1`) and clean them up with `unset -f` at the end. If the function crashes before the `unset -f`, those helpers persist in the global namespace for the remainder of the session.

This is a low-risk issue (the names are sufficiently obscure) but could cause baffling failures in a long-running interactive session where the same shell is reused. A `trap 'unset -f __boop_loader_addRoot' RETURN` at the top of each would make cleanup unconditional.

---

## Summary Table

| ID | File | Severity | Category | One-line description |
|---|---|---|---|---|
| C1 | `Collection/List/List` | CRITICAL | OOP convention | `$Class` should be `$_Class`; object identity always wrong on static calls |
| H1 | `Stream/Stream` | HIGH | Security | `eval "exec ${fd}>&-"` with unvalidated fd value |
| H2 | `boop` | HIGH | Security | Tmpfiles written by backfill/register/alias have no crash-cleanup trap |
| M1 | `lens` | MEDIUM | Correctness | `--not` silently ignored in `--fields` and `--chars` modes |
| M2 | `Args/Args` | MEDIUM | Correctness | `read -ra` in phases 4b/4d has no `local IFS`; breaks under non-default IFS |
| M3 | `lens` | MEDIUM | Correctness | `(( n++ ))` when n=0 returns exit 1; reaches code under set -e |
| L1 | `lens` | LOW | Standards | Locals not triple-prefixed; nameref collision risk |
| L2 | `lens` | LOW | Standards | EOL/fdelim mutex should use group `[Exclusive]` form |
| L3 | `lens` | LOW | Standards | Function headers incomplete (missing args/returns/gotchas) |
| L4 | `Stream/Stream` | LOW | Standards | `_scrubCharClass` locals named `c` and `__Stream_bc_tmp` (wrong prefix) |
| L5 | `blackjack` | LOW | Standards | Shuffle locals `__i/__j/__tmp` should use `__BJ_shuffle_` prefix |
| L6 | `Collection/List/List` | LOW | Standards | `[[ -n "${!arr[@]}" ]]` non-idiomatic; use `(( ${#arr[@]} ))` |
| S1 | `lens` | — | Speed | fdelimSet branch O(n·m) loop; replace inner loop with glob test |
| S2 | `boop` | — | Speed | PATH/BOOPPATH scanned on every class resolution; cache it |
| S3 | `boop` | — | Maintainability | Nested helpers survive crash if `unset -f` not reached; use `trap ... RETURN` |

---

*End of audit report.*
