# boop Framework -- TODO

Active work items. Completed items live in DEVLOG.md.
Design rationale lives in the relevant docs/ files.
Inline TODOs in source files should reference entries here by section name.

---

## ★ Error Severity Reclassification

Priority: HIGH. The framework over-uses `_Crash` for conditions that are
recoverable. The fatality level system (`_FatalLevel`) already exists to
escalate `_Error` to fatal — use it. The default should be survivable.

Principle: `_Crash` is for framework corruption and security violations.
Everything else is `_Error` + return 1. The caller checks the exit code.
Users who want strict mode set `_FatalLevel error`.

### Stay as `_Crash`:
- Shell injection / invalid identifiers (security boundary)
- Framework internal corruption (registry inconsistent with expectations)
- Explicit user `_Crash` calls
- `__boop.validate` failures
- `__boop.registerMethod` on non-existent function

### Reclassify to `_Error` + return 1:
- `pop`/`shift` on empty collection
- `peek` on empty stack/queue
- Out-of-range `set`/`delete` on List
- `destroy` on non-existent object (double-free)
- `Config.load` / `Config.loadINI` file not found
- `Args.parse` missing required option
- `Args.parse` unknown option
- Math division by zero
- `Stream.new` unable to open file
- Any "the data wasn't what I expected" condition

### Migration path:
1. Change each call site from `_Crash` to `_Error` + `return 1`
2. Update tests: `assert_fail` tests that spawn subshells expecting a
   crash need to check for non-zero exit instead
3. Verify `_FatalLevel error` still makes all of these fatal
4. Document the new contract in STANDARDS.md

### Tests affected:
Every `assert_fail` that tests a data-condition crash (empty pop, bad
index, missing file, etc.) will need updating. Tests for security
crashes (injection, invalid names) stay as-is.

---

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

DONE — `$obj.destroy` implemented in core (2026-05-26). See docs/boop.md
"Destroying Objects" section.

- `__boop.destroy` registered on root class, inherited by all objects
- Class-level `ClassName._destroy()` private hook convention
- Walks inheritance chain calling each ancestor's hook (most-derived first)
- Wipes __boop_static keys, unsets wrapper functions, removes registry entry
- Hooks implemented for: List, Map, Map.Fast, Set, Stack, Queue, Config,
  Stream, Iterator

Remaining:
- Dedicated test file (`test_destroy_ts`) with full lifecycle coverage
- JSON class _destroy hook (owns a Map.Fast internally)
- Audit blackjack for destroy opportunities in game loop

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
- **_Class leak audit**: any constructor that creates child objects
  must use `_Delegate` (or clear `_Class`) to prevent the child from
  being baked with the parent's class identity. Stack and Queue fixed
  (2026-05-26). Audit: TestSuite (creates List/Map in queue mode),
  BlackjackHand (isa List), JSON (creates Map.Fast), any future
  composition patterns. Add inheritance-correctness assertions to
  each class's test suite.

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

## YAML Parser (Data.YAML)

Pure-bash YAML subset parser. Storage: Map.Fast (flat compound keys),
same backend as Data.JSON. API mirrors Config.

**Stage 1 — the 80% subset:**
- Key-value pairs, nested mappings via indentation, simple sequences
- Comments, quoted strings, empty values
- Parser: Stream (line-by-line, buffered), indent stack tracking
- `Stream.putBack` for lookahead (already implemented)

**Stage 2 — flow syntax + multi-line:**
- Flow mappings `{key: val}` / sequences `[a, b]` → delegate to JSON.parse
- Literal block `|` / folded block `>` — read until dedent via putBack
- Block chomping (`|+`, `|-`, `>-`)

**Stage 3 — deferred:**
- Anchors/aliases, tags, merge keys, multi-document

---

## boson — Structured Data Query Tool

"Bash Oriented Scripting Object Notation" — a jq-like query engine
for structured data. Operates on any Map.Fast (JSON, YAML, Config).

Architecture: `Data.Boson` class (query engine) + `boson` CLI wrapper.
The query engine is format-agnostic — it queries Map.Fast regardless of
what parser populated it.

```bash
# CLI usage
boson '.users[0].name' < data.json
boson '.database.host' < config.yml

# Library usage
into=doc Data.JSON.parse < data.json
into=val $doc.query ".users[0].name"
into=val $doc.query ".users[].age"       # one per line
```

### Staged Roadmap

| Stage | Features | Builds on |
|-------|----------|-----------|
| 1 | Path expressions (`.foo.bar[2]`), array iteration (`[]`), raw output | Map.Fast.get, keysUnder |
| 2 | Select with comparisons (`select(.age > 30)`), pipe chaining | List.filter, Math comparison |
| 3 | String interpolation (`"Hello \(.name)"`), object construction (`{k: .v}`) | String manipulation |
| 4 | map/reduce/group_by, sort_by | List.filter/map/reduce (already built) |
| 5 | Recursive descent (`..`), multiple outputs | Key iteration with suffix match |

### What exists already:
- `Data.JSON.parse` — recursive descent parser → Map.Fast
- `Data.JSON.stringify` — serialize Map.Fast → JSON
- `Map.Fast.get` — point lookups by compound key
- `Map.Fast.keysUnder` — enumerate children at a prefix
- `List.filter/map/reduce/do` — functional collection ops
- `Math.DO` — expression tokenizer/evaluator (reusable for comparisons)

### What needs building:
- Path expression parser (`.foo[2].bar` → `foo.2.bar` compound key)
- Array iteration (enumerate numeric keys under a prefix, yield each)
- Comparison expression evaluator for select predicates
- Construction syntax parser (mini-language for building output objects)
- Pure-bash sort for sort_by (quicksort, ~40 lines)
- CLI wrapper script (`boson`)

---

## XML Parser (Future — Low Priority)

May not be worth pure-bash implementation. Deferred indefinitely.

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

---

## ★ Adoption & Distribution

### 1. Packaging, Bundling, and the Installer Mixin

**The model: every tool is a gateway to the framework.**

Standalone tools (boson, a YAML tool, etc.) are distributed as single-file
bundles — the framework + required classes concatenated inline, then the
tool's own code. They work immediately with no installation. But they also
carry the Installer mixin, which can bootstrap the full framework on demand.

```bash
# Just use it — zero install, single file
boson '.name' < data.json

# What's inside?
boson --about          # "boson v1.0 — built on boop v0.1.0"

# Want the full framework?
boson --install              # → ~/.local/lib/boop + .booprc
boson --install /opt/boop    # custom location
```

**Bundle format:**
- Framework (`boop`) concatenated at the top (inside `__boop_loaded` guard)
- Required classes in dependency order (load guards prevent double-reg)
- Tool's own code
- Installer mixin gated behind `--install` argument detection

**Installer mixin provides:**
- `--about` / `--version` — framework version bundled in this tool
- `--install [path]` — extract/clone full framework to disk
- `--update` — pull latest (git-based installs)
- Existing installation detection (don't clobber)
- `.booprc` generation with BOOPPATH pointing at the install
- Platform detection (Linux, macOS, WSL, Git Bash on Windows)

**Bundle build tool (`boop.bundle`):**
- Takes a tool script + a manifest of required classes
- Resolves dependency order via the class registry
- Concatenates into a single distributable file
- Appends the Installer mixin code

**Deferred:**
- `basher` package, `brew tap` — wait until post-1.0 stability
- Version-pinned installs (requires release tagging infrastructure)

### 2. Object Lifecycle / GC

DONE — see "Garbage Collection / Object Lifecycle" section above.

### 3. Error Recovery Beyond _Crash

Superseded by the Error Severity Reclassification (see top of this file).
Once data-condition crashes become `_Error` + return 1, normal exit codes
handle recovery. `_Guard` is unnecessary — the only remaining crashes are
framework corruption and security violations, which should not be caught.

### 4. Reduced Naming Ceremony

The `__ClassName_methodName_varname` convention is correct but verbose.
Every local is 30+ characters.

Options:
- **Preprocessor**: write class files with short names (`__self`, `__key`),
  expand to full convention at "build" time. Adds a build step.
- **Accepted cost**: document that this is the price of collision safety
  in a flat namespace. IDE snippets / templates reduce typing friction.
- **Shorter prefix policy**: allow `__CM_` (class initials + method initial)
  for deeply nested locals. Document the abbreviation in the class header.

### 5. Real-World Example Scripts

The blackjack game demonstrates the framework but not its *utility*.

Candidates:
- **Config-driven deploy script**: parse INI config, validate with Args,
  manage state with Map, structured logging, Signal for cleanup.
- **Log analyzer**: Stream a large log file, parse with field delimiters,
  accumulate stats in Map, output summary.
- **REST client wrapper**: Args for CLI, Config for credentials, Map for
  headers, structured JSON response handling.
- **System inventory tool**: collect host info, serialize to JSON, compare
  against expected state from Config.

### 6. Shell Completion for boopShell

Tab-completing `$obj.<TAB>` in the interactive REPL.

Implementation path:
- `complete -F __boop_complete` registered for the readline prompt.
- Completion function: if current word starts with `$` and contains `.`,
  extract the object ID, look up its class in `__boop_registry`, walk
  the method chain, offer method names.
- Also complete class names after `. boop` and `_Import`.
- Moderate complexity — readline completion in bash is well-documented.

### 7. Functional Collection Pipelines

`$list | filter fn | map fn | collect` without subshells.

Implementation path:
- Methods on List/Container: `$list.filter callback`, `$list.map callback`,
  `$list.reduce callback init` — each returns a new List (or modifies
  in-place with a flag).
- Chaining: each method returns `$_Self` (or a new object ID) so calls
  can be composed: `into=result $list.filter isEven`.
- No pipe operator needed — just method calls that return collection IDs.
- `each` already exists; `filter`/`map`/`reduce` are the same loop with
  different accumulation logic.

---

## Feasibility Notes (2026-05-26)

| Item | Effort | Complexity | Blockers |
|------|--------|------------|----------|
| Single-file bundle | 1-2 hours | Low | Ordering deps correctly |
| Install script | 2-3 hours | Low | Testing across platforms |
| `$obj.destroy` | 4-6 hours | Medium | Companion array naming conventions vary |
| `_Guard` error recovery | N/A | N/A | Superseded by error reclassification |
| Result objects | 1-2 days | High | Pervasive API change if adopted broadly |
| Preprocessor for names | 1-2 days | High | Adds build step, debugging indirection |
| Example scripts | 1 day each | Low | Just writing them |
| Shell completion | 4-8 hours | Medium | Readline integration, edge cases |
| `filter`/`map`/`reduce` | 3-4 hours | Low | API design (new list vs mutate) |

