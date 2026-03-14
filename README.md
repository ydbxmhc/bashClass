# boop

A thought exercise on creating a useful OOP-like paradigm for Bash programming.

## What Is This?

An OOP dispatch framework for bash. Classes, objects, inheritance, method resolution,
property accessors, type checking — all built on associative arrays and naming conventions.
No external dependencies beyond bash 5+. The `bencode`/`bdecode` convenience wrappers
use coreutils `base64` if available, but the framework itself doesn't require it.

The framework file is called `boop` because fun is a feature. The internal namespace
remains `__bashClass_*` — the filename is the personality, the internals are the plumbing.

## Quick Example

```bash
# Load the framework and import classes
. boop Cube

# Create a cube
into=cube Cube size=4 unit=cm
$cube.volume                         # __bashClass_RETURN = 64

# Named return — no global side-channel
into=vol $cube.volume
printf "Volume: %s\n" "$vol"         # Volume: 64

# Type checking
$cube.isa Cube                       # returns 0 (true)
$cube.isa Box                        # returns 0 (true — inherits)

# Display
$cube.toString                       # Cube(_a1b2c3){ size=4 ... }
$cube.toString pretty                # columnar with newlines

# Also works with `new`
into=c2 new Cube size=4
```

## Import System

```bash
# Load framework + classes in one line
. boop Box Cube

# Classes resolve their own dependencies — Cube loads Box automatically
. boop Cube
```

Class files use load guards (`__bashClass_registry` check) to prevent double-loading.
The framework uses a `__bashClass_loading` flag to prevent circular recursion during
import chains.

## Conventions

The framework follows these conventions internally. We recommend class authors
do the same — it prevents real bugs (especially nameref collisions) and keeps
things predictable across the call stack.

- Local variables in methods are prefixed: `__ClassName_methodName_varname`
- Value-producing methods end with: `__bashClass.return "$val" ${into:-}`
- Delegating methods pass `into=localvar` as a typecast to capture results
- `printf` everywhere, never `echo`
- Two-space indentation, no tabs (literal `$'\t'` in code is fine)
- Leading `__` prefix is reserved for framework internals

## Container Classes

The framework ships with `Container`, `List`, and `Map` — a virtual base class and two
concrete implementations that wrap bash's native array types with object semantics.

```bash
. boop List Map

# Indexed list — push, pop, shift, unshift, slice, negative indices
into=colors List
$colors.push "red" "green" "blue"
into=first $colors.get 0          # "red"
into=last $colors.get -1          # "blue"
into=len $colors.length           # 3

# Associative map — key-value pairs
into=config Map
$config.set "host" "localhost"
$config.set "port" "8080"
into=h $config.get "host"         # "localhost"
$config.has "port" && printf "port is set\n"
```

Container data lives in companion bash arrays (`__bashClass_data_${self}`), not in the
pipe-delimited descriptor. This gives native bash array performance for element access
while the object system handles identity, dispatch, and lifecycle.

### Composition

List elements and Map values can be any string, including object IDs. Storing one
container's ID inside another creates nested structures — multidimensional arrays,
dictionaries of lists, whatever you need.

```bash
# Multidimensional array via nested Lists
into=matrix List
for (( r=0; r < 3; r++ )); do
  into=row List
  $row.push "$(( r*3+1 ))" "$(( r*3+2 ))" "$(( r*3+3 ))"
  $matrix.push "$row"
done

# Access: nameref chain (no subshells)
into=row $matrix.get 1
into=val $row.get 2               # "6"

# Access: subshell chain (one-liner, but forks)
val=$( $( $matrix.get 0 ).get 1 ) # "2"
```

### Virtual Base Class

`Container` defines the interface contract. Child classes implement `get`, `set`, `delete`,
`length`, `clear`, `has`, and `toArray`. Calling a virtual method on a bare Container
crashes with a message naming the actual class that forgot to implement it.

## Status

Active development on `refactor-dispatcher` branch. See `REFACTOR_STATUS.md` for details.

## Project Structure

- `boop` — Core framework (dispatch, registry, encoding, return handler, import system)
- `Container` — Virtual base class for container types
- `List` — Indexed array container (push/pop/shift/unshift/slice/negative indices)
- `Map` — Associative array container (key-value pairs, keys/values/has)
- `Box` / `Cube` — Example classes
- `test_box_cube` — Functional test suite (14 tests)
- `test_containers` — Container/List/Map test suite (66 tests)
- `test_matrix` — Matrix benchmark (nested Lists, transpose, flip)
- `test_stress` — Adversarial stress test suite (132 assertions + benchmark)
