# boop Framework — Development Log

Completed work items, extracted from TODO.md. Most recent first.

---

## Partial Namespace Resolution

**Completed:** 2026-05

`Map::Fast` now resolves via index prefix expansion. The resolver
splits on `/`, checks the index for the first segment, expands it,
and resolves the remainder via R1. Priority 2b — fires between
exact index match and dynamic discovery. 5 tests in
`test_classpath_ts`.

---

## Math Input Validation

**Completed:** 2026-05

`__Math.resolve` now validates input before arithmetic. Garbage
strings get a clear crash: `"Math: invalid number 'garbage' —
expected a numeric value like '3.14' or '-42'"`. Single chokepoint,
no cryptic `10#` bash errors leak through.

---

## Fully Qualified Class Names and Import Aliasing

**Completed:** 2026-05

Classes register with FQN internally (`Geometry.Box`,
`Collection.Map.Fast`). Aliases are real registry entries with
`trueClass` pointing to the FQN. Auto-aliasing creates short names
when unambiguous. `_Import` with `as` clause for explicit aliases.
`_AutoAlias` modes: full/best/short/none. 50+ tests in
`tests/unit/test_alias_ts`. Full spec at
`.kiro/specs/namespace-aliasing/`.

---

## _Static Helper

**Completed:** 2026-05

Three Tier 2 helpers: `_Me` (returns object ID or class name),
`_Static k=v`/`_Static k` (per-method storage), `_Property k=v`/
`_Property k` (per-object/class storage). All use `__boop_static`
as backing store with auto-generated compound key paths.

---

## JSON Parser (core)

**Completed:** 2026-05

`Data.JSON.parse` into `Collection.Map.Fast`, `Data.JSON.stringify`
back to JSON. Handles objects, arrays, strings (with escapes),
numbers, booleans, null. Pure bash, no external dependencies.
45 tests in `tests/unit/test_json_ts`. Docs at `docs/JSON.md`.

---

## Config Class

**Completed:** 2026-05

Reads/writes flat key=value and INI files. `Config.load`,
`Config.loadINI`, `Config.new`, `Config.fromString`. Full get/set/
has/keys/sections/save/toINI/toFlat interface. Pure bash parsing,
no `source`. 71 tests in `tests/unit/test_config_ts`.

---

## Map::Fast — Flat Compound-Key Store

**Completed:** 2026-05

`Collection/Map/Fast/Fast`. O(1) get/set, optional prefix indexing
via `keysUnder`/`deleteUnder`. Custom separator support. 40 tests
in `tests/unit/test_map_fast_ts`.

---

## Args — CLI Argument Parser (core)

**Completed:** 2026-05

Two entry points: `Args.getOpts` (POSIX short options) and
`Args.parse` (GNU long + subcommand with schema). `--help`/`-h`
prints schema verbatim. Object mode returns Config. 57 tests in
`tests/unit/test_args_ts`. Docs at `docs/Args.md`.

---

## Inline Class Definitions in Executable Scripts

**Completed:** 2026-04

`BASH_SOURCE[0]` vs `$0` guard pattern. `blackjack` demonstrates:
sourcing loads `BlackjackHand` for tests; executing runs the game.

---

## Return System: Default to stdout + Newline Control

**Completed:** 2026-04

`auto` mode always outputs to stdout. `_Out` global still available
via explicit `_OutMode=global`. `_Delegate`/`_Super`/`_Cast` forward
`into="${into:-}"` to inner calls. Subshell footgun documented (not
warned — false-positive risk too high).

---

## Namespace Remaining Work — All Complete

**Completed:** 2026-05 (verified)

All four remaining items from the Namespace/ClassPath/Index section
are done:

- **`test_classpath_ts`** — 60+ assertions covering namespace resolution,
  index lookup, classPath overrides, rebuild, CFG round-trip, RC chain
  sourcing, BOOPPATH construction, deduplication, conflict exclusion,
  `_Load`/`_Require`, and `::` normalization.
- **Namespace directory migration** — all classes live in namespace
  directories (`Collection/List/List`, `Geometry/Box/Box`, etc.).
  `.boopIndex` generated with all 13 classes mapped.
- **`__boop_dir` removal** — previously completed.
- **Property-based tests** — `test_classpath_pbt` implements spec
  properties.

---

## Return System: stdout Default + Dispatcher Forwarding

**Completed:** 2026-04-25 (commit `9e3afe0`)

`boop.pass` auto mode now always writes to stdout. Removed the
`BASHPID == __boop_rootPID` check that previously sent returns to
`_Out` in the main shell. `_Out` is still writable via explicit
`_OutMode=global`.

`_Delegate`, `_Super`, and `_Cast` now explicitly forward
`into="${into:-}"` to inner calls. Three new tests in
`test_stress_ts` cover the indirect forwarding case (outer caller
sets `into=`, inner method dispatches without its own `into=`).

All `test_stress_ts` call sites using `$_Out` for capture were
updated to `into=varname` or `$()` subshell capture. Bash-c
subshell tests using `b=$_Out` fixed to `into=b`.

**Key decision:** function replacement (overwrite `_Warn` etc. with
`() { :; }`) is the right mechanism for log-level bypass, not
aliases. Aliases don't expand in function bodies in non-interactive
shells without `shopt -s expand_aliases`.

---

## Test Layer Reorganization

**Completed:** 2026-04-25 (commit `7f08f92`)

Tests reorganized from a flat directory into three layers:
- `tests/smoke/` — framework alive? Gates everything else.
- `tests/unit/` — class correctness in isolation
- `tests/integration/` — end-to-end, stress, adversarial

`tests/test_all` supports `smoke`, `unit`, `integration`, and
`all` modes. Naming convention check only runs in `all` mode.

---

## Classpath / Namespace / Index Core Implementation

**Completed:** 2026-04 (merged from `claude/classpath-namespace-system`)

The framework now has:
- `__boop.classResolve` — namespace-aware resolution chain
  (classPath override → .boopIndex → filesystem convention → bare file)
- `__boop.loader` — RC chain sourcing (`/etc/booprc`, `~/.booprc`,
  `./.booprc`), BOOPPATH parsing, `.boopIndex` sourcing, version
  mismatch detection
- `__boop.import` — rewritten to use classResolve with raw source fallback
- `boop.resolve` — public non-fatal resolution wrapper
- `boop.classPath` — full subcommand API (set/get/list/remove/has/dirs/rebuild)
- CFG serialization helper
- Filesystem fallback diagnostic

**Prior art surveyed:** Java (CLASSPATH), Python (PYTHONPATH), Perl
(PERL5LIB/@INC), Ruby (RUBYLIB), Lua (LUA_PATH). Chose Perl model:
`::` maps to `/` on disk, each class lives inside its own namespace
folder. Universal rule: directories represent functional domains, never
inheritance hierarchies.

**Namespace convention:** `Collection::List` lives at
`root/Collection/List/List`. When namespace name == class name
(e.g. `Math`), file lives at `root/Math/Math`. User says `. boop Math`,
not `. boop Math::Math`.

**Two-file config convention:**
- `.booprc` — user-editable bash script, sources `.boop.cfg`
- `.boop.cfg` — machine-managed, never hand-edited; pure declarations

**Resolution order** (depth-first per root):
1. `__boop_classPath["Name"]` — explicit override
2. `.boopIndex` lookup → filesystem path
3. `Name/Name` — filesystem convention
4. `Name` — bare file
5. Next BOOPPATH root
6. PATH fallback
7. `_Crash`

---

## Fatality Threshold ("use strict" for boop)

**Completed:** 2026-04 (commit in classpath branch)

Three new globals in boop logging section: `__boop_fatalLevel`
(global default, crash=0), `__boop_classFatalLevel` (per-class
overrides), `__boop_resolvedFatalLevel` (cache). Same hot/cold
inheritance resolution as the visibility threshold.

Public API: `_FatalLevel`. Default is `crash(0)` — only explicit
`_Crash` is fatal. Set to `error(1)` and `_Error` auto-crashes.
Set to `warn(2)` and both `_Warn` and `_Error` auto-crash. Per-class
overrides inherited via class chain. 22 tests in `test_logging_ts`.

**Fix:** `(( level > threshold )) || _Crash` is the correct
pattern — arithmetic `(( ))` returning non-zero on false would have
been mistaken for a `_Error`-level exit code.

---

## Framework-Wide LogLevel System

**Completed:** 2026-03/04 (commit `991cd4f`)

Six numeric levels: `silent(0)`, `error(1)`, `warn(2)`, `info(3)`,
`debug(4)`, `trace(5)`. Global default is `warn`. Per-class overrides
inherited via the class chain with cached resolution (one hash lookup
+ integer compare on the hot path). Fallback log file at
`${TMPDIR:-/tmp}/boop_${PID}.log` when stderr is unavailable.

Public API: `_Error`, `_Warn`, `_Info`, `_Debug`, `_Trace`, `_Crash`,
`_LogLevel`. 70 tests in `test_logging_ts` (grew from 51 as fatality
tests were added).

**Bug found during sweep:** `local -i` on the threshold variable in
`__boop.log` coerced empty string to `0`, defeating the `[[ -z ]]`
sentinel that triggers fallback to the global log level. Fixed by
removing `-i`.

---

## Reserved Variable Names & Inheritance Hygiene

**Completed:** 2026-03 (commit `5fd7306`)

Renamed `self`/`class` to `_Self`/`_Class` across the entire
codebase: framework, all class files, all test files, documentation.
Mixed-case single-underscore chosen for semi-private status (unlikely
to collide with user variables, still usable for inline typecasts).

`__ClassName_methodName_varname` convention for locals prevents
nameref collisions — bash namerefs resolve by name, not lexical
scope. Convention now enforced by `test_all` naming convention check.

**Full compliance sweep:** `boop`, `Container`, `List`, `Map`,
`Math`, `TestSuite`, `Box`, `Cube`, `Card`, `Deck`, `Hand`,
`blackjack`.

---

## Configurable Baked-Wrapper Typecast Behavior

**Completed:** 2026-03 (commit `boop/89de2f0`)

Tier 3 (unrelated class leakage) now emits `_Warn` instead of
silently ignoring. Tier 2 (legitimate typecast) fixed to use
`__boop.isa` directly, correctly handling upcasts (e.g. `_Class=Box`
on a Cube). Visibility via `_LogLevel`.

---

## Generalize Card/Deck/Hand Classes

**Completed:** 2026-03 (commit `731250e`)

Card is now a generic base class. PlayingCard extends Card with
suit/rank/faceUp and 52-card standard deck generation. Deck is a
generic ordered collection with shuffle/draw. Blackjack-specific
logic (ace adjustment, bust/blackjack) lives in the blackjack
script, not in base classes.

---

## Housekeeping

**Completed:** 2026-04 (commit `94f2858`)

Stale log files removed (`math_out.log`, `pi_growth.log`,
`tc_debug.log`, `bash.exe.stackdump`, `REFACTOR_STATUS.md`).
`test_matrix` verified (benchmark only, intentionally excluded
from test count). `.gitignore` covers `*.log` and `*.stackdump`.

---

## BOOPPATH and Version Declaration

Both subsumed by the Classpath/Namespace/Index implementation.
`BOOPPATH` is the multi-root search path. `__boop_version` exists;
the loader checks `__boop_preferred_version` from RC files. Version
constraint enforcement is deferred to the Meta-Components / SemVer
item in TODO.md.
