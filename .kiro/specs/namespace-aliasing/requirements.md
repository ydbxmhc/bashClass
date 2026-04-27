# Requirements: Fully Qualified Class Names and Import Aliasing

## Overview

Classes must use fully qualified namespace names internally to prevent
collisions when multiple namespaces define classes with the same short
name. Short names remain available as aliases for convenience, with
automatic aliasing when unambiguous and explicit aliasing for
disambiguation.

## Definitions

- **FQN (Fully Qualified Name)**: The complete namespace-qualified
  class name using dots as separators. Examples: `Geometry.Box`,
  `Collection.Map.Fast`, `Math.Math`.
- **Short Name**: The final segment of the FQN. Examples: `Box`,
  `Fast`, `Math`.
- **Alias**: A mapping from a user-facing name to an FQN. Can be
  the short name or a custom name via `_Import ... as ...`.

## Requirements

### 1. Internal Registration

1.1 Classes SHALL register in `__boop_registry` using their FQN.

1.2 Method functions SHALL be named using the FQN:
    `Geometry.Box.volume`, `Collection.Map.Fast.get`.

1.3 The method registry SHALL use FQN keys:
    `__boop_methodRegistry["Geometry.Box.volume"]`.

1.4 Internal variable prefixes SHALL use the FQN with dots replaced
    by underscores: `__Geometry_Box_volume_result`.

1.5 `boopClass` SHALL accept the FQN as the class name.

### 2. Automatic Aliasing

2.1 When a class is loaded, the system SHALL attempt to create
    aliases at multiple levels of the namespace hierarchy.
    For `Collection.Map.Fast`: `Fast`, `Map.Fast`, and
    `Collection.Map.Fast`.

2.2 Each alias level SHALL check independently for collisions.
    If the alias key already maps to a different FQN, that level
    is skipped with `_Info`. Other levels may still succeed.

2.3 The full FQN alias SHALL always succeed (no collision possible).

2.4 Index entries SHALL auto-alias on load using the same multi-level
    logic.

2.5 The alias registry SHALL be a global associative array mapping
    alias names to FQNs.

2.6 A global toggle `_AutoAlias` SHALL control auto-aliasing behavior:
    `full` (all levels, default), `best` (shortest unique alias + FQN
    only), `short` (short name + FQN only), `none` (no auto-aliasing,
    explicit `_Import` only).

2.7 `_AutoAlias` SHALL be settable in `.booprc` or per-script.

### 3. Explicit Import

3.1 `_Import ClassName` SHALL load the class (via `_Require`) AND
    create a short-name alias.

3.2 `_Import Namespace::Class as Alias` SHALL load the class AND
    create an alias with the specified name, stored literally
    (no normalization of the alias key).

3.3 Explicit `_Import` SHALL override any existing alias
    (implicit or explicit) for the same alias name.

3.4 `_Import` SHALL normalize `::` and `/` to `.` in the FQN
    target only. The alias key is stored as-is.

3.5 Multiple aliases for the same FQN SHALL be supported.
    `_Import X as a` and `_Import X as b` both work.

### 4. Full Qualification

4.1 The full qualified name SHALL always work for class construction,
    method calls, and `isa` checks, regardless of aliases.

4.2 `into=b Geometry.Box length=5` SHALL work even if no alias
    exists for `Box`.

### 5. Baked Wrappers

5.1 Baked wrappers on objects SHALL call the FQN method function
    internally, never the alias.

5.2 Constructor shorthands (`Box length=5`) SHALL resolve through
    the alias registry to find the FQN.

5.3 Removing or changing an alias SHALL NOT affect existing objects
    or their baked wrappers.

### 6. Backward Compatibility

6.1 Existing classes with unique short names SHALL continue to work
    with no code changes. Their FQN equals their current name (or
    the auto-alias makes them equivalent).

6.2 Existing scripts using short names SHALL continue to work as
    long as the short names remain unambiguous.

6.3 The `. boop ClassName` syntax SHALL continue to work, resolving
    through the alias/index system.

### 7. Class File Convention

7.1 Class files SHALL declare their FQN in the `boopClass` call.

7.2 The FQN SHALL match the filesystem namespace path with dots
    as separators: `Collection/Map/Fast/Fast` -> `Collection.Map.Fast`.

7.3 Load guards SHALL use the FQN:
    `[[ -n "${__boop_registry[Collection.Map.Fast]+set}" ]] && return`

