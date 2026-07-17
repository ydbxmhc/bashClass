# boop Framework -- TODO

Active work items. Completed items live in DEVLOG.md.
Design rationale lives in the relevant docs/ files.
Inline TODOs in source files should reference entries here by section name.

---

## ★ Hardened Full-Suite Run (morning priority — give it time to iterate)

Goal: prove the framework works when a *user's* shell is hostile — `set -e`,
`nounset`, `pipefail`, and aggressive globbing/case options — since real
callers may have any of these set. Two parts, because the obvious approach is
a trap.

**DON'T just run the existing suite under the options.** That corrupts the test
*harness*, not just exposes framework bugs:
- `set -e` aborts on commands TestSuite runs *on purpose* (`assert_fail`,
  negative `assert_ne` paths, "invalid input crashes" cases).
- `nocasematch` makes `[[ $a == $b ]]` case-insensitive, so TestSuite's own
  `assert_eq`/`assert_ne` comparisons silently flip on case-differing values.
Those failures are harness artifacts and tell us nothing about boop.

**Part 1 — hostile-caller `test_hardened` suite.** Exercise the framework FROM
a hostile caller and assert (in a normal shell) that it survives:

```bash
( set -euo pipefail; shopt -s globstar nullglob dotglob nocasematch nocaseglob
  . boop List Map Signal Eventable ...
  into=l List; $l.push a b c; into=n $l.length; [[ "$n" == 3 ]]   # survives -e?
  # representative ops per class; verify results and no unexpected abort )
```

Hostile options live in the CALLER subshell; assertions run in the normal
harness so verdicts stay trustworthy. Prime suspects: `nocasematch` in Signal
(signal-name compares), boop dispatch/validation (`[[ ]]` guards), Args (option
matching); `nullglob`/`dotglob` in any `for f in *glob*` loops.

**Part 2 — harden the TestSuite harness itself (it's a product, not just infra).**
A user may legitimately run TestSuite inside a script that already has
`errexit`/`nocasematch`/`nullglob` set. The harness should stay correct
regardless: normalize the shell state it depends on for its OWN work — e.g. pin
`shopt -u nocasematch` and a known IFS around its comparisons, and run
intentional-failure commands in guarded `if !`/`||` contexts so a caller's
errexit can't abort them.

Reference — the full hostile set (`-v`/`-x` are diagnostic noise; add `-x` only
to pinpoint a failure):

```bash
set -euo pipefail
shopt -s globstar nullglob dotglob nocasematch nocaseglob
```

Propagation note: options don't cross `bash` process boundaries unless exported
via `SHELLOPTS`/`BASHOPTS` or passed as flags — relevant if a runner must reach
exec'd child suites.

Status: baseline full run is GREEN (2026-07-15). The lone naming-check hit was
a false positive on the `__obj_*` object-ID glob in `boop.isObject`, since
fixed by excluding `__obj_` in the checker. This hardening is the next piece.

---

## Documentation Link Survey (deferred from 2026-07-14)

Full-site hotlink pass: link non-current-page class names in prose to their
doc pages (never inside code fences), matching the extensionless
`[Name](Name)` convention `docs/index.md` uses. Produce a link map first for
review, then apply.

**Already found — broken links to fix (targets live in `docs/`, not root, so
the `../` escapes the docs tree):**

```
docs/boop.md      → ../GOTCHAS.md    (should be GOTCHAS)
docs/JSON.md      → ../GOTCHAS.md
docs/Stream.md    → ../GOTCHAS.md
docs/boson.md     → ../TODO.md       (should be TODO)
docs/collider.md  → ../TODO.md   (×3)
docs/probe.md     → ../TODO.md
docs/tools.md     → ../TODO.md
```

Open question to settle during the survey (needs a live/Jekyll check from an
unblocked network): whether GitHub Pages serves the extensionless URLs
(`[Signal](Signal)` → `/docs/Signal`) or whether the docs should use the
`.md` form that `jekyll-relative-links` rewrites to `.html`.

---

## Documentation & Code Comment Fact-Check Audit

Full survey of every factual claim in every `.md` file under `docs/` and
every comment in every source file under the repo root, `boop`, `bin/`,
`Geometry/`, `Games/`, `Collection/`, `Math/`, `Testing/`, `Config/`,
`Data/`, `Text/`, `Signal/`, `SemVer/`, `Mixins/`, and `tests/`.

Specifically look for:
- Bash version requirements stated incorrectly (framework targets 4.3+,
  not 5.x — caught in boop.md intro)
- Feature availability claims tied to the wrong bash version
- Method names, signatures, or option flags that have drifted from the
  implementation
- Performance numbers or comparisons that are stale or fabricated
- Class/method references that point to non-existent or renamed items
- "@@" markers (known open questions) that have since been resolved
- Any other statement that can be checked against the source and is wrong

---

## `_Self` / `_Class` Default Audit (survey + evaluate — NOT a rewrite)

**This is an audit. Audit means survey and report, not refactor.** The job
is to walk every method that defaults `_Self` to `_Class` (directly, or via
`${_Self:-${_Class:-ClassName}}`), describe what it actually does, and judge
whether that default is right *for that specific method*. Do NOT blindly
align every class to one preamble — intent differs per method, and aligning
without thinking is exactly how this went wrong before.

### Design intent — the default is a FEATURE, not a bug

`_Self` deliberately falls back to `_Class` so the same inherited accessor
and method logic can operate on **either an object or the class itself**.
Class-level properties act as prototype defaults for new instances:

- Set `Box.color = blue` → every new Box instantiates blue.
- Later set `Box.color = red` → new Boxes instantiate red.
- A value set on an individual object always takes precedence over the
  class default.

So by default a constructor should consult the class for any attribute
defined on the class but not set on the object, and seed the new object
from the class value when one exists. That prototype behavior is the whole
point of the `_Self:-_Class` default.

If a given method should NOT behave that way, that method simply doesn't
use the default — write it however it needs to be. The decision is
per-method. Uniformity is not the goal; correctness-of-intent is.

### What this audit produces

For each method, report what it does and classify its use (or non-use) of
the `_Self:-_Class` default as one of:

- **Neat feature** — class-as-prototype behavior is intended and useful here.
- **Benign but useless** — harmless, but this method never meaningfully
  runs on the class, so the default does nothing either way.
- **Subtle bug waiting to happen** — would silently misbehave if ever
  called on the class (e.g. builds a nameref onto a class-level array).
- **Just dumb** — actively wrong or confusing; should change.
- **Something else** — doesn't fit the above; write down the reasoning.

The codebase is currently *mixed*: some methods default `_Self` to `_Class`,
others to empty (`${_Self:-}`). Reconciling that inconsistency — deciding
which each method *should* be and why — is part of the audit, not a
foregone conclusion in either direction.

### How we work this

One file at a time. **No hurry.** Look the methods over, discuss as much as
it takes, record notes below, come back another day, change focus when we
feel like it. We finish when we finish. Nothing here gets changed in code
until we've talked it through and agreed on the call for that method.

### Files to survey (check off as evaluated)

- [x] boop (core: `_Me`, `_Static`, `_Property`, accessors) — surveyed 2026-06-10; see Findings. One open thread (prototype inheritance) parked for later.
- [ ] Collection/Container/Container
- [ ] Collection/List/List
- [ ] Collection/Map/Map
- [ ] Collection/Map/Fast/Fast
- [ ] Collection/Set/Set
- [ ] Collection/Stack/Stack
- [ ] Collection/Stack/Fast/Fast
- [ ] Collection/Queue/Queue
- [ ] Collection/Queue/Fast/Fast
- [ ] Config/Config
- [ ] Geometry/Box/Box
- [ ] Geometry/Cube/Cube
- [ ] Text/String/String
- [ ] Math/Math
- [ ] SemVer/SemVer
- [ ] Signal/Signal
- [ ] Stream/Stream
- [ ] DateTime/DateTime
- [ ] Net/Socket/Socket
- [ ] Data/JSON/JSON
- [ ] Games (Card, PlayingCard, Deck)
- [ ] Mixins (Greetable, Serializable, Taggable, Terminal)
- [ ] Testing/TestSuite/TestSuite
- [ ] Args/Args

### Findings

_(per-file notes go here as we go — method, current default, classification,
reasoning, and any agreed action)_

#### boop (surveyed 2026-06-10)

Only three functions use the `${_Self:-${_Class:-boop}}` pattern, and all
three are the identity primitives — verdict: **neat feature, no change**:

- `_Me` (~519) — "who am I now": object ID / class name / `boop`. The
  fallback is the entire function. Essential.
- `_Static` (~533) — keys `identity.FUNCNAME.key`. Class fallback gives
  per-class (shared) static storage. Intentional.
- `_Property` (~553) — keys `identity.key`. **Load-bearing**: the
  class-level property accessors generated by `registerClass` are
  `Box.color() { ... _Class=Box _Property "color=$1" ... }`, so class
  property storage depends on this exact fallback. Removing it breaks
  `ClassName.prop`. Definitely not a bug.

Everything else in boop deliberately defaults `_Self` to empty
(`${_Self:-}`) and never falls back to class — these are low-level
primitives fed an explicit `_Self` by the baked dispatch wrappers:
`isObject`, `__boop.get`, `__boop.set`, `__boop.isa`, `__boop.mixes`,
`__boop.toString`, `__boop.inspect`, `__boop.destroy`, `__boop.trueClass`,
`__boop.new`. Correct as-is. So boop is internally consistent: identity
resolvers use the class fallback, storage primitives don't.

**OPEN THREAD (revisit — not a `_Self` issue, but adjacent):** the
prototype-inheritance behavior the design intends (a new Box inheriting
`Box.color` when its own `color` is unset). Today it is NOT wired up:
- `__boop.get` has no class fallback — comment says `getOrClass` was
  *removed* in favor of opt-in `inheritValueFor` (which isn't built yet).
- `__boop.new` only stores the explicit args passed to it; it does not
  seed from class-level defaults.
- BUT the `registerClass` comment (~1733) still claims "Instance accessors
  ... fall back to these when the property is absent from the instance
  descriptor." That comment is stale and describes removed behavior.

Suspicion (to verify): the automatic fallback existed a week/month ago and
was removed. **TODO tomorrow:** `git log -p`/`git blame` around `__boop.get`
and `getOrClass` to find when/why it was removed, then decide: re-implement
implicit instance→class fallback, build `inheritValueFor`, or (at minimum)
fix the stale `registerClass` comment.

---

## Error Severity Reclassification — DONE (2026-06-07)

All data-condition `_Crash` calls reclassified to `_Error` + return 1.
Contract documented in `docs/STANDARDS.md` "Error Handling" section.

`_Crash` now reserved exclusively for: security/injection violations,
framework internal corruption, class/mixin declaration errors, version
constraint failures, and abstract method stubs. Everything a caller can
reasonably recover from uses `_Error` + return 1 so `_FatalLevel` applies.

Files changed: `Collection/List/List`, `Collection/Container/Container`,
`Math/Math`, `Text/String/String`, `SemVer/SemVer`,
`Testing/TestSuite/TestSuite`, `Signal/Signal`. All test suites pass.

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
  Windows-saved files. The three file-load paths in `__Args_applyValue`
  (array `[]<`, map `{}<`, scalar `<`) do not strip `\r`. Only matters
  if Windows-saved files are a real input source for `<`-type args.
  Fix when needed: `line="${line%$'\r'}"` after each `read`.
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
and `_EOL` consistently. Current coverage is good but not fully audited.

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

STATUS (2026-06-07): Stage 1 and Stage 2 shipped. Stage 1: path/iteration/raw
+ sourceable output modes (26 assertions in `tests/tools/test_boson`). Stage 2:
pipe chaining + `select()` with full predicate set — `==`, `!=`, `<`, `>`,
`<=`, `>=`, `=~` (ERE), `-n`/`-z` (unary string tests), `has()` (key
existence). Non-leaf default output now re-emits JSON via
`__Data_JSON_stringifyPrefix`. Stages 3-5 remain. The standalone `Data.Boson`
query *class* is not yet extracted — the query logic lives inline in `boson`.

```bash
# CLI usage (working today)
boson '.users[0].name' < data.json
boson -r '.users[].email' < data.json                       # raw, one per line
boson --emit '.database' < config.json                      # sourceable assignments
boson --into=host '.database.host' < c.json
boson -E '.database' < c.json                               # eponymous (leaf-name vars)
boson -r '.users[] | select(.age > 30) | .name' < d.json   # pipe + select
boson -r '.items[] | select(.tag =~ "^err") | .msg' < d.json  # regex predicate
```

### Staged Roadmap

| Stage | Features | Status |
|-------|----------|--------|
| 1 | Path expressions (`.foo.bar[2]`), array iteration (`[]`), raw output | DONE |
| — | Sourceable output: `--emit`, `--into=VAR`, `-E`/`--eponymous` | DONE (doc-order preserved) |
| 2 | Pipe chaining, `select()` with comparisons, `-n`/`-z`, `has()`, `=~` | DONE |
| 3 | String interpolation (`"Hello \(.name)"`), object construction (`{k: .v}`) | TODO |
| 4 | map/reduce/group_by, sort_by | TODO |
| 5 | Recursive descent (`..`), multiple outputs | TODO |

### What exists already:
- `boson` CLI — Stage 1+2 complete
- `Data.JSON.parse` — recursive descent parser → Map.Fast
- `Data.JSON.stringify` / `__Data_JSON_stringifyPrefix` — serialize Map.Fast → JSON
- `Map.Fast.get` — point lookups by compound key
- `Map.Fast.keysUnder` — enumerate children at a prefix
- `List.filter/map/reduce/do` — functional collection ops
- `Math.DO` — expression tokenizer/evaluator (reusable for comparisons)

### What needs building (Stage 3+):
- String interpolation parser: find `\(...)` spans, substitute resolved values
- Object construction parser: `{key: .path, ...}` → build JSON from context
- Pure-bash sort for sort_by (quicksort, ~40 lines)
- Extract the format-agnostic query engine into a `Data.Boson` class so
  it's reusable as a library, not only via the CLI

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

## Documentation Sync Pass — DONE (2026-06-07)

All `local -I` references removed from docs. STANDARDS.md "Inherited
Identity Variables" section rewritten to document the actual mechanism
(direct assignment in dispatch wrappers; framework targets bash 4.3+
and deliberately avoids `local -I` which is bash 5.0 only).
Files updated: STANDARDS.md, Container.md, comparison.md, bash_style.md.

---

## README Accuracy Audit — DONE (2026-06-07)

Properties section rewritten (bash stores everything as strings, no type
system). `_Cast`/`_Delegate`/`_Bless` expanded with descriptions and
examples. Added `See docs/boop.md` reference after `_Super` description.

---

## ★ Adoption & Distribution

### 1. Packaging, Bundling, and the Installer Mixin

**The model: every tool is a gateway to the framework.**

The bundle+installer pattern is the *standard delivery vehicle* for all
boop-based standalone tools — boson, BusyBox fallbacks, example scripts,
anything intended to be dropped onto a system and run. The shape is always
the same: self-contained single file that works immediately with just bash,
and optionally bootstraps the full framework on demand.

This means:
- A stripped container gets a drop-in `grep` fallback that solves the
  immediate problem and can install the full framework for next time.
- boson ships the same way — useful standalone, gateway to the ecosystem.
- Any boop utility becomes its own installer. No separate install step,
  no bootstrap chicken-and-egg problem.

Standalone tools are distributed as single-file bundles — the framework +
required classes concatenated inline, then the tool's own code. They work
immediately with no installation. But they also carry the Installer mixin,
which can bootstrap the full framework on demand.

**Naming convention (settled 2026-06-04):** bundles are named `bundle-<tool>`
(e.g. `bundle-boson`). `collider`'s default output uses this prefix; it groups
all bundles together and keeps them visually distinct from the bare-named dev
scripts they were built from. The bare name (`boson`) is reserved for the
public release / the boopRoot-dependent dev script. Bundles are rename-safe —
nothing inside keys off the filename — so a user may drop the prefix locally.
(A trailing-dot or trailing-colon marker for dev scripts was considered and
rejected: Windows and git cannot represent either filename.)

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
- If boop is already loaded in the environment, the guards are no-ops —
  the bundle works correctly whether the framework is pre-installed or not

**Installer mixin provides:**
- `--about` / `--version` — framework version bundled in this tool
- `--install [path]` — extract/clone full framework to disk
- `--update` — pull latest (git-based installs)
- Existing installation detection (don't clobber)
- `.booprc` generation with BOOPPATH pointing at the install
- Platform detection (Linux, macOS, WSL, Git Bash on Windows)

**Bundle build tool (`collider`):**

A real tool, not a cat pipeline. The bundler must:

1. **Resolve the dependency graph statically.** Parse each class file
   for `. boop ClassName`, `_Require`, `_Load`, `_Import`, and
   `boopClass ... isa:Parent`. These are the edges. Recurse until all
   transitive deps are collected.

2. **Topological sort.** Parents before children, deps before dependents.
   A class that declares `isa:Box` must appear after Box in the bundle.
   A class that does `. boop Config` must appear after Config.

3. **Neutralize source lines.** Every `. boop ClassName` line in a
   bundled class file becomes a no-op (comment it out or replace with
   `: # bundled`). The framework's `__boop_loaded` guard handles the
   boop-itself case, but class-level source lines would trigger
   filesystem resolution that doesn't exist in a bundle context.

4. **Preserve load guards.** `boop.init ClassName || return 0` stays —
   it's the idempotency mechanism. If the bundle is sourced into a
   shell that already has boop loaded, the guards prevent double-reg.

5. **Optional: strip comment-only lines.** Lines matching `^\s*#` (but
   NOT shebangs, NOT `# shellcheck` directives) can be removed for a
   ~35% size reduction. This is a separate pass, off by default.
   Inline comments (`code  # comment`) are NOT stripped — that requires
   a real parser to distinguish `#` in strings/expansions from actual
   comments. Not worth the complexity for marginal gains.

6. **Append the Installer mixin** gated behind `--install` detection.

**Size budget (current stdlib):**
- Full with comments: ~461 KB, 10,294 lines
- Comment-only lines stripped: ~299 KB, 6,106 lines
- A typical tool (boson) would bundle boop + Args + Config + JSON +
  Map.Fast + List — maybe 60% of the stdlib. Estimated: ~180 KB stripped.

**What the bundler does NOT do:**
- Inline comment stripping (too fragile without a real parser)
- Minification (variable shortening, whitespace collapse — not worth it)
- Compilation or bytecode (bash doesn't support it)
- Tree-shaking individual functions (too coupled to be worth it)

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

### 5. BusyBox Coverage Survey

BusyBox bundles ~300 Unix tools into a single binary for minimal
environments where `sed`, `tr`, `awk`, etc. may not be present.

**The pitch:** not "replace BusyBox" but "consolation prize drop-in
for systems where bash is present but specific tools aren't." On any
given system — stripped container images, minimal cloud instances,
embedded Linux, odd CI environments — something you expect to just
be there sometimes isn't. A boop script that gracefully falls back
to a pure-bash implementation is more portable than one that crashes
with `command not found`.

#### What boop can cover (~40–50% of BusyBox surface area)

Text processing and data manipulation — the half that's pure
computation with no kernel interface:

| Tool(s) | boop equivalent | Status |
|---------|----------------|--------|
| `bc` | Math | Done — arbitrary precision, *better* than bc |
| `date` | DateTime | Done |
| `grep` (basic) | Stream + regex mode | Slower, no binary |
| `cut`, `awk` field split | Stream `-f`/`-F`/`-W` | Core use case |
| `wc` | Stream accumulation | Trivial to build |
| `head`/`tail` | Stream with record limits | Mostly covered |
| `cat` | Stream passthrough | Trivial |
| `tr` | String.replace | Done |
| `sort`/`uniq` | List + sort callback | Doable; slow on large input |
| `basename`/`dirname` | Parameter expansion | Pure bash already |
| `seq`, `yes`, `true`/`false` | Trivial loops/builtins | Trivial |
| `expr` | Math | Done |
| `printf`/`echo` | Builtins | Already there |
| Config/INI parsing | Config | Done, arguably more capable |
| JSON | Data.JSON | Done |
| `sed` (basic substitution) | String pipeline | Partial — no in-place file edit |

#### Partial / awkward

| Tool | Limitation |
|------|-----------|
| `find` | No filesystem traversal class — doable in bash, just tedious |
| `xargs` | Buildable; arg-splitting edge cases are fiddly |
| `tee` | Needs multi-FD output (Stream multi-FD model — planned) |
| `diff` | Doable but pure-bash LCS is slow on large files |
| `wget`/`curl` (basic) | `/dev/tcp` handles simple HTTP GETs; no HTTPS |
| `nc` | `/dev/tcp` covers basic cases; Stream::Socket would handle properly |

#### Hard limits — cannot replicate

| Category | Reason |
|----------|--------|
| Compression (`gzip`, `tar`, `xz`) | Binary format + null-byte problem in bash variables |
| Checksums (`md5sum`, `sha256sum`) | Bitwise ops are theoretically possible but agonizingly slow |
| Filesystem (`mount`, `mkfs`, `mknod`) | Kernel interface — must be external |
| Process/init (`ps` deep, `init`, `syslog`) | `/proc` is readable; `kill` needs syscall; init is a different world |
| User management (`passwd`, `login`) | Security-critical — should never be pure bash |
| Hardware (`ifconfig`, `udhcpc`, `mdev`) | Kernel interface |
| Editors (`vi`, `nano`) | Possible in theory; enormous scope |
| Shell (`ash`, `sh`) | Can't replace the thing running you |

#### Size and speed

- **BusyBox**: ~500KB–2MB compiled C binary covering ~300 tools
- **boop**: bash (~1.5MB) + framework + classes (~550KB source). If
  bash is already present, boop's marginal cost is ~550KB.
- **Speed**: BusyBox wins 10–100x on most operations. The exception
  is string-heavy work where boop avoids fork/exec overhead —
  `while read` + parameter expansion can beat chained external-tool
  pipelines on small-to-medium files. Crossover point: any operation
  where process startup dominates over computation.

#### Implementation approach

Don't build monolithic replacements. Build thin boop wrappers that:
1. Check for the real tool (`command -v grep`) and use it if present
2. Fall back to the pure-bash equivalent if not
3. Accept the same common flags so call sites don't need to change

The consolation-prize version doesn't need to match every flag or
handle every edge case — just the 80% that scripts actually use.

---

### 6. `lens` — Text Stream Inspection Tool

DONE (2026-06-04) — fully implemented and tested. 38 assertions in
`tests/tools/test_lens` cover all modes. See DEVLOG.

**Design (as built):**

One filtering axis per invocation:
- Position (relative): `--first`, `--last` (combinable, pipeline-ordered)
- Position (absolute): `--from`, `--to` (combinable, defines a range)
- Match: `--match`, `--no-match` (combinable, `--and`/`--or`)
- Fields: `--fields` (with `-f`/`-F`/`-W` for delimiter)
- Chars: `--chars`

These modes are mutually exclusive. Relative/absolute position also
exclusive with each other. `--not` inverts any mode (including fields and
chars). `--number` and `--count` are universal formatting options.
Multiple files are processed independently (per-file headers, or `-H`
filename prefixes, or a grand total in `--count` mode).

Stream delimiter options pass through: `-d`/`-D`/`-E` for record,
`-f`/`-F`/`-W` for field. Enables paragraph mode, CRLF, multi-char
delimiters out of the box.

Layered help: `--help` (compact synopsis), `--options` (full reference),
`--examples` (cookbook), `--about`, `--boop`.

**Deferred (not yet built):**
- `--cols 'FMT' RANGES` — combined field selection + printf formatting
- `--column` (auto-align) — requires buffering for max-width detection
- `--bytes RANGES` — byte-addressed slicing for binary/ASCII-only data

**Built 2026-06-05 (commits 8ce3bcc, 6741fcb) — now need suite tests + docs:**

- **Separate output delimiters** — DONE. `--ofs`/`--field-sep` and
  `--ors`/`--rec-sep`, defaulting to the input delimiter. Explicit empty
  (`--ofs ''`) honored via `Args.given`. Character-class input splitting errors
  without an explicit `--ofs` instead of guessing the first class char.
- **Literal insertion in field output** — DONE via auto-literals: any spec
  token that isn't a valid column spec is emitted verbatim. Spec-shaped literals
  use a `\` escape (`\4` → text "4"); `--spec-sep CHAR` changes the token
  separator so commas-in-literals need no escaping. All-elements OFS model:
  separator joins every element; empty input field = literal empty.
- **`--rec-after-byte N` / `--start-at-byte N`** — DONE. Pipe-capable bulk skip
  via `read -N`; rec-after-byte resyncs via Stream's own delimiter logic;
  start-at-byte is byte-exact (torn first record). `--number` tilde-prefixed
  (`~N`) under either, flagging seek-relative counts.

**Proposed features (designed, not built):**

- **Field/char slice operator (`:`).** A `start:end` slice form inside a spec
  token, e.g. `lens --fields 1:3-5,3,7:5-`. Sketch of intent: `1:3` could mean
  "fields 1 through 3", `7:` "field 7 to the last", `:5` "first through 5".
  NOTE: this overlaps the existing range operator `-` (`3-5`) and the open-range
  shorthand, so the grammar needs careful design — what does `:` add that `-`
  doesn't, and how do `1:3-5` / `7:5-` parse unambiguously? Decide the semantics
  before building. Lower priority than finishing tests/docs for the above.

- **`--cols 'FMT' RANGES`** (deferred, see above) and **`--column`** auto-align
  remain unbuilt; the literal/OFS work partly subsumes `--cols`.

---




### 7. Real-World Example Scripts

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

### 7. Shell Completion for boopShell

Tab-completing `$obj.<TAB>` in the interactive REPL.

Implementation path:
- `complete -F __boop_complete` registered for the readline prompt.
- Completion function: if current word starts with `$` and contains `.`,
  extract the object ID, look up its class in `__boop_registry`, walk
  the method chain, offer method names.
- Also complete class names after `. boop` and `_Import`.
- Moderate complexity — readline completion in bash is well-documented.

### 8. Functional Collection Pipelines

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


---

## NUL Byte Warning — Documentation Coverage

Add explicit NUL byte warning (cannot hold or detect; silently truncated) near
the top of documentation for any class or utility that handles values through
bash variables:

- [x] README.md — general note near top
- [x] docs/Stream.md — stream values pass through bash vars
- [x] docs/JSON.md — parsed string values stored in vars
- [x] Full boop framework doc (docs/boop.md)
- [x] GOTCHAS.md — created; NUL, $() newline stripping, read partial-line,
      $(</dev/fd/N) socket issue, nameref scoping

---

## `_Self` / `_Class` Default Audit (duplicate — see canonical entry above)

This was a second, also-incorrect copy of the old "preamble" entry. It
framed the `_Self:-_Class` default as a bug to be stamped out. It is not —
the default is intentional (class-level properties act as prototype
defaults for instances). The real task is the survey-and-evaluate audit
described in the canonical **`_Self` / `_Class` Default Audit** section
near the top of this file. Work it there.

---

## Documentation & Code Comment Fact-Check Audit

Full codebase sweep to verify all claims in docs and source comments
against the actual implementation. Do NOT do this during an active
feature sprint — schedule as a standalone pass.

Checklist:
- [ ] bash version requirements in all docs (`4.3+` vs `5.0+`)
- [ ] All method names in docs vs source (API reference tables)
- [ ] Object ID format in examples (`__obj_XX`, not `_64d...`)
- [ ] `auto` mode description (stdout always, not $_Out in main shell)
- [ ] Descriptor format (metadata only — no encoded property values)
- [ ] stale `EPOCHREALTIME` references in framework source comments
- [ ] Typecast-via-env-prefix feature: verify `_Class=X $obj.method`
  actually works with current `backfillMethods` wrappers (suspected broken)
- [ ] `__boop.stubAll` → was renamed to `__boop.backfillMethods`; ensure
  no other docs/tests still reference the old name
- [ ] `test_stress_ts` → renamed to `test_adversarial_ts`; audit all
  references including `docs/test_audit.md` and `docs/PLAN.md`
- [ ] Per-file stale comments: `docs/PLAN.md` still says "bash 5+"

---

---

## Collection underflow semantics — _Warn vs _Error (decide, then apply in one pass)

Deferred from the `$_Class` message cleanup. Underflow across the Collection
family (`List.pop`/`shift`, `Stack`/`Queue` `pop`/`peek`/`dequeue`, and the
`.Fast` variants) currently calls `_Error` + `return 1`. Earlier discussion
leaned toward a softer `_Warn` + `return 1` — recoverable, non-fatal under the
default `_FatalLevel`, only fatal under `_FatalLevel warn`. Decide warning vs
error, then apply consistently in ONE pass: fix the base (`List.pop`/`shift`)
and the composed `Stack`/`Queue` + inheriting `.Fast` variants follow. Update
docs (Stack/List/Queue/Deck/Card) and the "underflow" test-section wording to
match. Keep the underflow-vs-misuse distinction: the `.Fast` blocked-op stubs
(`shift` on a stack, `pop` on a queue, random access) are genuine API misuse
and should stay `_Error`, not become `_Warn`.

## Games.Deck.draw swallows List.pop's return code

`Games.Deck.draw` captures `$_Self.pop` into a local, ignores its exit status,
then unconditionally `boop.pass`es the (empty) value. Drawing from an empty
Deck therefore returns "" with exit 0 — no failure signal reaches the caller —
even though `List.pop` warns/errors and returns non-zero. The docs disagree
with each other and with reality: `docs/Deck.md` says "exits non-zero if
empty", `docs/Card.md` says "Crashes if empty"; neither holds. Fix `draw` to
propagate pop's failure (e.g. `into=card $_Self.pop || return 1`), then
reconcile both docs. Coordinate with the underflow-semantics decision above —
whatever `pop` does on empty, `draw` should forward it.

---

[↑ Site map](index)