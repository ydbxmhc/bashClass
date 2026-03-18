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

The `bencode`/`bdecode` helpers use coreutils `base64` for binary-safe
encoding, but the core framework doesn't touch it.

macOS ships bash 3.2 (thanks, GPL3). `brew install bash` fixes that.
If your users might be on macOS, tell them up front.

## Loading the Framework

```bash
# Load framework only
. boop

# Load framework + import classes (the common case)
. boop Box Cube

# Classes declare their own dependencies, so this:
. boop Cube
# ...automatically loads Box (Cube's parent) and boop itself.
```

The framework loads once. Re-sourcing `. boop` skips all definitions
(guarded by `__boop_loaded`) and only processes import arguments.
This means class files can safely do `. boop SomeDependency` without
re-executing the framework.

## The 30-Second Tour

```bash
. boop Cube Math

# Create objects
into=c Cube size=4 unit=cm
into=m Math 3.14

# Call methods — they look like what they are
into=vol $c.volume              # vol="64"
into=v $m.val                   # v="3.14"

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
#   length = 4
#   width  = 4
#   height = 4
# }
```

That's the shape of it. Everything below is the details.

---

## Creating Objects

Three equivalent syntaxes. Pick whichever reads best in context:

```bash
# Class-as-constructor (most common)
into=b Box length=5 width=3 height=7

# Explicit `new` keyword
into=b new Box length=5 width=3 height=7

# Full dispatch (you'll never need this, but it exists)
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

## Getting Values Back: The Return System

This is the part that makes boop feel different from "just bash functions."
Every value-producing function in the framework routes through a single
return handler (`__boop.return`). You choose how to receive the value.

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

Sometimes you just want the value on stdout. A few ways to get there:

```bash
# Grab it, then print it
into=vol $cube.volume
printf "%s\n" "$vol"            # 64

# Force stdout mode for one call — prints directly, no variable needed
__boop_returnMode=stdout $cube.volume
printf "\n"                     # (add a newline if you want one)

# That's a mouthful. Consider an alias:
alias show='__boop_returnMode=stdout'
show $cube.volume               # same thing, less typing

# Or use the global side-channel and print that
$cube.volume
printf "%s\n" "$__boop_RETURN"  # 64

# Subshell capture — classic bash, works anywhere
printf "Volume: %s\n" "$( $cube.volume )"  # Volume: 64
```

The first two avoid subshells entirely. The `__boop_returnMode=stdout`
prefix is a per-call override — it doesn't change the global default.

### Subshell Capture (Classic Bash)

```bash
vol=$( $cube.volume )           # works, but forks a subshell
```

The framework detects subshells (via `BASHPID` vs the root PID captured
at load time) and automatically switches to stdout mode. It works, but
every `$()` is a fork. For a single call, who cares. In a loop, it adds up.

Subshell capture does enable one-liner chaining through nested objects,
which `into=` can't do in a single expression:

```bash
# Subshell chain — one line, but forks at every level
val=$( $( $matrix.get 0 ).get 1 )    # "2"

# into= equivalent — no forks, but two lines
into=row $matrix.get 0
into=val $row.get 1                   # "2"
```

For nested containers, `itemAt` is the best of both worlds — one line,
no forks:

```bash
into=val $matrix.itemAt 0 1           # "2"
```

### Global Side-Channel

```bash
$cube.volume
printf "%s\n" "$__boop_RETURN"  # "64"
```

When no `into=` is provided and you're in the main shell, the value
lands in `__boop_RETURN`. It's a single flat global — the next
call overwrites it. Fine for quick one-offs, but `into=` is safer.

### Explicit Mode Override

```bash
__boop_returnMode=stdout $cube.volume    # force stdout
__boop_returnMode=nameref $cube.volume   # crash (no target!)
```

You can override the global mode per-call via environment prefix.
The modes are: `auto` (default), `global`, `stdout`, `nameref`,
`filesystem`. Auto does the right thing — global in main shell,
stdout in subshells.

```bash
# Change the default for the whole process
__boop.setDefaultMode stdout
```

---

## Properties: Get and Set

Every object inherits `get` and `set` from `boop`:

```bash
into=b Box length=5 width=3 height=7

# Read a property
into=len $b.get "length"        # len="5"

# Write a property
$b.set "color" "red"
into=c $b.get "color"           # c="red"
```

### Property Shorthand

When a class declares properties in its descriptor, objects get
dual-purpose accessor stubs:

```bash
# These are equivalent:
into=len $b.get "length"
into=len $b.length              # shorthand — no args = get

# Set via shorthand:
$b.length 10                    # one arg = set
```

The shorthand stubs are generated by `stubAll` from the `properties=`
field in the class descriptor. No args dispatches to `get`, one arg
dispatches to `set`.

### Value Encoding

Properties are stored in a pipe-delimited descriptor string. Values
containing pipes, equals signs, percents, newlines, or tabs are
automatically encoded on write and decoded on read. You never see the
encoding — it's transparent:

```bash
$b.set "notes" "width=3|height=7"
into=n $b.get "notes"           # n="width=3|height=7" (clean)
```

For binary data (null bytes, arbitrary byte sequences), use the
`bencode`/`bdecode` helpers, which go through `base64`. These require
a subshell (command substitution for the external tool), so they're
slower — use only when you actually need binary safety.

---

## Type Checking: `isa`

```bash
$cube.isa Cube      && printf "yes\n"   # 0 (true)
$cube.isa Box       && printf "yes\n"   # 0 (true — inherits)
$cube.isa boop && printf "yes\n"   # 0 (true — everything does)
$cube.isa Map       || printf "nope\n"  # 1 (false)

# No argument = return the class name
into=cls $cube.isa                  # cls="Cube"
```

`isa` with an argument walks the inheritance chain and returns an exit
code (0=true, 1=false). No value is produced — it's a boolean check,
bash-style.

`isa` with no argument returns the object's class name through the
normal return system.

---

## Display: `toString`

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

# Pretty via environment (same result)
prettyPrint=true into=s $b.toString
```

Internal metadata fields (`class`, `parent`, `methods`, `properties`)
are hidden. Only user-defined properties show up.

Container subclasses (List, Map) override `toString` to show their
contents instead of descriptor properties.

---

## Inheritance

Classes form a single-inheritance chain. Every class ultimately inherits
from `boop`, which provides `get`, `set`, `isa`, `toString`, `new`,
and `super`.

```
boop
  ├── Box
  │     └── Cube
  ├── Container
  │     ├── List
  │     └── Map
  └── Math
```

### Method Resolution Order (MRO)

When you call `$cube.volume`, the framework:

1. Checks the method registry for `Cube.volume` (O(1) hash lookup).
2. On cache miss, walks the parent chain: Cube → Box → boop.
3. When found (say, in Box), caches it as `Cube.volume` so the walk
   never happens again for that class+method pair.

After the first call, a baked wrapper replaces the stub — subsequent
calls go directly to the implementation function with zero dispatch
overhead.

### Typecasting

You can force a method to resolve against a different class in the
inheritance chain:

```bash
# Normal: dispatches to Cube.volume
into=v $cube.volume

# Typecast: dispatches to Box.volume instead
into=v _Class=Box $cube.volume
```

The baked wrapper detects the class mismatch and handles three cases:

1. Exact match (or no ambient class) — fast path, direct call.
2. Family member (ambient class is an ancestor) — legitimate typecast,
   falls back to full dispatch for correct MRO resolution.
3. Unrelated class (leakage from `local -I`) — emits a `_Warn`
   diagnostic and uses the baked class. The warning is controlled by
   the logging system's per-class level, so users can silence it or
   (when the fatality threshold is implemented) make it fatal.

### `super`

Call the parent class's implementation of a method:

```bash
# Inside a class method:
_Self=$_Self _Class=$_Class __boop.dispatch super volume
```

Crashes if you're already at the root (`boop` has no parent).

---

## Writing a Class

Here's the anatomy of a class file. This is `Box` — a real class in the
project, slightly condensed:

```bash
#!/bin/bash

# Load guard — skip if already registered
[[ -n "${__boop_registry[Box]+set}" ]] && return 2>/dev/null

# Load the framework (and any parent classes)
. boop

# --- Class Descriptor ---
# Pipe-delimited: class name, parent, method list, property list
__boop_registry["Box"]="|class=Box|parent=boop\
|methods=calc,area,top,end,side,bottom,volume,new\
|properties=length,width,height,unit,color"

# --- Method Implementations ---
# Convention: ClassName.methodName() { ... }

Box.volume() {
  local -I _Self _Class
  local __Box_volume_l __Box_volume_h __Box_volume_w __Box_volume_vol
  __boop.parse "$_Self" "length" __Box_volume_l
  __boop.parse "$_Self" "height" __Box_volume_h
  __boop.parse "$_Self" "width"  __Box_volume_w
  into=__Box_volume_vol required=3 Box.calc \
    "$__Box_volume_l" "$__Box_volume_h" "$__Box_volume_w"
  __boop.return "$__Box_volume_vol" ${into:-}
}

Box.new() {
  local -I _Class
  : "${_Class:=Box}"
  local __Box_new_self
  into=__Box_new_self __boop.new "$@"
  __boop.return "$__Box_new_self" ${into:-}
}

# ... other methods ...

# --- Registration ---
__boop.registerMethod Box volume Box.volume
__boop.registerMethod Box new     Box.new
# ... register all methods ...

# --- Finalize ---
__boop.registerClass Box
```

### The Pattern, Step by Step

1. **Load guard**: Check `__boop_registry[ClassName]+set`. If the
   class is already loaded, `return` immediately. The `2>/dev/null`
   silences the error when the file is executed directly (not sourced).

2. **Source dependencies**: `. boop ParentClass` loads the framework
   and any parent classes. The framework's import system handles
   circular prevention.

3. **Descriptor**: Register a pipe-delimited string in
   `__boop_registry["ClassName"]`. Fields:
   - `class=` — the class name (in the descriptor string)
   - `parent=` — the parent class (use `boop` for root)
   - `methods=` — comma-separated list of method names
   - `properties=` — comma-separated list of property names

4. **Method functions**: Name them `ClassName.methodName`. Start with
   `local -I _Self _Class` to inherit the calling object's identity.
   End value-producing methods with `__boop.return "$val" ${into:-}`.

5. **Register methods**: `__boop.registerMethod ClassName method ClassName.method`
   for each method. The implementing function must exist at registration time.

6. **Finalize**: `__boop.registerClass ClassName` creates class-level
   wrappers and the constructor shorthand.

### Subclassing

Inherit from an existing class by setting `parent=` in the descriptor
and sourcing the parent:

```bash
#!/bin/bash
[[ -n "${__boop_registry[Cube]+set}" ]] && return 2>/dev/null

. boop Box    # loads Box (our parent)

__boop_registry["Cube"]="|class=Cube|parent=Box\
|methods=new,side,top,end,bottom,volume\
|properties=size,length,width,height,unit"

Cube.new() {
  local -I _Class
  : "${_Class:=Cube}"
  local __Cube_new_size=1 __Cube_new_self

  for __Cube_new_arg in "$@"; do
    [[ "$__Cube_new_arg" =~ ^size=([0-9]+)$ ]] && \
      __Cube_new_size="${BASH_REMATCH[1]}"
  done

  # Delegate to base constructor with derived dimensions
  into=__Cube_new_self __boop.new "$@" \
    length=$__Cube_new_size width=$__Cube_new_size height=$__Cube_new_size
  __boop.return "$__Cube_new_self" ${into:-}
}

# Override methods as needed...
Cube.volume() {
  local -I _Self _Class
  local __Cube_volume_size __Cube_volume_vol
  __boop.parse "$_Self" "size" __Cube_volume_size
  into=__Cube_volume_vol required=3 Box.calc \
    "$__Cube_volume_size" "$__Cube_volume_size" "$__Cube_volume_size"
  __boop.return "$__Cube_volume_vol" ${into:-}
}

# Register and finalize
__boop.registerMethod Cube new    Cube.new
__boop.registerMethod Cube volume Cube.volume
__boop.registerClass Cube
```

Methods not overridden are inherited. Cube gets `calc`, `area`, `get`,
`set`, `isa`, `toString` from its ancestors without doing anything.

---

## Naming Conventions

These aren't suggestions — they prevent real bugs.

| What | Convention | Why |
|------|-----------|-----|
| Local variables | `__ClassName_methodName_varname` | Prevents nameref collisions across the call stack. Bash namerefs resolve by name, not scope — if two functions both use `local val`, a nameref in the inner function can accidentally bind to the outer function's `val`. Prefixing makes names unique. |
| Value return | `__boop.return "$val" ${into:-}` | Routes through the universal return handler. The `${into:-}` passes the caller's nameref target (if any) so the value lands directly in their variable. |
| Delegation capture | `into=__ClassName_method_localvar SomeCall` | Captures a sub-call's return value into a prefixed local. Same collision-prevention logic. |
| Output | `printf`, never `echo` | `echo` interprets backslash escapes on some platforms. `printf` is predictable everywhere. |
| Framework internals | `__boop_*` or `__boop.*` | Leading double underscore = hands off. |

### The `local -I` Pattern

Most methods start with:

```bash
local -I _Self _Class
```

`local -I` (bash 5.1+) creates inherited locals — the variable is
local to this function but initialized with the value from the calling
scope. This is how `_Self` and `_Class` flow through the dispatch chain
without being passed as explicit arguments.

One gotcha: `local -I` variables are writable by callees in the same
scope chain. This matters for deep traversal methods (like `itemAt`)
where the cursor changes class on every step. Those methods use explicit
`_Self=` and `_Class=` environment prefixes on each dispatch call to
prevent leakage. See the Container source for the full explanation.

---

## The Import System

```bash
. boop Cube Math List
```

Arguments after `boop` are class names to import. Resolution order
(first match wins):

1. `__boop_classPath["ClassName"]` — explicit path override
2. `__boop_dir` — the directory where `boop` lives (co-located files)
3. `PATH` — the shell's standard search path

```bash
# Register a custom path for a class
__boop_classPath["MyClass"]="/opt/lib/MyClass"
. boop MyClass    # loads from /opt/lib/MyClass
```

### Load Guards

Two layers prevent double-loading and circular recursion:

- **Registry check**: If `__boop_registry[ClassName]` is already set,
  the class file's own load guard (`return 2>/dev/null`) skips it.
- **Loading flag**: `__boop_loading[ClassName]` is set while a class
  file is being sourced. If boop re-enters import for the same class
  (because the class file sources boop as part of its dependency chain),
  the flag catches it and skips. This prevents infinite recursion in
  chains like: Cube → `. boop Box` → Box → `. boop` → boop tries to
  import Box again.

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
it never sanitizes and proceeds. If a name is bad, you get a crash with
a clear message, not a silent corruption.

---

## Static Storage

`__boop_static` is a global associative array available to any
function in any class for cross-call persistence:

```bash
# Cache a computed value
__boop_static["Math.pi.cache_20"]="3.14159265358979323846"

# Check the cache later
local cached="${__boop_static[Math.pi.cache_20]:-}"
if [[ -n "$cached" ]]; then
  # cache hit — skip the expensive computation
fi
```

Convention: keys are `"FunctionName.varName"` or
`"ClassName.method.varName"`. Each function owns its own namespace.
Data persists for the lifetime of the shell process.

This lives in `boop` (not in any class file) because it's a
framework-level facility. Math uses it for pi memoization. Your
classes can use it for whatever they need.

---

## Under the Hood

### Object Storage

Objects are entries in `__boop_registry`, a global associative array.
The key is the object ID (e.g., `_64d0895be1590`), the value is a
pipe-delimited descriptor string:

```
|class=Box|parent=boop|length=%335|width=%333|height=%337|
```

Values are percent-encoded (pipes, equals, percents, newlines, tabs)
so they don't corrupt the delimiter structure. `__boop.parse`
extracts and decodes fields by regex match on the descriptor string.

Classes are also entries in the same registry — distinguished by context,
not by a type field. `__boop_registry["Box"]` holds the class
descriptor (methods, properties, parent). `__boop_registry["_64d..."]`
holds an object descriptor (class, property values).

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
walk, no registry lookup. The `if` guard handles typecasting: if someone
calls `_Class=OtherClass $obj.volume`, the baked class won't match, so
it falls back to dispatch for correct resolution.

Cost: one `eval` per method at object creation, one dispatch on first
call, then zero overhead forever after.

### Container Companion Arrays

Container subclasses (List, Map) store their data in separate bash
arrays (`__boop_data_${self}`), not in the pipe-delimited descriptor.
This gives native bash array performance for element access. The
descriptor only holds metadata (class, parent, type).

Map also maintains a companion indexed array (`__boop_keys_${self}`)
that tracks key insertion order. All traversal methods (keys, values,
toArray, toString, each, iterator) walk keys in the order they were
first added. Overwriting an existing key updates the value but preserves
its position. Deleting a key removes it from the order; re-inserting
places it at the end.

Why not encode arrays into the descriptor? Because bash arrays can't
nest inside associative arrays, and encoding list elements into a
pipe-delimited string would mean escaping delimiters inside delimiters.
Fragile, slow, and not worth the pain.

### Iterator: Companion Class

Iterator is a stateful cursor for traversing containers. It's defined
inside the Container source file (not a separate file) because it's
useless without Container and Container benefits from having it always
available.

Iterator inherits from `boop` (not Container). It doesn't hold
data and doesn't fulfill the Container contract — it holds a reference
to a container and a position. The relationship is composition: Container
*has-a* Iterator, Iterator *references* a Container.

Every Container instance gets lazy iterator delegation. Calling
`$list.next` or `$map.hasNext` auto-creates an internal Iterator on
first use and forwards to it. For independent cursors, create Iterators
explicitly:

```bash
# Lazy delegation — auto-created, one per container
while $list.hasNext; do
  into=val $list.next
  into=idx $list.iterIndex
  printf "[%s] %s\n" "$idx" "$val"
done
$list.iterReset                      # back to start

# Explicit — independent cursor, you manage it
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

Delegation methods on Container: `next`, `prev`, `hasNext`, `hasPrev`,
`current`, `iterIndex`, `iterReset`. These forward to the lazy internal
Iterator. The names `iterIndex` and `iterReset` avoid collision with
potential Container methods.

Methods on Iterator objects (explicit or internal): `next`, `prev`,
`hasNext`, `hasPrev`, `current`, `index`, `reset`.

For Map iterators, the ordered key list is snapshotted at creation time.
Mutations to the Map after the iterator is created don't affect the
snapshot — predictable traversal over live-view consistency.

Subclasses that don't want iterators call `$_Self.noIterators` in their
constructor:

```bash
MyStack.new() {
  local -I _Class; : "${_Class:=MyStack}"
  local __MyStack_new_self
  into=__MyStack_new_self __boop.new "$@"
  declare -ga "__boop_data_${__MyStack_new_self}"
  $__MyStack_new_self.noIterators     # walls off all iterator methods
  __boop.return "$__MyStack_new_self" ${into:-}
}
```

After `noIterators`, any call to `$obj.next`, `$obj.iterator`, etc.
crashes with "ClassName does not support iterators".

---

## Logging

The framework includes a built-in logging system with six numeric levels,
per-class overrides inherited via the class chain, and cached resolution.

### Levels

| Level   | Num | Purpose |
|---------|-----|---------|
| silent  | 0   | Suppress everything (even errors) |
| error   | 1   | Fatal or near-fatal conditions |
| warn    | 2   | Unexpected but recoverable (default) |
| info    | 3   | Notable lifecycle events |
| debug   | 4   | Detailed internal state |
| trace   | 5   | Finest grain — descriptor dumps, dispatch steps |

### Usage

```bash
# In any method or script:
_Warn  "unexpected value: $foo"
_Debug "entering loop with $count items"
_Trace "descriptor: $desc"
_Error "something broke"
_Crash "fatal — cannot continue"    # always prints, then exits 1

# Set levels:
_LogLevel warn              # global default
_LogLevel debug Math        # Math and descendants get debug
_LogLevel trace             # everything at trace
```

### How It Works

Log calls inherit `_Class` via `local -I`, so the framework knows which
class context the call is in. The resolved level for each class is cached
after the first lookup — subsequent calls are one hash lookup + one
integer compare. The inheritance walk only happens once per class (until
invalidated by `_LogLevel`).

When a class has no explicit override, the walk continues up the parent
chain until it finds one, falling back to the global default.

```bash
_LogLevel warn              # global = warn
_LogLevel debug Box         # Box = debug
# Cube inherits from Box, so Cube resolves to debug
# Map has no override, resolves to global warn
```

### Unloaded Classes

If `_Class` refers to a class that isn't in the registry (not loaded,
or a typo), the resolution walk can't find a parent chain. It falls
back to the global default. This is by design — logging should never
crash because of a missing class.

### Fallback Log File

If stderr is unavailable (closed, redirected), log output falls back
to `${TMPDIR:-/tmp}/boop_${PID}.log`. Per-process PID suffix prevents
concurrent sessions from stomping each other. The fallback path is
stored in `__boop_logFile` and can be overridden.

### Output Format

```
[LEVEL] caller: message
```

Where `caller` is the function name from the call stack (e.g.,
`Box.volume`, `main`). The log wrappers (`_Warn`, etc.) are
automatically skipped in the stack walk.

---

## Framework API Reference

### Core Functions

| Function | Description |
|----------|-------------|
| `__boop.new` | Object constructor. Generates ID, builds descriptor, registers, stubs methods. |
| `__boop.return` | Universal return handler. Routes values via nameref, stdout, global, or filesystem. |
| `__boop.dispatch` | Method dispatcher with MRO, caching, and lazy baking. |
| `__boop.parse` | Extract a field from a descriptor string. Decodes values. |
| `__boop.get` | Read a property from an object's descriptor. |
| `__boop.set` | Write a property to an object's descriptor. |
| `__boop.isa` | Type check with inheritance walk. |
| `__boop.toString` | Human-readable object display (compact or pretty). |
| `__boop.super` | Dispatch a method against the parent class. |
| `__boop.crash` | *Removed* — replaced by `_Crash` (see Logging below). |

### Logging

| Function | Description |
|----------|-------------|
| `_Trace` | Log at trace level (5). |
| `_Debug` | Log at debug level (4). |
| `_Info` | Log at info level (3). |
| `_Warn` | Log at warn level (2). |
| `_Error` | Log at error level (1). |
| `_Crash` | Exit with tagged message to stderr. Supports `_Err` (exit code) and `_StackTrace` (frame count). |
| `_LogLevel` | Set global or per-class log level. |
| `__boop.log` | Core log function (use the wrappers above instead). |
| `__boop.resolveLogLevel` | Resolve effective level for a class with caching. |
| `__boop.setLogLevel` | Set log level and invalidate cache. |

### Registration & Import

| Function | Description |
|----------|-------------|
| `__boop.registerMethod` | Map "Class.method" → implementing function in the method registry. |
| `__boop.registerClass` | Finalize a class: create class-level wrappers and constructor shorthand. |
| `__boop.stubAll` | Generate lazy stubs for all methods on an object. |
| `__boop.refresh` | Tear down baked wrappers and re-stub (for runtime method changes). |
| `__boop.import` | Resolve and source class files. |
| `__boop.validate` | Reject unsafe identifiers/function names. |

### Encoding

| Function | Description |
|----------|-------------|
| `__boop.encode` | Percent-encode pipes, equals, percents, newlines, tabs. |
| `__boop.decode` | Reverse of encode. |
| `__boop.bencode` | Base64 encode (binary-safe, requires subshell). |
| `__boop.bdecode` | Base64 decode (binary-safe, requires subshell). |

### Serialization

| Function | Description |
|----------|-------------|
| `__boop.serialize` | Dump registry to tab-delimited file. |
| `__boop.deserialize` | Load registry from tab-delimited file. |

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
| `__boop_returnMode` | Current global return mode (default: "auto"). |
| `__boop_dir` | Directory where boop lives (resolved at load time). |
| `__boop_RETURN` | Side-channel for global return mode. |
| `__boop_rootPID` | Root process PID (for subshell detection). |
| `__boop_loaded` | Framework initialization flag. |
| `__boop_logLevel` | Global default log level (default: 2/warn). |
| `__boop_classLogLevel` | Per-class log level overrides (associative array). |
| `__boop_resolvedLogLevel` | Cached resolved levels (associative array). |
| `__boop_logFile` | Fallback log file path when stderr is unavailable. |

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

boop does NOT set `set -u` (or any other shell option). The framework
should never alter the caller's shell environment. If you want `set -u`
in your scripts, set it yourself — boop will work fine with it.

If boop ever needs to temporarily change a shell option internally, it
saves and restores it. Your shell options are your business.

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
$id.volume    # works — object is in the main shell's registry
```

### Property Order

Properties in the descriptor reflect insertion order. Mutations
(via `set`) preserve position. Duplicate keys from constructor args
are allowed — both end up in the descriptor, but `get`/`parse` match
the first one. This is documented behavior, not a bug, but it's
probably not what you want. Don't pass the same key twice.

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
boop                          (root — get, set, isa, toString, new, super)
  ├── Box                          (3D geometry — volume, area, top, side, end, bottom)
  │     └── Cube                   (equal-sided Box — overrides geometry methods)
  ├── Container                    (virtual base — defines collection interface)
  │     ├── List                   (indexed array — push, pop, shift, slice, etc.)
  │     └── Map                    (insertion-ordered associative array — key-value pairs)
  ├── Iterator                     (stateful cursor — companion to Container, defined in Container file)
  └── Math                         (arbitrary precision arithmetic — pi, expressions, etc.)
```

When Container loads, it augments `boop` with `itemFrom` and `setOn`,
so every object (not just containers) can traverse containers stored in
its properties. It also registers the Iterator companion class.

---

## Project Structure

| File | What It Is |
|------|-----------|
| `boop` | The framework. Load this first, load this only. |
| `Box` | Example class: 3D rectangular prism. |
| `Cube` | Example class: equal-sided Box (inherits Box). |
| `Container` | Virtual base class for collections. Also defines the Iterator companion class. |
| `List` | Indexed array container. |
| `Map` | Insertion-ordered associative array container. |
| `Math` | Arbitrary precision arithmetic, pi, expression evaluators. |
| `TestSuite` | Structured test harness — assertions, sections, timing, quiet/verbose modes. |
| `docs/` | You are here. |
| `test_testsuite` | 31 tests — TestSuite testing itself. |
| `test_box_cube_ts` | 45 tests for Box and Cube. |
| `test_containers_ts` | 155 tests for Container, List, Map, Iterator, and delegation. |
| `test_math_ts` | 75 tests for Math (including pi verification). |
| `test_stress_ts` | 131 adversarial tests for the framework itself. |
| `test_logging_ts` | 51 tests for the logging system. |
| `test_pi_growth` | Incremental pi benchmark (not a TestSuite file). |
| `test_matrix` | Matrix operations benchmark (not a TestSuite file). |
