# bashClass

A thought exercise on creating a useful OOP-like paradigm for Bash programming.

## What Is This?

An OOP dispatch framework for bash. Classes, objects, inheritance, method resolution,
property accessors, type checking — all built on associative arrays and naming conventions.
No external dependencies beyond bash 5+ and coreutils `base64`.

## Quick Example

```bash
source Cube_new

# Create a cube with size 4
class=Cube __bashClass.dispatch new size=4 unit=cm
cube="$__bashClass_RETURN"

# Use dotted method syntax
$cube.volume    # __bashClass_RETURN = 64
$cube.size      # __bashClass_RETURN = 4
$cube.isa Cube  # returns 0 (true)
$cube.isa Box   # returns 0 (true — Cube inherits from Box)
$cube.toString  # Cube(_a1b2c3){class=Cube size=4 unit=cm ...}
```

## Status

Active development on `refactor-dispatcher` branch. See `REFACTOR_STATUS.md` for details.

## Project Structure

- `bashDispatcher` — Core framework (dispatch, registry, encoding, return handler)
- `Box_new` / `Cube_new` — Example classes using the new system
- `test_box_cube` — Test suite
- `bashClass` / `bashObject` / `Box` / `Cube` — Original implementation (preserved)
