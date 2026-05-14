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
- **CRLF stripping in file-load** (`__Args_applyValue`): `IFS= read -r`
  preserves `\r` on Windows-saved files. Every array element, map key,
  and scalar slurped from a file will have a trailing carriage return.
  Fix: strip `\r` after each `read` in all three file-load paths
  (`array[]<`, `map{}<`, scalar `<`). Pattern: `line="${line%$'\r'}"`.
- **`_Delimiter` fallback inconsistency**: `Args.parse` line ~357 uses
  `${_Delimiter:-$'\n'}` — hardcodes `$'\n'` instead of `$_EOL` as all
  other classes do. Change to `${_Delimiter:-$_EOL}`.
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

### Stream -- Implementation Status

**WIP.** Class exists at `Stream/Stream`, loads, schema parsing works.
Two test failures remain (eof flag, field assignment in multi-char mode).

### Open Design Question: Buffer Strategy

Current implementation has three separate read paths:
1. Fixed-width (`-n N`): `read -N` directly from FD
2. Single-char EOL: `read -d` directly from FD (bypasses buffer)
3. Multi-char EOL: buffer-scan algorithm

**Recommendation:** keep both paths, but make the buffer the *fallback*:
- If single-char EOL AND no buffer content pending: use `read -d` (fast)
- If fixed-width: use `read -N`
- Otherwise: buffer-scan (handles everything including leftover buffer
  from a previous multi-char read)

Key insight: check `_buf` first. If there's buffered content from a
previous read, drain the buffer before falling back to `read -d`. This
gives correctness AND speed for the common case.

### Performance Concerns in Read

1. **Property access overhead:** every Read call does 8 `__boop.get`
   calls (hash lookups + boop.pass). For a hot loop, this is significant.
   Consider caching config in a bash array keyed by stream ID, populated
   once at construction, read directly in Read without the property system.

2. **The `$#` fast-path check:** design says "if no args, straight into
   the fast path." Implementation checks `$#` for field overrides but
   still loads all 8 properties every time. Real optimization: skip
   property loads entirely when nothing changed since last call.

3. **`eval` in field assignment:** `eval "read -r $fields <<< ..."` is
   necessary for dynamic variable names but is a potential injection
   vector. Constructor should validate field names are valid bash
   identifiers before storing them.

4. **`into=` asymmetry:** when fields are configured, Read assigns to
   globals directly (via eval read). When no fields configured, uses
   boop.pass. `into=` only works in no-fields mode. Document clearly.

### Remaining Implementation Work

- Fix eof flag persistence after single-char fast-path EOF
- Fix field assignment in multi-char EOL path (fields stored but not
  reaching the eval-read because the variable isn't populated correctly)
- Add field-name validation in constructor
- Add `test_stream_ts` to `tests/test_all`
- Implement `readOnly:` descriptor token (separate from Stream but
  needed for the property-access model)
- Consider: `inheritValueFor` utility method on root boop class

### Design: Two-Layer Delimiter Architecture

The **output side** is complete. All multi-value methods (List.toArray,
Map.keys, Map.values, Map.toArray, Config.keys, Config.toFlat, etc.)
respect the two IO-control variables with correct semantics:

- `_EOL` = record separator (between entries). Default: `$'\n'`.
  Arrays join elements on `_EOL`. Maps join records on `_EOL`.
- `_Delimiter` = field separator (within a record, e.g. key from value).
  Default: empty (unset). Each method picks its own context-appropriate
  fallback (Map uses `=`, Config uses `=`, a CSV parser would use `,`).

Multi-character values work on the output side (tested with `$'\r\n'`).
Single-character is the fast path; multi-char just works because
`printf -v` and string concatenation don't care about length.

The **input side** is NOT built. Config.load, __boop.parseConfig, and
similar methods still use hardcoded `while IFS= read -r line` (newline
records, `=` field separator). These work for the common case but don't
respect `_EOL`/`_Delimiter` for custom formats.

### What needs building: the IO class

A class (or small family of classes under `IO/`) that handles the
complex input path — multi-character delimiters, streaming reads,
buffered I/O. The output side stays as-is (fast path, already done).

**Core concept: `Read` method with double-buffer scanning.**

```
IO.File.open "/path/to/file" mode=read
# or
into=reader IO.Reader.new fd=$some_fd

# Then:
_EOL=$'\n\n' into=paragraph $reader.Read    # paragraph mode
_EOL=$'\r\n' into=line $reader.Read         # CRLF line mode
_EOL=$'\n'   into=line $reader.Read         # normal line mode (fast path)
```

**Algorithm for multi-char `_EOL` scanning:**

1. Maintain an internal buffer string (pre-loaded ~8KB from the FD
   via `read -N 8192`)
2. On each `Read` call, scan the buffer for `_EOL` using
   `${buffer%%"$eol"*}` (parameter expansion finds the first match)
3. If found: return everything before the match, advance the buffer
   past the match + delimiter length
4. If not found: append more data from the FD to the buffer, retry
5. If FD is exhausted and buffer is non-empty: return the remainder
   (final record without trailing delimiter)
6. If FD is exhausted and buffer is empty: return empty, signal EOF

**Fast-path optimization:** when `_EOL` is a single character, skip
the buffer entirely and use `read -d "$eol"` directly. This is the
common case and costs nothing extra.

**Field splitting within a record:**

After `Read` returns a record, the caller (or a helper) splits on
`_Delimiter` for key/value parsing:
```bash
into=record $reader.Read
key="${record%%"${_Delimiter:-=}"*}"
value="${record#*"${_Delimiter:-=}"}"
```
This splits on the first occurrence of `_Delimiter`, leaving subsequent
occurrences in the value (same semantics as `IFS='=' read -r k v`).

**Text.String mixin integration:**

The IO class mixes in Text.String so that records returned by `Read`
are String objects with trim/split/replace available immediately:
```bash
into=line $reader.Read
$line.trim
into=fields $line.split ","    # hypothetical split method
```

**Relationship to existing code:**

Once the IO class exists, `Config.load` and `__boop.parseConfig` can
optionally delegate to it for the read loop. For the common case
(newline-delimited, `=` field separator) they'd still use the fast
path (`read -r`). The IO class is for when the caller needs something
the fast path can't do.

**Classes in the family:**

- `IO::File` — wraps a persistent FD. open/close/read/readLine/
  readAll/write/seek/tell/eof. The `Read` method lives here.
- `IO::Buffer` — in-memory accumulator. The double-buffer backing
  store for Read. Also useful standalone for building output strings
  efficiently before flushing.
- `IO::Pipe` — bidirectional channel via named FIFO. Deferred until
  File and Buffer are proven.
- `IO::Reader` — possibly a lighter "just the read side" without
  file management. TBD whether this is separate or just File in
  read-only mode.

**Null bytes:**

Bash variables cannot hold `\0`. Document clearly. The IO class
operates on text (everything except null). Binary data with embedded
nulls requires byte-by-byte `read -N 1` with `LC_ALL=C` and is out
of scope for the initial implementation.

### Internal descriptor separator (low priority)

The framework uses comma as the internal separator for method lists,
property lists, and mixin lists in class descriptors (`|methods=a,b,c|`).
This effectively reserves comma as unusable in method/property names.
Worth considering an alternative character (unit separator `$'\x1f'`?
pipe? something else?) at some point. Same applies to Taggable's
comma-separated tag storage.

### Short-term: respect _EOL/_Delimiter in user-facing input (deferred)

Config.load, Config.loadINI, __boop.parseConfig, and __boop.new all
use hardcoded delimiters for user-facing data. The fix is to default
to the current character but read from the variable:

- Record splitting: `while IFS= read -r -d "${_EOL:0:1}" line`
  (note: `read -d` only supports single-char; multi-char _EOL is
  IO class territory)
- Field splitting (key=value): `IFS="${_Delimiter:-=}" read -r k v`
  where the first occurrence of _Delimiter separates key from value

This preserves current behavior while opening the door for callers
who set _Delimiter to `:` or `|`. Deferred until the IO class exists
to handle the multi-char case properly.

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

### Class Properties (static/instance fallback)

**Design decision (settled):** No implicit fallback. Java/C#/Ruby model.

- `$obj.prop` reads the instance's own value from `__boop_static["${objId}.${prop}"]`
- `ClassName.prop` reads the class value from `__boop_static["${className}.${prop}"]`
- These are independent. Setting one doesn't affect the other.
- If a developer wants inherited defaults, they call `$obj.inheritValueFor prop`
  in their constructor — explicit, not magic.

**`inheritValueFor`** — utility method on root `boop`. Walks the chain:
instance → class → parent class → ... → root. Sets the local property
to the first value found. Easy to call in a constructor for opt-in
inheritance.

**Core refactor (in progress):** property values are moving OUT of the
descriptor string and INTO `__boop_static`. The descriptor becomes
schema-only (`|class=X|parent=Y|methods=...|properties=...|`). This
makes get/set a single hash lookup instead of a regex parse, eliminates
encode/decode for values, and cleanly separates "what properties exist"
from "what values they hold."

Changes needed:
- `__boop.new` — write initial values to `__boop_static["${objId}.${prop}"]`
- `__boop.get` — read from `__boop_static["${_Self}.${prop}"]`
- `__boop.set` — write to `__boop_static["${_Self}.${prop}"]`
- `toString` / `inspect` — read values from `__boop_static`
- `encode`/`decode` — may become unnecessary for property values
- Descriptor format — drop `|prop=value|` segments
- Instance accessor in `backfillMethods` — use `__boop.get` (no fallback)

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
- **`Map::Fast` bare `${_Delimiter}`**: three places in `Fast/Fast`
  (`keys`, `keysUnder`, `toString`) use `${_Delimiter}` with no
  fallback — silently empty if `_Delimiter` is unset. Change to
  `${_Delimiter:-$_EOL}` for consistency with all other classes.

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

### Stream
- **`_trim` is a stub**: the `trim` schema key is parsed and stored as
  `_trim` property, but `Stream.Read` never reads or applies it. Need to
  actually strip trailing whitespace (or just `\r`) from each field/record
  when `trim=true`. The CRLF use-case (`--eol $'\r\n'` + trim) is the
  primary motivator.

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

