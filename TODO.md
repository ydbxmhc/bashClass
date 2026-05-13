# boop Framework -- TODO

Active work items. Completed items live in DEVLOG.md.
Inline TODOs in source files should reference entries here by section name.

---

## ★ Meta-Components -- Phase 2

Phase 1 (SemVer, boop version guard, class version token, `_Require`
version checking) is done -- see DEVLOG.

| Component | What it enables | Fallback without it |
|-----------|----------------|---------------------|
| **ArgParser** | key=value, positional, flag parsing for constructors and methods | Warn, ignore args / use current ad-hoc loops |
| **Help** | `--help` on classes, auto-generated from descriptors | Warn, no help output |

- **Argument-Parsing Object** -- becomes the ArgParser meta-component
- **Class File Execution Guard & Help System** -- becomes the Help
  meta-component
- **Inline Arguments on Class Load** -- enabled by ArgParser

---

## `::` Syntax -- Future Uses

Mixins done (see DEVLOG). Remaining:

### Lazy Sub-Modules

`Math::Trig` loads trig functions only when first touched. Doesn't inherit
from Math -- extends its surface area on demand. Could hook into the existing
lazy stub/bake mechanism. No implementation yet.

### Multiple Inheritance Disambiguation

`B::A.method` to resolve through a specific lineage when two parents
provide the same method. The mixin `::` syntax already handles the
common case (method-only composition); true MI with stateful parents
is deferred and may never be needed.

---

## Class Variant Conventions (`::Simple` and `::Fast`)

Two naming conventions for class variants with specific optimization
axes. Not mandatory -- not every class has, needs, or will ever need
one of these. The convention exists so a reader seeing `Foo`, `Foo::Simple`,
or `Foo::Fast` in the tree immediately understands what they're looking
at without having to read the file for a first clue.

### `Class::Simple`

A minimal-dependency variant for use *inside* the dependency graph of
core classes. Typically a subset of the full API, no dependencies on
other framework classes beyond the root `boop`, and focused on the one
or two operations that matter for the intended caller. Examples that
may want one:

- `Collection::Map::Simple` -- plain key-value hash with set/get/has/keys,
  no ordering, no delimiters, no Iterator.
- `Config::Simple` -- flat `key=value` parser with `#` comments and
  blank-line skipping. No INI sections, no object wrapper, no round-trip.
  Target consumers: Args types registry, `__boop.parseConfig`, anywhere
  else the framework needs to read a config file without pulling in
  Config's full surface area.

### `Class::Fast`

An optimized-hot-path variant. Already demonstrated by `Collection::Map::Fast`
(flat compound-key store, O(1) get/set, no insertion ordering). The
conventional signal is "this sacrifices features for speed."

### What the convention is NOT

- Not a mandate. Most classes will have neither variant.
- Not a symmetry requirement. A class can have `::Simple` without
  `::Fast`, or vice versa.
- Not the same as inheritance. The variants don't share an inheritance
  chain -- each implements what it needs directly.

### Caveats

- **Auto-short-alias**: `Simple` and `Fast` are too generic to auto-alias.
- **Documentation**: each variant documents its own interface.
- **Refactoring momentum**: expect churn as new classes arrive and old
  ones get carved into Simple / Fast / Full forms.

---

## Args -- Pending Items

Core done. Implementation at `Args/Args`. 71 tests in
`tests/unit/test_args_ts`. Docs at `docs/Args.md`.

### Pending
- Schema validation warnings for common mistakes (typos, duplicate
  option names, missing `=` on value-taking options)
- **Value validators in the schema** (`Args.types` registry):
  - Named types: `: size = int+` / `: host = fqdn` / `: port = port`
  - Inline regex: `: name = ~ ^[a-z][a-z0-9]*$`
  - Pluggable registry -- internal associative array seeded at class load
    with common types (int, int+, int0+, float, identifier, word, path,
    ipv4, fqdn, email, port, bool). Public API: `Args.types.add NAME PATTERN`,
    `.get`, `.has`, `.list`, `.remove`.
  - Unknown named type crashes at schema parse (typo safety).
  - Validation runs between phase 3 (parsing) and phase 4 (required check).
  - Error shape: `Args.parse: 'size' = 'abc' does not match int+ (^[1-9][0-9]*$)`.
  - Empty values skip validation (absence is valid for non-required fields).
  - Eventual refactor: once `Config::Simple` exists, use it as the
    types-registry backing store so the registry can be loaded from a
    config file.

---

## Class File Execution Guard & Help System

Classes should support a standard help interface. Running a class file
directly (or calling `ClassName --help` or `ClassName.help`) should
print a synopsis auto-generated from the class descriptor (methods,
properties), enhanced with a `description` property and per-method
docstrings.

`boop.init` already handles the load guard and direct-execution
detection. The remaining work is the help-text generation and the
`--help` flag recognition.

---

## Class-File Documentation Pass

Started with Box and Cube. Remaining class files need the same
treatment: file-level overview (what, inheritance, usage example),
per-method comment blocks (purpose, args, return, non-obvious
behavior), clear voice throughout.

Files remaining:
- Collection/Container/Container
- Collection/List/List
- Collection/Map/Map
- Collection/Map/Fast/Fast
- Collection/Stack/Stack
- Collection/Queue/Queue
- Collection/Set/Set
- Config/Config
- Data/JSON/JSON
- Math/Math
- Games/Card/Card
- Games/Deck/Deck
- Games/PlayingCard/PlayingCard
- Testing/TestSuite/TestSuite
- Args/Args
- Signal/Signal (already well-commented)
- Text/String/String (already well-commented)
- DateTime/DateTime (already well-commented)
- SemVer/SemVer
- Mixins/* (Greetable, Taggable, Terminal, Serializable)

---

## JSON -- Pending Items

Core done. Implementation at `Data/JSON/JSON`. 67 tests in
`tests/unit/test_json_ts`. Docs at `docs/JSON.md`.

### Pending
- **`JSON.parseDeep`** -- inflate flat store into real nested Map/List
  objects. Design work needed for type inference (numeric string vs
  array index). Medium-sized.

---

## YAML / XML Parsers (Future)

YAML: indentation-sensitive, harder than JSON. Consider a subset
parser (flat key-value, simple lists) before attempting full spec.

XML: attributes + content + nesting. Significantly more complex.
May not be worth pure-bash implementation.

Both deferred until JSON is proven and Map::Fast is stable.

---

## Phase 2 Collections

Stack, Queue, Set done -- see DEVLOG.

### LinkedList (deferred)

Each node would be a full boop object. In practice: O(n) traversal to
any insertion point, heavy per-element overhead. Revisit if a concrete
use case emerges that List can't serve.

---

## I/O Classes (Phase 5)

All implementable in pure bash using persistent file descriptors --
no forks, no subshells, no external tools.

### File
Wraps a persistent file descriptor opened with `exec {fd}<>file`.
Interface: `open`, `close`, `read`, `readLine`, `readAll`, `write`,
`seek`, `tell`, `eof`.

### Buffer
Accumulates writes in a string variable, flushes on demand or at
a size threshold.

### Pipe
Bidirectional in-memory channel using bash's `exec {rfd}<> <(...)` or
a named FIFO. Needs design work.

### Read utilities
`mapfile`/`readarray` for bulk line-array reads. `read -t 0` for
non-blocking poll. `read -N n` for exact byte counts. Wrap as static
methods on an `IO` namespace class.

---

## Return System Filesystem Mode

`boop.passPath` -- use call stack introspection to determine a
filesystem-backed return path. Would allow returning data via temp files
instead of variables, useful for large payloads.

Consider: `_File` as a Tier 2 inherited var on `boop.pass` for explicit
file output. Don't overthink it.

---

## Implicit Object Declaration on Return (`_AS=`)

Explore whether `boop.pass` could auto-wrap a return value as an
object of a specified class. Might not be worth the complexity.

---

## Try/Catch Mechanism -- Low Priority

Bash has no native try/catch. Every approach has serious tradeoffs.
Revisit if a compelling use case emerges.

---

## Extensive Logging Hooks -- Remaining Areas

Class method implementations now have `_Info`/`_Debug`/`_Trace`
hooks (see DEVLOG). Remaining areas lack coverage:

- `__boop.import` -- log every resolution step at `_Debug`/`_Trace`
- `__boop.loader` -- log each rc/cfg file sourced or skipped at `_Info`
- `boop.classPath` -- log set/remove/rebuild at `_Info`
- Object lifecycle -- creation/destruction at `_Debug`
- Method dispatch -- MRO cache misses at `_Debug`, every dispatch at `_Trace`
- Property access -- `__boop.get`/`__boop.set` at `_Trace`
- `boop.pass` -- mode selection at `_Trace`

### Log-Level Bypass via Function Replacement

When `_LogLevel` is high, silenced functions still pay invocation
cost. Replace with no-op bodies at level-change time. Restore real
implementations when level rises.

---

## Per-Class Work

### boop (root class)
- `setOn` coverage: method exists, test coverage unclear
- `boop_install` bootstrap script (see Namespace design in DEVLOG)
- Scaffolding (`boop new MyClass`): generate class file skeleton

### Math
- Output format modes (scientific, engineering, fixed decimal)
- `Math::Trig` submodule (sin, cos, tan, etc.)
- `Math::Stats` submodule (mean, median, stddev, etc.)

### Collection (Container, List, Map, Iterator)
- Iterator stability after mutation: document or enforce
- Container test coverage audit (23 methods)
- List: `insertAt`/`removeAt` for LinkedList compatibility
- Map: verify insertion-order guarantee is correctly handled
- **Defensive array access policy**: design pass needed to pick a
  consistent policy across all collection classes. See DEVLOG for
  the discussion context.

### Games (Card, PlayingCard, Deck, Blackjack)
- `test_blackjack` coverage audit
- Remaining blackjack polish:
  - GameState class using Serializable (save/resume mid-game)
  - Config for settings (starting bankroll, deck count, etc.)
  - Args in `BlackjackHand.new` constructor
- **Partial redraw** (UI optimization): `draw_table` currently clears
  and rebuilds the whole screen on every state change. Better shape:
  `Terminal.moveTo row col` + layout constants for each region.
- **Flash/flicker**: every screen refresh repaints all UI chrome.
  Goal: only the cells that actually changed.
- **Streamlined betting**: the current bet flow is a plain `read`
  prompt on a bare line. Needs a design pass for something more
  integrated.

### Geometry (Box, Cube)
- 91 tests passing, no known gaps.

---

## Test Coverage Audit

Every declared method in every class should have test coverage:
- Valid usage (expected inputs -> expected outputs)
- Expected failures (bad inputs -> clear crash messages)
- Unexpected/garbage inputs (fails gracefully)

Priority: Container (23 methods), Math (26 methods), List (15),
Map (12), Iterator (8).

---

## Documentation Sync Pass

Several docs are out of date with current conventions:

- **`docs/STANDARDS.md`** -- says `local -I _Self _Class` is required.
  Wrong; update to describe the current `local _Self="${_Self:-}"` pattern.
- **`docs/Container.md`** -- `MyStack.new()` example uses `local -I _Class`.
- **`docs/comparison.md`** -- references `local -I` as dispatch overhead.
- **`docs/PLAN.md`** -- mentions `local -I` as a bash 5 feature.
- **`docs/bash_style.md`** -- TODO asks to document `local -I`; resolve
  by documenting *why the framework doesn't use it* instead.
- Add "why we don't use local -I" section to STANDARDS.md.

---

## README Accuracy Audit

Remaining points:

1. "objects with encapsulated state" -> state is convention-private, not mechanism-private
2. Helper documentation (`_Super`, `_Cast`, `_Delegate`, `_Bless`) needs examples
3. "No subshells in the hot path" -> JSON stringify no longer uses `sort -n` (fixed)
4. "Properties are typed as strings" -> meaningless in bash, rewrite
5. Every non-obvious claim needs a reference to docs/
6. Needs "why we don't use local -I" section in STANDARDS.md

