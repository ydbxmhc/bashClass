# boop — The Framework

An OOP dispatch system for bash 4.3+. Classes, objects, inheritance, method
resolution, property accessors, type checking, value encoding, serialization,
and a universal return handler — all built on associative arrays and naming
conventions. No external dependencies. No subshells in the hot path. No
apologies.

> **NUL bytes.** Bash variables cannot hold or detect NUL bytes. Any value
> containing a NUL will be silently truncated at the first one — no error,
> no warning. This applies to all object properties, map keys and values,
> and anything else stored in a bash variable. See [GOTCHAS.md](GOTCHAS.md).

The framework file is called `boop` because life is too short for
`bash_object_oriented_programming_framework.sh`. The internal namespace
is `__boop_*` — the filename is the personality, the internals are
the plumbing.

## Requirements

- bash 4.3+ (associative arrays, namerefs)
- That's it. Seriously.

macOS ships bash 3.2 (thanks, GPL3). `brew install bash` fixes that.
If your users might be on macOS, tell them up front.

---

## Loading the Framework

```bash
# Load framework only
. boop

# Load framework + import classes (the common case)
. boop Cube Math

# Namespace syntax — :: maps to / on disk
. boop Collection::Map Config Args

# Classes declare their own dependencies; this:
. boop Cube
# ...automatically loads Geometry::Box (Cube's parent).
```

The framework loads once. Re-sourcing `. boop` skips all definitions
(guarded by `__boop_loaded`) and only processes import arguments.
Class files can safely do `. boop SomeDependency` at their top without
re-executing the framework.

---

## The Five-Minute Tour

```bash
. boop Geometry::Cube Math Collection::Map

# Create objects
into=c Cube size=4 unit=cm
into=m Math 3.14
into=mp Map

# Call methods
into=vol $c.volume          # vol="64"
into=v   $m.val             # v="3.14"
$mp.set host localhost
$mp.set port 5432
into=h $mp.get host         # h="localhost"

# Type checking walks the inheritance chain
$c.isa Cube && printf "yes\n"   # yes
$c.isa Box  && printf "yes\n"   # yes (Cube inherits Box)
$c.isa Map  && printf "nope\n"  # (silence — returns 1)

# Display
into=s $c.toString pretty
printf "%s\n" "$s"
# Geometry.Cube(__obj_01) {
#   size   = 4
#   unit   = cm
#   ...
# }

# Deep dive — full property and inheritance chain
$c.inspect
# [Geometry.Cube __obj_01]
#   class:   Geometry.Cube extends Geometry.Box extends boop
#   size     = 4
#   length   = 4
#   width    = 4
#   height   = 4
#   unit     = cm
#   methods: new, side, top, end, bottom, volume, calc, area, get, set, ...
```

Short names (`Cube`, `Map`) work immediately after loading because the
framework auto-aliases them when the class is registered. Details in
[Fully Qualified Names & Aliases](#fully-qualified-names--aliases).

---

## Getting Values Back: The Return System

This is the part that makes boop feel different from "just bash functions."
Every value-producing function in the framework routes through a single
return handler (`boop.pass`). You choose how to receive the value.

### `into=` — The Recommended Way

```bash
into=vol $cube.volume           # vol="64" — direct, no subshell
into=name $map.get "host"       # name="localhost"
into=pi Math.pi 20              # pi is a Math object
into=v $pi.val                  # v="3.14159265358979323846"
```

`into=varname` creates a nameref binding. The value is written directly
into your variable — zero-copy, no subshell, no `$_Out` write.
This is the fast path and the one you should use almost everywhere.

### Just Print It

```bash
# Grab it, then print it
into=vol $cube.volume
printf "%s\n" "$vol"            # 64

# Force stdout mode for one call — prints directly, no variable needed
_OutMode=stdout $cube.volume

# Alias makes it readable
alias show='_OutMode=stdout'
show $cube.volume               # same thing

# Write to $_Out — use _OutMode=global
_OutMode=global $cube.volume
printf "%s\n" "$_Out"

# Subshell capture — classic bash, works anywhere
printf "Volume: %s\n" "$( $cube.volume )"
```

### Subshell Capture

```bash
vol=$( $cube.volume )           # works, but forks a subshell
```

The framework detects subshells (via `BASHPID` vs the root PID captured
at load time) and automatically switches to stdout mode inside them. It
works, but every `$()` is a fork. Fine once; in a loop it adds up.

Subshell capture enables one-liner chaining through nested objects,
which `into=` can't do in a single expression:

```bash
# Subshell chain — one line, but forks at every level
val=$( $( $matrix.get 0 ).get 1 )

# into= equivalent — no forks, but two lines
into=row $matrix.get 0
into=val $row.get 1
```

For nested containers, `itemAt` is the best of both worlds:

```bash
into=val $matrix.itemAt 0 1     # one line, zero forks
```

### Write to `$_Out`

```bash
_OutMode=global $cube.volume
printf "%s\n" "$_Out"           # "64"
```

`global` mode writes to `$_Out` instead of stdout. A single flat
global — the next call overwrites it. Fine for quick one-offs, but
`into=` is safer.

### Explicit Mode Override

```bash
_OutMode=stdout $cube.volume    # force stdout
_OutMode=global $cube.volume    # force $\_Out
```

Modes: `auto` (default), `global`, `reply`, `stdout`, `nameref`, `filesystem`.
`auto` is always stdout — use `global` to write to `$_Out` instead.

```bash
_OutMode stdout    # change the process default
```

### Output Formatting: `_EOL` and `_Delimiter`

Two variables control how values are formatted when returned:

```bash
# _EOL — appended after each value in stdout mode (default: newline)
_EOL=$'\n'       # default — newline after each value
_EOL=""          # raw — no trailing newline (pipe-friendly)

# _Delimiter — separator for multi-value returns (default: $_EOL)
into=keys $map.keys             # keys="host\nport\n..." (newline-separated)

_Delimiter=$'\t' into=keys $map.keys   # tab-separated for this one call
_Delimiter='|'   into=all  $list.toArray
```

`_Delimiter` is used by `Map.keys`, `Map.values`, `Map.toArray`,
`List.toArray`, `List.slice`, `Config.keys`, `Config.sections`, and any
other method that joins multiple values into a single string. It defaults
to `_EOL` when not set, so the common case (newline-separated) requires
no configuration.

Set `_Delimiter` per-call via environment prefix, or set it globally
for a pipeline stage.

---

## Creating Objects

Two equivalent syntaxes:

```bash
# Class-as-constructor (most common)
into=b Box length=5 width=3 height=7

# Explicit `new` keyword
into=b new Box length=5 width=3 height=7
```

Constructor arguments are `key=value` pairs. Values are stored in
`__boop_static` keyed by object ID. The object gets a unique ID from a
global counter (`__obj_01`, `__obj_02`, ...) — no subshell, no clock.

After construction, the object has a direct wrapper function for every
method in its class and all ancestor classes. Each wrapper is a one-hop
call: `$obj.method` → `objid.method` → `ClassName.method` — no dispatch
overhead on any call after creation.

---

## Destroying Objects

Every object inherits `destroy` from `boop`. It's the symmetric inverse
of construction — tears down everything that `new` and class-level
initialization built:

```bash
into=m Map
$m.set host localhost
$m.set port 5432
# ... use it ...
$m.destroy                    # gone — registry, static keys, wrappers, companion arrays
```

After `destroy`, the object ID is dead. Calling any method on it fails
with "command not found" (the wrapper functions are unset). Holding a
stale ID is the caller's problem — same as a dangling pointer.

### When to Use It

- **Long-running shells** — objects accumulate without bound otherwise.
- **Loops that create objects** — destroy at the end of each iteration.
- **Interactive sessions** — clean up scratch objects.
- **Scripts that manage resources** — Stream objects hold open FDs,
  temp-file wrappers hold disk state.

Short-lived scripts can ignore it entirely. The process exits and the
OS reclaims everything.

### What It Does (Execution Order)

1. **Class-level `_destroy` hook** — if the class defines a private
   `ClassName._destroy()` function, it's called first. This is where
   classes clean up companion arrays, close file descriptors, destroy
   owned child objects, or remove temp files. The hook is walked up the
   inheritance chain (most-derived first), so each ancestor cleans up
   what it allocated.

2. **Wipe `__boop_static` keys** — every key prefixed with the object
   ID is removed.

3. **Unset wrapper functions** — all functions named `${objId}.*` are
   removed via `compgen -A function`.

4. **Remove registry entry** — the object ID becomes unresolvable.

### Writing a `_destroy` Hook

If your class allocates companion arrays or external resources in its
constructor, write a `_destroy` function. It's a private convention —
not registered as a method, not in the `public:` list:

```bash
# In your class file, after the method implementations:
MyClass._destroy() {
  local _Self="${_Self:-}" _Class="${_Class:-MyClass}"
  unset "__boop_data_${_Self}"          # companion array
  rm -f "${__boop_static[${_Self}.tmpfile]:-}"  # temp file, if any
}

# The boopClass declaration does NOT mention _destroy:
boopClass MyClass has:... public:new,...
```

The core finds it via `declare -F ClassName._destroy` during teardown.
If your class doesn't allocate anything beyond properties, you don't
need a hook — the core cleanup handles `__boop_static` and wrappers.

### Cascading Destruction

If your class owns child objects (like [Stack](Stack) owns a [List](List)), destroy them
in your `_destroy` hook:

```bash
Collection.Stack._destroy() {
  local _Self="${_Self:-}" _Class="${_Class:-Collection.Stack}"
  local -n __ref="__Collection_Stack_list_${_Self}"
  # Destroy the owned List
  if [[ -n "$__ref" && -n "${__boop_registry[$__ref]+set}" ]]; then
    _Self="$__ref" _Class=Collection.List __boop.destroy
  fi
  unset "__Collection_Stack_list_${_Self}"
}
```

### Double-Destroy

Calling `$obj.destroy` twice crashes on the second call — the registry
check at the top of `__boop.destroy` rejects unknown IDs. This is
intentional: double-free is a logic error, not a no-op.

---

## Properties: Get and Set

Every object inherits `get` and `set` from `boop`:

```bash
into=b Box length=5 width=3 height=7

into=len $b.get "length"        # len="5"
$b.set "color" "red"
into=c $b.get "color"           # c="red"
```

### Property Shorthand

When a class declares properties in its `boopClass` declaration, objects
get dual-purpose accessor stubs:

```bash
# These are equivalent:
into=len $b.get "length"
into=len $b.length              # shorthand — no args = get

# Set via shorthand:
$b.length 10                    # one arg = set
```

### Value Storage

Properties are stored in `__boop_static` as `"objectId.propName"` keys —
plain associative array entries, no encoding. Bash associative arrays can
hold arbitrary strings (except NUL bytes), so values are stored verbatim:

```bash
$b.set "notes" "width=3|height=7"
into=n $b.get "notes"           # n="width=3|height=7" (clean)
```

---

## Type Checking: `isa` and `trueClass`

```bash
$cube.isa Cube      && printf "yes\n"   # 0 (true)
$cube.isa Box       && printf "yes\n"   # 0 (true — inherits)
$cube.isa boop      && printf "yes\n"   # 0 (true — everything does)
$cube.isa Map       || printf "nope\n"  # 1 (false)
```

`isa` with an argument walks the inheritance chain and returns an exit
code (0=true, 1=false). It handles aliases correctly: `$obj.isa Fast`
passes if the object is an instance of `Collection.Map.Fast`, even if
you loaded it under a short alias.

```bash
# trueClass — returns the FQN of the object's class
into=fqn $cube.trueClass        # fqn="Geometry.Cube"

into=fm Fast
into=fqn $fm.trueClass          # fqn="Collection.Map.Fast"
```

`trueClass` is the unambiguous version. `isa` with no argument also
returns the FQN (they're equivalent), but `$obj.trueClass` reads more
clearly when that's your intent.

---

## Display: `toString` and `inspect`

### `toString` — User-Facing Representation

```bash
# Compact (default)
into=s $b.toString
# Geometry.Box(__obj_01){ length=5 width=3 height=7 unit= color= }

# Pretty — columnar with alignment
into=s $b.toString pretty
# Geometry.Box(__obj_01) {
#   length = 5
#   width  = 3
#   height = 7
#   unit   = 
#   color  = 
# }
```

Internal metadata (`class`, `parent`, `methods`, `properties`, `trueClass`)
is hidden. Only user-defined properties show up. [Container](Container) subclasses
(List, [Map](Map)) override `toString` to show their contents.

### `inspect` — Debug View

```bash
$obj.inspect              # always prints to stdout — pipe it, page it
$obj.inspect | less
```

`inspect` shows everything `toString` hides. You get the full
inheritance chain, every property including internal ones (decoded),
and the complete method list gathered from the entire ancestry:

```
[Geometry.Cube __obj_01]
  class:   Geometry.Cube extends Geometry.Box extends boop
  size     = 4
  length   = 4
  width    = 4
  height   = 4
  unit     = cm
  methods: new, side, top, end, bottom, volume, calc, area, get, set, isa, toString, inspect, super
```

This is your first stop when something isn't dispatching the way you
expect, or when you want to verify that properties landed correctly.

---

## Inheritance

Classes form a single-inheritance chain. Every class ultimately inherits
from `boop`, which provides `get`, `set`, `isa`, `toString`, `inspect`,
`new`, and `super`.

### Method Resolution Order (MRO)

When you call `$cube.volume`, the framework:

1. Checks the method registry for `Cube.volume` (O(1) hash lookup).
2. On cache miss, walks the parent chain: Cube → Box → boop.
3. When found (say, in Box), caches it as `Cube.volume` so the walk
   never happens again for that class+method pair.

After the first call, a baked wrapper replaces the stub — subsequent
calls go directly to the implementation function with zero dispatch
overhead.

### Dispatch Helpers

Four helpers cover the common dispatch scenarios:

#### `_Super` — Same Object, Parent Class

Call the parent's implementation of the current method. The most common
use is in overridden methods that need to extend (not replace) the base:

```bash
Cube.new() {
  local _Class="${_Class:-Cube}"
  local __Cube_new_self
  # Set up cube-specific defaults, then hand off to parent
  into=__Cube_new_self _Super new size="$size" length="$size" "$@"
  boop.pass "$__Cube_new_self" ${into:-}
}
```

`_Super method [args...]` — walks up one level in the MRO from the
current `_Class`. Crashes if already at the root (boop has no parent).

#### `_Delegate` — Different Object, Clean Context

Call a method on another object with a clean class context. Prevents
`_Class` from leaking across object boundaries:

```bash
# Without _Delegate, the ambient _Class leaks into $other's method call.
# With _Delegate, the class context is cleared so dispatch resolves fresh.
_Delegate $other.someMethod arg1 arg2
into=result _Delegate $other.compute value
```

Under the hood: `_Delegate` sets `_Class=""` before forwarding. This
ensures that if `$other` is a Map, dispatch resolves against Map's MRO,
not whatever class is currently active.

#### `_Cast` — Same Object, Explicit Class

Force dispatch against a specific class in the inheritance chain. Useful
when you know exactly which ancestor's implementation you want:

```bash
# Dispatch $cube's `volume` against Box's implementation,
# bypassing Cube's override:
into=v _Cast Box $cube volume
```

Signature: `_Cast ClassName $obj method [args...]`

This is a power-user escape hatch. Prefer `_Super` in most cases.

#### `_Bless` — Runtime Re-Classification

Stamp an existing object with a new class, regenerating all method and
property wrappers. The nuclear option for runtime type mutation:

```bash
# Reclassify an object in place
_Bless $obj NewClassName
$obj.someNewMethod    # now dispatches against NewClassName
```

`_Bless` rewrites the `class` field in the descriptor and force-regenerates
every wrapper. It checks that `$obj` is actually an object (not a class)
and that `NewClassName` is a registered class. Use sparingly — it's
correct but surprising to readers.

### Typecasting via Environment Prefix

For one-off overrides without helpers:

```bash
# Normal: dispatches to Cube.volume
into=v $cube.volume

# Typecast: dispatches to Box.volume instead
into=v _Class=Box $cube.volume
```

The baked wrapper handles three cases:

1. Exact match (or no ambient class) — fast path, direct call.
2. Family member (ambient class is an ancestor) — legitimate typecast,
   falls back to full dispatch for correct MRO resolution.
3. Unrelated class (mismatched ambient `_Class`) — emits a `_Warn`
   diagnostic and uses the baked class.

---

## Fully Qualified Names & Aliases

Classes live in namespace directories. A class's Fully Qualified Name
(FQN) is its namespace path, dot-separated:

```
Collection/Map/Fast   →   Collection.Map.Fast
Geometry/Cube         →   Geometry.Cube
Testing/TestSuite     →   Testing.TestSuite
```

When you load a class, the framework automatically creates aliases at
each suffix level (controlled by `_AutoAlias`). For `Collection.Map.Fast`:

| Alias | Works? | Notes |
|-------|--------|-------|
| `Collection.Map.Fast` | always | FQN itself |
| `Map.Fast` | if unambiguous | intermediate alias |
| `Fast` | if unambiguous | short alias |

All three can be used interchangeably:

```bash
. boop Collection::Map::Fast

into=fm  Fast          # via short alias
into=fm  Map.Fast      # via intermediate alias
into=fm  Collection.Map.Fast  # via FQN
```

The `isa` method resolves aliases through the `trueClass` field, so type
checks always work regardless of which name you used.

### `_AutoAlias`

```bash
_AutoAlias=full     # alias all suffix levels (default)
_AutoAlias=best     # alias shortest unique level + FQN
_AutoAlias=short    # alias only the short name + FQN
_AutoAlias=none     # no auto-aliasing — only explicit _Import creates aliases
```

If two loaded classes share the same short name (say, `Collection.Map`
and `Data.Map`), the short alias `Map` is ambiguous. In `full` mode an
info message is logged and the alias is skipped — you must use a longer
form or an explicit alias. In `best` mode only the first loaded wins
the short alias.

### `trueClass`

Every object stores its `trueClass` — the FQN of the class it was
actually constructed from — in its descriptor. Aliases always resolve
back to the FQN for type-checking and dispatch. A `_Class` of `Fast`
and a `_Class` of `Collection.Map.Fast` are treated identically by the
dispatch engine.

---

## The Import System

### Loading Classes

Three entry points with different failure behavior:

```bash
# _Require — fatal. Crashes if the class can't be loaded.
# Use for hard dependencies your script cannot run without.
_Require Config
_Require Math Config List    # crashes if any fail

# _Load — non-fatal. Returns 0/1. Use for optional features.
_Load Math || printf "precision math unavailable\n"
if _Load Args; then
  Args.parse "$SCHEMA" "$@"
fi

# _Import — like _Require, but also creates a named alias.
# Use when you want a short or custom name for a namespaced class.
_Import Collection::Map::Fast              # load + auto-alias
_Import Collection::Map::Fast as FastMap   # load + explicit alias "FastMap"
_Import Games::PlayingCard  as Card        # collides with Games::Card? name it explicitly
```

Both `_Load` and `_Require` accept multiple class names. `_Load`
returns 0 only if all names succeed.

The `. boop ClassName` syntax at the top of a script uses `_Require`
internally, so it crashes on failure — by design, since a script that
can't load its classes can't run.

### Framework Version Guard

Scripts can declare a minimum boop version as an argument to the source line:

```bash
. boop require:1.2+          # crash if running boop < 1.2.0
. boop require:>=1.1.0       # explicit form; same semantics
. boop require:1.2+ List Map # version guard and class loads in one line
```

The `require:` token is processed before any class loads. If the running boop
does not satisfy the constraint, boop searches `BOOPPATH` and `PATH` for a
compatible version, includes its path in the crash message if found, and
crashes either way. There is no silent degradation.

This check uses comparison logic inlined in boop core — it does not depend on
the SemVer class and fires during framework initialization before any class
can be loaded. See [docs/SemVer.md](SemVer.md) for the constraint syntax and
architecture.

### Class Version Declarations

A class can declare its version in the `boopClass` statement:

```bash
boopClass Math version:1.3.0 '
  public:add,subtract,...
'
```

The version is stored in the registry descriptor and accessible to `_Require`
for constraint checking:

```bash
_Require Math 1.2+           # load Math; crash if its declared version < 1.2.0
```

A version argument to `_Require` is any token starting with a digit, `>`, or
`<`, or ending with `+`. Class names start with uppercase, so there is no
ambiguity.

**Class version enforcement requires SemVer to be loaded.** If SemVer is not
in the registry when `_Require` checks a class version, it warns and
continues. Load SemVer before any versioned `_Require` call:

```bash
. boop SemVer Math 1.2+      # SemVer loads first; Math version is enforced
```

See [docs/SemVer.md](SemVer.md) for the full version system documentation.

### `.boopIndex` and the Namespace Index

Classes are organized in namespace directories. Each library root
contains a `.boopIndex` file that maps short names to their namespace
paths. The framework sources `.boopIndex` from each root during
initialization:

```bash
# .boopIndex (auto-generated by: boop.classPath rebuild .)
declare -gA __boop_Index=(
  [Math]="Math"
  [Cube]="Geometry/Cube"
  [Box]="Geometry/Box"
  [Map]="Collection/Map"
  [List]="Collection/List"
  [Container]="Collection/Container"
  [Fast]="Collection/Map/Fast"
  [Config]="Config"
  [Args]="Args"
  [TestSuite]="Testing/TestSuite"
  ...
)
```

Resolution order (first match wins):

1. `__boop_classPath` — explicit path overrides
2. `__boop_Index` — short-name index, resolved per root
3. Dynamic discovery — scan each root (`.` + BOOPPATH + PATH)
4. Raw source fallback — `. "$class"` (lets bash try PATH directly)

```bash
# Register a custom path override
boop.classPath set MyClass /opt/lib/MyClass
. boop MyClass    # loads from /opt/lib/MyClass

# Regenerate .boopIndex after adding/renaming classes
boop.classPath rebuild .

# Show effective root list
boop.classPath dirs

# Namespace import via :: syntax
. boop Collection::List   # :: maps to / on disk
```

### Load Guards and Circular Prevention

Two layers prevent double-loading and circular recursion:

- **Registry check**: If `__boop_registry[ClassName]` is already set,
  `boop.init ClassName || return 0` exits immediately.
- **Loading flag**: `__boop_loading[ClassName]` is set while a class
  file is being sourced. Re-entry for the same class skips it.

This prevents infinite recursion in chains like:
`Cube → . boop Box → Box → . boop → boop re-imports Box`.

### RC Files

During bootstrap, boop sources:

1. `/etc/booprc` — system-wide config
2. `~/.booprc` — user config
3. `./.booprc` — project-local config

RC files can set `_AutoAlias`, `_OutMode`, `_LogLevel`, add roots to
`BOOPPATH`, or register custom class paths.

---

## Writing a Class

### `boopClass`

`boopClass` declares a class in a single call. It builds the registry
descriptor, registers all methods, finalizes the class, and runs
auto-aliasing. This replaces the manual three-step pattern entirely.

Here's `Config` — a real class in the project:

```bash
#!/bin/bash

. boop

boop.init Config || return 0

# ... method implementations ...

Config.get() {
  local _Class="${_Class:-Config}" _Self="${_Self:-}"
  local __Config_get_key="$1"
  local -n __Config_get_data="__boop_config_${_Self}"
  boop.pass "${__Config_get_data[$__Config_get_key]:-}" ${into:-}
}

Config.set() { ... }
Config.has() { ... }
# ... etc ...

boopClass Config has:file,format '
  public:new,load,loadINI,fromString,get,set,has,keys,sections,save,toFlat,toINI
'
```

The declaration at the bottom:

```bash
boopClass ClassName [isa:Parent] [has:prop1,prop2] [public:method1,method2] [custom:method=impl,...]
```

- **`isa:Parent`** — parent class (default: `boop`)
- **`has:p1,p2`** — property names (get/set shorthand stubs)
- **`public:m1,m2`** — methods where the implementing function is
  `ClassName.methodName` (the convention). Registers them automatically.
- **`custom:m=fn`** — methods where the implementing function has a
  non-standard name (e.g., internal helpers or mixins)

Tokens can appear in any order, across multiple lines or arguments:

```bash
boopClass Math isa:boop \
  has:digits,scale,neg \
  public:new,eq,lt,gt,le,ge,cmp,round,toInt,toScale,format,val,toString,isZero \
  custom:add=__Math.i_add,sub=__Math.i_sub,mul=__Math.i_mul,div=__Math.i_div
```

### `boopExtend` — Adding Methods to an Existing Class

When you need to add methods to a class that's already registered —
including a class you don't own like `boop` itself — use `boopExtend`:

```bash
# Container adds traversal methods to every object (via boop)
boopExtend boop public:itemFrom,setOn
```

`boopExtend` is non-destructive: it appends methods and properties to the
existing descriptor rather than replacing it. It's the correct way to
write mixins or to patch a class from outside its source file.

### Full Class Anatomy

Here's a complete class from scratch. FQN-aware, uses `boopClass`:

```bash
#!/bin/bash

# Load the framework (and any parent classes)
. boop

# Guard — skip if already registered, print help if run directly
boop.init Point || return 0

# --- Method Implementations ---
# Convention: ClassName.methodName() { ... }

Point.new() {
  local _Class="${_Class:-Point}"
  local __Point_new_self
  into=__Point_new_self __boop.new "$@"
  boop.pass "$__Point_new_self" ${into:-}
}

Point.distanceTo() {
  local _Class="${_Class:-Point}" _Self="${_Self:-}"
  local __Point_dt_x1 __Point_dt_y1 __Point_dt_x2 __Point_dt_y2 __Point_dt_other="$1"
  __boop.parse "$_Self"            "x" __Point_dt_x1
  __boop.parse "$_Self"            "y" __Point_dt_y1
  __boop.parse "$__Point_dt_other" "x" __Point_dt_x2
  __boop.parse "$__Point_dt_other" "y" __Point_dt_y2
  local __Point_dt_result
  # ... compute distance ...
  boop.pass "$__Point_dt_result" ${into:-}
}

# --- Class Declaration ---
boopClass Point has:x,y public:new,distanceTo
```

### The Pattern, Step by Step

1. **Load guard**: `. boop ParentClass` then `boop.init ClassName || return 0`
   — source the framework first (so the registry exists), then guard: already
   loaded exits via `|| return 0`; run directly prints help and exits 1.

2. **Source dependencies**: `. boop ParentClass` loads the framework
   and parent. The import system handles circular prevention.

3. **Method functions**: Named `ClassName.methodName`. Start value-
   producing methods with `boop.pass "$val" ${into:-}` at the end.
   Methods that need object identity open with:
   `local _Class="${_Class:-ClassName}" _Self="${_Self:-}"`

4. **`boopClass` declaration**: One line at the bottom. All registration,
   finalization, and auto-aliasing happens here.

### Manual Registration (Legacy / Fine-Grained Control)

The manual three-step pattern still works and is sometimes necessary
(e.g., when implementing function names don't follow the convention):

```bash
# Step 1: Write the registry descriptor
__boop_registry["Box"]="|class=Box|trueClass=Geometry.Box|parent=boop\
|methods=calc,area,top,end,side,bottom,volume,new\
|properties=length,width,height,unit,color"

# Step 2: Register each method
__boop.registerMethod Box volume Box.volume
__boop.registerMethod Box new     Box.new
# ... register all methods ...

# Step 3: Finalize (creates class-level wrappers + constructor shorthand)
__boop.registerClass Box
```

`boopClass` does all three steps in one call. Prefer it.

### Subclassing

```bash
#!/bin/bash
. boop Geometry::Box    # load parent

boop.init Cube || return 0

Cube.new() {
  local _Class="${_Class:-Cube}"
  local __Cube_new_size="${size:-1}"
  for __Cube_new_arg in "$@"; do
    [[ "$__Cube_new_arg" =~ ^size=([0-9]+)$ ]] && __Cube_new_size="${BASH_REMATCH[1]}"
  done
  local __Cube_new_self
  into=__Cube_new_self __boop.new "$@" \
    length="$__Cube_new_size" width="$__Cube_new_size" height="$__Cube_new_size"
  boop.pass "$__Cube_new_self" ${into:-}
}

Cube.volume() {
  local _Class="${_Class:-Cube}" _Self="${_Self:-}"
  local __Cube_volume_size
  __boop.parse "$_Self" "size" __Cube_volume_size
  local __Cube_volume_vol
  into=__Cube_volume_vol required=3 Box.calc \
    "$__Cube_volume_size" "$__Cube_volume_size" "$__Cube_volume_size"
  boop.pass "$__Cube_volume_vol" ${into:-}
}

boopClass Cube isa:Box has:size,length,width,height,unit public:new,volume
```

Methods not overridden are inherited. `Cube` gets `calc`, `area`,
`get`, `set`, `isa`, `toString`, `inspect` from ancestors for free.

---

## Naming Conventions

These aren't suggestions — they prevent real bugs.

| What | Convention | Why |
|------|-----------|-----|
| Local variables | `__ClassName_methodName_varname` | Prevents nameref collisions. Bash namerefs resolve by name, not scope — two functions both using `local val` will collide via nameref. Unique prefixes prevent this. |
| Value return | `boop.pass "$val" ${into:-}` | Routes through the universal return handler. `${into:-}` passes the caller's nameref target. |
| Delegation capture | `into=__ClassName_method_localvar SomeCall` | Captures a sub-call's return into a prefixed local. Same collision-prevention logic. |
| Output | `printf`, never `echo` | `echo` interprets backslash escapes on some platforms. `printf` is predictable everywhere. |
| Framework internals | `__boop_*` or `__boop.*` | Leading double underscore = hands off. |
| Semi-private helpers | `__ClassName.*` | Double underscore prefix signals internal use. Not enforced, just convention. |

### The `_Self` and `_Class` Pattern

Most methods that need object identity start with:

```bash
local _Class="${_Class:-ClassName}" _Self="${_Self:-}"
```

The dispatcher sets `_Self` and `_Class` as environment variables
before calling the method function. The method captures them into
ordinary locals — which are visible to any function called from within
that scope via bash's dynamic scoping, but never leak back to the
caller once the function returns.

---

## Configuration Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `_OutMode` | `"auto"` | Return mode: auto, global, reply, stdout, nameref, filesystem |
| `_EOL` | `$'\n'` | Line ending appended in stdout mode |
| `_Delimiter` | `""` (→`_EOL`) | Multi-value separator for keys/values/arrays |
| `_AutoAlias` | `"full"` | Alias depth: full, best, short, none |
| `_Out` | (side-channel) | Global return value when mode=global |

Set per-call with environment prefix:

```bash
_Delimiter=$'\t' into=rows $map.toArray   # tab-separated for this call
_EOL=""          _OutMode=stdout $obj.val  # raw stdout with no newline
```

Set globally for a pipeline stage or entire script:

```bash
_AutoAlias=none    # suppress auto-aliasing (use explicit _Import)
_EOL=""            # raw output mode
_LogLevel=debug    # more verbose logging
```

---

## Serialization

Save and restore the entire object registry:

```bash
# Save all objects and class definitions to a file
__boop.serialize "state.dat"

# Load them back (in a new shell, or after clearing)
__boop.deserialize "state.dat"
```

The file format is tab-delimited: `key<TAB>descriptor` per line.
Keys are validated on load to prevent injection from tampered files.

Serialization captures descriptor data only. Baked wrapper functions
are NOT saved — they're regenerated on next access via the stub/bake
mechanism. After deserializing, call `__boop.refresh` on objects
you need to call methods on:

```bash
__boop.deserialize "state.dat"
__boop.refresh "$my_object_id"
$my_object_id.volume    # works — stubs regenerated
```

---

## Validation

Every user-supplied name that touches `eval`, registries, or dispatch
goes through `__boop.validate`:

```bash
__boop.validate "Box"                     # OK — valid identifier
__boop.validate "my-class"                # CRASH — dashes not allowed
type=function __boop.validate "Box.calc"  # OK — dots allowed in function mode
```

Identifier mode (default): `[A-Za-z_][A-Za-z0-9_]*` — no dots, no dashes,
no spaces, no shell metacharacters.

Function mode: same, but dots are allowed (because bash functions can
contain dots, and the dispatch system relies on `ClassName.method` naming).

This is the front door for security. The framework validates and rejects —
it never sanitizes and proceeds. A bad name crashes with a clear message,
never silently corrupts.

---

## Static Storage

`__boop_static` is a global associative array for cross-call persistence:

```bash
# Cache a computed value
__boop_static["Math.pi.cache_20"]="3.14159265358979323846"

# Check the cache later
local cached="${__boop_static[Math.pi.cache_20]:-}"
if [[ -n "$cached" ]]; then
  # cache hit — skip the expensive computation
fi
```

Convention: keys are `"ClassName.method.varName"`. Data persists for
the lifetime of the shell process. Math uses it for pi memoization.

---

## Named Stacks — `_Stack` {#stack}

`_Stack` is a core primitive (alongside `_Me`, `_Static`, and `_Property`)
for keeping named, ordered stacks of values on an object or class. It's a
double-ended queue under the hood, so it serves as a stack, a queue, or a
deque depending on which ends you use.

Storage lives in `__boop_static`, scoped by identity (`_Me`: the object ID in
an object method, the class name in a class method, else `boop`). Keys are:

```
<identity>.__stack.<name>.head   first live index (inclusive)
<identity>.__stack.<name>.tail   one past the last (exclusive)
<identity>.__stack.<name>.<i>    the element at index i
```

`size = tail - head`, so there's no separate count to keep in sync, and the
live range `[head, tail)` is kept hole-free (only `remove` compacts). Because
every key sits under the `<identity>.` prefix, [object destruction](#destroying-objects)
wipes an object's stacks automatically — no cleanup hook required.

| Op | Effect |
|---|---|
| `_Stack push NAME VAL...` | Append one or more values to the top |
| `_Stack pop NAME` | Remove & return the top (`into=`; `''` + rc 1 if empty) |
| `_Stack shift NAME` | Remove & return the bottom (`into=`; `''` + rc 1 if empty) |
| `_Stack peek NAME` | Return the top without removing (`into=`) |
| `_Stack size NAME` | Number of live elements (`into=`) |
| `_Stack empty NAME` | Exit 0 if empty, 1 if not |
| `_Stack list NAME` | Newline-joined, bottom → top (`into=`) |
| `_Stack each NAME FN [args]` | Call `FN element [args]` for each, top → bottom (LIFO) |
| `_Stack remove NAME VAL` | Remove the first occurrence (from the bottom) by value |
| `_Stack clear NAME` | Drop all elements and metadata |

```bash
myMethod() {
  _Stack push audit "opened $1"       # per-object stack, keyed by $_Self
  _Stack push audit "validated $1"
  into=n _Stack size audit            # n=2
  into=last _Stack pop audit          # last="validated ..."
}
```

The dispatch-style reads (`each`, `peek`, `list`) touch `__boop_static` by
direct index and never route through the `into=`/`boop.pass` return
machinery, so they're safe to call from inside a `trap` handler. Mutations
(`push`/`pop`/`shift`/`remove`) are not meant to run from within an async trap.

`_Stack` is the shared substrate for [Signal](Signal)'s handler stacks and the
[Eventable](Eventable) mixin's per-object event channels.

---

## Under the Hood

### Object Storage

Objects are entries in `__boop_registry`, a global associative array.
The key is the object ID (e.g., `__obj_01`), the value is a
pipe-delimited descriptor string holding only metadata:

```
|class=Box|trueClass=Geometry.Box
```

Property values live in `__boop_static["__obj_01.propname"]` — plain
associative array entries, no encoding. `__boop.parse` extracts fields
from the descriptor by regex match.

Classes are also entries in the same registry — distinguished by context.
`__boop_registry["Box"]` holds the class descriptor (methods, properties,
parent, trueClass). `__boop_registry["__obj_01"]` holds an object descriptor.

### Wrappers

When an object is created, `__boop.backfillMethods` generates a direct
wrapper function for every method in the class hierarchy:

```bash
# What backfillMethods generates:
__obj_01.volume() { _Self='__obj_01' _Class='Box' Box.volume "$@"; }
```

This is a one-hop call: `$obj.volume` → `__obj_01.volume` → `Box.volume`.
No dispatch overhead on normal calls. The wrapper is sourced from a
tmpfile — one `source` call covers all methods for the object.

Cost: one wrapper function per method at object creation time. After
that, every call is a direct bash function invocation.

### FQN and `trueClass`

When a class is declared with a FQN (e.g., `Collection.Map.Fast`), the
descriptor stores `trueClass=Collection.Map.Fast`. Aliases clone the
descriptor with a different `class=` but keep `trueClass` pointing to
the FQN. The stub/bake system uses `trueClass` when generating wrappers,
so wrappers always call the canonical implementation function regardless
of which alias was used to create the object.

### Container Companion Arrays

Container subclasses (List, Map) store their data in separate bash
arrays (`__boop_data_${self}`), not in the pipe-delimited descriptor.
This gives native bash array performance for element access. The
descriptor holds only metadata (class, trueClass, parent, type).

Map also maintains a companion indexed array (`__boop_keys_${self}`)
that tracks key insertion order. All traversal methods walk keys in
insertion order. Overwriting an existing key updates the value but
preserves its position. Deleting a key removes it from the order.

### Iterator: Companion Class

Iterator is a stateful cursor for traversing containers. It's defined
inside the Container source file (not a separate file) because it's
useless without Container.

Iterator inherits from `boop` (not Container). It holds a reference
to a container and a position — it doesn't own data.

Every Container instance gets lazy iterator delegation. Calling
`$list.next` auto-creates an internal Iterator on first use:

```bash
# Lazy delegation — auto-created, one per container
while $list.hasNext; do
  into=val $list.next
  into=idx $list.iterIndex
  printf "[%s] %s\n" "$idx" "$val"
done
$list.iterReset                      # back to start

# Explicit cursor — you manage it
into=iter $list.iterator
while $iter.hasNext; do
  into=val $iter.next
  printf "%s\n" "$val"
done

# Multiple independent cursors on the same container
into=iter1 $list.iterator
into=iter2 $list.iterator
into=v1 $iter1.next                  # advances iter1 only
into=v2 $iter2.next                  # advances iter2 only
```

For Map iterators, the ordered key list is snapshotted at creation
time. Mutations after the iterator is created don't affect the snapshot.

Subclasses that don't want iterators call `$_Self.noIterators` in
their constructor to wall off all iterator methods.

---

## Logging

The framework includes a built-in logging system with six numeric
levels, per-class overrides inherited via the class chain, and cached
resolution.

### Levels

| Level  | Num | Purpose |
|--------|-----|---------|
| silent | -1  | Suppress everything (even errors) |
| crash  | 0   | Reserved — triggers immediate crash |
| error  | 1   | Fatal or near-fatal conditions |
| warn   | 2   | Unexpected but recoverable (default) |
| info   | 3   | Notable lifecycle events |
| debug  | 4   | Detailed internal state |
| trace  | 5   | Finest grain — descriptor dumps, dispatch steps |

### Usage

```bash
_Warn  "unexpected value: $foo"
_Debug "entering loop with $count items"
_Trace "descriptor: $desc"
_Error "something broke"
_Crash "fatal — cannot continue"    # always prints, then exits 1

_LogLevel warn              # global default
_LogLevel debug Math        # Math and descendants get debug
_LogLevel trace             # everything at trace
```

### How It Works

Log calls read `_Class` from the current scope — each method sets it
as a local at the top, so it's visible to `_Debug`/`_Trace`/etc. via
bash's dynamic scoping. The resolved level for each class is
cached after the first lookup — subsequent calls are one hash lookup
plus one integer compare. The inheritance walk only happens once per
class (until invalidated by `_LogLevel`).

```bash
_LogLevel warn              # global = warn
_LogLevel debug Box         # Box = debug
# Cube inherits from Box → resolves to debug
# Map has no override → resolves to global warn
```

### Fatality Threshold

Two independent thresholds: visibility (what gets printed) and fatality
(what auto-crashes after printing). Default: only explicit `_Crash` is fatal.

```bash
_FatalLevel error           # _Error now prints AND crashes
_FatalLevel warn            # _Warn and _Error both auto-crash
_FatalLevel crash           # reset to default
_FatalLevel warn Math       # per-class: Math warnings are fatal
```

The message is always printed before the crash:

```
[WARN] Box.volume: unexpected dimension
[CRASH] WARN elevated to fatal (from Box.volume)
```

Same inheritance model as `_LogLevel`.

### Output Format

```
[LEVEL] caller: message
```

Where `caller` is the function name from the call stack.

---

## Framework API Reference

### Core Dispatch

| Function | Description |
|----------|-------------|
| `__boop.new` | Object constructor. Generates ID, builds descriptor, registers, stubs methods. |
| `boop.pass` | Universal return handler. Routes values via nameref, stdout, global, or filesystem. |
| `__boop.dispatch` | Method dispatcher with MRO, caching, and lazy baking. |
| `__boop.parse` | Extract a field from a descriptor string. Decodes values. |
| `__boop.get` | Read a property from an object's descriptor. |
| `__boop.set` | Write a property to an object's descriptor. |
| `__boop.isa` | Type check with inheritance walk. Resolves aliases via trueClass. |
| `__boop.trueClass` | Return the object's Fully Qualified class Name (FQN). |
| `__boop.toString` | Human-readable object display (compact or pretty). |
| `__boop.inspect` | Full debug view: class chain, all properties decoded, all methods. |
| `__boop.super` | Dispatch a method against the parent class. |

### Dispatch Helpers

| Function | Description |
|----------|-------------|
| `_Super method [args]` | Same object, parent class implementation. Crashes at root. |
| `_Delegate $obj.method [args]` | Different object, clears class context. Prevents `_Class` leakage. |
| `_Cast Class $obj method [args]` | Same object, explicit class override. Bypasses baked wrapper. |
| `_Bless $obj ClassName` | Runtime re-classification. Rewrites descriptor, force-regenerates wrappers. |

### Class Declaration

| Function | Description |
|----------|-------------|
| `boopClass Name [tokens...]` | Declare a class. Builds descriptor, registers methods, finalizes, auto-aliases. |
| `boopExtend Name [tokens...]` | Add methods/properties to an existing class. Non-destructive. |
| `__boop.registerMethod` | Map "Class.method" → implementing function in the method registry. |
| `__boop.registerClass` | Finalize a class: create class-level wrappers and constructor shorthand. |
| `__boop.backfillMethods` | Generate direct wrappers for all methods and property accessors on an object. |
| `__boop.refresh` | Tear down baked wrappers and re-generate them (for runtime method changes). |
| `__boop.autoAlias` | Run auto-aliasing for a FQN after registration. Respects `_AutoAlias`. |
| `__boop.createAlias` | Clone a class descriptor under a new name. |

### Import & Loading

| Function | Description |
|----------|-------------|
| `_Require Class [...]` | Fatal loader. Crashes if any class fails to load. |
| `_Load Class [...]` | Non-fatal loader. Returns 0/1. Never crashes. |
| `_Import Class [as Alias]` | Load + create explicit alias. Supports `::` and `/` separators. |
| `__boop.import` | Internal resolver. Tries classPath → index → dynamic → raw source. |
| `__boop.classResolve` | Namespace-aware resolution. Returns path via nameref. |
| `__boop.loader` | Bootstrap: source RC chain, parse BOOPPATH, source `.boopIndex` files. |
| `boop.resolve` | Public non-fatal resolution wrapper. Returns path via `boop.pass`. |
| `boop.classPath` | Subcommand API: `set`, `get`, `list`, `remove`, `has`, `dirs`, `rebuild`. |

### Logging

| Function | Description |
|----------|-------------|
| `_Trace` | Log at trace level (5). |
| `_Debug` | Log at debug level (4). |
| `_Info` | Log at info level (3). |
| `_Warn` | Log at warn level (2). |
| `_Error` | Log at error level (1). |
| `_Crash` | Print message to stderr, exit 1. Supports `_Err` (exit code). |
| `_LogLevel [level] [ClassName]` | Set global or per-class log level. |
| `_FatalLevel [level] [ClassName]` | Set global or per-class fatality threshold. |
| `__boop.log` | Core log function with level resolution and caching (use wrappers). |
| `__boop.setLogLevel` | Set log level and invalidate resolved cache. |
| `__boop.setFatalLevel` | Set fatality level and invalidate resolved cache. |

### Encoding

| Function | Description |
|----------|-------------|
| `__boop.encode` | Percent-encode pipes, equals, percents, newlines, tabs. |
| `__boop.decode` | Reverse of encode. |
| `__boop.validate` | Reject unsafe identifiers or function names (type=function mode). |

### Serialization

| Function | Description |
|----------|-------------|
| `__boop.serialize` | Dump registry to tab-delimited file. |
| `__boop.deserialize` | Load registry from tab-delimited file (validates keys). |

### Configuration

| Function | Description |
|----------|-------------|
| `_OutMode [mode]` | Get or set the global return mode. Call form prints current mode. |
| `__boop.inSubshell` | Returns 0 if current context is a subshell. |

### Global Variables

| Variable | Description |
|----------|-------------|
| `__boop_registry` | Master object/class store (associative array). |
| `__boop_methodRegistry` | Method resolution cache: "Class.method" → function name. |
| `__boop_classPath` | Explicit path overrides for class file resolution. |
| `__boop_loading` | In-progress load tracker (circular recursion prevention). |
| `__boop_static` | Cross-call static storage for any function. |
| `__boop_Index` | Short-name → namespace-path index (merged from all roots). |
| `__boop_alias` | Alias registry: user-facing name → FQN. |
| `__boop_version` | Framework version string (read-only). |
| `__boop_rootPID` | Root process PID (for subshell detection). |
| `__boop_loaded` | Framework initialization flag. |
| `_OutMode` | Current global return mode (default: `"auto"`). |
| `_Out` | Side-channel for global return mode. |
| `_EOL` | Line ending appended in stdout mode (default: `$'\n'`). |
| `_Delimiter` | Multi-value separator for keys/values/arrays (default: `""` → `_EOL`). |
| `_AutoAlias` | Alias depth on class load: full, best, short, none (default: `"full"`). |
| `__boop_logLevel` | Global default log level (default: 2/warn). |
| `__boop_classLogLevel` | Per-class log level overrides (associative array). |
| `__boop_resolvedLogLevel` | Cached resolved levels (associative array). |
| `__boop_logFile` | Fallback log file path when stderr is unavailable. |
| `__boop_fatalLevel` | Global default fatality level (default: 0/crash). |
| `__boop_classFatalLevel` | Per-class fatality level overrides (associative array). |
| `__boop_resolvedFatalLevel` | Cached resolved fatality levels (associative array). |

---

## Gotchas and Things That Will Bite You

### Nameref Collisions

This is the big one. Bash namerefs resolve by name, not by lexical scope.
If function A has `local val` and calls function B which has
`local -n ref=val`, the nameref in B binds to A's `val` — not some
hypothetical global `val`. This is why every local variable in the
framework is prefixed `__ClassName_methodName_varname`. It's ugly, but
it's correct.

If you skip the prefix and use short names like `result` or `tmp`,
you will eventually get a mysterious "circular nameref" error or,
worse, silent value corruption. Don't skip the prefix.

### `set -u` and the Framework

boop does NOT set `set -u` (or any other shell option). If you want
`set -u` in your scripts, set it yourself — boop will work fine with it.
The framework saves and restores any shell options it temporarily changes
internally. Your shell options are your business.

### Subshells and Object Creation

Objects created in a subshell don't exist in the parent shell:

```bash
# This object vanishes when the subshell exits:
id=$( new Box length=5 width=3 height=7 )
$id.volume    # CRASH — object not in parent's registry
```

Use `into=` instead:

```bash
into=id new Box length=5 width=3 height=7
$id.volume    # works
```

### Aliases and `isa`

`isa` resolves both the object's class and the queried class through
`trueClass` before comparing. So `$obj.isa Fast` correctly matches an
object whose `trueClass` is `Collection.Map.Fast`, even if you created
it with `into=obj Fast`. However, raw string comparisons on `_Class`
may surprise you:

```bash
into=m Fast key=val
# $m's descriptor: class=Fast, trueClass=Collection.Map.Fast

$m.isa Fast              # true (trueClass match)
$m.isa Map.Fast          # true (trueClass is a suffix match)
$m.isa Collection.Map.Fast  # true

# But direct class inspection:
__boop.parse "$m" "class" cls
printf "%s\n" "$cls"     # "Fast" — the alias name, not the FQN
```

For type-safe checks, always use `isa`. Don't compare `_Class` strings
directly if aliases are involved.

### Property Order

Properties in the descriptor reflect insertion order. Mutations via
`set` preserve position. Duplicate keys from constructor args are
allowed — both end up in the descriptor, but `get`/`parse` match the
first one. This is documented behavior, not a bug, but probably not
what you want. Don't pass the same key twice.

### Deep Traversal and Object Identity

In deep traversal methods (`itemAt`, `setAt`, `itemFrom`, `setOn`),
the cursor changes identity and class on every step. These methods
copy the initial `_Self` and `_Class` into explicit cursor variables
and use `_Self=`/`_Class=` environment prefixes on every dispatch call
to ensure each step operates on the right object. If you write your
own traversal code that dispatches to multiple different objects in
sequence, follow the same pattern — don't assume ambient `_Self` is
still correct after dispatching to another object.
The Container source has a detailed block comment explaining this.

---

## The Class Hierarchy

```
boop                             (root — get, set, isa, toString, inspect, new, super, itemFrom, setOn)
  │
  ├── Geometry
  │     ├── Box                  (3D rectangular prism — volume, area, top, side, end, bottom)
  │     └── Cube                 (equal-sided Box — overrides all geometry methods)
  │
  ├── Collection
  │     ├── Container            (virtual base — defines collection interface, registers Iterator)
  │     │     ├── List           (indexed array — push, pop, shift, unshift, slice, etc.)
  │     │     └── Map            (insertion-ordered key-value store)
  │     │           └── Fast     (Map variant with O(1) delete — no insertion-order guarantee)
  │     └── Iterator             (stateful cursor — companion to Container, defined in Container file)
  │
  ├── Math                       (arbitrary precision arithmetic — pi, expressions, etc.)
  │
  ├── Config                     (config file reader/writer — flat key=value and INI formats)
  │
  ├── Args                       (CLI argument parser — getOpts and full GNU long + subcommand parser)
  │
  ├── Data
  │     └── JSON                 (JSON serialization — encode/decode between bash and JSON)
  │
  └── Games
        ├── Card                 (playing card — suit, rank, display)
        ├── PlayingCard          (extended card with value semantics)
        └── Deck                 (shuffled deck — draw, shuffle, deal)
```

`Container` also adds `itemFrom` and `setOn` to `boop` on load, so
every object can traverse containers stored in its properties.

`Iterator` inherits from `boop` (not Container). It holds a reference
and a position; it doesn't own data.

---

## Project Structure

| Path | What It Is |
|------|-----------|
| `boop` | The framework. Load this first, load this only. |
| `.boopIndex` | Auto-generated class index. Rebuilt by `boop.classPath rebuild .` |
| `Geometry/Box/Box` | 3D rectangular prism class. |
| `Geometry/Cube/Cube` | Equal-sided Box (inherits Box). |
| `Collection/Container/Container` | Virtual container base class + Iterator companion. |
| `Collection/List/List` | Indexed array container. |
| `Collection/Map/Map` | Insertion-ordered associative array container. |
| `Collection/Map/Fast/Fast` | Map variant with O(1) delete. |
| `Math/Math` | Arbitrary precision arithmetic. |
| `Config/Config` | Config file reader/writer (flat and INI formats). |
| `Args/Args` | CLI argument parser (getOpts + full long/subcommand parser). |
| `Data/JSON/JSON` | JSON encode/decode. |
| `Games/Card/Card` | Playing card. |
| `Games/PlayingCard/PlayingCard` | Extended playing card with value semantics. |
| `Games/Deck/Deck` | Shuffled deck of cards. |
| `Testing/TestSuite/TestSuite` | Structured test harness — assertions, sections, timing. |
| `blackjack` | Blackjack game built on the Games namespace. |
| `tests/` | All test files. |
| `docs/` | You are here. |

### Test Files

| File | What It Tests |
|------|--------------|
| `tests/unit/test_testsuite_ts` | TestSuite testing itself (~31 assertions). |
| `tests/unit/test_box_cube_ts` | Box and Cube (~45 tests). |
| `tests/unit/test_containers_ts` | Container, List, Map, Iterator, delegation (~155 tests). |
| `tests/unit/test_math_ts` | Math including pi verification (~75 tests). |
| `tests/integration/test_adversarial_ts` | Framework adversarial tests (edge cases, NUL, encoding, dispatch). |
| `tests/unit/test_logging_ts` | Logging system (~51 tests). |
| `tests/unit/test_config_ts` | Config class (flat and INI formats). |
| `tests/unit/test_classpath_ts` | Classpath resolution and .boopIndex. |
| `tests/unit/test_args_ts` | Args parser (getOpts and full parse). |

---

[↑ Site map](index)
