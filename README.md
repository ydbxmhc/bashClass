# boop

An OOP dispatch framework for bash 5+. Classes, objects, inheritance,
method resolution, property accessors, type checking — built on
associative arrays and naming conventions. No external dependencies.
No subshells in the hot path.

The framework file is called `boop` because fun is a feature. The
internal namespace is `__bashClass_*` — the filename is the personality,
the internals are the plumbing.

## Quick Start

```bash
# Load the framework and import a class
. boop Cube

# Create an object
into=c Cube size=4 unit=cm

# Call methods
into=vol $c.volume
printf "%s\n" "$vol"                 # 64

# Type checking walks the inheritance chain
$c.isa Cube && printf "it's a cube\n"    # it's a cube
$c.isa Box  && printf "it's a box\n"     # it's a box

# Display
$c.toString pretty
# Cube(_a1b2c3) {
#   size   = 4
#   unit   = cm
#   length = 4
#   width  = 4
#   height = 4
# }
```

## Requirements

- bash 5.0+ (associative arrays, `local -I`, `EPOCHREALTIME`, namerefs)
- That's it

macOS ships bash 3.2 (GPL2). `brew install bash` fixes that. If your
users might be on macOS, tell them up front.

The `bencode`/`bdecode` convenience wrappers use coreutils `base64` if
available, but the framework itself doesn't require it.

## Install

```bash
git clone <repo-url>
# Ensure the directory is in your PATH, or source with full path:
. /path/to/boop Cube
```

No build step. No package manager. Just files and a shell.

## The Return System

Every value-producing function routes through a universal return handler.
The recommended way to capture values:

```bash
# into= — direct nameref, no subshell, no global side-channel
into=vol $cube.volume               # vol="64"
into=name $map.get "host"           # name="localhost"

# Subshell capture works too (but forks)
vol=$( $cube.volume )               # vol="64"

# Global side-channel (overwritten by next call)
$cube.volume
printf "%s\n" "$__bashClass_RETURN"  # 64
```

`into=` is the fast path. Use it.

## Import System

```bash
# Load framework + classes in one line
. boop Box Cube Math

# Classes resolve their own dependencies
. boop Cube                          # loads Box automatically
```

Class files use load guards to prevent double-loading. The framework
uses a loading flag to prevent circular recursion during import chains.

Resolution order: `__bashClass_classPath` registry → `boop`'s directory
→ `PATH`.

## Collections

```bash
. boop List Map

# Indexed list
into=colors List
$colors.push "red" "green" "blue"
into=first $colors.get 0             # "red"
into=last  $colors.get -1            # "blue" (negative indices)

# Insertion-ordered associative map
into=config Map
$config.set "host" "localhost"
$config.set "port" "8080"
into=h $config.get "host"            # "localhost"
$config.has "port" && printf "yes\n"     # yes

# Keys come back in insertion order
into=k $config.keys                  # "host\nport" (not random hash order)
```

### Iteration

Two styles: callback-based (`each`) and cursor-based (Iterator).

```bash
# Callback — function called for each element
show() { printf "  %s = %s\n" "$1" "$2"; }
$config.each show
#   host = localhost
#   port = 8080

# Iterator — lazy, auto-created on first use
$colors.push "red" "green" "blue"
while $colors.hasNext; do
  into=val $colors.next
  printf "%s\n" "$val"
done
# red
# green
# blue
```

### Nested Structures

List elements and Map values can be object IDs, creating nested
structures — multidimensional arrays, dictionaries of lists, whatever:

```bash
into=matrix List
for (( r=0; r < 3; r++ )); do
  into=row List
  $row.push "$(( r*3+1 ))" "$(( r*3+2 ))" "$(( r*3+3 ))"
  $matrix.push "$row"
done

into=val $matrix.itemAt 1 2          # "6"
$matrix.setAt "99" 1 2               # matrix[1][2] = "99"
```

## Math

Arbitrary precision arithmetic. Numbers stored as digit strings with
tracked sign and decimal position. All arithmetic is digit-by-digit
using bash's native `$(( ))` on small chunks. No forks, no subshells.

```bash
. boop Math

# Static API — quick math, plain value strings
into=v Math.add 1.5 2.3              # "3.8"
into=v Math.multiply 2.5 4           # "10"
into=v Math.DO "( 10 + 5 ) / 3"     # "5"

# Pi to arbitrary precision
into=pi Math.pi 50
into=v $pi.val
printf "%s\n" "$v"
# 3.14159265358979323846264338327950288419716939937510
```

## Writing a Class

```bash
#!/bin/bash
[[ -n "${__bashClass_registry[MyClass]+set}" ]] && return 2>/dev/null
. boop

__bashClass_registry["MyClass"]="|class=MyClass|parent=bashClass\
|methods=new,greet|properties=name"

MyClass.new() {
  local -I _Class; : "${_Class:=MyClass}"
  local __MyClass_new_self
  into=__MyClass_new_self __bashClass.new "$@"
  __bashClass.return "$__MyClass_new_self" ${into:-}
}

MyClass.greet() {
  local -I _Self _Class
  local __MyClass_greet_name
  __bashClass.parse "$_Self" "name" __MyClass_greet_name
  __bashClass.return "Hello, $__MyClass_greet_name" ${into:-}
}

__bashClass.registerMethod MyClass new   MyClass.new
__bashClass.registerMethod MyClass greet MyClass.greet
__bashClass.registerClass MyClass
```

```bash
. boop MyClass
into=obj MyClass name=World
into=msg $obj.greet
printf "%s\n" "$msg"                 # Hello, World
```

See [docs/boop.md](docs/boop.md) for the full framework reference,
including inheritance, typecasting, the return system, naming conventions,
and all the gotchas.

## Conventions

- Local variables: `__ClassName_methodName_varname` (prevents nameref collisions)
- Value return: `__bashClass.return "$val" ${into:-}`
- Output: `printf` everywhere, never `echo`
- Framework internals: `__bashClass_*` prefix (hands off)

## Class Hierarchy

```
bashClass                          (root — get, set, isa, toString, new, super)
  ├── Box                          (3D geometry)
  │     └── Cube                   (equal-sided Box)
  ├── Container                    (virtual base for collections)
  │     ├── List                   (indexed array)
  │     └── Map                    (insertion-ordered associative array)
  ├── Iterator                     (stateful cursor — companion to Container)
  ├── Math                         (arbitrary precision arithmetic)
  └── TestSuite                    (structured test harness)
```

## Tests

All tests use the TestSuite class. Default output is quiet (failures +
summary only). Set `TESTSUITE_VERBOSE=1` for full output.

```bash
bash test_testsuite                  # 31 tests (TestSuite self-test)
bash test_box_cube_ts                # 45 tests
bash test_containers_ts              # 155 tests (List, Map, Iterator, delegation)
bash test_math_ts                    # 75 tests (includes pi verification)
bash test_stress_ts                  # 131 adversarial framework tests
bash test_logging_ts                 # 51 tests (logging system)
bash test_pi_growth                  # incremental pi benchmark (not TestSuite)
```

488 assertions across 6 TestSuite files, all passing.

## Documentation

Detailed docs for each class live in `docs/`:

- [boop (framework)](docs/boop.md) — the full reference
- [Box](docs/Box.md) / [Cube](docs/Cube.md) — geometry examples
- [Container](docs/Container.md) — virtual base + Iterator companion class
- [List](docs/List.md) / [Map](docs/Map.md) — collections
- [Math](docs/Math.md) — arbitrary precision arithmetic

## Status

Active development. See [PLAN.md](PLAN.md) for the roadmap.
