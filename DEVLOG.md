# boop Framework -- Development Log

Completed work items, extracted from TODO.md. Most recent first.

---

## Stream Class -- Core Implementation

**Completed:** 2026-05-20

Record-oriented reader wrapping a file descriptor. Three parse modes
(direct/regex/pe) chosen at construction and locked for the object's life.

- Constructor parses options via Args into a Config object
- Direct mode: pre-built `read` args array, one builtin call per record
- Buffered modes: regex or parameter expansion for record/field extraction
- Field assignment via nameref (no eval, no `read <<<`)
- Field names stored as real arrays (`__boop_data_${_Self}_fields`)
- Object data in `__Stream_data` global associative array (eliminates
  `__boop.get` overhead -- 2-3x speedup over property system)
- Record delimiters: `-d` (single char), `-D` (exact string), `-E` (char class, collapsing)
- Field delimiters: `-f` (char class, non-stacking), `-F` (exact string)
- Fixed-width mode (`-n N`)
- Field-name validation (rejects non-identifiers)
- 138 tests passing (unit + edge cases)
- Benchmarks at `tests/bench/bench_stream` and `tests/bench/bench_blocksize_rigorous`
- Args `[Exclusive]` section added for mutual exclusion validation
- Removed unnecessary continuation backslashes across entire codebase (45 instances)
- Logging format updated: timestamp + right-justified 7-char level tag

---

## Text.String Class

**Completed:** 2026-05-13

String objects with mutating and non-mutating method variants. Two
families: bare verbs (trim, upcase, ...) mutate in place; -ed forms
(trimmed, upcased, ...) return new objects. Pipeline method `do`
executes a comma-separated chain in one call. All operations are pure
bash parameter expansion -- zero forks. 76 tests.

---

## DateTime Class

**Completed:** 2026-05-13

Date/time objects storing UTC epoch internally. Construction from
ISO 8601 or epoch is zero-fork (pure bash arithmetic). Only
`DateTime.parse` with non-ISO input spawns one subshell (date -d)
at construction; everything after is free. Arithmetic (addDays,
addHours), comparison (before, after, equals), diff, and formatting
all via printf builtin strftime. 71 tests.

---

## Signal Class

**Completed:** 2026-05-12

Managed per-signal callback stacks layered on top of bash's single-slot
trap. LIFO dispatch, extra-arg forwarding, error resilience (one bad
handler doesn't break the chain). Rejects KILL/STOP/DEBUG/RETURN with
clear error messages. Internalizes pre-existing traps at load time.
All methods are class-level (no instances). 46 tests using real signals
(USR1, USR2) plus delivery verification in isolated subshells.

---

## Parse Config Files as Data

**Completed:** 2026-05-12

`__boop.parseConfig` reads `.boopIndex` and `.boop.cfg` line-by-line
instead of sourcing them as bash scripts. Handles old formats
(`[Key]="Value"`, `__boop_classPath["Key"]="Value"`) and new canonical
`Key=Value`. First-write-wins semantics. Unrecognized lines emit
`_Warn`. No eval, no source, no code execution for machine-managed
config files.

---

## JSON Key Order Preservation

**Completed:** 2026-05-12

Stringify now tracks each leaf key in a companion indexed array
(`__boop_keys_${doc}`) alongside the Fast data hash. When present,
stringify iterates the ordered array so object keys appear in the
same order as the original JSON. Raw Fast objects (no keys array)
fall back to hash iteration. Also added `Data.JSON.validate` --
subshell-free validity check without crashing. 67 tests total.

---

## Stderr Redirection Audit

**Completed:** 2026-05-12

All three categories addressed:
- Class file load guards: replaced by `boop.init` (no more
  `&& return 2>/dev/null`)
- TestSuite assert_ok/assert_fail: stderr captured to temp file,
  emitted via `_Debug`
- boop import fallback: stderr captured and emitted via `_Debug`
- Signal class: all four `2>/dev/null` removed; stderr let through
- DateTime.parse: `date -d` stderr let through

---

## test_all Auto-Logging

**Completed:** 2026-05-08

`tests/test_all` now does `exec > >(tee "$__ta_log") 2>&1` at the
top, writing all output to `test_all.log` at the repo root. Every
run leaves a log for later inspection without needing to remember
to pipe manually.

---

## Mixin System

**Completed:** 2026-05

Method-only mixins: bundles of functions with no constructor or state that
can be composed into any class at bake time.

**Core additions to `boop`:**

- `boopMixin Name public:m1,m2` — declares a mixin; registers in
  `__boop_mixin_registry` and `__boop_methodRegistry`
- `mixin:Name` token in `boopClass` — wires a mixin into a class
- `boop.initMixin` — load guard + direct-execution detection for mixin files
- `__boop.mixes` / `$obj.mixes Name` — walks the inheritance chain checking
  the `mixins=` field; analogous to `isa` but for the mixin dimension
- `$obj.Mixin::method` — explicit provenance dispatch; always routes to that
  mixin's implementation regardless of which method won the default slot

**Resolution order:** class-defined methods win; then first mixin listed in
`boopClass`; then subsequent mixins (shadowed but still reachable via `::`).

**Inheritance:** `registerClass` registers each mixin method in
`__boop_methodRegistry[ClassName.method]`, so subclasses pick it up
automatically via the normal MRO walk.

**Design decisions:** method-only (no mixin state), bake-time resolution
(zero per-call overhead), class wins / first-mixin-wins for conflicts,
`mixes` for membership check (not `isa`), `::` for explicit disambiguation.

Includes two demo/test mixins (`Greetable`, `Taggable`) and 29 tests
in `tests/unit/test_mixin_ts`.

---

## Phase 2 Collections — Stack, Queue, Set

**Completed:** 2026-05

All three use composition, not inheritance. Each holds its backing
store internally and exposes only its own interface.

**Stack** (`Collection/Stack`) — LIFO. Composes a List; delegates
`push`/`pop`/`getAt(-1)` through it with `_Self` swapped to the
internal list ID. `push`, `pop`, `peek`, `size`, `isEmpty`. Crashes
on underflow. 19 tests.

**Queue** (`Collection/Queue`) — FIFO. Same composition pattern over
List; `enqueue` → List.push, `dequeue` → List.shift. `enqueue`,
`dequeue`, `peek`, `size`, `isEmpty`. Crashes on underflow. 19 tests.

**Set** (`Collection/Set`) — Unordered unique members. Backed by a
raw bash associative array (keys = members, O(1) ops). No intermediate
object needed. `add`, `has`, `remove`, `size`, `isEmpty`, `toArray`,
`union`, `intersect`, `difference`. Set operations return new Set
objects and leave operands unchanged. 38 tests.

LinkedList deferred — see TODO.

---

## Load Guard Refactor — `boop.init`

**Completed:** 2026-05

Replaced the `[[ -n "${__boop_registry[...]+set}" ]] && return 2>/dev/null`
pattern across all 15 class files. New pattern:

```bash
. boop
boop.init ClassName || return 0
```

`boop.init` (public, in boop core) handles three cases: already loaded
(returns 1, `|| return 0` exits cleanly), executed directly (`bash Box`
→ prints "Box is a boop class file. Load it with: . boop Box", exits 1),
first load (returns 0, loading continues). `__boop.guard` (internal)
is the pure registry-presence check that `boop.init` delegates to.

The `|| return 0` is intentional: `__boop.import` checks source exit
code, and the class alias (`Container`) can differ from the registry key
(`Collection.Container`), making a post-source registry check unreliable.

---

## Meta-Components Phase 1 — Version Guards and SemVer

**Completed:** 2026-05

Four interlocking pieces shipped together:

**SemVer class** (`SemVer/SemVer`) — pure bash, no external tools.
`SemVer.compare "1.2.3" "1.3.0"` → `-1`/`0`/`1` via `into=` or stdout.
`SemVer.satisfies "1.3.0" "1.2+"` → exit 0/1. Delegates to comparison
primitives inlined in boop core for the bootstrapping case. 38 tests.

Constraint syntax: `1.2+` (≥1.2.0), `>=1.2.3`, `>1.2`, `<=2.0`,
`<2.0`, `1.2.3` (exact). Pre-release suffixes ignored; missing
minor/patch default to 0.

**boop version guard** — `. boop require:1.2+` checks `__boop_version`
at source time before any class loading. If unsatisfied, walks
BOOPPATH/PATH for a candidate boop whose version satisfies the
constraint (reads the file line-by-line, no sourcing). Reports the
path if found; crashes either way. Re-loading a different boop core
at runtime (bless-it-in) deferred as a future concern.

**`boopClass version:` token** — `boopClass Math version:1.3.0 '...'`
stores `version=1.3.0` in the registry descriptor. Parsed by
`__boopClass.parseTokens`; harmlessly ignored by everything that
doesn't look for it.

**`_Require` class version checking** — `_Require Math 1.2+` loads
Math then enforces the version floor. After loading, extracts
`version=` from the registry descriptor. If SemVer is loaded, calls
`SemVer.satisfies` and crashes on failure. If SemVer is absent, emits
`_Warn` and continues (graceful degradation). Multiple classes in one
call: `_Require SemVer Math 1.2+ Config`.

Spec: `.kiro/specs/meta-components/design.md`

---

## JSON Unicode Escapes

**Completed:** 2026-05

`\uXXXX` escape sequences (BMP) and surrogate pairs (`🎉`
→ 🎉, emoji and extended CJK) now decode to UTF-8. The original
implementation used `printf '%b' "\U..."` which is locale-dependent
and failed silently with `LC_CTYPE=POSIX`. Replaced with manual
UTF-8 encoding: pure bash integer arithmetic computes the 1–4 byte
sequence; `printf -v x '\\x%02X' byte` + `printf -v result "$fmt"`
emits the bytes locale-independently. 54 tests, 6 previously failing
unicode cases now pass.

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

## Args Subcommand Scoping

**Completed:** 2026-05-08

Subcommand-scoped options (`[SubcmdName]` sections in the schema)
are now truly scoped. Using a scoped option before the subcommand
or under the wrong subcommand is a hard error. Object mode omits
out-of-scope variables entirely. Required validation skips
out-of-scope options. 6 new tests (63 total in Args suite).

Also: `_remaining` in object mode uses the delimiter instead of
IFS join (preserves word boundaries for args with spaces). `getOpts`
parses the optstring into a lookup set at start instead of fragile
`*opt:*` glob matching.

---

## Logging Hooks Throughout Codebase

**Completed:** 2026-05-08

`_Trace`/`_Debug`/`_Info` calls added throughout class method
implementations:

- `_Info` — object lifecycle (new, load, fromString)
- `_Debug` — mutations (set, delete, clear, push, pop, shift, unshift)
- `_Trace` — reads (getAt, has, keys, values, toArray, toString, calc)

Setting `_LogLevel debug` or `_LogLevel trace` now produces
meaningful diagnostic output. Also refactored `eval "name+=()"` to
`declare -gA "name=()"` — simpler, same effect.

Not yet covered: `__boop.import`, `__boop.loader`, `boop.classPath`,
object dispatch, property access, `boop.pass`. See "Extensive Logging
Hooks" in TODO for remaining scope.

---

## JSON Unicode Escape Handling

**Completed:** 2026-05-08

`\uXXXX` escapes now decode properly instead of being skipped.
Handles basic BMP characters and UTF-16 surrogate pairs for
characters beyond the BMP (emoji, CJK extensions). Rejects
unpaired surrogates and invalid hex with clear error messages.

Implementation uses `printf %b` with a dynamically-built `\U`
escape (bash 5+). Two-step format: `%08X` pads the codepoint,
then `%b` interprets the resulting `\U` sequence. 9 new tests
covering BMP chars, surrogate pairs, lowercase hex, mixed
literal/escape text, and error cases.

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
