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

## Status

Active development on `refactor-dispatcher` branch. See `REFACTOR_STATUS.md` for details.

## Project Structure

- `boop` — Core framework (dispatch, registry, encoding, return handler, import system)
- `Box` / `Cube` — Example classes
- `test_box_cube` — Functional test suite (14 tests)
- `test_stress` — Adversarial stress test suite (132 assertions + benchmark)
