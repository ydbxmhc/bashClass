# Bash OOP Framework Refactoring Status

## Current Status: Core Implementation Complete — Testing & Hardening Phase

Branch: `refactor-dispatcher`

## What We Built

### Universal Dispatch System (`bashDispatcher`)

A complete OOP dispatch framework for bash built around a single associative array registry
with pipe-delimited descriptor values. Classes and objects share the same registry, distinguished
by their `type` field.

**Key architectural decisions:**

- **Single registry, descriptor values**: `__bashClass_registry["Box"]` holds a pipe-delimited
  string with all metadata (type, parent, methods, properties). Simple keys, O(1) lookup,
  self-documenting values.
- **Validate and reject**: No sanitization. If input is bad, crash. Period.
- **`__bashClass.return` universal handler**: Every function that produces a value routes through
  one function that respects the global `__bashClass_returnMode`. Supports `auto`, `nameref`,
  `stdout`, `global`, and `filesystem` modes. This means the user can set one knob and the
  entire framework adapts — want rock-solid file-based returns? Set `filesystem`. Want speed?
  Leave it on `auto` (defaults to `global` in main process, `stdout` in subshells).
- **Nameref-safe locals**: Every function prefixes its local variables with the function name
  (`__parse_key`, `__return_val`, `__encode_val`, etc.) to prevent nameref collisions across
  the call stack. This was discovered the hard way — bash namerefs resolve to the *nearest*
  matching name on the stack, so a `local value` in `__bashClass.return` would shadow the
  caller's `value`.
- **Dots in names**: Method and property names use dots (`Box.volume`, `$obj.length`) as a
  deliberate safety feature. `$obj.foo=123` fails because it's not a valid variable name.
  With underscores, `$obj_foo=123` would silently create a useless variable.
- **Single inheritance with MRO caching**: `dispatch` walks the parent chain on cache miss,
  then caches the result. Simple, fast after first call.
- **Typecast syntax**: Inline ephemeral variables as function options.
  `type=function __bashClass.validate "$name"` or `input=file __bashClass.bencode "$path"`.
  Leverages bash's `local -l` for case-insensitive matching.

### Class Hierarchy

```
bashClass (root — all standard methods registered here)
  └── Box (calc, area, top, end, side, bottom, volume, new)
        └── Cube (new, side, top, end, bottom, volume)
```

### Standard Interface Methods (inherited from bashClass)

| Method     | Description |
|------------|-------------|
| `new`      | Constructor. Generates unique object ID, builds descriptor, creates dotted wrapper functions (`$obj.method`) via eval. |
| `get`      | Retrieve a property value. Routes through `parse` → `return`. |
| `set`      | Update a property value. Encodes automatically. |
| `isa`      | Type checking with ancestry walk. No args returns class name. With arg, returns 0/1. |
| `toString` | Formats descriptor for display, skipping internal fields. |
| `super`    | Call parent class implementation of a method. |

### Encoding Stack

| Function   | Purpose | Subshell? |
|------------|---------|-----------|
| `encode`   | Escapes `%`, `\|`, `=`, newline, tab for safe descriptor storage | No |
| `decode`   | Reverses encode | No |
| `bencode`  | Base64 encode via external `base64` tool. For binary/null-safe data | Yes |
| `bdecode`  | Base64 decode. Reverse of bencode | Yes |

All four route through `__bashClass.return` and accept an optional nameref target as `$2`.

## What Changed From Original Design

- **Coprocess approach abandoned**: Discussed and explicitly rejected. Encapsulation by
  convention is sufficient. The IPC overhead wasn't worth it for what amounts to the same
  level of "privacy" that most languages provide at the bytecode level anyway.
- **Multiple inheritance deferred**: Single inheritance covers our needs. Can revisit later.
- **`__bashClass_refCounter` removed**: Was used for unique nameref names in `parse`. No longer
  needed after `__bashClass.return` centralized the return logic with its own scoped nameref.
- **`get` no longer hardcodes global mode**: Previously called `
parse` with `__bashClass_RETURN`
  as a forced nameref target. Now just calls `parse` with no target, letting the user's
  chosen return mode flow through.

## Known TODOs

### Typecast Variable Naming Convention
The typecast interface variables (`input`, `type`, `self`, `class`) use short common names
that could collide with user locals. Need to evaluate a convention that's still ergonomic
but safer. Candidates: `_Input`, `_Type` (leading underscore + mixed case), all caps, or
something else. Tracked in code as a TODO comment.

### `output=file` for bdecode
Binary round-trip is lossy through bash variables (nulls get dropped). Need an `output=file`
option on `bdecode` so decoded binary data can go straight to a file without passing through
a variable. Tracked in code as a TODO comment.

### Filesystem Return Mode — Path Introspection
When `__bashClass_returnMode=filesystem`, the return handler writes to a temp file. Currently
uses `FUNCNAME[1]` and `$BASHPID` for the filename. Plan is to build a dedicated function
that introspects the call stack (`FUNCNAME`, `BASH_ARGV`) to generate hierarchical paths
(e.g., `Box.length`) so the tmpdir is self-documenting. Uses `>|` to handle `noclobber`.

### `__bashClass.return` Stress Testing
Need a comprehensive test suite that exercises:
- All five return modes explicitly
- Nameref collisions (the bug we already found and fixed)
- Nested calls (encode inside parse inside dispatch)
- Subshell detection (auto mode switching)
- Edge cases: empty values, special characters, very long strings
- Tests that should succeed, tests that should fail, and tests designed to surprise us

### Clone, Destroy, Equals
Deferred. Expected to be more complex than they initially sound. `equals` is either trivially
easy (`[[ $this == $that ]]`) or sneaky-complex (deep comparison). Clone needs to handle
the wrapper functions. Destroy needs to clean up wrappers and registry entries.

### Composition Patterns
Prefer composition over inheritance. Need to document recommended patterns and possibly
provide helper methods.

## Files in This Branch

| File | Purpose |
|------|---------|
| `bashDispatcher` | Core framework — dispatch, registry, encoding, standard methods |
| `Box_new` | Box class implementation using new dispatcher |
| `Cube_new` | Cube class (extends Box) using new dispatcher |
| `test_box_cube` | Comprehensive test suite — 10 test groups |
| `bashClass` | Original framework (preserved for reference) |
| `bashObject` | Original object system (preserved for reference) |
| `Box` | Original Box (preserved for reference) |
| `Cube` | Original Cube (preserved for reference) |
| `test_Box` | Original Box test (preserved for reference) |
| `testCube` | Original Cube test (preserved for reference) |
| `README.md` | Project overview |
| `REFACTOR_STATUS.md` | This file |

## Design Philosophy

- **Consistency above all**: Every function that returns a value goes through `__bashClass.return`.
  No exceptions. If the user sets a mode, everything obeys it.
- **Validate and reject, never sanitize**: If they aren't following the API, that's their problem.
- **Dots as safety**: Method names use dots because `$obj.foo=123` fails where `$obj_foo=123` doesn't.
- **Lean and dense**: One-liners when possible. Curlies only for multiple commands.
- **printf everywhere**: Never echo.
- **Subshells only when unavoidable**: Namerefs and globals for internal plumbing. Subshells
  only for `base64` callouts and user-chosen stdout mode.
- **This is a personal project**: For learning and showcasing quirky bash skills. Fun is a feature.
