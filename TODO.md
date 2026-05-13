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

### Design: Two-Layer Delimiter Architecture

`_EOL` and `_Delimiter` are the universal IO-control variables across
the framework. They default to `$'\n'` and `${_EOL}` respectively,
and are set inline on commands that need them changed. Two layers
handle them:

**Layer 1 -- the fast path (current, single-char optimized):**
- Used directly in `printf`, parameter expansion, `read -d`
- Zero overhead beyond what bash already does
- This is what Map.keys, List.toArray, boop.pass, Config.keys, etc.
  use today and will continue to use
- The standard: every method that joins or splits respects these
  variables. Rigorous application throughout the common codebase.
- Single characters are the common case and should stay fast.

**Layer 2 -- the IO class (complex path, multi-char capable):**
- Mixes in Text.String for string-manipulation toolkit
- Internal double-buffer: pre-loads chunks (~8KB) from an FD into a
  bash variable, scans for the delimiter using parameter expansion,
  returns one "record" at a time, refills when exhausted
- Handles multi-character `_EOL` (paragraph mode with `$'\n\n'`,
  CRLF sequences, arbitrary byte patterns)
- Handles multi-character `_Delimiter` (e.g. `$',\r\n'` to split
  on comma-CRLF within a record)
- Exposed as a `Read` method (capital R) on the IO class, possibly
  also as a `_Read` Tier 2 helper for framework-internal use
- The caller sets `_EOL` and `_Delimiter` the same way regardless
  of which layer executes -- the intent is expressed identically

**The hybrid principle:**
- Single-char delimiter + data fits in a variable: fast path (no IO class)
- Multi-char delimiter, streaming data, or paragraph mode: IO class Read
- Same variable names, same caller intent, different execution paths

**Null bytes:**
Bash variables cannot hold `\0` (C string terminator). `read` stops at
null. The only way to handle binary with embedded nulls is byte-by-byte
via `read -N 1` with `LC_ALL=C`, never storing in a variable. This is
possible but painful and slow. Document the limitation clearly; don't
pretend to solve it unless a real use case demands it.

### Stream -- Current Status

**Core complete.** 138 tests passing (`tests/unit/test_stream_ts`).
Benchmarks at `tests/bench/bench_stream` and `tests/bench/bench_blocksize_rigorous`.

Three parse modes, chosen at construction:
- **direct**: single-char EOL, delegates to `read -d` from FD. Full
  `read` compatibility. Pre-built args array, one call per record.
- **regex**: buffered, char-class EOL (`-E`). Regex extracts records.
- **pe**: buffered, exact-string EOL (`-D`) or exact-string field
  delimiter (`-F`). Parameter expansion extracts records/fields.

Field assignment via nameref (no eval, no `read <<<`). Field names
stored as real arrays (`__boop_data_${_Self}_fields`). Object data
stored in `__Stream_data` global associative array with compound keys
for fast access (eliminates `__boop.get` overhead in hot path).

### Stream -- Remaining Work

- ~~**Documentation rewrite**~~ done
- ~~**Add `test_stream_ts` to `tests/test_all`**~~ done
- ~~**Field-name validation**~~ done
- ~~**`-W CHARS` (collapsing field delimiter)**~~ done
- ~~**`_trim`**~~ removed (not needed; use String or parameter expansion post-read)
- ~~**IFS classification in buffered mode**~~ moot (read/Read split eliminates the question)
- ~~**`_Delimiter` semantics**~~ resolved (Stream does not use it; document only)
- **`-R "$regex"` (custom field regex)**: designed, not implemented.
  User-provided regex for field splitting. Escape hatch for complex cases.
- **Multi-FD I/O model**: each Stream object has up to three FDs:
  - `in` -- read source (default: stdin dup)
  - `out` -- write target (default: stdout dup)
  - `err` -- object-level logging/errors (default: stderr dup)
  Each independently configurable via:
  - `--fd-in N` / `--fd-out N` / `--fd-err N` (explicit FDs)
  - `--path-in FILE` / `--path-out FILE` / `--path-err FILE` (open paths)
  - `-u N` defaults to `--fd-in` unless `-m write|append|rw`
  - `-P FILE` defaults to `--path-in` unless `-m write|append`
  - `-m read|write|append|rw` controls open mode for `-P`/`-u` shortcuts
  - `--in=none` / `--out=none` to explicitly close/disable a direction
  Read methods use `in`. Write methods use `out`. Both can coexist.
  If both `in` and `out` point to the same FD (e.g. socket), that's valid.
  Shell redirections on the constructor call persist (existing behavior).
  No sigil parsing (`>>`, `<` etc.) -- that's shell syntax, not ours.
  Design with Stream::Socket in mind (bidirectional on one FD).
  - **Close direction semantics**: use `<&-` to close `in`, `>&-` for `out`/`err`.
    Both operators call `close(fd)` at the syscall level, but direction should
    match the fd's open mode for semantic clarity.
  - **Granular close**: `$s.closeIn` / `$s.closeOut` as separate methods.
    `$s.close` closes all open FDs. Half-close is a real pipe use case:
    write everything, `closeOut` to signal EOF downstream, still read results.
  - **Write-EOF semantics**: `closeOut` IS the write-EOF signal. No separate
    `eof_out` state needed. `eof` property remains read-side only
    ("no more data coming in"). Closing the write fd is the action, not a flag.
  - **FD deduplication on close**: if `fd_in == fd_out` (bidirectional socket),
    closing both directions would double-close the same fd number. Guard needed.
  - **`write()`/`writeLine()` use wrong fd today**: they reference `fd` (the
    read fd). Works now because there is only one fd. Will silently break when
    `fd_in` and `fd_out` are separate. Fix during multi-FD implementation.
  - **Current `eof=1` in `close()` is a stopgap**: conflates "data exhausted"
    with "fd released by caller." Correct fix when multi-FD lands: nil out
    `fd_in` and check for nil in read methods. `eof` should stay read-side
    only and reflect data exhaustion, not caller-initiated close.
- **Non-blocking reads**: for pipes/sockets where blocking is unacceptable.
  Direct mode: `read -t 0` polls. Buffered mode: `read -t $timeout -N`
  on fill, work with partial buffer. Needs a third return state beyond
  0 (success) and 1 (EOF) -- "no complete record yet, try again."
  Options: return code 2, or a `wouldBlock` property, or a dedicated
  `$s.poll` / `$s.tryRead` method. Essential for Stream::Socket.
- **`into=` leak through dynamic scoping**: `into=` from the caller leaks
  into Args.parse. Workaround: explicit `into=__local _Class='' Args.parse`.
  Needs a framework-level solution (TODO: scope isolation for `into=`).

### Stream -- Performance Notes

Benchmarking shows blockSize has negligible impact in the 256-2048 range.
The dominant cost is per-record overhead (method dispatch, hash lookups,
regex/PE operations). The `__Stream_data` optimization (eliminating
`__boop.get` calls) provided 2-3x speedup.

Further optimization opportunities:
- Reduce per-record hash lookups (currently ~5 per buffered Read)
- Pre-build combined record+field regex at construction (one `=~` per Read)
- Consider caching the entire read-args array for buffered mode too
- Profile the nameref field assignment loop vs alternatives

### ★ Garbage Collection / Object Lifecycle

Objects live in `__boop_static` (property values), `__boop_registry`
(schema descriptors), and class-specific stores (`__Stream_data`,
`__boop_data_*` arrays). Currently no mechanism to reclaim storage.

Needs discussion:
- `$obj.destroy` must clean: `__boop_registry`, `__boop_static` keys,
  `__Stream_data` keys matching `${objId}.*`, field arrays, readArgs arrays
- Reference counting vs explicit destroy
- Serialization interaction (do we serialize dead objects?)
- Immediate concern: blackjack hands accumulate without bound

### Two-Layer Delimiter Architecture

The **output side** is complete (`_EOL` + `_Delimiter` respected by all
multi-value methods). The **input side** is now handled by Stream for
the complex cases. Existing code (`Config.load`, `__boop.parseConfig`)
works fine as-is with hardcoded delimiters -- Stream is additive, not
a replacement.

### Fixed-Width Field Parsing (Phase 2 of Stream)

Deferred. Design: `[Format NAME]` sections with `WIDTH:FIELDNAME` tokens.
Constructor builds offset table, Read slices by position. Format-switching
via discriminator field. Separate method from delimited Read.

### Internal descriptor separator (low priority)

Comma reserved in method/property/mixin names. Consider `$'\x1f'` or
pipe as alternative. Same applies to Taggable's comma-separated storage.

### Consistency audit needed
Every method in the framework that joins or splits values should be
verified to respect `_Delimiter` (for multi-value) and `_EOL` (for
output termination) consistently. Current coverage is good but not
audited for completeness.

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
- **`-R "$regex"` field splitting**: designed, not yet implemented.
- **Multi-FD I/O model**: see I/O Classes section above for full design.
- **`into=` scope leak**: `into=` from caller leaks into Args.parse
  inside Stream.new. Workaround exists; needs framework-level fix.

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

