# boop — The Framework

An OOP dispatch system for bash 5+. Classes, objects, inheritance, method
resolution, property accessors, type checking, value encoding, serialization,
and a universal return handler — all built on associative arrays and naming
conventions. No external dependencies. No subshells in the hot path. No
apologies.

The framework file is called `boop` because life is too short for
`bash_object_oriented_programming_framework.sh`. The internal namespace
is `__boop_*` — the filename is the personality, the internals are
the plumbing.

## Requirements

- bash 5.0+ (associative arrays, `local -I`, `EPOCHREALTIME`, namerefs)
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
# Cube(_64d...) {
#   size   = 4
#   unit   = cm
#   ...
# }

# Deep dive — full descriptor + inheritance chain
$c.inspect
# object:  _64d0895be1590
# class:   Cube extends Box extends boop
#   size     = 4
#   unit     = cm
#   length   = 4
#   width    = 4
#   height   = 4
# methods: new, side, top, end, bottom, volume, calc, area, get, set, ...
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
into your variable — zero-copy, no subshell, no global side-channel.
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

# Global side-channel — printed by the next call, not ideal
$cube.volume
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

### Global Side-Channel

```bash
$cube.volume
printf "%s\n" "$_Out"           # "64"
```

When no `into=` is provided in the main shell, the value lands in `_Out`.
A single flat global — the next call overwrites it. Fine for quick
one-offs, but `into=` is safer.

### Explicit Mode Override

```bash
_OutMode=stdout $cube.volume    # force stdout
_OutMode=global $cube.volume    # force $\_Out
```

Modes: `auto` (default), `global`, `stdout`, `nameref`, `filesystem`.
Auto writes to `$_Out` in the main shell; stdout in subshells.

```bash
__boop.setDefaultMode stdout    # change the process default
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

Three equivalent syntaxes. Pick whichever reads best in context:

```bash
# Class-as-constructor (most common)
into=b Box length=5 width=3 height=7

# Explicit `new` keyword
into=b new Box length=5 width=3 height=7

# Full dispatch (rarely needed)
into=b _Class=Box __boop.dispatch new length=5 width=3 height=7
```

Constructor arguments are `key=value` pairs. They land in the object's
descriptor as encoded properties. The object gets a unique ID generated
from `EPOCHREALTIME` (hex-encoded microseconds — fast, no subshell,
monotonically increasing).

After construction, the object has lazy stubs for every method in its
class and all ancestor classes. The first call to any method triggers
dispatch resolution and bakes a direct wrapper — subsequent calls skip
dispatch entirely.

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

### Value Encoding

Properties are stored in a pipe-delimited descriptor string. Values
containing pipes, equals signs, percents, newlines, or tabs are
automatically encoded on write and decoded on read. You never see the
encoding:

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
# Box(_64d...){{ length=5 width=3 height=7 }

# Pretty — columnar with alignment
into=s $b.toString pretty
# Box(_64d...) {
#   length = 5
#   width  = 3
#   height = 7
# }
```

Internal metadata (`class`, `parent`, `methods`, `properties`, `trueClass`)
is hidden. Only user-defined properties show up. Container subclasses
(List, Map) override `toString` to show their contents.

### `inspect` — Debug View

```bash
$obj.inspect              # always prints to stdout — pipe it, page it
$obj.inspect | less
```

`inspect` shows everything `toString` hides. You get the full
inheritance chain, every property including internal ones (decoded),
and the complete method list gathered from the entire ancestry:

```
object:  _64d0895be1590
class:   Cube extends Box extends boop
  class      = Cube
  trueClass  = Geometry.Cube
  parent     = Box
  size       = 4
  unit       = cm
  length     = 4
  width      = 4
  height     = 4
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
  local -I _Self _Class; : "${_Class:=Cube}"
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
3. Unrelated class (leakage from `local -I`) — emits a `_Warn`
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
  the class file's load guard (`return 2>/dev/null`) exits immediately.
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

### The Modern Way: `boopClass`

`boopClass` declares a class in a single call. It builds the registry
descriptor, registers all methods, finalizes the class, and runs
auto-aliasing. This replaces the manual three-step pattern entirely.

Here's `Config` — a real class in the project:

```bash
#!/bin/bash

[[ -n "${__boop_registry[Config]+set}" ]] && return 2>/dev/null

. boop

# ... method implementations ...

Config.get() {
  local _Self="${_Self:-${_Class:-Config}}" _Class="${_Class:-Config}"
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

# Load guard — skip if already registered
[[ -n "${__boop_registry[Point]+set}" ]] && return 2>/dev/null

# Load the framework (and any parent classes)
. boop

# --- Method Implementations ---
# Convention: ClassName.methodName() { ... }

Point.new() {
  local _Class="${_Class:-Point}"
  local __Point_new_self
  into=__Point_new_self __boop.new "$@"
  boop.pass "$__Point_new_self" ${into:-}
}

Point.distanceTo() {
  local -I _Self _Class
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

1. **Load guard**: `[[ -n "${__boop_registry[ClassName]+set}" ]] && return 2>/dev/null`
   — skip if already loaded, without crashing when run directly.

2. **Source dependencies**: `. boop ParentClass` loads the framework
   and parent. The import system handles circular prevention.

3. **Method functions**: Named `ClassName.methodName`. Start value-
   producing methods with `boop.pass "$val" ${into:-}` at the end.
   For methods that need `_Self` and `_Class`, use `local -I _Self _Class`
   (inherited from caller) or set them explicitly via boopClass defaults.

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
[[ -n "${__boop_registry[Cube]+set}" ]] && return 2>/dev/null

. boop Geometry::Box    # load parent

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
  local -I _Self _Class
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

### The `local -I` Pattern

Most methods that need object identity start with:

```bash
local -I _Self _Class
```

`local -I` (bash 5.1+) creates inherited locals — the variable is local
to this function but initialized from the calling scope. This is how
`_Self` and `_Class` flow through the dispatch chain without explicit
argument passing.

One gotcha: `local -I` variables are writable by callees in the same
scope chain. Deep traversal methods (like `itemAt`) that dispatch to
multiple different objects in sequence use explicit `_Self=` and
`_Class=` environment prefixes on each call to prevent leakage.

---

## Configuration Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `_OutMode` | `"auto"` | Return mode: auto, global, stdout, nameref, filesystem |
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

## Under the Hood

### Object Storage

Objects are entries in `__boop_registry`, a global associative array.
The key is the object ID (e.g., `_64d0895be1590`), the value is a
pipe-delimited descriptor string:

```
|class=Box|trueClass=Geometry.Box|parent=boop|length=%335|width=%333|height=%337|
```

Values are percent-encoded (pipes, equals, percents, newlines, tabs)
so they don't corrupt the delimiter structure. `__boop.parse` extracts
and decodes fields by regex match on the descriptor.

Classes are also entries in the same registry — distinguished by context.
`__boop_registry["Box"]` holds the class descriptor (methods, properties,
parent, trueClass). `__boop_registry["_64d..."]` holds an object descriptor.

### Lazy Stubs and Baking

When an object is created, `stubAll` generates tiny eval'd functions
for every method:

```bash
# What stubAll generates (conceptually):
_64d0895be1590.volume() {
  __init=true _Self='_64d0895be1590' _Class='Box' \
    __boop.dispatch volume "$@"
}
```

On first call, `__init=true` tells dispatch to bake a direct wrapper:

```bash
# What dispatch bakes (conceptually):
_64d0895be1590.volume() {
  if [[ ${_Class:-Box} != 'Box' ]]; then
    _Self='_64d0895be1590' __boop.dispatch volume "$@"
  else
    _Self='_64d0895be1590' _Class='Box' Box.volume "$@"
  fi
}
```

The baked wrapper calls `Box.volume` directly — no dispatch, no MRO
walk, no registry lookup. The `if` guard handles typecasting.

Cost: one `eval` per method at object creation, one dispatch on first
call, then zero overhead forever.

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

Log calls inherit `_Class` via `local -I`, so the framework knows which
class context the call is in. The resolved level for each class is
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
| `__boop.stubAll` | Generate lazy stubs for all methods on an object. |
| `__boop.refresh` | Tear down baked wrappers and re-stub (for runtime method changes). |
| `__boop.autoAlias` | Run auto-aliasing for a FQN after registration. Respects `_AutoAlias`. |
| `__boop.createAlias` | Clone a class descriptor under a new name. |
| `__boop.backfillMethods` | Ensure inherited methods are stubs on an object. |

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
| `__boop.setDefaultMode` | Set global return mode (auto/nameref/stdout/global/filesystem). |
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

### Container `local -I` Leak

In deep traversal methods (`itemAt`, `setAt`, `itemFrom`, `setOn`),
the cursor changes identity and class on every step. Because `local -I`
creates shared bindings up the call stack, dispatching to one object
can leak its `_Class` value into the next iteration. These methods use
explicit `_Self=`/`_Class=` environment prefixes on every dispatch call
to prevent this. If you write your own traversal code that dispatches
to multiple different objects in sequence, you'll need the same pattern.
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
| `tests/unit/test_stress_ts` | Framework adversarial tests (~131 tests). |
| `tests/unit/test_logging_ts` | Logging system (~51 tests). |
| `tests/unit/test_config_ts` | Config class (flat and INI formats). |
| `tests/unit/test_classpath_ts` | Classpath resolution and .boopIndex. |
| `tests/unit/test_args_ts` | Args parser (getOpts and full parse). |
