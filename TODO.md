# boop Framework — TODO

Collected future work items. Inline TODOs in source files should
reference entries here by section name.

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

## Configurable Baked-Wrapper Typecast Behavior

When a baked wrapper detects an ambient class that is neither an exact
match nor in the baked class's inheritance chain (e.g., `_Class=Hand`
leaking into a Card method via `local -I`), the current behavior
silently ignores it and uses the baked class (fast path). This is safe
but hides potential user errors.

Desired: a per-class setting (inherited, with a global default) that
controls the response to unrelated-class leakage in baked wrappers:

- `silent` — ignore and use baked class (current behavior)
- `warn` — use baked class but emit a diagnostic to stderr
- `strict` — crash with an informative message

The setting should be resolvable at bake time (not every call) so the
behavior can be hardcoded into the wrapper. Needs a registry walk for
the first class-specific value in the inheritance chain, falling back
to the global default. Something like `__bashClass_typecastMode` or a
class property like `implicitSelfTypecast`.

Source: `boop` dispatch/bake section.

---

## Framework-Wide LOGLEVEL System

A global default log level with per-class overrides (inherited via the
class chain). Would support the typecast warning above and provide a
general diagnostic facility for class authors.

Levels: `silent`, `warn`, `info`, `debug`, `trace`.

Output to stderr with structured prefix (class/method/object ID).
Per-class overrides walk the inheritance chain for the first
class-specific value, falling back to the global default.

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

`__bashClass.registerClass` could detect when the class file is being
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
- Stored in a `__bashClass_help` registry or inline in the descriptor

---

## Binary-Safe Encode/Decode Output Mode

`__bashClass.bdecode` currently returns decoded data via the standard
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
- A `__bashClass.main` convention that registerClass can detect
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
Current resolution order: classPath registry → `__bashClass_dir` → PATH.
Add BOOP_CLASSPATH between classPath registry and `__bashClass_dir`.
Enables separate-repo class libraries without hand-registration.

Source: PLAN.md Phase 4.

---

## Version Declaration (Phase 4)

```bash
declare -gr __bashClass_version="0.1.0"
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

`__bashClass.returnPath` — use call stack introspection to determine a
filesystem-backed return path. Would allow returning data via temp files
instead of variables, useful for large payloads.

Source: PLAN.md Running Notes.

---

## Housekeeping

- Clean up stale log files (`math_out.log`, `pi_growth.log`,
  `tc_debug.log`) @@
- `test_matrix` — not in the test count table; verify it still runs @@
