# Requirements Document

## Introduction

The boop bash OOP framework currently resolves class files via a flat, single-directory layout with trivial fallback to `PATH`. This system implements the namespace resolution, short-name index, configuration persistence, and public API needed to support namespaced class organization, multi-root library search, and user-configurable class path overrides. The scope covers four components: rewriting `__boop.import` for namespace-aware multi-root resolution, the `.boopIndex` short-name index system, the `.booprc`/`.boop.cfg` configuration convention, and the `boop.classPath` public API.

## Glossary

- **Import_System**: The `__boop.import` function in the `boop` framework file, responsible for resolving class names to filesystem paths and sourcing class files.
- **Namespace**: A `::` delimited hierarchical identifier for a class (e.g., `Collection::List`). Maps to directory separators on disk.
- **Short_Name**: The final segment of a namespace identifier (e.g., `List` from `Collection::List`). Used for convenient bare-name imports.
- **Library_Root**: A directory containing a boop namespace tree, a `.boopIndex`, and optionally `.booprc`/`.boop.cfg` files. The framework directory (`__boop_dir`) is always the first root.
- **Root_List**: The ordered sequence of Library_Roots searched during import resolution: `__boop_dir` first, then `BOOPPATH` entries left to right, then `PATH` as final fallback.
- **BOOPPATH**: A colon-delimited environment variable listing additional Library_Root directories, analogous to `PATH`/`GOPATH`/`MANPATH`.
- **BoopIndex**: A `.boopIndex` file at each Library_Root containing a `declare -gA __boop_Index` associative array mapping Short_Names to full Namespace paths.
- **ClassPath_Registry**: The `__boop_classPath` associative array providing explicit per-class path overrides that take highest priority during resolution.
- **Namespace_Convention**: The filesystem mapping rule where `A::B` resolves to `root/A/B/B` — the class file shares the name of its innermost namespace segment and lives inside a directory of the same name.
- **RC_File**: A `.booprc` file — a human-editable bash script sourced during framework initialization, analogous to `.bashrc`.
- **CFG_File**: A `.boop.cfg` file — a machine-managed configuration file serialized by `boop.classPath`, containing structured declarations (hash assignments). Never hand-edited.
- **Loader**: The `__boop.loader` internal method responsible for the RC/CFG bootstrap sequence and BOOPPATH parsing during framework initialization.
- **ClassPath_API**: The `boop.classPath` public method providing subcommands (`set`, `get`, `list`, `remove`, `has`, `dirs`, `rebuild`) for runtime manipulation of the ClassPath_Registry and configuration persistence.
- **Depth_First_Resolution**: The default search strategy where all resolution steps (classPath override, index lookup, filesystem convention, bare file) are exhausted within one Library_Root before moving to the next.

## Requirements

### Requirement 1: Namespace-to-Filesystem Mapping

**User Story:** As a framework developer, I want a deterministic
rule that converts any class identifier into a filesystem path so
that the import system, the index generator, and the install script
all agree on where a class file lives.

#### Definitions

A **namespace identifier** is a string that names a class,
optionally including its namespace path. The conventional
separator is `::` for readability in code. The `/` separator
is equally valid.

Internally, the import system normalizes `::` to `/` via simple
string substitution. After normalization, the result is treated
as a relative path. No splitting into segments is required.

This means:
- `. boop Collection::List` and `. boop Collection/List` are
  identical after normalization.
- Class and namespace names MAY contain single colons (e.g.,
  `:X`, `X:`). To use such names, use `/` as the separator
  instead of `::` to avoid ambiguous parsing. This is a
  documented edge case, not a primary use pattern.

#### Resolution Rule

After normalization, let `class` be the resulting path string.
The import system resolves it in two checks per Library_Root:

1. **Namespace convention:** try `root/$class/${class##*/}`
   (the class path, plus the last component repeated as a
   file inside a same-named directory)
2. **Bare file fallback:** try `root/$class`

First readable file wins. The filesystem enforces mutual
exclusivity — a path cannot be both a file and a directory —
so there is no ambiguity.

Examples:

| User writes | After normalization | Step 1 (try first) | Step 2 (fallback) |
|---|---|---|---|
| `Math` | `Math` | `root/Math/Math` | `root/Math` |
| `Math::Trig` | `Math/Trig` | `root/Math/Trig/Trig` | `root/Math/Trig` |
| `Collection::List` | `Collection/List` | `root/Collection/List/List` | `root/Collection/List` |
| `Math::Math` | `Math/Math` | `root/Math/Math/Math` | `root/Math/Math` |

#### Acceptance Criteria

1. THE Import_System SHALL normalize `::` to `/` via string substitution before resolution.
2. FOR each Library_Root, THE Import_System SHALL first check whether `root/$class/${class##*/}` exists and is a readable file. IF so, it SHALL be used.
3. WHEN the namespace convention path does not exist, THE Import_System SHALL check whether `root/$class` exists and is a readable file. IF so, it SHALL be used.
4. THE Import_System SHALL reject empty identifiers and identifiers that resolve to empty paths. WHEN this occurs, THE Import_System SHALL call `_Crash`.
5. THE resolution rule SHALL be applied consistently by the Import_System, `boop.classPath rebuild`, and `boop_install`.
6. THIS requirement defines the mapping convention only. The full resolution order is specified in Requirement 2.

### Requirement 2: Bootstrap and Resolution Order

**User Story:** As a framework user, I want boop to bootstrap
itself from PATH, load my configuration, and then resolve classes
through a clear priority chain so that I can control where classes
come from without fighting the framework.

#### Bootstrap Sequence

1. User sources `boop` (bash finds it via `PATH` or explicit path).
2. `boop` loads its own definitions (globals, functions, etc.).
3. `boop` sources the RC chain: `/etc/booprc` → `~/.booprc` →
   `./.booprc` (each may source its own `.boop.cfg`, set
   `BOOPPATH`, populate the index, etc.).
4. `boop` processes its import arguments (the class names passed
   after `boop` on the source line).

#### Class Resolution Order

When the import system needs to find a class, it checks in this
order:

1. **Already loaded** — if the class is in `__boop_registry`,
   skip (already sourced).
2. **Explicit override** — if `__boop_classPath["class"]` is set,
   source that path directly.
3. **Index** — if `__boop_Index["class"]` is set, normalize the
   value and apply the R1 resolution rule (namespace convention
   then bare file) against each root in the effective BOOPPATH.
4. **Dynamic discovery** — for each root in the effective
   BOOPPATH, apply the R1 resolution rule using the class name.
5. **Raw source fallback** — attempt `. "$class"` as a last
   resort, in case bash's native source resolution finds
   something the two-check rule missed.
6. **Failure** — `_Crash` with a message listing the class name
   and the locations that were searched.

The **effective BOOPPATH** is the user's `BOOPPATH` with `PATH`
appended. This means dynamic discovery searches BOOPPATH roots
first, then PATH directories, in one unified loop. A user MAY
duplicate PATH entries in BOOPPATH to change their priority order.

During dynamic discovery, the import system SHALL maintain a
scratchpad of roots already checked and skip duplicates. A root
is a duplicate only if it is the exact same path — a root that
is a subdirectory of a previously checked root is NOT a duplicate
and SHALL be checked independently.

`__boop_dir` is not a separate concept in the resolution order.
The directory where `boop` lives was already on `PATH` (that's
how it was found), so it is covered by the implicit PATH
appendage. If a user wants that directory searched with higher
priority, they add it to `BOOPPATH` explicitly.

#### Acceptance Criteria

1. THE Import_System SHALL source the RC chain (Requirement 7) before processing any import arguments.
2. WHEN a class is already in `__boop_registry`, THE Import_System SHALL skip it without any filesystem checks.
3. WHEN `__boop_classPath` contains an entry for the class, THE Import_System SHALL source that path directly, skipping all other resolution steps.
4. THE Import_System SHALL construct the effective BOOPPATH as: the current working directory (`.`), then `BOOPPATH` entries, then `PATH` entries.
5. DURING dynamic discovery, THE Import_System SHALL track roots already checked in a scratchpad associative array and skip exact duplicates. Subdirectories of previously checked roots SHALL NOT be treated as duplicates. THE Import_System SHALL unset the scratchpad when resolution completes (whether successful or not).
6. WHEN `__boop_Index` contains an entry for the class, THE Import_System SHALL resolve the index value against each root in the effective BOOPPATH using the R1 resolution rule.
7. WHEN the index does not contain the class, THE Import_System SHALL attempt dynamic discovery against each root in the effective BOOPPATH using the R1 resolution rule.
8. WHEN all prior steps fail, THE Import_System SHALL attempt `. "$class"` as a raw source fallback.
9. WHEN the raw source fallback also fails, THE Import_System SHALL call `_Crash` with a message listing the class name and the locations searched.

#### Implementation Note

The resolution logic (steps 2–8) SHALL be factored into an
internal `__boop.resolve` function that returns the resolved
file path (or empty string on failure) without sourcing. The
import system calls `__boop.resolve` then sources the result.
A public `boop.resolve` method exposes this as a non-fatal
interrogation: returns exit code 0 and the path via `boop.pass`
if found, exit code 1 if not. Usage:

```bash
if into=loc boop.resolve Math::Trig; then
  . "$loc"
fi
```

### Requirement 3: Import Load Guards

**User Story:** As a framework developer, I want the existing load guard and circular-recursion protection to continue working with the new resolution system so that class loading remains safe.

#### Acceptance Criteria

1. WHEN a class is already registered in `__boop_registry`, THE Import_System SHALL skip resolution entirely and continue to the next argument.
2. WHEN a class has `__boop_loading` set to 1, THE Import_System SHALL skip resolution entirely and continue to the next argument.
3. WHEN a class file is successfully sourced, THE Import_System SHALL unset the `__boop_loading` entry for that class.
4. IF a class file fails to source (non-zero exit code), THEN THE Import_System SHALL call `_Crash` with a message identifying the class name and the file path that failed.

### Requirement 4: BoopIndex File Format

**User Story:** As a framework maintainer, I want a persisted index file at each library root so that short-name lookups are fast and do not require filesystem scanning on every import.

#### Acceptance Criteria

1. THE BoopIndex file SHALL be named `.boopIndex` and located at the top level of a Library_Root.
2. THE BoopIndex file SHALL be a sourceable bash script that populates the in-memory `__boop_Index` associative array with short-name → namespace-path mappings.
3. WHEN the BoopIndex is sourced, THE Loader SHALL merge its entries into the in-memory `__boop_Index` associative array.
4. WHEN multiple Library_Roots define the same Short_Name in their respective BoopIndex files, THE Loader SHALL use the entry from the first Library_Root in the Root_List (earlier roots take precedence).

### Requirement 5: BoopIndex Generation and Conflict Detection

**User Story:** As a framework maintainer, I want the index to be auto-generated by scanning the namespace tree so that I do not have to maintain it by hand.

#### Acceptance Criteria

1. WHEN `boop.classPath rebuild` is invoked, THE ClassPath_API SHALL scan the namespace tree of the target Library_Root and regenerate the `.boopIndex` file.
2. WHEN two or more namespaces within the same Library_Root define a class with the same Short_Name, THE ClassPath_API SHALL remove that Short_Name from the generated BoopIndex.
3. WHEN a Short_Name conflict is detected during rebuild, THE ClassPath_API SHALL emit an `_Info` diagnostic listing the conflicting namespaces.
4. THE BoopIndex SHALL be a declaration, not a cache — filesystem fallback hits SHALL NOT auto-update the BoopIndex.
5. WHEN a class is resolved via filesystem fallback (steps c or d), THE Import_System SHALL emit an `_Info` diagnostic suggesting the user register the class or run `rebuild`.

### Requirement 6: RC File Convention

**User Story:** As a framework user, I want human-editable configuration files sourced at startup so that I can customize framework behavior per-system, per-user, and per-project.

#### Acceptance Criteria

1. THE Loader SHALL source RC_Files in this precedence order: `/etc/booprc` first, then `~/.booprc`, then `./.booprc`.
2. WHEN an RC_File does not exist at a given tier, THE Loader SHALL skip it silently and proceed to the next tier.
3. EACH RC_File SHALL be responsible for sourcing its own co-located CFG_File (e.g., `~/.booprc` sources `~/.boop.cfg`).
4. WHEN an RC_File exists but fails to source (non-zero exit code), THE Loader SHALL call `_Crash` with a message identifying the offending file.
5. WHEN the RC chain or BOOPPATH configuration indicates a preferred boop version (via `__boop_version` comparison) that differs from the currently loaded version, THE Loader SHALL emit a `_Warn` diagnostic identifying the mismatch and the path to the preferred version.

### Requirement 7: CFG File Convention

**User Story:** As a framework user, I want machine-managed configuration files that persist my classPath registrations across sessions so that I do not have to re-register paths on every shell startup.

#### Acceptance Criteria

1. THE CFG_File SHALL contain only structured declarations: `__boop_classPath` hash assignments and no procedural logic.
2. WHEN `boop.classPath set` or `boop.classPath remove` is invoked, THE ClassPath_API SHALL rewrite the target CFG_File as a complete serialization of the current ClassPath_Registry state.
3. THE ClassPath_API SHALL default to writing `~/.boop.cfg` unless the caller overrides the target via `_CfgFile` environment variable.
4. WHEN `_CfgFile` is set, THE ClassPath_API SHALL read from and write to the specified path instead of `~/.boop.cfg`.
5. WHEN a CFG_File does not exist at a given tier, THE Loader SHALL skip it silently.

### Requirement 8: BOOPPATH Parsing

**User Story:** As a framework user, I want to specify additional library roots via an environment variable so that I can install third-party boop libraries in arbitrary locations.

#### Acceptance Criteria

1. THE Loader SHALL parse the `BOOPPATH` environment variable by splitting on colon (`:`) delimiters.
2. WHEN a `BOOPPATH` entry refers to a directory that does not exist, THE Loader SHALL emit an `_Info` diagnostic and skip that entry.
3. WHEN `BOOPPATH` contains empty segments (e.g., from trailing or double colons), THE Loader SHALL ignore the empty segments.
4. THE Loader SHALL source the `.boopIndex` file from each valid Library_Root during initialization. WHEN multiple roots define the same short name, earlier roots in the effective BOOPPATH SHALL take precedence (the implementation strategy for achieving this is unspecified).

### Requirement 9: ClassPath API — `set` Subcommand

**User Story:** As a framework user, I want to register an explicit path override for a class so that I can point the import system at a specific file regardless of namespace conventions.

#### Acceptance Criteria

1. WHEN `boop.classPath set ClassName /path/to/file` is invoked, THE ClassPath_API SHALL store the mapping in `__boop_classPath["ClassName"]`.
2. WHEN `boop.classPath set` is invoked, THE ClassPath_API SHALL validate that the class name is non-empty.
3. WHEN `boop.classPath set` is invoked with a path that does not exist or is not a readable file, THE ClassPath_API SHALL call `_Crash` with a descriptive message.
4. WHEN `boop.classPath set` overwrites an existing registration, THE ClassPath_API SHALL emit an `_Info` diagnostic noting the override.
5. WHEN `boop.classPath set` succeeds, THE ClassPath_API SHALL rewrite the target CFG_File with the updated ClassPath_Registry state.

### Requirement 10: ClassPath API — `get` Subcommand

**User Story:** As a framework user, I want to query the registered path for a class so that I can verify or script against the current configuration.

#### Acceptance Criteria

1. WHEN `boop.classPath get ClassName` is invoked and the class is registered, THE ClassPath_API SHALL return the registered path via `boop.pass`.
2. WHEN `boop.classPath get ClassName` is invoked and the class is not registered, THE ClassPath_API SHALL return an empty string via `boop.pass`.

### Requirement 11: ClassPath API — `list` Subcommand

**User Story:** As a framework user, I want to see all registered classPath overrides so that I can audit the current configuration.

#### Acceptance Criteria

1. WHEN `boop.classPath list` is invoked, THE ClassPath_API SHALL return all entries in the ClassPath_Registry formatted as `ClassName=/path/to/file` lines via `boop.pass`.
2. WHEN the ClassPath_Registry is empty, THE ClassPath_API SHALL return an empty string via `boop.pass`.

### Requirement 12: ClassPath API — `remove` Subcommand

**User Story:** As a framework user, I want to unregister a classPath override so that the import system falls back to normal resolution for that class.

#### Acceptance Criteria

1. WHEN `boop.classPath remove ClassName` is invoked and the class is registered, THE ClassPath_API SHALL remove the entry from `__boop_classPath`.
2. WHEN `boop.classPath remove ClassName` succeeds, THE ClassPath_API SHALL rewrite the target CFG_File with the updated ClassPath_Registry state.
3. WHEN `boop.classPath remove ClassName` is invoked and the class is not registered, THE ClassPath_API SHALL emit an `_Info` diagnostic and take no further action.

### Requirement 13: ClassPath API — `has` Subcommand

**User Story:** As a framework user, I want to test whether a class has an explicit classPath registration so that I can script conditional behavior.

#### Acceptance Criteria

1. WHEN `boop.classPath has ClassName` is invoked and the class is registered in `__boop_classPath`, THE ClassPath_API SHALL return exit code 0.
2. WHEN `boop.classPath has ClassName` is invoked and the class is not registered, THE ClassPath_API SHALL return exit code 1.

### Requirement 14: ClassPath API — `dirs` Subcommand

**User Story:** As a framework user, I want to see the effective root search order so that I can debug resolution issues.

#### Acceptance Criteria

1. WHEN `boop.classPath dirs` is invoked, THE ClassPath_API SHALL return the effective BOOPPATH entries (one per line) in search order via `boop.pass`.
2. THE `dirs` output SHALL include `.` (current directory) first, then each valid `BOOPPATH` entry, then each `PATH` entry, in the order they would be searched.

### Requirement 15: ClassPath API — `rebuild` Subcommand

**User Story:** As a framework maintainer, I want to regenerate the `.boopIndex` by scanning the namespace tree so that the index reflects the current filesystem state.

#### Acceptance Criteria

1. WHEN `boop.classPath rebuild` is invoked, THE ClassPath_API SHALL scan the namespace tree of the target Library_Root.
2. THE `rebuild` scan SHALL discover class files by walking directories recursively and identifying files that match the R1 resolution convention.
3. WHEN `rebuild` completes, THE ClassPath_API SHALL write the generated BoopIndex to the `.boopIndex` file at the target Library_Root.
4. WHEN `rebuild` detects Short_Name conflicts, THE ClassPath_API SHALL exclude the conflicting Short_Name from the BoopIndex and emit an `_Info` diagnostic for each conflict.

### Requirement 16: ClassPath API Return Convention

**User Story:** As a framework user, I want the classPath API to follow the standard boop return convention so that `into=` variable capture works consistently.

#### Acceptance Criteria

1. THE ClassPath_API `get`, `list`, and `dirs` subcommands SHALL return values via `boop.pass` so that `into=` variable capture works.
2. THE ClassPath_API `has` subcommand SHALL communicate via exit code only (0 for found, 1 for not found) and SHALL NOT call `boop.pass`.
3. THE ClassPath_API `set`, `remove`, and `rebuild` subcommands SHALL return no value via `boop.pass` on success (mutation operations).
