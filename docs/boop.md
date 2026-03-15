# boop — The Framework

An OOP dispatch system for bash 5+. Classes, objects, inheritance, method
resolution, property accessors, type checking, value encoding, serialization,
and a universal return handler — all built on associative arrays and naming
conventions. No external dependencies. No subshells in the hot path. No
apologies.

The framework file is called `boop` because life is too short for
`bash_object_oriented_programming_framework.sh`. The internal namespace
is `__bashClass_*` — the filename is the personality, the internals are
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
(guarded by `__bashClass_loaded`) and only processes import arguments.
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
into=b class=Box __bashClass.dispatch new length=5 width=3 height=7
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
return handler (`__bashClass.return`). You choose how to receive the value.

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
__bashClass_returnMode=stdout $cube.volume
printf "\n"                     # (add a newline if you want one)

# That's a mouthful. Consider an alias:
alias show='__bashClass_returnMode=stdout'
show $cube.volume               # same thing, less typing

# Or use the global side-channel and print that
$cube.volume
printf "%s\n" "$__bashClass_RETURN"  # 64

# Subshell capture — classic bash, works anywhere
printf "Volume: %s\n" "$( $cube.volume )"  # Volume: 64
```

The first two avoid subshells entirely. The `__bashClass_returnMode=stdout`
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
printf "%s\n" "$__bashClass_RETURN"  # "64"
```

When no `into=` is provided and you're in the main shell, the value
lands in `__bashClass_RETURN`. It's a single flat global — the next
call overwrites it. Fine for quick one-offs, but `into=` is safer.

### Explicit Mode Override

```bash
__bashClass_returnMode=stdout $cube.volume    # force stdout
__bashClass_returnMode=nameref $cube.volume   # crash (no target!)
```

You can override the global mode per-call via environment prefix.
The modes are: `auto` (default), `global`, `stdout`, `nameref`,
`filesystem`. Auto does the right thing — global in main shell,
stdout in subshells.

```bash
# Change the default for the whole process
__bashClass.setDefaultMode stdout
```

---

## Properties: Get and Set

Every object inherits `get` and `set` from `bashClass`:

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
$cube.isa bashClass && printf "yes\n"   # 0 (true — everything does)
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
from `bashClass`, which provides `get`, `set`, `isa`, `toString`, `new`,
and `super`.

```
bashClass
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
2. On cache miss, walks the parent chain: Cube → Box → bashClass.
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
into=v class=Box $cube.volume
```

The baked wrapper detects the class mismatch and falls back to full
dispatch, so typecasts always resolve correctly even after baking.

### `super`

Call the parent class's implementation of a method:

```bash
# Inside a class method:
self=$self class=$class __bashClass.dispatch super volume
```

Crashes if you're already at the root (`bashClass` has no parent).

---

## Writing a Class

Here's the anatomy of a class file. This is `Box` — a real class in the
project, slightly condensed:

```bash
#!/bin/bash

# Load guard — skip if already registered
[[ -n "${__bashClass_registry[Box]+set}" ]] && return 2>/dev/null

# Load the framework (and any parent classes)
. boop

# --- Class Descriptor ---
# Pipe-delimited: class name, parent, method list, property list
__bashClass_registry["Box"]="|class=Box|parent=bashClass\
|methods=calc,area,top,end,side,bottom,volume,new\
|properties=length,width,height,unit,color"

# --- Method Implementations ---
# Convention: ClassName.methodName() { ... }

Box.volume() {
  local -I self class
  local __Box_volume_l __Box_volume_h __Box_volume_w __Box_volume_vol
  __bashClass.parse "$self" "length" __Box_volume_l
  __bashClass.parse "$self" "height" __Box_volume_h
  __bashClass.parse "$self" "width"  __Box_volume_w
  into=__Box_volume_vol required=3 Box.calc \
    "$__Box_volume_l" "$__Box_volume_h" "$__Box_volume_w"
  __bashClass.return "$__Box_volume_vol" ${into:-}
}

Box.new() {
  local -I class
  : "${class:=Box}"
  local __Box_new_self
  into=__Box_new_self __bashClass.new "$@"
  __bashClass.return "$__Box_new_self" ${into:-}
}

# ... other methods ...

# --- Registration ---
__bashClass.registerMethod Box volume Box.volume
__bashClass.registerMethod Box new     Box.new
# ... register all methods ...

# --- Finalize ---
__bashClass.registerClass Box
```

### The Pattern, Step by Step

1. **Load guard**: Check `__bashClass_registry[ClassName]+set`. If the
   class is already loaded, `return` immediately. The `2>/dev/null`
   silences the error when the file is executed directly (not sourced).

2. **Source dependencies**: `. boop ParentClass` loads the framework
   and any parent classes. The framework's import system handles
   circular prevention.

3. **Descriptor**: Register a pipe-delimited string in
   `__bashClass_registry["ClassName"]`. Fields:
   - `class=` — the class name
   - `parent=` — the parent class (use `bashClass` for root)
   - `methods=` — comma-separated list of method names
   - `properties=` — comma-separated list of property names

4. **Method functions**: Name them `ClassName.methodName`. Start with
   `local -I self class` to inherit the calling object's identity.
   End value-producing methods with `__bashClass.return "$val" ${into:-}`.

5. **Register methods**: `__bashClass.registerMethod ClassName method ClassName.method`
   for each method. The implementing function must exist at registration time.

6. **Finalize**: `__bashClass.registerClass ClassName` creates class-level
   wrappers and the constructor shorthand.

### Subclassing

Inherit from an existing class by setting `parent=` in the descriptor
and sourcing the parent:

```bash
#!/bin/bash
[[ -n "${__bashClass_registry[Cube]+set}" ]] && return 2>/dev/null

. boop Box    # loads Box (our parent)

__bashClass_registry["Cube"]="|class=Cube|parent=Box\
|methods=new,side,top,end,bottom,volume\
|properties=size,length,width,height,unit"

Cube.new() {
  local -I class
  : "${class:=Cube}"
  local __Cube_new_size=1 __Cube_new_self

  for __Cube_new_arg in "$@"; do
    [[ "$__Cube_new_arg" =~ ^size=([0-9]+)$ ]] && \
      __Cube_new_size="${BASH_REMATCH[1]}"
  done

  # Delegate to base constructor with derived dimensions
  into=__Cube_new_self __bashClass.new "$@" \
    length=$__Cube_new_size width=$__Cube_new_size height=$__Cube_new_size
  __bashClass.return "$__Cube_new_self" ${into:-}
}

# Override methods as needed...
Cube.volume() {
  local -I self class
  local __Cube_volume_size __Cube_volume_vol
  __bashClass.parse "$self" "size" __Cube_volume_size
  into=__Cube_volume_vol required=3 Box.calc \
    "$__Cube_volume_size" "$__Cube_volume_size" "$__Cube_volume_size"
  __bashClass.return "$__Cube_volume_vol" ${into:-}
}

# Register and finalize
__bashClass.registerMethod Cube new    Cube.new
__bashClass.registerMethod Cube volume Cube.volume
__bashClass.registerClass Cube
```

Methods not overridden are inherited. Cube gets `calc`, `area`, `get`,
`set`, `isa`, `toString` from its ancestors without doing anything.

---

## Naming Conventions

These aren't suggestions — they prevent real bugs.

| What | Convention | Why |
|------|-----------|-----|
| Local variables | `__ClassName_methodName_varname` | Prevents nameref collisions across the call stack. Bash namerefs resolve by name, not scope — if two functions both use `local val`, a nameref in the inner function can accidentally bind to the outer function's `val`. Prefixing makes names unique. |
| Value return | `__bashClass.return "$val" ${into:-}` | Routes through the universal return handler. The `${into:-}` passes the caller's nameref target (if any) so the value lands directly in their variable. |
| Delegation capture | `into=__ClassName_method_localvar SomeCall` | Captures a sub-call's return value into a prefixed local. Same collision-prevention logic. |
| Output | `printf`, never `echo` | `echo` interprets backslash escapes on some platforms. `printf` is predictable everywhere. |
| Framework internals | `__bashClass_*` or `__bashClass.*` | Leading double underscore = hands off. |

### The `local -I` Pattern

Most methods start with:

```bash
local -I self class
```

`local -I` (bash 5.1+) creates inherited locals — the variable is
local to this function but initialized with the value from the calling
scope. This is how `self` and `class` flow through the dispatch chain
without being passed as explicit arguments.

One gotcha: `local -I` variables are writable by callees in the same
scope chain. This matters for deep traversal methods (like `itemAt`)
where the cursor changes class on every step. Those methods use explicit
`self=` and `class=` environment prefixes on each dispatch call to
prevent leakage. See the Container source for the full explanation.

---

## The Import System

```bash
. boop Cube Math List
```

Arguments after `boop` are class names to import. Resolution order
(first match wins):

1. `__bashClass_classPath["ClassName"]` — explicit path override
2. `__bashClass_dir` — the directory where `boop` lives (co-located files)
3. `PATH` — the shell's standard search path

```bash
# Register a custom path for a class
__bashClass_classPath["MyClass"]="/opt/lib/MyClass"
. boop MyClass    # loads from /opt/lib/MyClass
```

### Load Guards

Two layers prevent double-loading and circular recursion:

- **Registry check**: If `__bashClass_registry[ClassName]` is already set,
  the class file's own load guard (`return 2>/dev/null`) skips it.
- **Loading flag**: `__bashClass_loading[ClassName]` is set while a class
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
__bashClass.serialize "state.dat"

# Load them back (in a new shell, or after clearing)
__bashClass.deserialize "state.dat"
```

The file format is tab-delimited: `key<TAB>descriptor` per line.
Keys are validated on load to prevent injection from tampered files.

Serialization captures descriptor data only. Baked wrapper functions
are NOT saved — they're regenerated on next access via the stub/bake
mechanism. After deserializing, call `__bashClass.refresh` on objects
you need to call methods on:

```bash
__bashClass.deserialize "state.dat"
__bashClass.refresh "$my_object_id"
$my_object_id.volume    # works — stubs regenerated
```

---

## Validation

Every user-supplied name that touches `eval`, registries, or dispatch
goes through `__bashClass.validate`:

```bash
__bashClass.validate "Box"                     # OK — valid identifier
__bashClass.validate "my-class"                # CRASH — dashes not allowed
type=function __bashClass.validate "Box.calc"  # OK — dots allowed in function mode
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

`__bashClass_static` is a global associative array available to any
function in any class for cross-call persistence:

```bash
# Cache a computed value
__bashClass_static["Math.pi.cache_20"]="3.14159265358979323846"

# Check the cache later
local cached="${__bashClass_static[Math.pi.cache_20]:-}"
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

Objects are entries in `__bashClass_registry`, a global associative array.
The key is the object ID (e.g., `_64d0895be1590`), the value is a
pipe-delimited descriptor string:

```
|class=Box|parent=bashClass|length=%335|width=%333|height=%337|
```

Values are percent-encoded (pipes, equals, percents, newlines, tabs)
so they don't corrupt the delimiter structure. `__bashClass.parse`
extracts and decodes fields by regex match on the descriptor string.

Classes are also entries in the same registry — distinguished by context,
not by a type field. `__bashClass_registry["Box"]` holds the class
descriptor (methods, properties, parent). `__bashClass_registry["_64d..."]`
holds an object descriptor (class, property values).

### Lazy Stubs and Baking

When an object is created, `stubAll` generates tiny eval'd functions
for every method:

```bash
# What stubAll generates (conceptually):
_64d0895be1590.volume() {
  __init=true self='_64d0895be1590' class='Box' \
    __bashClass.dispatch volume "$@"
}
```

On first call, `__init=true` tells dispatch to bake a direct wrapper:

```bash
# What dispatch bakes (conceptually):
_64d0895be1590.volume() {
  if [[ ${class:-Box} != 'Box' ]]; then
    self='_64d0895be1590' __bashClass.dispatch volume "$@"
  else
    self='_64d0895be1590' class='Box' Box.volume "$@"
  fi
}
```

The baked wrapper calls `Box.volume` directly — no dispatch, no MRO
walk, no registry lookup. The `if` guard handles typecasting: if someone
calls `class=OtherClass $obj.volume`, the baked class won't match, so
it falls back to dispatch for correct resolution.

Cost: one `eval` per method at object creation, one dispatch on first
call, then zero overhead forever after.

### Container Companion Arrays

Container subclasses (List, Map) store their data in separate bash
arrays (`__bashClass_data_${self}`), not in the pipe-delimited descriptor.
This gives native bash array performance for element access. The
descriptor only holds metadata (class, parent, type).

Why not encode arrays into the descriptor? Because bash arrays can't
nest inside associative arrays, and encoding list elements into a
pipe-delimited string would mean escaping delimiters inside delimiters.
Fragile, slow, and not worth the pain.

---

## Framework API Reference

### Core Functions

| Function | Description |
|----------|-------------|
| `__bashClass.new` | Object constructor. Generates ID, builds descriptor, registers, stubs methods. |
| `__bashClass.return` | Universal return handler. Routes values via nameref, stdout, global, or filesystem. |
| `__bashClass.dispatch` | Method dispatcher with MRO, caching, and lazy baking. |
| `__bashClass.parse` | Extract a field from a descriptor string. Decodes values. |
| `__bashClass.get` | Read a property from an object's descriptor. |
| `__bashClass.set` | Write a property to an object's descriptor. |
| `__bashClass.isa` | Type check with inheritance walk. |
| `__bashClass.toString` | Human-readable object display (compact or pretty). |
| `__bashClass.super` | Dispatch a method against the parent class. |
| `__bashClass.crash` | Exit with error message(s) to stderr. Optional custom exit code. |

### Registration & Import

| Function | Description |
|----------|-------------|
| `__bashClass.registerMethod` | Map "Class.method" → implementing function in the method registry. |
| `__bashClass.registerClass` | Finalize a class: create class-level wrappers and constructor shorthand. |
| `__bashClass.stubAll` | Generate lazy stubs for all methods on an object. |
| `__bashClass.refresh` | Tear down baked wrappers and re-stub (for runtime method changes). |
| `__bashClass.import` | Resolve and source class files. |
| `__bashClass.validate` | Reject unsafe identifiers/function names. |

### Encoding

| Function | Description |
|----------|-------------|
| `__bashClass.encode` | Percent-encode pipes, equals, percents, newlines, tabs. |
| `__bashClass.decode` | Reverse of encode. |
| `__bashClass.bencode` | Base64 encode (binary-safe, requires subshell). |
| `__bashClass.bdecode` | Base64 decode (binary-safe, requires subshell). |

### Serialization

| Function | Description |
|----------|-------------|
| `__bashClass.serialize` | Dump registry to tab-delimited file. |
| `__bashClass.deserialize` | Load registry from tab-delimited file. |

### Configuration

| Function | Description |
|----------|-------------|
| `__bashClass.setDefaultMode` | Set global return mode (auto/nameref/stdout/global/filesystem). |
| `__bashClass.inSubshell` | Returns 0 if current context is a subshell. |

### Global Variables

| Variable | Description |
|----------|-------------|
| `__bashClass_registry` | Master object/class store (associative array). |
| `__bashClass_methodRegistry` | Method resolution cache: "Class.method" → function name. |
| `__bashClass_classPath` | Explicit path overrides for class file resolution. |
| `__bashClass_loading` | In-progress load tracker (circular recursion prevention). |
| `__bashClass_static` | Cross-call static storage for any function. |
| `__bashClass_returnMode` | Current global return mode (default: "auto"). |
| `__bashClass_dir` | Directory where boop lives (resolved at load time). |
| `__bashClass_RETURN` | Side-channel for global return mode. |
| `__bashClass_rootPID` | Root process PID (for subshell detection). |
| `__bashClass_loaded` | Framework initialization flag. |

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
can leak its `class` value into the next iteration. These methods use
explicit `self=`/`class=` environment prefixes on every dispatch call
to prevent this. If you write your own traversal code that dispatches
to multiple different objects in sequence, you'll need the same pattern.
The Container source has a detailed block comment explaining this.

---

## The Class Hierarchy

```
bashClass                          (root — get, set, isa, toString, new, super)
  ├── Box                          (3D geometry — volume, area, top, side, end, bottom)
  │     └── Cube                   (equal-sided Box — overrides geometry methods)
  ├── Container                    (virtual base — defines collection interface)
  │     ├── List                   (indexed array — push, pop, shift, slice, etc.)
  │     └── Map                    (associative array — key-value pairs)
  └── Math                         (arbitrary precision arithmetic — pi, expressions, etc.)
```

When Container loads, it augments `bashClass` with `itemFrom` and `setOn`,
so every object (not just containers) can traverse containers stored in
its properties.

---

## Project Structure

| File | What It Is |
|------|-----------|
| `boop` | The framework. Load this first, load this only. |
| `Box` | Example class: 3D rectangular prism. |
| `Cube` | Example class: equal-sided Box (inherits Box). |
| `Container` | Virtual base class for collections. |
| `List` | Indexed array container. |
| `Map` | Associative array container. |
| `Math` | Arbitrary precision arithmetic, pi, expression evaluators. |
| `docs/` | You are here. |
| `test_box_cube` | 14 tests for Box and Cube. |
| `test_containers` | 88 tests for Container, List, and Map. |
| `test_math` | 75 tests for Math (including pi verification). |
| `test_stress` | 132 adversarial tests for the framework itself. |
| `test_pi_growth` | Incremental pi benchmark. |
| `test_matrix` | Matrix operations benchmark (nested Lists). |
