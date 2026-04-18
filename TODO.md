# boop Framework — TODO

Collected future work items. Inline TODOs in source files should
reference entries here by section name.

---

## ★ Namespace, ClassPath, Index, and Configuration System

**Priority item.** The framework needs a complete class organization
and resolution system: namespaced directory layout, a short-name
index, a multi-root classPath with per-root resolution, persistent
configuration via rc/cfg files, and a public API for managing it all.

### Current State

Everything is flat files in one directory. `__boop_classPath` is an
empty associative array that nothing populates. Import resolution is
trivial: check the hash, check `__boop_dir`, fall through to `PATH`.
No namespaces, no index, no configuration persistence.

### Prior Art (Cross-Language Survey)

| Language | Directory model | Env var | Key insight |
|----------|----------------|---------|-------------|
| Java | Package hierarchy: `com/example/geometry/Box.java` | `CLASSPATH` | Dirs = domain namespaces, never inheritance |
| Python | Package dirs with `__init__.py`: `geometry/box.py` | `PYTHONPATH` | Dirs = functional areas |
| Perl | `::` maps to dirs: `Geometry/Box.pm` = `Geometry::Box` | `PERL5LIB` | `@INC` searched per-root, depth-first |
| Ruby | Flat under `lib/`, namespace subdirs: `my_gem/widget.rb` | `RUBYLIB` | One class per file, module = folder |
| Lua | Template paths with `?`: `./?.lua` | `LUA_PATH` | String-based, no directory convention |

**Universal rule:** directories represent functional domains or
namespaces, never inheritance hierarchies. `Cube extends Box` —
they're siblings in the same namespace, not parent/child folders.

### Namespace Directory Convention

Follow the Perl model: `::` maps to directory separators. Every
class lives inside its namespace folder. The class file shares the
name of its innermost directory.

```
lib/
  Collection/
    Container/
      Container         # ← Collection::Container class
    List/
      List              # ← Collection::List class
    Map/
      Map               # ← Collection::Map class
    Set/
      Set               # ← Collection::Set (future)
  Math/
    Math                # ← Math class (namespace = class)
    Trig/
      Trig              # ← Math::Trig class
    Stats/
      Stats             # ← Math::Stats class
  Cards/
    Card/
      Card              # ← Cards::Card class
    Deck/
      Deck              # ← Cards::Deck class
    Hand/
      Hand              # ← Cards::Hand class
  IO/
    ...                 # ← future
```

**Rule:** when a namespace folder has a class with the same name
(e.g., `Math`), the class file lives *inside* the folder as
`Math/Math` — not outside it. The user still says `. boop Math`,
not `. boop Math::Math`. The import system handles this (see
resolution below).

### Short-Name Index — `.boopIndex`

A persisted file at each library root containing a `__boop_Index`
associative array mapping short class names to their full namespace
paths.

```bash
# .boopIndex — auto-generated, do not edit unless resolving conflicts
declare -gA __boop_Index=(
  [Container]="Collection::Container"
  [List]="Collection::List"
  [Map]="Collection::Map"
  [Math]="Math"
  [Trig]="Math::Trig"
  [Card]="Cards::Card"
  [Deck]="Cards::Deck"
  [Hand]="Cards::Hand"
)
```

**Auto-generation:** whenever a class is registered (via
`registerClass` or equivalent), the index is rebuilt. This can be
suppressed via configuration if the user wants manual control.

**Conflict handling:** if two namespaces both define a class with
the same short name (e.g., `Util` exists in both `IO::Util` and
`Math::Util`), that short name is *removed* from the index. Both
classes remain accessible by full namespace name. The conflict can
be explicitly resolved by manually adding the preferred mapping
back to `.boopIndex`.

**The index is a declaration, not a cache.** Filesystem fallback
hits do NOT auto-update the index. Only deliberate registration
events modify it. A successful fallback should emit `_Info`:
"List resolved via filesystem fallback — consider registering it."

### Multi-Root Resolution — Depth-First Per Root

`BOOP_CLASSPATH` is a colon-delimited list of library roots. Each
root is a complete boop library with its own `.boopIndex`, its own
namespace tree, its own `.booprc`/`.boop.cfg`. Resolution is
**depth-first by default** — exhaust all resolution strategies
within one root before moving to the next.

**Root list construction** (in order):
1. `__boop_dir` — where `boop` itself lives (always first)
2. `BOOP_CLASSPATH` entries — left to right

**Per-root resolution** (for each root, in order):
1. `__boop_classPath["ClassName"]` — explicit per-class override
   (nuclear option, always wins within this root)
2. `.boopIndex` lookup — short name → full namespace → filesystem
   path via namespace convention (`Collection::List` → 
   `root/Collection/List/List`)
3. `Name/Name` — filesystem convention fallback (directory + 
   same-named file inside it)
4. `Name` — bare file fallback (legacy/flat layout)

**Cross-root behavior:**
```
for each root in [__boop_dir, BOOP_CLASSPATH...]:
  try per-root resolution (steps 1–4)
  found? → stop, use it
  not found? → next root

all roots exhausted → PATH fallback (bash native source)
still not found → _Crash
```

This enables **version layering**: `BOOP_CLASSPATH="/opt/boop/v2:
/opt/boop/v1"` means v2 is checked first. If v2 has `Math` but
not `Math::Stats`, v1's `Math::Stats` fills the gap. Multiple
complete installs at different versions, searched in priority order.

**Customizable search strategy:** depth-first (exhaust one root
before trying the next) is the default. The search strategy is
configurable for future needs (e.g., breadth-first: check all
indexes first across all roots, then all filesystem conventions,
etc.). Default is depth-first because it gives the most predictable
"this root wins" behavior.

### Two-File Convention — `.booprc` + `.boop.cfg`

Separation of concerns: human-editable config vs machine-managed
structured data.

**`.booprc`** — user-editable bash script (like `.bashrc`). Can
contain arbitrary bash: log level overrides, custom hooks, env
setup, whatever the user wants. Its job is to source `.boop.cfg`
and add any hand-written customizations on top.

**`.boop.cfg`** — machine-managed, never hand-edited. Contains
structured declarations serialized by `boop.classPath` and future
config methods. Pure data — hash assignments, array entries, no
procedural logic. Always a complete serialization of current state,
not an append log. Rewritten in full on every mutation.

Three tiers, sourced in order of increasing precedence (later
values override earlier ones):

1. `/etc/booprc` (+ `/etc/boop.cfg`) — system-wide defaults
2. `~/.booprc` (+ `~/.boop.cfg`) — user-global preferences
3. `./.booprc` (+ `./.boop.cfg`) — project-local overrides

Files that don't exist are silently skipped. Same precedence model
as `.gitconfig` (system → global → local).

A typical `~/.booprc`:
```bash
# Source machine-managed config (classPath registrations, etc.)
[[ -f ~/.boop.cfg ]] && . ~/.boop.cfg

# User customizations
_LogLevel debug Math    # verbose logging for Math during dev
_OutMode stdout         # prefer stdout for CLI scripts
```

A typical `~/.boop.cfg` (written by `boop.classPath`, not by hand):
```bash
# Auto-generated by boop.classPath — do not edit manually
__boop_classPath["MyUtils"]="/home/user/lib/MyUtils"
__boop_classPath["GameEngine"]="/opt/boop-libs/GameEngine"
```

### `__boop.loader` — RC Discovery and Sourcing

Internal method responsible for the rc file bootstrap sequence.
Called once during `boop` initialization, after globals are declared
but before import arguments are processed.

Responsibilities:
- Source `/etc/booprc`, `~/.booprc`, `./.booprc` in order
- Each rc file is responsible for sourcing its own `.boop.cfg`
- Skip missing files silently
- Errors in rc files crash with a clear message pointing at the
  offending file and line
- Parse `BOOP_CLASSPATH` env var — split on colons, validate
  directories exist, build the root list
- Source `.boopIndex` from each root in the root list
- Emit `_Info` diagnostics for each file sourced

Open question: should `.booprc` files be allowed to import classes
(`. boop SomeClass`)? Probably yes — a project rc might want to
pre-register and pre-load utility classes. Circular risk is low
(rc files aren't class files) but worth noting.

### `boop.classPath` — Public API and Configuration Serializer

Tier 3 public method. Two roles: runtime manipulation of the class
path registry, and serialization of state back to `.boop.cfg`.

Subcommand pattern:

```bash
boop.classPath set  ClassName /path/to/file  # register + persist
boop.classPath get  ClassName                # query → path or empty
boop.classPath list                          # dump all registrations
boop.classPath remove ClassName              # unregister + rewrite
boop.classPath has  ClassName                # test → exit code 0/1
boop.classPath dirs                          # list roots in order
boop.classPath rebuild                       # regenerate .boopIndex
```

**Serialization behavior** (`set`, `remove`, `rebuild`):
- Updates the live `__boop_classPath` hash immediately
- Rewrites `~/.boop.cfg` (default) as a complete serialization
- Target cfg file overridable: `_CfgFile=./.boop.cfg` for
  project-local persistence
- `rebuild` scans the namespace tree and regenerates `.boopIndex`,
  detecting and removing conflicting short names

**Validation on `set`**:
- Class name must pass `__boop.validate` (identifier rules)
- Path must exist and be a readable file (`[[ -f && -r ]]`)
- Overwriting an existing registration emits `_Info`, not an error

Returns via `boop.pass` so `into=` works naturally.

### Namespace-to-Filesystem Mapping

The `::` separator maps to `/` on disk. The class file shares the
name of its innermost namespace segment and lives inside a directory
of the same name.

| User says | Namespace | Filesystem path |
|-----------|-----------|----------------|
| `Math` | `Math` | `root/Math/Math` |
| `Math::Trig` | `Math::Trig` | `root/Math/Trig/Trig` |
| `List` | `Collection::List` | `root/Collection/List/List` (via index) |
| `Collection::List` | `Collection::List` | `root/Collection/List/List` (direct) |

**Import resolution for a bare name like `List`:**
1. Check `__boop_classPath["List"]` — explicit override
2. Check `__boop_Index["List"]` — finds `Collection::List` →
   resolve to `root/Collection/List/List`
3. Check `root/List/List` — filesystem convention
4. Check `root/List` — bare file fallback
5. Next root (repeat 1–4)
6. `PATH` fallback
7. `_Crash`

### Implementation Notes

- `__boop.loader` runs inside the `(( ! __boop_loaded ))` guard —
  fires once per process
- RC files are sourced (not executed) — they share the shell context
- Public API methods registered via `__boop.registerMethod` on the
  root `boop` class
- `boop.classPath set` does NOT trigger an immediate import —
  registration and loading are separate concerns
- The `::` separator is already reserved in the TODO for mixins/
  classlets/multiple-inheritance. Namespace usage here is compatible:
  `::` in import context means namespace, `::` in dispatch context
  means mixin provenance. No collision — they operate in different
  phases (load time vs call time).
- `.boopIndex` should be `.gitignore`-able for projects that prefer
  explicit full-namespace imports only

### Canonical Directory Layout

The repo *is* the library — no `lib/` wrapper. The install target
is a single directory containing `boop` and all namespace folders.
Tests and docs live alongside but are not part of the runtime
library.

```
<install_root>/                # e.g., /usr/local/lib/boop/
  boop                         # framework entry point
  .boopIndex                   # auto-generated short-name index
  .booprc                      # optional project-level rc
  .boop.cfg                    # optional project-level cfg
  Collection/
    Container/
      Container                # Collection::Container
    List/
      List                     # Collection::List
    Map/
      Map                      # Collection::Map
    Iterator/
      Iterator                 # Collection::Iterator
  Geometry/
    Box/
      Box                      # Geometry::Box
    Cube/
      Cube                     # Geometry::Cube
  Math/
    Math                       # Math (namespace = class)
  Games/
    Card/
      Card                     # Games::Card
    PlayingCard/
      PlayingCard              # Games::PlayingCard
    Deck/
      Deck                     # Games::Deck
    Blackjack/
      Blackjack                # Games::Blackjack (executable)
      BlackjackHand/
        BlackjackHand          # Games::Blackjack::BlackjackHand
  Testing/
    TestSuite/
      TestSuite                # Testing::TestSuite
  bin/                         # internal utilities (not library classes)
    test_all
    test_blackjack
    test_box_cube_ts
    test_containers_ts
    test_logging_ts
    test_math_ts
    test_matrix
    test_pi_growth
    test_smoke
    test_stress_ts
    test_testsuite_ts
    boop_install               # bootstrap installer
  docs/                        # not part of the library
    ...
```

### `boop_install` — Bootstrap Script

A standalone install script that sets up boop on a fresh system.

Responsibilities:
- Copy (or symlink) the library tree to the install target
  (default: `/usr/local/lib/boop/` or user-specified location)
- Create a symlink in a PATH directory (default:
  `/usr/local/bin/boop` → `<install_root>/boop`) so that
  `. boop` works from anywhere
- Generate the initial `.boopIndex` by scanning the namespace tree
- Create a starter `~/.booprc` if one doesn't exist (with the
  `.boop.cfg` source line and commented-out examples)
- Verify bash version (5.0+ required)
- Detect existing installations and offer upgrade/overwrite
- Support `--prefix`, `--symlink`, `--no-rc` flags for
  customization
- Emit clear success/failure messages

The symlink is the bootstrap: it puts `boop` on PATH, and `boop`
resolves `__boop_dir` via `realpath` on `BASH_SOURCE[0]`, which
follows the symlink back to the real install root. From there,
everything else is discoverable.

Uninstall: remove the symlink and the install directory. The rc
files in `~/` and `/etc/` are left alone (user data).

Source: `boop` (import section, initialization), all class files.

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
this. A full compliance sweep was completed across all source files:
`boop`, `Container`, `List`, `Map`, `Math`, `TestSuite`, `Box`, `Cube`,
`Card`, `Deck`, `Hand`, and `blackjack`. The naming convention is now
enforced automatically by `test_all` — any non-compliant prefix
(`__lowercase_`) that isn't a known class or framework name fails the
build.

During the sweep, a latent bug was found and fixed in `__boop.log`:
`local -i` on the threshold variable coerced empty string to `0`,
defeating the `[[ -z ]]` sentinel that triggers fallback to the global
log level. The fix was removing the `-i` flag.

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

## BOOP_CLASSPATH (Phase 4) — ✓ Subsumed

Now part of the ★ priority item: "Namespace, ClassPath, Index, and
Configuration System." `BOOP_CLASSPATH` is the multi-root search
path, with depth-first per-root resolution, `.boopIndex` at each
root, and version layering across roots. See that section for the
full design.

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

`boop.passPath` — use call stack introspection to determine a
filesystem-backed return path. Would allow returning data via temp files
instead of variables, useful for large payloads.

Consider: `_File` as a Tier 2 inherited var on `boop.pass` for explicit
file output. Would unify the filesystem mode with a user-friendly
inline pattern (`_File="/var/log/app.log" _Warn "something"`). Open
questions around precedence (`into=` vs `_File` vs mode), whether it
replaces the current filesystem mode or layers on top, and how much
the framework should manage output streams vs leaving that to the user.
Don't overthink it — users can always manage their own redirects.

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
instead of the `_Out` side-channel. Add a global
`_OutNewline` flag (default on) controlling whether
stdout output includes a trailing newline.

Existing code that relies on the implicit global (e.g.,
`test_stress_ts`) should be updated to use explicit
`into=_Out` — code should say where to put values.

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
