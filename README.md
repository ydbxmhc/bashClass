# boop

A thought exercise on creating a useful OOP-like paradigm for Bash programming.

## What Is This?

An OOP dispatch framework for bash. Classes, objects, inheritance, method resolution,
property accessors, type checking — all built on associative arrays and naming conventions.
No external dependencies beyond bash 5+ and coreutils `base64`.

The framework file is called `boop` because fun is a feature. The internal namespace
remains `__bashClass_*` — the filename is the personality, the internals are the plumbing.

## Quick Example

```bash
. boop Cube

# Three ways to create objects
new Cube size=4 unit=cm              # global convenience function
cube="$__bashClass_RETURN"

Cube size=4 unit=cm                  # class-as-constructor
cube="$__bashClass_RETURN"

class=Cube __bashClass.dispatch new size=4 unit=cm   # explicit dispatch
cube="$__bashClass_RETURN"

# Use dotted method syntax
$cube.volume    # __bashClass_RETURN = 64
$cube.size      # __bashClass_RETURN = 4
$cube.isa Cube  # returns 0 (true)
$cube.isa Box   # returns 0 (true — Cube inherits from Box)

# toString: compact or pretty
$cube.toString          # Cube(_a1b2c3){ size=4 unit=cm ... }
$cube.toString pretty   # columnar format with newlines

# Named return via __return typecast (no global side-channel)
__return=my_vol $cube.volume
printf "Volume: %s\n" "$my_vol"
```

## Import System

```bash
# Load framework + classes in one line
. boop Box Cube

# Classes resolve their own dependencies — Cube loads Box automatically
. boop Cube

# From anywhere (if boop is in PATH)
. "$(boop import)/boop" Cube
```

Class files use load guards (`__bashClass_registry` check) to prevent double-loading.
The framework uses a `__bashClass_loading` flag to prevent circular recursion during
import chains.

## Conventions

- All local variables in methods must be prefixed: `__ClassName_methodName_varname`
- Every value-producing method ends with: `__bashClass.return "$val" ${__return:-}`
- Delegating methods pass `__return=localvar` as a typecast to capture results
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
