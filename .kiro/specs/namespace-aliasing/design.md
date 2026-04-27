# Design: Fully Qualified Class Names and Import Aliasing

## Architecture

### Alias Registry

A new global associative array:

```bash
declare -gA __boop_alias
# __boop_alias["Box"]="Geometry.Box"
# __boop_alias["Map.Fast"]="Collection.Map.Fast"
# __boop_alias["Fast"]="Collection.Map.Fast"
# __boop_alias["GBox"]="Geometry.Box"       (explicit _Import as)
# __boop_alias["A::B"]="Collection.Map.Fast" (explicit, literal key)
```

Aliases map user-facing names to FQNs. Looked up during:
- Constructor shorthand dispatch (`Box length=5`)
- Class-level method calls (`Math.add 1 2`)
- `isa` checks with short names

### Key Rules

- The **FQN** (internal) always uses dots: `Collection.Map.Fast`
- The **alias key** (user-facing) is stored exactly as specified.
  `_Import X as A::B` stores key `A::B`, not `A.B`.
- Only the **target** (FQN lookup) normalizes `::` and `/` to dots.
- The alias key is also used as the bash function name for
  constructor shorthands: `A::B.new` is a real function.

### Resolution Order

When a name is used (constructor, method call, isa):
1. Check `__boop_registry` directly (is it an FQN?)
2. Check `__boop_alias` (is it an alias? resolve to FQN)
3. Fail

### Auto-Aliasing

During class loading, the system attempts to create aliases at
multiple levels of the namespace hierarchy. For `Collection.Map.Fast`:

1. `Fast` (short name -- last segment)
2. `Map.Fast` (one level up)
3. `Collection.Map.Fast` (full FQN -- always succeeds, no collision)

Each level checks independently for collisions:
- If the alias key is not set, create it
- If it's already set to the SAME FQN, no-op
- If it's already set to a DIFFERENT FQN, skip (collision) and
  emit `_Info`

This means `Fast` might collide but `Map.Fast` might not. The
user gets the shortest unambiguous alias automatically.

### Auto-Alias Toggle

```bash
declare -g _AutoAlias="full"   # default
```

| Value | Behavior |
|-------|----------|
| `full` | Auto-alias at all levels (short + intermediate + full). Default. |
| `best` | Auto-alias only the shortest unique (unambiguous) level + full FQN. |
| `short` | Auto-alias only the short name + full FQN. |
| `none` | No auto-aliasing. Only explicit `_Import` creates aliases. Full FQN always works. |

Settable in `.booprc` or per-script. Useful for large projects
where auto-aliasing creates too much noise.

### _Import

```bash
# Load + auto-alias (same as loading, but explicit)
_Import Collection::Map::Fast
# _Require Collection.Map.Fast
# Auto-alias: Fast, Map.Fast, Collection.Map.Fast

# Load + explicit alias (overrides any existing)
_Import Collection::Map::Fast as MapFast
# _Require Collection.Map.Fast
# __boop_alias["MapFast"] = "Collection.Map.Fast"
# Overrides any existing alias for "MapFast"

# Explicit alias with :: in the alias name (literal, not normalized)
_Import Collection::Map::Fast as Map::Fast
# __boop_alias["Map::Fast"] = "Collection.Map.Fast"
# Constructor: Map::Fast.new
# Method call: Map::Fast.get

# Multiple aliases for the same class
_Import SomeClass as x1
_Import SomeClass as x2
# Both x1 and x2 resolve to SomeClass
# x1.new and x2.new both create SomeClass objects
```

### isa Behavior with Aliases

`isa` resolves through aliases before checking. The object's
descriptor stores the FQN, not the alias.

```bash
_Import SomeClass as x1
_Import SomeClass as x2
into=a x1.new
$a.isa x1         # true (x1 -> SomeClass, descriptor says SomeClass)
$a.isa x2         # true (x2 -> SomeClass, same FQN)
$a.isa SomeClass   # true (direct FQN match)
```

The object doesn't know which alias was used to create it.

### FQN Derivation

The FQN is derived from the filesystem path relative to the
library root, with `/` replaced by `.` and the trailing duplicate
segment dropped (R1 convention):

```
Collection/Map/Fast/Fast      ->  Collection.Map.Fast
Geometry/Box/Box              ->  Geometry.Box
Math/Math                     ->  Math
Testing/TestSuite/TestSuite   ->  Testing.TestSuite
```

### Class File Convention

```bash
# Load guard uses FQN
[[ -n "${__boop_registry[Geometry.Box]+set}" ]] && return 2>/dev/null

. boop

# Method functions use FQN
Geometry.Box.new() { ... }
Geometry.Box.volume() { ... }

# boopClass uses FQN
boopClass Geometry.Box 'has:length,width,height public:new,volume'
```

### Baked Wrappers

Baked wrappers on objects always call the FQN method function.
Never the alias. The alias is resolved once at construction time
and the FQN is baked in permanently.

Removing or changing an alias does NOT affect existing objects.

### Constructor Shorthands

When an alias is created, a constructor shorthand function is
generated:

```bash
# For alias "Box" -> "Geometry.Box":
Box() { Geometry.Box.new "$@"; }

# For alias "Map::Fast" -> "Collection.Map.Fast":
Map::Fast() { Collection.Map.Fast.new "$@"; }
```

If the alias changes, the shorthand is regenerated.

### Inheritance

Parent references in `boopClass` resolve through aliases:

```bash
# Full FQN (always works)
boopClass Geometry.Cube isa:Geometry.Box 'has:size public:new,side'

# Alias (resolved at registration time)
boopClass Geometry.Cube isa:Box 'has:size public:new,side'
```

Internally the descriptor always stores the FQN:
`|parent=Geometry.Box|`

## Migration Path

### Phase 1: Add alias infrastructure
- Add `__boop_alias` registry and `_AutoAlias` toggle
- Add `_Import` function
- Add alias resolution to constructor dispatch, method calls, `isa`
- Auto-alias on class load (multi-level)
- All existing code continues to work (FQN == short name for
  current classes with no namespace depth)

### Phase 2: Rename existing classes to FQN
- Update each class file: `boopClass`, method names, load guard,
  variable prefixes
- Update tests to match
- Auto-aliases keep backward compatibility -- `Box` still works

### Phase 3: New classes use FQN from the start
- `Collection.Map.Fast`, `Data.JSON`, etc.
- Short names work via auto-alias

## Deferred

- `_Import Geometry::*` (glob import) -- add later when needed
- Per-class alias scoping (aliases visible only in certain contexts)

