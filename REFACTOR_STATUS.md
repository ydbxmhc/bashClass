# Bash OOP Framework Refactoring Status

## Current Status: Core Implementation Complete — Testing & Hardening Phase

Branch: `refactor-dispatcher`

## What We Built

### Universal Dispatch System (`boop`)

A complete OOP dispatch framework for bash built around a single associative array registry
with pipe-delimited descriptor values. Classes and objects share the same registry, distinguished
by their `type` field. The framework file is named `boop` — the internal namespace remains
`__bashClass_*`.

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
  caller's `value`. User class methods follow the same convention: `Box.volume` uses
  `__Box_volume_l`, `__Box_volume_vol`, etc. If users don't follow this convention and
  get nameref collisions, that's on them.
- **`into` typecast for named returns**: Any value-producing method can accept a
  `into=varname` typecast prefix. The method passes `${into:-}` (unquoted) as the
  second argument to `__bashClass.return`, which writes directly into the caller's named
  variable via nameref. When `into` is unset, the expansion vanishes (no empty arg
  passed) and the global return mode governs. This enables zero-copy delegation chains:
  `into=__Box_volume_vol required=3 Box.calc "$l" "$h" "$w"` writes the result
  straight into `volume`'s local without touching `__bashClass_RETURN`. Thin wrappers
  like `Box.area` can pass through the caller's `into` directly:
  `required=2 into=${into:-} Box.calc "$@"`.
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

### Import System

The framework provides automatic class loading with path resolution and double-load
protection.

- `. boop Cube` — loads framework + imports Cube (which pulls in Box automatically)
- `__bashClass.import Box Cube` — programmatic import after framework is loaded

Resolution order: `__bashClass_classPath` registry → `__bashClass_dir` (co-located) → PATH.

Load guards: class files check `__bashClass_registry` on entry. The framework uses
`__bashClass_loading` to prevent circular recursion when a class file re-sources `boop`
as part of its own dependency chain.

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
Done. `test_stress` covers all five return modes, nameref collisions, nested calls,
subshell detection, edge cases, and adversarial inputs. 132 assertions across 27 sections.

### Rename bashClass → boop
Done. The framework file was renamed from `bashClass` to `boop`. Internal symbols
(`__bashClass_*`) were intentionally kept — the filename is the personality, the
internals are the plumbing. All source references, tests, and docs updated.

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
| `boop` | Core framework — dispatch, registry, encoding, standard methods, import system |
| `Box` | Box class implementation |
| `Cube` | Cube class (extends Box) |
| `test_box_cube` | Functional test suite — 14 test groups |
| `test_stress` | Adversarial stress test suite — 132 assertions + optional benchmark |
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

## Writing Class Methods — Conventions

### Local Variable Naming

All local variables in a method MUST be prefixed with `__ClassName_methodName_`. This
prevents nameref collisions when methods delegate to each other through the call stack.

```bash
# Good
Box.volume() {
  local -I self class
  local __Box_volume_l __Box_volume_h __Box_volume_w __Box_volume_vol
  ...
}

# Bad — will collide with other functions that use 'length'
Box.volume() {
  local -I self class
  local length height width vol
  ...
}
```

Framework internals use `__functionName_` (e.g., `__parse_key`, `__return_val`). User
class methods use `__ClassName_methodName_` (e.g., `__Box_volume_l`). If you don't
follow this convention and get nameref collisions, that's your problem.

### Returning Values

Every method that produces a value must end with:

```bash
__bashClass.return "$result" ${into:-}
```

The `${into:-}` is intentionally unquoted. When `into` is unset, it expands to
nothing and disappears — no empty argument is passed. When set to a valid identifier,
it passes through as the nameref target. Invalid identifiers crash at the nameref
assignment, which is correct behavior.

### Delegating to Other Methods

When calling another value-producing method, declare a prefixed local and pass its name
via the `into` typecast:

```bash
Box.volume() {
  local -I self class
  local __Box_volume_l __Box_volume_h __Box_volume_w __Box_volume_vol
  __bashClass.parse "$self" "length" __Box_volume_l
  __bashClass.parse "$self" "height" __Box_volume_h
  __bashClass.parse "$self" "width" __Box_volume_w
  into=__Box_volume_vol required=3 Box.calc "$__Box_volume_l" "$__Box_volume_h" "$__Box_volume_w"
  __bashClass.return "$__Box_volume_vol" ${into:-}
}
```

For thin wrappers that don't need to inspect the result, pass `into` through:

```bash
Box.area() {
  local -I self class
  required=2 into=${into:-} Box.calc "$@"
}
```

### Zero-Dimension Validation

`Box.calc` rejects zero and non-integer arguments. The check:

```bash
[[ "${arg:-}" =~ ^[0-9]+$ ]] && ((arg)) || __bashClass.crash "..."
```

The `&&` chain validates: (1) it's a digit string, AND (2) it's nonzero. If either
fails, the `||` fires the crash. A box with a zero dimension is nonsensical.
