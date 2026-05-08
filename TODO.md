# boop Framework — TODO

Active work items. Completed items live in DEVLOG.md.
Inline TODOs in source files should reference entries here by section name.

---

## ★ Meta-Components and Graceful Degradation

**Priority item.** The core (`boop`) should define well-known
extension points that optional meta-components can fill. If a
meta-component is installed, the core uses it. If not, the core
emits `_Warn` and carries on with reduced functionality. Sane
defaults, customizable behavior.

This is the "limp along without" pattern -- the core never hard-
depends on anything outside itself, but it gets smarter when
optional tools are present.

### Motivating Use Cases

- **`require Math 1.2+`** -- version-gated class loading. Needs
  a SemVer parser to enforce the constraint. If SemVer isn't
  available, warn and load without checking.

- **`loadClass Math _Out=stdout version=1.2+`** -- per-class
  arguments at load time. Needs ArgParser to parse key=value
  args. If ArgParser isn't available, warn and fall back to
  bare-name loading.

- **Class version declarations** -- classes declare their version
  in their descriptor (via `boopClass`). `require` checks it
  after loading. Without SemVer, the version is stored but never
  enforced.

### Candidate Meta-Components

| Component | What it enables | Fallback without it |
|-----------|----------------|---------------------|
| **SemVer** | Version parsing, comparison, range matching | Warn, skip version checks |
| **ArgParser** | key=value, positional, flag parsing for constructors and methods | Warn, ignore args / use current ad-hoc loops |
| **Help** | `--help` on classes, auto-generated from descriptors | Warn, no help output |

### Design Principles

- Meta-components live in the standard namespace tree like any
  other class. They're loaded via the normal import path.
- The core checks for their presence at the point of use, not at
  init time. Lazy detection -- no startup penalty.
- Detection is a simple registry check:
  `[[ -n "${__boop_registry[SemVer]+set}" ]]`
- The warn-and-continue behavior is the default. A user who wants
  strict enforcement can set `_FatalLevel warn` and missing
  meta-components become fatal.
- Each extension point has a well-defined interface the core
  codes against. The meta-component implements that interface.
  Swappable implementations are possible (e.g., a lightweight
  SemVer vs a full-featured one).

### Relationship to Existing TODO Items

- **Argument-Parsing Object** -- becomes the ArgParser meta-component
- **Version Declaration** -- becomes SemVer meta-component + class
  version property + `require` function
- **Class File Execution Guard & Help System** -- becomes the Help
  meta-component
- **Inline Arguments on Class Load** -- enabled by ArgParser

### Open Questions

- Should `require` be a function or a keyword in the source line?
  `require Math 1.2+` vs `. boop require:Math:1.2+`
- How do classes declare their version? Property in `boopClass`
  call? Separate `declare`?
- Should meta-components be auto-loaded on first use, or must the
  user explicitly import them?
- Can meta-components depend on each other? (ArgParser probably
  doesn't need SemVer, but `require` might need both.)

Needs a full spec pass before implementation.

---

## `::` Syntax -- Mixins, Classlets, and Multiple Inheritance

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

## Args -- Pending Items

Core done. Implementation at `Args/Args`. 57 tests in
`tests/unit/test_args_ts`. Docs at `docs/Args.md`.

### Pending
- Cross-subcommand option isolation (deferred)
- Schema validation warnings for common mistakes

---

## Argument-Parsing Object -- See Meta-Components

Now part of the ★ Meta-Components system. ArgParser becomes an
optional meta-component that the core can leverage for key=value
parsing in constructors, `loadClass`, and `require`. See that
section for the full design.

---

## Inline Arguments on Class Load -- See Meta-Components

Now part of the ★ Meta-Components system. Enabled by the ArgParser
meta-component. See that section for the design.

Original idea: `. boop Math precision=128` passes key=value pairs
to the class during loading. The bulk-load form (`. boop Math Cube
List`) stays as-is.

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

- **Class file load guards** (`&& return 2>/dev/null`): Deferred to
  the Load Guard & Class Init Refactor (all 12 instances).

- **TestSuite assert_ok/assert_fail**: ✓ Already fixed — stderr is
  captured to a temp file and emitted via `_Debug`.

- **boop import fallback**: ✓ Fixed — stderr captured and emitted
  via `_Debug` instead of discarded.

Principle: Only suppress stderr when you know exactly what the error
will be, you're expecting it, and the content has no debugging value.

---

## Security: Parse Config Files as Data, Not Code

Currently `.boopIndex` and `.boop.cfg` are sourced as bash scripts.
This means a malicious or corrupted file can execute arbitrary code
during framework initialization. The current trust model matches
`.bashrc` (if an attacker can write your config, you're already
compromised), but we should harden this.

Goal: convert `.boopIndex` and `.boop.cfg` from sourced scripts to
parsed data files. Read them line by line, extract key=value pairs
via parameter expansion, populate the arrays manually. No `eval`,
no `source`, no code execution.

Implementation:
- Write a `__boop.parseConfig` function that reads a file and
  populates a named associative array from `key=value` lines
- Ignore blank lines and `#` comments
- Reject lines that don't match the expected pattern (emit `_Warn`)
- Use this for `.boopIndex` and `.boop.cfg` instead of sourcing
- The file format stays the same (valid bash syntax) so it's
  still human-readable and backward-compatible if someone does
  source it manually

Priority: low (current trust model is adequate). Do this when
the framework is mature enough to worry about hostile environments.

---

## JSON -- Pending Items

Core done. Implementation at `Data/JSON/JSON`. 45 tests in
`tests/unit/test_json_ts`. Docs at `docs/JSON.md`.

### Pending
- `JSON.parseDeep` -- inflate flat store into real Map/List objects
- Unicode escape handling (`\uXXXX` currently skipped)
- Key order preservation in stringify (hash iteration order)

---

## YAML / XML Parsers (Future)

YAML: indentation-sensitive, harder than JSON. Consider a subset
parser (flat key-value, simple lists) before attempting full spec.

XML: attributes + content + nesting. Significantly more complex.
May not be worth pure-bash implementation -- consider requiring
an external tool as an optional dependency.

Both deferred until JSON is proven and Map::Fast is stable.

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

## Phase 2 Collections

### Stack
Classic LIFO. Constrain List: expose `push`, `pop`, `peek`,
`isEmpty`. Hide `shift`, `unshift`, `get`-by-index.

### Queue
Classic FIFO. Expose `enqueue` (push), `dequeue` (shift),
`peek`, `isEmpty`. Possibly `size`.

### LinkedList
Each node is itself an object (or a Map entry). Requires `insertAt`,
`removeAt`, `next`/`prev` traversal. Decide whether doubly-linked is
worth the complexity at this stage.

### Set
Unique unordered collection. Implement on top of Map keys — values are
irrelevant, keys are the members. Expose `add`, `has`, `remove`,
`toArray`, `union`, `intersect`. Arguably simpler than LinkedList.

---

## String Class (Phase 3)

Minimum useful interface, all in pure bash parameter expansion —
no forks, no subshells:

`trim`, `split`, `join`, `contains`, `startsWith`, `endsWith`,
`replace`, `replaceAll`, `length`, `toUpper`, `toLower`, `substring`,
`indexOf`, `padLeft`, `padRight`.

Heavy string work is already happening natively everywhere. A class
wrapper gives callers a consistent interface and makes complex string
pipelines readable.

---

## I/O Classes (Phase 5)

All implementable in pure bash using persistent file descriptors —
no forks, no subshells, no external tools.

### File
Wraps a persistent file descriptor opened with `exec {fd}<>file`.
Interface: `open`, `close`, `read`, `readLine`, `readAll`, `write`,
`seek`, `tell`, `eof`.

### Buffer
Accumulates writes in a string variable, flushes on demand or at
a size threshold. Zero I/O cost for buffered writes; one write
per flush.

### Pipe
Bidirectional in-memory channel using bash's `exec {rfd}<> <(...)` or
a named FIFO. Needs design work — bash FD plumbing for in-process
pipes is finicky.

### Read utilities
`mapfile`/`readarray` for bulk line-array reads. `read -t 0` for
non-blocking poll. `read -N n` for exact byte counts. Wrap as static
methods on an `IO` namespace class.

---

## Return System Filesystem Mode

`boop.passPath` — use call stack introspection to determine a
filesystem-backed return path. Would allow returning data via temp files
instead of variables, useful for large payloads.

Consider: `_File` as a Tier 2 inherited var on `boop.pass` for explicit
file output. Open questions around precedence (`into=` vs `_File` vs
mode). Don't overthink it — users can always manage their own redirects.

---

## Implicit Object Declaration on Return (`_AS=`)

Explore whether `boop.pass` could auto-wrap a return value as an
object of a specified class:

```bash
into=o _AS=List boop.classPath list
$o.length    # → number of entries
```

Open questions:
- Does `boop.pass` handle the wrapping, or does the caller's
  `into=` assignment trigger it?
- Performance cost of creating an object on every return?
- What if the class isn't loaded yet — auto-import?
- Is this just sugar for `into=raw method; into=o List "$raw"`?

Might not be worth the complexity. Investigate and decide.

---

## Try/Catch Mechanism -- Low Priority

Bash has no native try/catch. Every approach has serious tradeoffs.
Conclusion: the cure is worse than the disease. Developers should
handle errors explicitly with exit codes and `_Crash`. The fatality
threshold (`_FatalLevel`) already provides escalation control.

Revisit if a compelling use case emerges.

---

## Extensive Logging Hooks Throughout Codebase

The logging system exists but most of the codebase doesn't use it.
The framework needs comprehensive logging instrumentation so that
turning up the log level actually reveals what's happening.

Priority areas:
- `__boop.import` — log every resolution step at `_Debug`/`_Trace`
- `__boop.loader` — log each rc/cfg file sourced or skipped at `_Info`
- `boop.classPath` — log set/remove/rebuild at `_Info`
- Object lifecycle — creation/destruction at `_Debug`
- Method dispatch — MRO cache misses at `_Debug`, every dispatch at `_Trace`
- Property access — `__boop.get`/`__boop.set` at `_Trace`
- `boop.pass` — mode selection at `_Trace`

Principle: `_Info` = lifecycle events. `_Debug` = decisions.
`_Trace` = everything.

### Log-Level Bypass via Function Replacement

When `_LogLevel` is high, silenced functions still pay invocation
cost. Replace with no-op bodies (`() { :; }`) at level-change time.
Restore real implementations when level rises. Per-class overrides
complicate this — function replacement is global but per-class checks
are inside `__boop.log`.

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
- **Defensive array access policy**: when a method accesses its
  backing array (`__boop_data_*`, `__boop_keys_*`) and the array
  is uninitialized or missing (corrupted/destroyed object), what
  should happen? Options: (a) `_Error` — fatal under strict
  `_FatalLevel`, survivable under loose; (b) `_Warn` + return
  empty/zero; (c) silent empty (current `:-` behavior). The right
  answer probably depends on the user's session posture — `set -u`
  users want a crash, cowboy coders want resilience. We have the
  machinery (`_FatalLevel`, `_LogLevel`) to make this configurable.
  Design pass needed to pick a consistent policy across all
  collection classes.

### Games (Card, PlayingCard, Deck, Blackjack)
- `test_blackjack` coverage audit
- Consider whether Blackjack logic belongs in `BlackjackHand` class

### Geometry (Box, Cube)
- 91 tests passing, no known gaps. Revisit when new classes added.

---

## Test Coverage Audit

Every declared method in every class should have test coverage:
- Valid usage (expected inputs → expected outputs)
- Expected failures (bad inputs → clear crash messages)
- Unexpected/garbage inputs (fails gracefully)

Priority: Container (23 methods), Math (26 methods), List (15),
Map (12), Iterator (8). Also CLI-level testing for Tier 3 public
methods.

---

## README Accuracy Audit

Points to address in the next README edit pass:

1. "objects with encapsulated state" → state is convention-private, not mechanism-private
2. "The default fatality threshold is `error`" → WRONG, default is `crash`
3. "1,400+ assertions" → verify actual count
4. "~2,200 lines of bash" → actual is ~2,500
5. "production-quality implementations" → soften (JSON lacks unicode, Math has gaps)
6. Helper documentation (`_Super`, `_Cast`, `_Delegate`, `_Bless`) needs examples
7. "No subshells in the hot path" → JSON stringify uses `sort -n`
8. "Properties are typed as strings" → meaningless in bash, rewrite
9. Every non-obvious claim needs a reference to docs/
10. Needs "why we don't use local -I" section in STANDARDS.md
