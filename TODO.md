# boop Framework -- TODO

Active work items. Completed items live in DEVLOG.md.
Design rationale lives in the relevant docs/ files.
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
  meta-component. `boop.init` already handles load guard and direct-
  execution detection. Remaining: help-text generation, `--help` flag.
- **Inline Arguments on Class Load** -- enabled by ArgParser

---

## `::` Syntax -- Future Uses

Mixins done (see DEVLOG). Remaining:

- **Lazy Sub-Modules**: `Math::Trig` loads on first touch. Hooks into
  existing lazy stub/bake mechanism. No implementation yet.
- **MI Disambiguation**: `B::A.method` to resolve through a specific
  lineage. Deferred -- mixin `::` handles the common case.

---

## Args -- Pending Items

Core done. 71 tests. Docs at `docs/Args.md`.

- **CRLF stripping in file-load**: `IFS= read -r` preserves `\r` on
  Windows files. Fix: `line="${line%$'\r'}"` in all three file-load paths.
- **`_Delimiter` fallback inconsistency**: line ~357 hardcodes `$'\n'`
  instead of `$_EOL`. Change to `${_Delimiter:-$_EOL}`.
- **Schema validation warnings**: typos, duplicate option names, missing
  `=` on value-taking options.
- **Value validators** (`Args.types` registry): named types (`int+`,
  `fqdn`, `port`), inline regex, pluggable registry. Validation runs
  between parsing and required-check. See `docs/Args.md` for full design.

---

## I/O Classes (Phase 5)

### Stream -- Remaining Work

- **`-R "$regex"` (custom field regex)**: user-provided regex for field
  splitting. Same contract as built-in regexes (capture group 1 = field,
  full match = advance). Escape hatch for complex delimiter logic.
- **Multi-FD I/O model**: each object gets `in`/`out`/`err` FDs,
  independently configurable. `--fd-in`/`--fd-out`/`--fd-err`,
  `--path-in`/`--path-out`/`--path-err`, `-m read|write|append|rw`.
  Design with Stream::Socket in mind (bidirectional on one FD).
  See `docs/Stream.md` for full design notes.
- **Non-blocking reads**: `read -t 0` poll for direct mode, `read -t N`
  for buffered fill. Third return state needed ("no complete record yet").
  Dedicated `$s.poll` or `$s.tryRead` method. Essential for Socket.
- **Fixed-width field parsing** (Phase 2): `[Format NAME]` sections with
  `WIDTH:FIELDNAME` tokens. Offset tables, format-switching via
  discriminator field. Separate method from delimited Read.
- **`into=` scope leak**: `into=` from caller leaks into Args.parse.
  Workaround in place; needs framework-level scope isolation.

### Stream -- Optimization Opportunities

- Pre-build combined record+field regex (one `=~` per Read)
- Reduce per-record hash lookups in buffered mode
- Profile nameref assignment loop vs alternatives

### ★ Garbage Collection / Object Lifecycle

Objects accumulate in `__boop_static`, `__boop_registry`, and companion
arrays (`__boop_data_*`). No reclaim mechanism exists.

- Explicit `$obj.destroy`: clean registry, static keys, companion arrays,
  wrapper functions (`compgen -A function "${objId}."` + `unset -f`)
- Classes are never GC'd unless explicitly requested
- Immediate concern: blackjack hands accumulate without bound
- Serialization interaction: only serialize live objects

### Delimiter Consistency Audit

Every method that joins or splits values should respect `_Delimiter`
and `_EOL` consistently. Current coverage is good but not audited.
`Map::Fast` has three bare `${_Delimiter}` references with no fallback.

### Internal Descriptor Separator (low priority)

Comma reserved in method/property/mixin names. Consider `$'\x1f'` or
pipe as alternative. Same applies to Taggable's comma-separated storage.

---

## Return System Filesystem Mode

`boop.passPath` -- filesystem-backed return path via call stack
introspection. Useful for large payloads that don't fit comfortably
in variables. Consider `_File` as a Tier 2 inherited var on `boop.pass`.

---

## Implicit Object Declaration on Return (`_AS=`)

Explore whether `boop.pass` could auto-wrap a return value as an
object of a specified class. Might not be worth the complexity.

---

## Try/Catch Mechanism -- Low Priority

Bash has no native try/catch. Every approach has serious tradeoffs.
Revisit if a compelling use case emerges.

---

## Extensive Logging Hooks

Remaining areas lack coverage:
- `__boop.import` -- resolution steps at `_Debug`/`_Trace`
- `__boop.loader` -- rc/cfg files sourced/skipped at `_Info`
- `boop.classPath` -- set/remove/rebuild at `_Info`
- Object lifecycle -- creation/destruction at `_Debug`
- Method dispatch -- MRO cache misses at `_Debug`
- Property access -- `__boop.get`/`__boop.set` at `_Trace`
- `boop.pass` -- mode selection at `_Trace`

Log-level bypass (replacing silenced functions with `:` no-op) is
already implemented. Verify it covers all tiers correctly.

---

## Per-Class Work

### boop (root class)
- `setOn` coverage: method exists, test coverage unclear
- `boop_install` bootstrap script (see Namespace design in DEVLOG)
- Scaffolding (`boop new MyClass`): generate class file skeleton
- `inheritValueFor` utility: walk instance -> class -> parent chain,
  set local property to first value found. Opt-in inheritance.

### Math
- Output format modes (scientific, engineering, fixed decimal)
- `Math::Trig` submodule (sin, cos, tan, etc.)
- `Math::Stats` submodule (mean, median, stddev, etc.)

### Collection (Container, List, Map, Iterator)
- Iterator stability after mutation: document or enforce
- Container test coverage audit (23 methods)
- List: `insertAt`/`removeAt` for LinkedList compatibility
- Map: verify insertion-order guarantee
- Defensive array access policy: consistent across all collections
- `Map::Fast` bare `${_Delimiter}`: add fallback in 3 places

### Games (Card, PlayingCard, Deck, Blackjack)
- `test_blackjack` coverage audit
- GameState class using Serializable (save/resume)
- Config for settings (bankroll, deck count)
- Partial redraw: `Terminal.moveTo` + layout constants
- Flash/flicker: only repaint changed cells
- Streamlined betting UI

### JSON
- `JSON.parseDeep` -- inflate flat store into nested Map/List objects.
  Design work needed for type inference.

### Geometry (Box, Cube)
- 91 tests passing, no known gaps.

---

## YAML / XML Parsers (Future)

Both deferred until JSON is proven and Map::Fast is stable.
YAML subset (flat key-value, simple lists) before full spec.
XML may not be worth pure-bash implementation.

---

## Class-File Documentation Pass

File-level overview, per-method comment blocks, clear voice.
Files remaining: Container, List, Map, Map::Fast, Stack, Queue, Set,
Config, JSON, Math, Card, Deck, PlayingCard, TestSuite, Args, SemVer,
Mixins/*. (Signal, String, DateTime already well-commented.)

---

## Documentation Sync Pass

Several docs reference `local -I` which the framework no longer uses:
- `docs/STANDARDS.md`, `docs/Container.md`, `docs/comparison.md`,
  `docs/PLAN.md`, `docs/bash_style.md`
- Add "why we don't use local -I" section to STANDARDS.md.

---

## README Accuracy Audit

1. "encapsulated state" -> convention-private, not mechanism-private
2. Helper docs (`_Super`, `_Cast`, `_Delegate`, `_Bless`) need examples
3. "Properties are typed as strings" -> meaningless in bash, rewrite
4. Every non-obvious claim needs a reference to docs/

