# boop Framework — TODO

Collected future work items. Inline TODOs in source files should
reference entries here by section name.

---

## `::` Syntax — Mixins, Classlets, and Multiple Inheritance

The `::` separator is conventional in bash for namespaced functions
(`mylib::init`). boop doesn't use it — dots handle class.method
dispatch. That frees `::` for a new role.

Three potential applications, possibly overlapping:

### Mixins / Traits ("Classlets")

Bundles of methods without constructors or state — `Serializable`,
`Comparable`, `Printable`. Not full classes, just method sets you
mix into a real class on demand. The `::` identifies provenance:
`Serializable::save` is the `save` method provided by the
`Serializable` mixin, distinguishing it from any `save` the class
defines itself.

### Lazy Sub-Modules

`Math::Trig` loads trig functions only when first touched. It
doesn't inherit from Math — it extends Math's surface area on
demand. The `::` signals "sub-module of" without implying an
inheritance relationship. Could hook into the existing lazy
stub/bake mechanism: first call to `Math::Trig.sin` triggers
the load.

### Multiple Inheritance Disambiguation

If A inherits from both B and C, and both provide `method`,
`B::A.method` specifies which lineage to resolve through.
Similar to C++'s `Base::method()` — explicit, no magic, the
programmer picks the path. Avoids Python-style MRO linearization
complexity.

Open questions:
- Does `::` participate in dispatch, or is it purely a source-time
  resolution hint?
- Can classlets have state (properties), or are they method-only?
- How does `isa` work with mixins? `$obj.isa Serializable`?
- Performance: does this add overhead to the hot path, or is it
  resolved at bake time and free thereafter?

This is a design exploration — no implementation yet.

---

## Load Guard & Class Init Refactor

The current load guard pattern in every class file:

```bash
[[ -n "${__boop_registry[ClassName]+set}" ]] && return 2>/dev/null
```

Has two problems:

1. The `return` silently fails when the file is executed directly
   (not sourced), and `2>/dev/null` hides the error. Under `set -e`
   this is a silent fatal exit with no explanation.

2. There's no help output — running `bash Box` does nothing useful.

Planned replacement: a `boop.init` method on the root class that
handles the load guard, detects direct execution, and prints help text.
Design includes per-class help via `__boop_help["ClassName"]`,
inheritable defaults, and a single-statement call pattern in class
files. Details still under discussion.

See also: "Class File Execution Guard & Help System" (below).

Source: `boop`, all class files.

---

## Reserved Variable Names & Inheritance Hygiene ✓ DONE

The framework inherits exactly two names via `local -I`: `_Self` and
`_Class`. Every method in every class uses one or both. These are
effectively reserved words — user code must not use them unlocalized.

The rename from `self`/`class` to `_Self`/`_Class` was completed across
the entire codebase: framework (`boop`), all class files, all test files,
and all documentation. The mixed-case single-underscore convention was
chosen to be semi-private (unlikely to collide with user variables) while
still being usable when needed for inline typecasts.

Beyond `-I`, any variable a function references without `local` will
resolve up the call stack. The baked wrappers in `boop` set `_Self`
and `_Class` as plain (non-local) assignments intentionally — they're
dispatch glue. But this means any unlocalized variable in any method
silently inherits from its caller, which is a latent collision risk.

The `__ClassName_methodName_varname` convention exists to prevent
this, but compliance isn't audited.

The silent-correction behavior in dispatch is the sharpest edge here.
When a method is delegated from a class that doesn't have it to one
that does, the baked wrapper silently adopts the target class's
identity. That's great when intentional, but a nightmare to debug
when it isn't — the call succeeds with the wrong `_Self`/`_Class` and
nothing complains.

Policy — refactor as we go:
- Every file we touch for other work gets scanned for unlocalized
  variables that could inherit unexpected values. Sanitize on sight.
- Every internal call in `boop` should be explicit about setting
  `_Self`/`_Class`, or explicitly occluding them (clearing to empty),
  unless we intentionally want inheritance (as in baked wrappers).
- Priority: `boop` itself, then class files in order of complexity.

Source: `boop` dispatch/bake section, all class files.

---

## Configurable Baked-Wrapper Typecast Behavior ✓ DONE

Tier 3 (unrelated class leakage) now emits a `_Warn` diagnostic
instead of silently ignoring. Tier 2 (legitimate typecast) fixed to
use `__boop.isa` directly, correctly handling upcasts (e.g.,
`_Class=Box` on a Cube). Users control visibility via `_LogLevel`.

Source: `boop` dispatch/bake section.

---

## Framework-Wide LOGLEVEL System ✓ DONE

Implemented in `boop` as framework infrastructure. Six numeric levels:
`silent(0)`, `error(1)`, `warn(2)`, `info(3)`, `debug(4)`, `trace(5)`.
Global default is `warn`. Per-class overrides inherited via the class
chain with cached resolution (one hash lookup + integer compare on the
hot path). Fallback log file at `${TMPDIR:-/tmp}/boop_${PID}.log` when
stderr is unavailable.

Public API: `_Error`, `_Warn`, `_Info`, `_Debug`, `_Trace`, `_Crash`,
`_LogLevel`. 51 tests in `test_logging_ts`.

---

## Fatality Threshold ("use strict" for boop)

The logging system has a visibility threshold — what gets printed. A
second threshold would control what becomes fatal: the "fatality level."

If fatality is set to `warn`, any `_Warn` call prints AND crashes.
Set to `error` and only `_Error` kills. Set to `silent` and nothing
is auto-fatal (`_Crash` remains explicitly fatal regardless).

This is the `use strict` / `set -e` equivalent for boop. The framework
author writes `_Warn "leakage detected"` because it's recoverable from
the framework's perspective. But a user debugging a subtle dispatch bug
sets fatality to `warn` and the process stops right at the point of
leakage instead of silently continuing.

Implementation: a second per-class + global threshold
(`__boop_fatalLevel`), checked in `__boop.log` after the
visibility check. If the message level is at or below the fatality
threshold, log it and then crash. Clean extension of the existing
system.

Source: `boop` logging section.

---

## Argument-Parsing Object

A reusable class for parsing `key=value`, positional, and flag
arguments in constructors and methods. Would replace the ad-hoc
`for/case` loops in every `.new()` method.

Sketch:
```bash
into=args ArgParser "suit= rank= faceUp=0" "$@"
$args.get suit   # → "♠"
$args.get faceUp # → "0" (default)
```

Needs to handle: required vs optional, defaults, type validation,
positional fallback, unknown-key rejection.

---

## Class File Execution Guard & Help System

Class files like `Box`, `List`, etc. are meant to be sourced, not
executed directly. Currently running `bash Box` silently succeeds and
does nothing — confusing for users.

### Execution Guard

`__boop.registerClass` could detect when the class file is being
executed directly (`BASH_SOURCE` == `$0`) and respond appropriately:

- If the class has a flag indicating it's NOT meant to be executed
  directly (the common case), print a usage message and exit:
  `"Box is a class file. Source it with: . boop Box"`

- If the class IS meant to be executable (like `blackjack`), skip the
  guard and let the script continue to its main logic.

Flag could be a class property (`executable=false`) or a parameter to
`registerClass`.

### Help System

Classes should support a standard help interface. Running a class file
directly (or calling `ClassName --help` or `ClassName.help`) should
print a synopsis:

```
Box — 3D rectangular container

Properties:
  length, width, height — dimensions (integers)
  unit — measurement unit (optional)
  color — display color (optional)

Methods:
  volume  — returns length × width × height
  area    — returns 2D area of given dimensions
  top     — returns area of top face
  ...

Usage:
  . boop Box
  into=b Box length=5 width=3 height=7
  $b.volume  # → 105
```

This could be:
- Auto-generated from the class descriptor (methods, properties)
- Enhanced with a `description` property and per-method docstrings
- Stored in a `__boop_help` registry or inline in the descriptor

---

## Binary-Safe Encode/Decode Output Mode

`__boop.bdecode` currently returns decoded data via the standard
return mechanism, but bash variables silently drop null bytes. For true
binary-safe round-trip, need `output=file` support that writes decoded
data directly to a file without passing through a variable.

Source: `boop` bencode/bdecode section.

---

## Stderr Redirection Audit

Several places in the codebase use `2>/dev/null` to suppress errors.
Each should be reviewed:

- **Class file load guards** (`&& return 2>/dev/null`): Currently
  suppresses "return outside function" error. Should be replaced with
  `BASH_SOURCE` vs `$0` check to only return when sourced. See
  "Class File Execution Guard" above.

- **TestSuite assert_ok/assert_fail**: Suppresses stderr from the
  command being tested. This hides real errors — should probably let
  stderr through and capture it for the failure message.

- **boop import fallback** (`. "$__import_class" 2>/dev/null`):
  Suppresses "file not found" before the crash message. Borderline —
  crash message is more informative, but original error has path info.

Principle: Only suppress stderr when you know exactly what the error
will be, you're expecting it, and the content has no debugging value.

---

## Inline Class Definitions in Executable Scripts

Currently, class files must be separate files to be both sourceable
(for testing/reuse) and executable (for standalone scripts). The
blackjack example originally defined all classes inline, but this
prevented sourcing just the classes without running the game loop.

Investigate a pattern for defining classes inline in an executable
script while still allowing them to be sourced separately. Options:

- `BASH_SOURCE` vs `$0` guard before the main logic
- A `__boop.main` convention that registerClass can detect
- A flag/property on the class that marks the file as executable

Related: "Class File Execution Guard" section above.

---

## Generalize Card/Deck/Hand Classes

Card, Deck, and Hand currently have blackjack-specific logic (ace
rules, 52-card fill, etc.). These concepts are reusable beyond
blackjack — tarot decks, index cards, any collection of items with
a "hand" metaphor.

Consider splitting into generic base classes and game-specific
subclasses:

- `Card` — generic card with arbitrary properties
- `PlayingCard extends Card` — suit/rank/faceUp, 52-card standard
- `Deck` — generic ordered collection with shuffle/draw
- `PlayingDeck extends Deck` — fills with 52 PlayingCards
- `Hand` — generic scored collection
- `BlackjackHand extends Hand` — ace adjustment, bust/blackjack logic

---

## Signal Handler Class

A class for registering at-exit and on-error callbacks into a managed
stack. Bash's `trap` only allows one handler per signal — this class
would layer a callback stack on top of it, so multiple components can
register cleanup/error behaviors without stomping each other.

Core interface:
- `onExit callback` — push a function onto the EXIT handler stack
- `onError callback` — push a function onto the ERR handler stack
- `remove callback` — pull a specific callback off the stack
- Stack executes LIFO on signal (last registered runs first)

Natural consumer of the Stack class (Phase 2). Could also support
arbitrary signals beyond EXIT/ERR if the design generalizes cleanly.

---

## Stack Class (Phase 2)

Classic LIFO collection. Constrain List: expose `push`, `pop`, `peek`,
`isEmpty`. Hide `shift`, `unshift`, `get`-by-index.

Source: PLAN.md Phase 2.

---

## Queue Class (Phase 2)

Classic FIFO collection. Expose `enqueue` (push), `dequeue` (shift),
`peek`, `isEmpty`. Possibly `size`.

Source: PLAN.md Phase 2.

---

## LinkedList Class (Phase 2)

Each node is itself an object (or a Map entry). Requires `insertAt`,
`removeAt`, `next`/`prev` traversal. Decide whether doubly-linked is
worth the complexity at this stage. @@

Source: PLAN.md Phase 2.

---

## Set Class (Phase 2)

Unique unordered collection. Implement on top of Map keys — values are
irrelevant, keys are the members. Expose `add`, `has`, `remove`,
`toArray`, `union`, `intersect`. Arguably simpler than LinkedList.

Source: PLAN.md Phase 2.

---

## String Class (Phase 3)

Heavy string work is happening natively everywhere. A proper wrapper
would clean up downstream code and give callers a consistent interface.

Minimum useful interface: `trim`, `split`, `join`, `contains`,
`startsWith`, `endsWith`, `replace`, `length`, `toUpper`, `toLower`,
`substring`.

All implementable in pure bash parameter expansion — no forks, no
subshells. Fits the no-external-dependencies philosophy.

Source: PLAN.md Phase 3.

---

## BOOP_CLASSPATH (Phase 4)

Colon-delimited environment variable for class file search paths.
Current resolution order: classPath registry → `__boop_dir` → PATH.
Add BOOP_CLASSPATH between classPath registry and `__boop_dir`.
Enables separate-repo class libraries without hand-registration.

Source: PLAN.md Phase 4.

---

## Version Declaration (Phase 4)

```bash
declare -gr __boop_version="0.1.0"
```

No enforcement needed yet. Lets downstream scripts check compatibility.
Semantic versioning from the start.

Source: PLAN.md Phase 4.

---

## I/O Classes (Phase 5 — Deferred)

Potential I/O class layer. `read` has real limitations for
high-record-count streams. No use-case pressure yet — revisit when
something concrete drives the need. @@

Source: PLAN.md Phase 5.

---

## Return System Filesystem Mode

`__boop.returnPath` — use call stack introspection to determine a
filesystem-backed return path. Would allow returning data via temp files
instead of variables, useful for large payloads.

Source: PLAN.md Running Notes.

---

## Housekeeping ✓ DONE

- Stale log files removed (`math_out.log`, `pi_growth.log`,
  `tc_debug.log`, `bash.exe.stackdump`, `REFACTOR_STATUS.md`)
- `test_matrix` verified — runs correctly, not a TestSuite file
  (benchmark only, intentionally excluded from test count)
- `.gitignore` already covers `*.log` and `*.stackdump`

---

## Test Coverage Audit

Every declared method in every class should have test coverage:

- Valid usage (expected inputs produce expected outputs)
- Expected failures (bad inputs crash with clear messages)
- Unexpected/garbage inputs (fails gracefully, not dramatically)

Classes with the most surface area to audit:
- Container (23 methods), Math (26 methods + static wrappers),
  List (15 methods), Map (12 methods), Iterator (8 methods)
- Card/Deck/Hand — `test_blackjack` exists but coverage is unknown
- boop root methods — `setOn` coverage unclear

Also: CLI-level testing for Tier 3 public methods. These need
creative adversarial input from a human who enjoys breaking things.

---

## Input Validation on Math Public API

`Math.add`, `Math.subtract`, etc. accept garbage strings without
complaint — the error surfaces deep in `__Math.toInt64` as a cryptic
`10#` bash arithmetic error. The validation belongs in
`__Math.resolve`, which is the single chokepoint for all numeric
input. After parsing, check that digits are actually all digits;
crash with a helpful message if not.

Also consider: variadic behavior (`Math.add 1 2 3 4` sums all),
single-argument identity (`Math.add 5` returns 5).

---

## Return System: Default to stdout + Newline Control

Change `auto` mode so main shell defaults to stdout (with newline)
instead of the `__boop_RETURN` side-channel. Add a global
`__boop_returnNewline` flag (default on) controlling whether
stdout output includes a trailing newline.

Existing code that relies on the implicit global (e.g.,
`test_stress_ts`) should be updated to use explicit
`into=__boop_RETURN` — code should say where to put values.

`into=` always wins regardless of mode. The mode only matters when
no explicit target is given.

---

## Try/Catch Mechanism

Bash has no native try/catch. The framework currently uses
`_Crash` (which calls `exit`) for all fatal errors,
and `assert_fail` wraps commands in subshells to isolate crashes.

A try/catch pattern would let user code attempt operations that
might crash and handle the failure without dying. Options:

- Subshell-based: `try` runs in a subshell, captures exit code
  and stderr, `catch` block runs on failure. Simple but forks.
- Trap-based: `ERR` trap with a recovery mechanism. Complex,
  interacts badly with `set -e`, fragile across bash versions.
- Flag-based: set a "don't crash, set error flag" mode on
  `_Crash`, let callers check the flag. Lightweight
  but changes crash semantics globally.

Related: Signal Handler Class (already in TODO), Fatality Threshold.
