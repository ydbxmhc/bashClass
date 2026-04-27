# boop Framework — TODO

Active work items. Completed items live in DEVLOG.md.
Inline TODOs in source files should reference entries here by section name.

---

## ★ Namespace, ClassPath, Index, and Configuration System

**Priority item.** ✓ Core implementation complete. The framework now has:
- `__boop.classResolve` — namespace-aware resolution (classPath → index → dynamic discovery)
- `__boop.loader` — RC chain sourcing, BOOPPATH parsing, .boopIndex sourcing, version mismatch detection
- `__boop.import` — rewritten to use classResolve with raw source fallback
- `boop.resolve` — public non-fatal resolution wrapper
- `boop.classPath` — full subcommand API (set/get/list/remove/has/dirs/rebuild)
- CFG serialization helper
- Filesystem fallback diagnostic

### Remaining Work

- **Test suite (`test_classpath_ts`)**: Dedicated test file exercising
  the classpath/namespace system end-to-end. Should cover: namespace
  resolution, index lookup, classPath overrides, rebuild, CFG round-trip,
  RC chain sourcing, BOOPPATH construction, deduplication, error cases.
  Add to `test_all` in the unit tests section.
- **Namespace directory migration**: Move existing flat class files into
  the namespace directory layout described below. Generate `.boopIndex`.
- **Remove `__boop_dir`**: ✓ Done. Declaration removed from `boop`.
- **Property-based tests**: Optional tasks from the spec (Properties 1-13).

### Design Reference

Core implementation complete. See DEVLOG.md for implementation notes
and prior art survey. The following sections document the design for
ongoing and future work.

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

`BOOPPATH` is a colon-delimited list of library roots (same format
as `PATH`, same naming convention as `GOPATH`/`MANPATH`). Each
root is a complete boop library with its own `.boopIndex`, its own
namespace tree, its own `.booprc`/`.boop.cfg`. Resolution is
**depth-first by default** — exhaust all resolution strategies
within one root before moving to the next.

**Root list construction** (in order):
1. `__boop_dir` — where `boop` itself lives (always first)
2. `BOOPPATH` entries — left to right

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
for each root in [__boop_dir, BOOPPATH...]:
  try per-root resolution (steps 1–4)
  found? → stop, use it
  not found? → next root

all roots exhausted → PATH fallback (bash native source)
still not found → _Crash
```

This enables **version layering**: `BOOPPATH="/opt/boop/v2:
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
- Parse `BOOPPATH` env var — split on colons, validate
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

## Reserved Variable Names & Inheritance Hygiene ✓ → DEVLOG

---

## Configurable Baked-Wrapper Typecast Behavior ✓ → DEVLOG

---

## Framework-Wide LOGLEVEL System ✓ → DEVLOG

---

## Fatality Threshold ✓ → DEVLOG

---

## Args — CLI Argument Parser ★ IN PROGRESS

Two entry points, one class. Implementation at `Args/Args`.

### `Args.getOpts` — POSIX short options (thin getopts wrapper)
```bash
Args.getOpts ":vf:" "$@"
shift $((OPTIND-1))
# Sets: $v=1 (boolean), $f=<value> (value-taking)
# $__Args_orig holds original args array
```
Leading `:` in optstr = silent error mode. Value-taking options (letter`:`) get
the value; booleans get `"1"`. Unknown option or missing value → `_Crash`.
Caller must `shift $((OPTIND-1))` after to consume processed args.

### `Args.parse` — GNU long + subcommand parser

Schema is an INI-style string passed as the first argument.

```bash
Args.parse '
[Use]
  ${0##*/} [options] ACTION [args]

[Options]
  verbose | v                       # boolean flag → $verbose
  output | o = /tmp/out.txt         # value-taking, with default → $output
  : required | r =                  # required, value-taking → $required

[Subcommands]
  deploy | d                        # canonical name is "deploy"
  rollback | rb

[deploy]
  env | e =                         # deploy-specific option → $env

[rollback]
  : version | ver =                 # required for rollback → $version
' "$@"
```

**Option line syntax** (left of `#` is parsed, right is help text):
- `[: ] varName [| alias...] [= [default] | :]`
- Leading `:` → required
- Trailing `=` → takes a value; `= default` sets the default
- Trailing `:` → takes a value (no default form)
- No sigil → boolean (absent=`""`, present=`"1"`)
- First entry = variable name (must be valid bash identifier, no hyphens)
- Additional entries = CLI aliases (may contain hyphens)
- Single-char entries map to `-x`; multi-char entries map to `--name`

**After parse (scope-write mode — no `into=`):**
- `$varName` set for each option (value or default or empty)
- `$_Action` = canonical subcommand name (or empty)
- `$_ArgsRemaining` = array of remaining positionals
- `$__Args_orig` = array of original args
- To restore `$@`: `set -- "${_ArgsRemaining[@]}"`

**Object mode (`into=args Args.parse schema "$@"`):**
- Returns a Config object. `_Require Config` called internally.
- Access: `$args.get varName`, `$args.get _action`, `$args.get _remaining`
- Scope vars are NOT set in object mode.

**Behavior:**
- `--` terminates option processing; remainder → `_ArgsRemaining`
- Short clustering: `-abc` = `-a -b -c`
- `-xVALUE` attaches value to short option within cluster
- Unknown option → `_Crash`
- Missing required value → `_Crash`
- Missing required option → `_Crash` (checked after full parse)
- All option sections (`[Options]`, `[subcommandName]`) contribute to the
  same alias pool. Subcommand-specific options are globally available
  (cross-subcommand validation is a future enhancement).

### What's done
- `Args/Args` — full implementation of both entry points
- `Config.fromString` — added to `Config/Config` (used by future tooling)

### What's pending
- `tests/unit/test_args_ts` — test file not yet written
- `tests/test_all` — needs `test_args_ts` in unit loop and `Args/Args` in naming check
- `--help` auto-generation from schema (deferred — needs description storage)
- Cross-subcommand option isolation (deferred — currently all options share alias pool)

---

## Argument-Parsing Object -- See Meta-Components

Now part of the ★ Meta-Components system. ArgParser becomes an
optional meta-component that the core can leverage for key=value
parsing in constructors, `loadClass`, and `require`. See that
section for the full design.

Original sketch:
```bash
into=args ArgParser "suit= rank= faceUp=0" "$@"
$args.get suit   # -> "spades"
$args.get faceUp # -> "0" (default)
```

Needs to handle: required vs optional, defaults, type validation,
positional fallback, unknown-key rejection.

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

`.booprc` remains a sourced bash script by design — it's explicitly
user code. The hardening applies only to machine-managed files
(`.boopIndex`, `.boop.cfg`) where the content is structured and
predictable.

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

## Inline Class Definitions in Executable Scripts ✓

The `BASH_SOURCE[0]` vs `$0` guard is the pattern. After `boopClass`
registration, add:

```bash
[[ "${BASH_SOURCE[0]}" != "${0}" ]] && return 0
# main logic here — only runs when executed directly, not sourced
```

`blackjack` demonstrates this: sourcing it loads `BlackjackHand` for
tests; executing it runs the game. No separate class file needed.

See also: "Class File Execution Guard" section above for the remaining
work (auto-help when sourced-as-executed without this guard).

---

## Generalize Card/Deck/Hand Classes ✓ → DEVLOG

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

## BOOPPATH ✓ → DEVLOG (subsumed by Classpath/Namespace system)

## Version Declaration → See Meta-Components (SemVer component)

---

## I/O Classes (Phase 5)

All implementable in pure bash using persistent file descriptors —
no forks, no subshells, no external tools. Fits the zero-fork philosophy.

### File

Wraps a persistent file descriptor opened with `exec {fd}<>file`.
Avoids the open/close overhead of re-reading files per call.

```bash
into=f File.open "/var/log/app.log" mode=append
$f.write "event: $data"
$f.readLine   # reads next line via read -r -u $fd
$f.close
```

Interface: `open`, `close`, `read`, `readLine`, `readAll`
(`mapfile -t arr -u $fd`), `write`, `seek`, `tell`, `eof`.

### Buffer

Accumulates writes in a string variable, flushes on demand or at
a size threshold. Zero I/O cost for buffered writes; one write
per flush.

```bash
into=buf Buffer.new
$buf.append "line one\n"
$buf.append "line two\n"
$buf.flush   # one write to FD/file
$buf.toString
```

### Pipe

Bidirectional in-memory channel using bash's `exec {rfd}<> <(...)` or
a named FIFO. Useful for producer/consumer patterns within a script
without spawning subprocesses.

Needs design work — bash FD plumbing for in-process pipes is finicky.
Start with named FIFOs (`mkfifo`) as the backing store; revisit for
anonymous pipe options.

### Read utilities

`mapfile`/`readarray` for bulk line-array reads. `read -t 0` for
non-blocking poll. `read -N n` for exact byte counts. Wrap these
as static methods on a `IO` namespace class so callers don't need
to remember the flags.

Source: PLAN.md Phase 5.

---

## Config Class ✓

A Config object that reads and writes structured config files in pure
bash. Two formats, one interface.

### Property file (flat key=value)

Same format as `.boop.cfg` — one `key=value` per line, `#` comments,
blank lines ignored. Keys are top-level; no sections.

```bash
into=cfg Config.load ~/.myapp.cfg
$cfg.get theme          # → "dark"
$cfg.set theme light
$cfg.save ~/.myapp.cfg  # rewrite in place
```

### INI file

`[section]` headers divide key=value groups. Keys are stored
internally as `section.key` so the same get/set/has interface works
for both formats. Section name `""` (empty) is the implicit top-level
for keys before the first header.

```bash
into=cfg Config.loadINI /etc/myapp.ini
$cfg.get database.host  # → "localhost"
$cfg.get database.port  # → "5432"
$cfg.keys database      # → "host port user password"
$cfg.sections           # → "database server logging"
```

### Interface

```
Config.load file        → new Config object backed by property file
Config.loadINI file     → new Config object backed by INI file
Config.new              → empty Config object (no file)
$cfg.get key            → value or empty string
$cfg.set key val        → update in memory
$cfg.has key            → exit code 0/1
$cfg.keys [section]     → space-separated key list
$cfg.sections           → section list (INI only)
$cfg.save [file]        → write current state back
$cfg.toINI [file]       → write as INI format
$cfg.toFlat [file]      → write as flat key=value
```

### Implementation notes

- Backed by a per-object associative array `__boop_config_${_Self}`
  (same pattern as Map's companion storage).
- `Config.load` / `Config.loadINI` parse with a `while IFS= read -r`
  loop — pure bash, zero forks. Regex matching for `[section]` headers
  and `key=value` lines via `[[ =~ ]]`.
- Keys in flat files stored as-is. Keys in INI files stored as
  `section.key`; the section prefix is stripped by `$cfg.get` when
  a bare key is given and it matches exactly one section.
- `$cfg.save` rewrites the file entirely (not append). Preserves
  comments from the original file if they were captured during load.
  (Comment preservation is optional / Phase 2.)
- Deliberately does NOT `source` the file — pure data parsing, no
  code execution. See "Security: Parse Config Files as Data" section.

Implementation complete: `Config/Config`, 71 tests in `tests/unit/test_config_ts`.

Source: discussed as extension of .boop.cfg concept.

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

## Housekeeping ✓ → DEVLOG

---

## Extensive Logging Hooks Throughout Codebase

The logging system exists (`_Error`, `_Warn`, `_Info`, `_Debug`,
`_Trace`) but most of the codebase doesn't use it. The framework
needs comprehensive logging instrumentation so that turning up the
log level actually reveals what's happening.

Priority areas:

- **`__boop.import`** — log every resolution step: which root is
  being searched, which strategy matched (classPath, index,
  filesystem, bare file), what file was sourced. At `_Debug` level.
  At `_Trace`, log the full root list and index contents.

- **`__boop.loader`** — log each rc/cfg file sourced or skipped,
  `BOOPPATH` parsing results, index loading. `_Info` level.

- **`boop.classPath`** — log every `set`, `remove`, `rebuild`
  operation including what was written and where. `_Info` level.

- **Object lifecycle** — `__boop.new` and `destroy` should log
  object creation/destruction at `_Debug`. Constructor arguments
  at `_Trace`.

- **Method dispatch** — `registerClass` wrapper generation,
  MRO cache hits/misses, inherited method resolution. `_Debug`
  for cache misses, `_Trace` for every dispatch.

- **Property access** — `__boop.get`/`__boop.set` at `_Trace`
  level. Too noisy for anything less.

- **`boop.pass`** — log mode selection and target variable at `_Trace`.
  Subshell footgun `_Debug` already added (into= in subshell emits advisory).

- **Class files** — each class's `.new()` should log construction
  at `_Debug`. Complex methods (Container iteration, Math
  arithmetic) should log entry/exit at `_Trace`.

Principle: `_Info` shows lifecycle events (loaded X, sourced Y).
`_Debug` shows decisions (chose this path because...). `_Trace`
shows everything (every get/set, every dispatch, every argument).
A user debugging a resolution issue should be able to set
`_LogLevel trace` and see the complete story.

Source: `boop`, all class files.

### Log-Level Bypass via Function Replacement (Performance)

When `_LogLevel` is set high (e.g. `ERROR`), every `_Warn`, `_Info`,
`_Debug`, and `_Trace` call still pays the cost of a function invocation
that immediately returns. At high call volume this adds up.

**Mechanism: function replacement, not aliases.** Aliases don't expand
inside function bodies in non-interactive shells. The correct approach
is to overwrite the silenced functions with no-op bodies at `_LogLevel`
change time:

```bash
# Inside __boop.setLogLevel, after updating __boop_logLevel:
_Trace() { :; }
(( __boop_logLevel >= __boop_LOG_DEBUG )) || _Debug() { :; }
(( __boop_logLevel >= __boop_LOG_INFO  )) || _Info()  { :; }
(( __boop_logLevel >= __boop_LOG_WARN  )) || _Warn()  { :; }
# Restore real implementations for active levels (re-source or eval)
```

`:` is a bash builtin — the cheapest possible no-op. Plain string args
still get evaluated before the call (bash evaluates args before dispatch),
but that's only significant if the message involves a subshell — which
it shouldn't, per our no-subshell policy.

For expensive message construction in hot paths, use an inline guard
at the call site to skip arg evaluation entirely:

```bash
(( __boop_logLevel >= __boop_LOG_DEBUG )) && _Debug "hot-path detail: $val"
```

Caveats:
- Must restore real implementations when `_LogLevel` rises again
- Benchmark: re-defining N functions per level change should be
  negligible vs the per-call savings on stable long-running scripts
- Per-class log levels complicate this — function replacement is global,
  but per-class checks happen inside `__boop.log`. Consider whether
  the bypass applies only when the GLOBAL level silences a tier (per-class
  overrides can still route through the real function).

---

## Per-Class Work

---

### boop (root class)

- **`setOn` coverage**: method exists, test coverage unclear
- **`boop_install` bootstrap script**: puts boop on PATH, generates
  initial `.boopIndex`, creates starter `~/.booprc`. See Classpath
  section for full spec.
- **`boop.inspect`**: pretty-print an object's full state for debugging.
  Should show class, inheritance chain, all properties with current
  values, and method list. Registered on root `boop` class so every
  object inherits it. Tier 3 public, output to stdout by default.
  ```
  [Box _abc123]
    class:  Box (extends boop)
    length: 5
    width:  3
    height: 7
    methods: new, volume, area, top, side, front, toString
  ```
- **Scaffolding (`boop new MyClass`)**: generate a class file skeleton
  from a template. Could live as a subcommand on the `boop` root class
  or as a standalone `boop_new` script. Output is a ready-to-edit file
  with load guard, boopClass declaration, and stub `.new()`. High
  friction reducer for new users.

---

### Math

Math uses chunked arbitrary-precision arithmetic entirely in bash —
no forks, no subshells, no external tools. 9 digits per chunk, base
10^9, fits in int64. `printf -v` for all string formatting.
All returns via nameref. See `Math/Math` header for algorithm notes.

- **Input validation on public API**: `Math.add`, `Math.subtract`,
  etc. accept garbage strings without complaint — error surfaces deep
  in `__Math.toInt64` as a cryptic `10#` bash arithmetic error.
  Validation belongs in `__Math.resolve` (single chokepoint). After
  parsing, verify digits are all-digit; crash with helpful message.

- **Variadic public methods**: `Math.add 1 2 3 4` should sum all
  args. `Math.add 5` (single arg) should return identity. Same for
  `mul`. Currently requires exactly two operands.

- **Output format modes**: scientific notation (`3.14e10`), engineering
  notation, fixed decimal places. Currently outputs raw digit string
  with implicit decimal position. Needs a `Math.format` or `format=`
  typecast option on results.

- **`Math::Trig` submodule**: `sin`, `cos`, `tan`, `asin`, `acos`,
  `atan`, `atan2`. Already have `arctan` series internally (used for
  pi). Expose as a loadable submodule. No forks — same digit-math
  approach as `pi`.

- **`Math::Stats` submodule**: `mean`, `median`, `stddev`, `variance`,
  `min`, `max`, `sum`. Operates on List or array of Math objects.

---

### Collection (Container, List, Map, Iterator)

- **Iterator stability after mutation**: behavior when the underlying
  container is modified during iteration is undefined. Document the
  contract or enforce it (crash on structural modification).

- **Container test coverage audit**: 23 methods — valid usage,
  expected failures, garbage inputs. See Test Coverage Audit section.

- **List**: 15 methods — coverage audit. `insertAt`/`removeAt`
  needed for LinkedList compatibility.

- **Map**: 12 methods — coverage audit. Insertion-order guarantee
  should be documented explicitly (currently relies on bash 4.0+
  associative array ordering, which is NOT insertion-ordered —
  verify this is handled correctly).

---

### String (Phase 3)

Minimum useful interface, all in pure bash parameter expansion —
no forks, no subshells:

`trim`, `split`, `join`, `contains`, `startsWith`, `endsWith`,
`replace`, `replaceAll`, `length`, `toUpper`, `toLower`, `substring`,
`indexOf`, `padLeft`, `padRight`.

Heavy string work is already happening natively everywhere. A class
wrapper gives callers a consistent interface and makes complex string
pipelines readable.

---

### Games (Card, PlayingCard, Deck, Blackjack)

- **`test_blackjack` coverage**: test file exists but coverage depth
  unknown. Audit against all public methods.
- **Blackjack**: lives in `Games/Blackjack/` namespace. Hand scoring,
  soft/hard ace logic, split/double-down, dealer AI — currently
  all in the script. Consider whether any logic belongs in
  `BlackjackHand` class.

---

### Geometry (Box, Cube)

- **Box/Cube**: 91 tests passing, coverage looks solid. No known
  gaps. Revisit when new geometry classes are added.

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


## Return System: Default to stdout + Newline Control ✓

✓ `auto` mode now always outputs to stdout. `_Out` global still
available via explicit `_OutMode=global`. All `test_stress_ts` call
sites updated to use `into=varname` or `$()` capture.

`into=` always wins regardless of mode. The mode only matters when
no explicit target is given.

### `into=` in Subshells — Known Silent Footgun

`into=varname $obj.method` inside a subshell silently loses the
value: the nameref write succeeds into the subshell's scope, stdout
is suppressed (nameref path returns early), and the value evaporates
when the subshell exits. No crash, no warning.

A blanket `_Warn` for "into= in subshell" would false-positive on
legitimate patterns (e.g., using `into=` inside a subshell to chain
intermediate calls before `printf`-ing the result out). Left as a
documentation note. The safe idioms are:

```bash
# Option 1: into= for intermediate work, printf the final result
result=$( into=tmp $obj.compute; printf "%s" "$tmp" )

# Option 2: subshell capture of stdout directly
result=$( $obj.compute )
```

### Per-Class / Per-Namespace Output Mode

Consider per-class output mode overrides, same pattern as the log
level system: global default, per-class overrides via an associative
array, inheritance through the class chain, cached resolution.

Use case: a CLI utility class might want stdout by default, while
a library class wants global. The class author sets the default,
the user can override per-class or globally.

### `into=` Forwarding Through Dispatchers ✓

✓ `_Delegate`, `_Super`, and `_Cast` now explicitly forward
`into="${into:-}"` to inner calls. Three new tests in
`test_stress_ts` cover the indirect forwarding case (outer caller
sets `into=`, inner method dispatches without its own `into=`).

---

## Implicit Object Declaration on Return (`_AS=`)

Explore whether `boop.pass` could auto-wrap a return value as an
object of a specified class. The caller would declare the desired
type inline:

```bash
into=o _AS=List boop.classPath list
$o.length    # → number of entries
$o.each ...  # iterate as a List
```

This would let any method that returns a multi-value string
(newline-delimited, etc.) hand back a typed object instead of a
raw string — without the callee knowing or caring about the
wrapping.

Open questions:
- Does `boop.pass` handle the wrapping, or does the caller's
  `into=` assignment trigger it?
- Performance cost of creating an object on every return?
- What if the class isn't loaded yet — auto-import?
- Is this just sugar for `into=raw method; into=o List "$raw"`?

Might not be worth the complexity. Investigate and decide.

---

## Try/Catch Mechanism -- Low Priority

Bash has no native try/catch. Every approach has serious tradeoffs:

- **Subshell**: clean isolation, but loses all side effects (variable
  mutations, registry changes, object creation). Dealbreaker for a
  framework built on global state.
- **eval + trap ERR**: side effects survive, but the try block is
  either a string (eval, gross) or a function name. `_Crash` would
  need to know it's inside a try context and `return` instead of
  `exit`. Unwinding the call stack requires either `set -e` behavior
  or every function checking a try-depth flag. Fragile.
- **Signal-based**: `_Crash` sends USR1, try wrapper traps it. But
  bash signal delivery is unpredictable -- only between commands,
  not mid-builtin.

Conclusion: the cure is worse than the disease. Developers should
handle errors explicitly with exit codes and `_Crash`. The fatality
threshold (`_FatalLevel`) already provides escalation control.

Revisit if a compelling use case emerges that can't be solved with
explicit error handling.

---

## Codebase Audit — Refactor & Tune Candidates (2026-04-26)

Walk-through of the framework + class files looking for the same
shape of issue that motivated the API Shape steering rule (see
`.kiro/steering/api-shape.md`, `docs/STANDARDS.md`, and
`docs/bash_style.md`). Findings grouped by severity. None of these
are urgent; the suite is green and the hot paths that matter most
(Math, dispatch) are already heavily optimized.

### A. Apply the new "Primitives Inward" rule elsewhere

#### A1. `Config.load` (flat) — symmetric `fromFlatString` ✓ DONE

**File:** `Config/Config:42-70`

`Config.load` is the flat `key=value` analogue of `Config.loadINI`,
but there is no `Config.fromFlatString`. The same extract-a-private-
parser refactor we just applied to `loadINI`/`fromString` should
apply here:

- Extract `__Config.parseFlat <self>` reading lines from stdin.
- `Config.load <file>` → `__Config.parseFlat $self < "$file"`.
- New `Config.fromFlatString <str>` → `__Config.parseFlat $self <<< "$str"`.

Tiny PR. Mostly mechanical. Lock in the principle by demonstrating
it across both formats.

#### A2. `Map.values` / `Map.toArray` / `Map.toString` — single-printf serialization

**File:** `Collection/Map/Map:163-220`

`List.toArray` (`List:302-314`) builds its delimited output with one
`printf -v out "%s${d}" "${arr[@]}"` then trims the trailing
delimiter — clean, fast, idiomatic. `Map.values` and `Map.toArray`
instead loop with a `(( first ))` guard and N concatenations:

```bash
# Map.values today — N concatenations
for k in "${keys[@]}"; do
  (( first )) || out="${out}${d}"
  out="$out${arr[$k]}"
  first=0
done
```

`Map.values` is a direct port of `List.toArray` (just walking
ordered-keys → values). `Map.toArray` and `Map.toString` need a
small intermediate step (build the `key=value` / `k="v"` strings
into a temp array first, then one `printf -v`).

Same shape applies to `Map.toString` and the per-iteration
concatenation in `Map.each`'s siblings. Worth a small unification
pass.

#### A3. `TestSuite.exec` — lazy stderr capture

**File:** `Testing/TestSuite/TestSuite:68-97`

`exec ok` and `exec fail` both fork `mktemp`, redirect stderr to
the tmpfile, then `rm -f` it after — for *every* assertion. The
captured stderr is only read when `_Debug` is enabled and the
file is non-empty:

```bash
local __TS_exec_stderr; __TS_exec_stderr=$(mktemp)
if _Self="" _Class="" "$@" 2>"$__TS_exec_stderr"; then ...
[[ -s "$__TS_exec_stderr" ]] && _Debug "$(<"$__TS_exec_stderr")"
rm -f "$__TS_exec_stderr"
```

Costs: `mktemp` fork, file create, redirect, file read, fork+rm —
per assertion. With 1000+ assertions across the suite this is the
single biggest fork count in test runs.

Options:
- **Lazy**: only redirect to tmpfile when `__boop_logLevel` is at
  `DEBUG` or above. In the common case (quiet runs), redirect
  stderr to `/dev/null` and skip the tmpfile dance entirely.
- **Process substitution**: `2> >(... capture ...)` — but bash
  process subst can race with the parent reading state.
- **Var capture**: `{ stderr=$(cmd 2>&1 1>&3); } 3>&1` — captures
  stderr to a variable directly, no tmpfile. Standard idiom.

The var-capture form is cleanest; it forks a subshell for the
capture but no disk I/O. For a test runner the disk-I/O is the
expensive part on Windows/Git Bash where syscalls are slow.

### B. Hot-path candidates (deeper investigation)

#### B1. `__boop.parse` — descriptor regex on every property read

**File:** `boop:694-707`

Every property read (`$obj.get foo`, every internal `__boop.parse
"$class" "parent"` during MRO walks, every `Container.toString`
fetching `type`) runs:

```bash
local pattern="\\|${field}=([^|]*)"
[[ "$descriptor" =~ $pattern ]]
```

That's a regex compile + match against the full descriptor string,
every time. For a deeply nested `deepGet` walk
(`Collection/Container/Container:246-257`) it's once per level.

Two possible approaches:
1. **Cache parsed descriptors** at registration time into
   per-field associative arrays: `__boop_field_<class>_<field>`.
   Property reads become an O(1) array lookup. One-time cost at
   `registerClass`; pays off forever after.
2. **Cache parsed instance descriptors** lazily on first property
   access — same idea but per-instance instead of per-class.

This is core architecture, not a small change. Profile first to
confirm `__boop.parse` is actually a hotspot before doing the
work; the regex is fast in absolute terms, just runs frequently.

#### B2. `Map.delete` — O(n) array rebuild

**File:** `Collection/Map/Map:90-107`

```bash
Map.delete() {
  unset "__Map_del_arr[$key]"
  local -a __Map_del_new=()
  for k in "${keys[@]}"; do
    [[ "$k" != "$key" ]] && __Map_del_new+=("$k")
  done
  __Map_del_keys=("${__Map_del_new[@]+...}")
}
```

For workloads with many deletes on a large Map this is O(n) per
delete, O(n²) for clear-by-deletion. Bash arrays don't support
efficient mid-array splice, so the fundamental cost is hard to
escape, but:

- Tracking key→position in a companion assoc array makes the
  search O(1); the splice is still O(n) but skips the linear
  scan.
- Tombstone deletion (mark removed, compact lazily) trades
  memory for speed. Probably overkill.

Document the cost in the method header; flag for revisit if a
real workload hits it.

### C. Dead code

#### C1. `__boop.dispatch` — large commented-out function

**File:** `boop:769-801`

~33 lines of commented-out function body with a doc-block above it
explaining what the *replacement* (direct call-through via baked
wrappers) does. The comment block above is useful; the carcass
below is just noise. Delete the body, keep the explanatory comment
about why dispatch is no longer the primary call path.

#### C2. `Container.toString` pretty-print branch is broken *and* dead

**File:** `Collection/Container/Container:223-240`

Line 237 has `printf -v var "format" <newline> args` with no
backslash continuation:

```bash
  printf -v __Container_ts_out "%s(%s) {\n  type   = %s\n  length = %s\n}" 
    "$_Class" "$_Self" "$__Container_ts_type" "$__Container_ts_len"
```

Bash parses these as two separate commands — the second line would
try to *execute* `$_Class` with the rest as args. The branch
doesn't blow up because every concrete subclass (`List`, `Map`)
overrides `toString` and the branch is never reached on a raw
`Container`. But it's a latent bug: if anyone ever calls
`$container.toString pretty` on something that inherits without
overriding, it breaks.

Two fixes in one: add the `\`, and add a test for raw-Container
pretty so this is no longer dead code path.

### D. Known fragility (already commented in source)

#### D1. `TestSuite._route` — pipe-delimited arg packing in queue mode

**File:** `Testing/TestSuite/TestSuite:122-132`

Existing comment: `# @@ pipe-delimited args are fragile if args
contain literal pipes.` Queue mode is rarely used (immediate is
the default), but the issue is real. Two paths:

- Use a delimiter known not to occur in args (e.g., `$'\x1f'` —
  ASCII Unit Separator). Cheap, mostly fixes it.
- Store args in a List instead of a packed string. More objects
  per assertion, but no encoding fragility. List is already a
  Container, so this fits the framework.

The List route is the principled answer; the delimiter swap is
the 1-line "good enough."

### Priority Stack

If picking these up, suggested order:

1. ~~**A1** (Config.fromFlatString) — locks in the API-shape rule.~~ ✓ DONE
2. **C1** (delete dead `__boop.dispatch` body) — pure cleanup, no risk.
3. **C2** (fix Container.toString pretty + test) — latent bug.
4. **A3** (lazy stderr in TestSuite.exec) — biggest wall-clock win.
5. **A2** (Map serializer cleanup) — small, mostly cosmetic.
6. **D1** (TestSuite._route arg encoding) — only matters if queue
   mode gets real use.
7. **B1** / **B2** — measure first; defer until there's evidence
   the cost matters in a real workload.
