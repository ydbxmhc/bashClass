# Implementation Plan: Classpath Namespace System

## Overview

Replace the flat `__boop.import` with a namespace-aware, multi-root resolution system. Implementation proceeds bottom-up: core resolution primitives first, then the loader/bootstrap, then the public API, then wiring into the existing import path. Each task builds on the previous and ends with integration.

## Tasks

- [x] 1. Define new globals and factor out `__boop.resolve`
  - [x] 1.1 Declare new global variables in `boop`
    - Add `declare -gA __boop_Index` (short-name → namespace-path index)
    - Add `declare -gr __boop_version` with a version string
    - Remove `__boop_dir` usage from the codebase (its directory is already on `PATH`)
    - _Requirements: 1.1, 2.4_

  - [x] 1.2 Implement namespace normalization in `__boop.resolve`
    - Create `__boop.resolve()` function in `boop`
    - Normalize `::` to `/` via bash string substitution (`${class//::///}`)
    - Reject empty identifiers with `_Crash`
    - _Requirements: 1.1, 1.4_

  - [x] 1.3 Implement R1 resolution rule inside `__boop.resolve`
    - For a given root and normalized class, try `root/$class/${class##*/}` first (readable file check)
    - Fall back to `root/$class` (readable file check)
    - _Requirements: 1.2, 1.3_

  - [x] 1.4 Implement the full resolution priority chain in `__boop.resolve`
    - Check `__boop_classPath["$class"]` first — return if set and readable
    - Check `__boop_Index["$class"]` — if set, normalize index value, apply R1 against each root
    - Dynamic discovery — apply R1 against each root using the normalized class name
    - Build effective root list: `.` + `BOOPPATH` entries + `PATH` entries
    - Deduplicate roots via scratchpad associative array (exact path match only); unset scratchpad on completion
    - Return resolved path or empty string on failure
    - _Requirements: 2.3, 2.4, 2.5, 2.6, 2.7_

  - [ ]* 1.5 Write property test: Namespace normalization preserves content (Property 1)
    - **Property 1: Namespace normalization preserves content**
    - Generate 100+ random strings containing `::`, `/`, single `:`, and other characters
    - Verify output contains no `::`, all `::` replaced with `/`, non-`::` content preserved
    - **Validates: Requirements 1.1**

  - [ ]* 1.6 Write property test: R1 resolution prefers namespace convention over bare file (Property 2)
    - **Property 2: R1 resolution prefers namespace convention over bare file**
    - Create temp directory trees with namespace convention files and/or bare files
    - Verify R1 returns the namespace convention path when both exist, bare file when only it exists, nothing when neither exists
    - **Validates: Requirements 1.2, 1.3**

  - [ ]* 1.7 Write property test: Resolution priority chain is strict (Property 3)
    - **Property 3: Resolution priority chain is strict**
    - Set up classPath overrides, index entries, and filesystem files with varying combinations
    - Verify classPath always wins, then index, then dynamic discovery
    - **Validates: Requirements 2.3, 2.6, 2.7**

- [x] 2. Checkpoint — Ensure `__boop.resolve` tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Implement `__boop.loader` and RC/CFG bootstrap
  - [x] 3.1 Implement RC chain sourcing in `__boop.loader`
    - Create `__boop.loader()` function in `boop`
    - Source `/etc/booprc` → `~/.booprc` → `./.booprc` in order; skip missing files silently
    - Crash with file path on source failure
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [x] 3.2 Implement BOOPPATH parsing in `__boop.loader`
    - Split `BOOPPATH` on `:`, filter empty segments
    - Skip non-existent directories with `_Info` diagnostic
    - Build effective root list: `.` + BOOPPATH entries + PATH entries
    - _Requirements: 8.1, 8.2, 8.3_

  - [x] 3.3 Implement `.boopIndex` sourcing in `__boop.loader`
    - Source `.boopIndex` from each valid root during initialization
    - Ensure earlier roots take precedence for duplicate short names (skip if key already set in `__boop_Index`)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 8.4_

  - [x] 3.4 Implement version mismatch detection in `__boop.loader`
    - Compare `__boop_version` after RC chain is sourced
    - Emit `_Warn` if mismatch detected
    - _Requirements: 6.5_

  - [ ]* 3.5 Write property test: Effective BOOPPATH construction order (Property 4)
    - **Property 4: Effective BOOPPATH construction order**
    - Generate 100+ random BOOPPATH and PATH strings with varying entries
    - Verify root list starts with `.`, then BOOPPATH entries left-to-right, then PATH entries left-to-right
    - Verify empty segments are filtered out
    - **Validates: Requirements 2.4, 8.1, 8.3, 14.1, 14.2**

  - [ ]* 3.6 Write property test: Root deduplication uses exact path matching only (Property 5)
    - **Property 5: Root deduplication uses exact path matching only**
    - Generate root lists with exact duplicates and subdirectory relationships
    - Verify exact duplicates are skipped, subdirectories are NOT treated as duplicates
    - **Validates: Requirements 2.5**

  - [ ]* 3.7 Write property test: BOOPPATH parsing filters empty segments (Property 13)
    - **Property 13: BOOPPATH parsing filters empty segments**
    - Generate 100+ BOOPPATH strings with leading colons, trailing colons, consecutive colons
    - Verify parsing produces only non-empty segments
    - **Validates: Requirements 8.1, 8.3**

  - [ ]* 3.8 Write property test: Index precedence — earlier roots win (Property 8)
    - **Property 8: Index precedence — earlier roots win**
    - Create multiple roots with overlapping short names in `.boopIndex` files
    - Source all indexes, verify `__boop_Index` contains the value from the first root
    - **Validates: Requirements 4.4, 8.4**

- [x] 4. Checkpoint — Ensure loader and bootstrap tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Rewrite `__boop.import` and add `boop.resolve` public wrapper
  - [x] 5.1 Rewrite `__boop.import` to use `__boop.resolve`
    - Replace the existing `__boop.import` function body in `boop`
    - For each class argument: check `__boop_registry` (skip), check `__boop_loading` (skip), set loading flag
    - Call `__boop.resolve` to get path; if found, source it; if empty, attempt raw `. "$class"` fallback
    - Crash on source failure or complete resolution failure (single `_Crash` with class name and searched locations)
    - Unset `__boop_loading` on success
    - _Requirements: 2.1, 2.2, 2.3, 2.8, 2.9, 3.1, 3.2, 3.3, 3.4_

  - [x] 5.2 Implement `boop.resolve` public wrapper
    - Non-fatal wrapper around `__boop.resolve`
    - Return exit code 0 and path via `boop.pass` if found
    - Return exit code 1 if not found
    - Register on the `boop` class
    - _Requirements: 2 (Implementation Note)_

  - [ ]* 5.3 Write property test: Load guards prevent redundant and circular loading (Property 6)
    - **Property 6: Load guards prevent redundant and circular loading**
    - Pre-populate `__boop_registry` and `__boop_loading` flags for random class names
    - Verify import skips resolution for registered/loading classes
    - Verify `__boop_loading` is unset after successful source
    - **Validates: Requirements 2.2, 3.1, 3.2, 3.3**

- [x] 6. Checkpoint — Ensure import rewrite tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement `boop.classPath` public API
  - [x] 7.1 Implement `boop.classPath` subcommand dispatcher
    - Create `boop.classPath()` function with subcommand dispatch (`set`, `get`, `list`, `remove`, `has`, `dirs`, `rebuild`)
    - Crash on unknown subcommand
    - Register on the `boop` class
    - _Requirements: 16.1, 16.2, 16.3_

  - [x] 7.2 Implement `set` subcommand
    - Validate non-empty class name (crash if empty)
    - Validate path exists and is readable (crash if not)
    - Emit `_Info` if overwriting existing entry
    - Store in `__boop_classPath`, rewrite CFG file
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [x] 7.3 Implement `get` subcommand
    - Return registered path via `boop.pass`, or empty string if not registered
    - _Requirements: 10.1, 10.2_

  - [x] 7.4 Implement `list` subcommand
    - Dump all entries as `ClassName=/path` lines via `boop.pass`
    - Return empty string if registry is empty
    - _Requirements: 11.1, 11.2_

  - [x] 7.5 Implement `remove` subcommand
    - Unset from `__boop_classPath`, rewrite CFG file
    - Emit `_Info` if class not registered
    - _Requirements: 12.1, 12.2, 12.3_

  - [x] 7.6 Implement `has` subcommand
    - Return exit code 0 if registered, 1 if not
    - No `boop.pass` call
    - _Requirements: 13.1, 13.2_

  - [x] 7.7 Implement `dirs` subcommand
    - Return effective root list (one per line) via `boop.pass`
    - Order: `.` first, then BOOPPATH entries, then PATH entries
    - _Requirements: 14.1, 14.2_

  - [x] 7.8 Implement CFG serialization helper
    - Rewrite target CFG file as complete serialization of `__boop_classPath`
    - Default target: `~/.boop.cfg`; override via `_CfgFile` environment variable
    - Output only `__boop_classPath` hash assignments, no procedural logic
    - Called by `set` and `remove` subcommands
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [ ]* 7.9 Write property test: CFG serialization round-trip (Property 11)
    - **Property 11: CFG serialization round-trip**
    - Perform 100+ random sequences of `set` and `remove` operations
    - After each sequence, verify CFG file is a complete serialization of `__boop_classPath`
    - Source CFG into a clean associative array, verify it reproduces the exact same key-value pairs
    - Verify CFG contains only hash assignments, no procedural logic
    - **Validates: Requirements 7.1, 7.2, 9.5, 12.2**

  - [ ]* 7.10 Write property test: ClassPath registry behaves as a correct key-value store (Property 12)
    - **Property 12: ClassPath registry behaves as a correct key-value store**
    - Perform 100+ random sequences of `set`, `get`, `remove`, `has` operations
    - Verify: `get` after `set(k,v)` returns `v`; `has` after `set(k,v)` returns 0; `get` after `remove(k)` returns empty; `has` after `remove(k)` returns 1; `list` includes all current entries
    - **Validates: Requirements 9.1, 10.1, 10.2, 11.1, 12.1, 13.1, 13.2**

- [x] 8. Checkpoint — Ensure classPath API tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Implement `rebuild` subcommand and index generation
  - [x] 9.1 Implement `rebuild` subcommand
    - Scan namespace tree of target Library_Root recursively
    - Discover class files matching R1 convention (directory containing same-named file)
    - Detect short-name conflicts (same short name from multiple namespaces within one root)
    - Exclude conflicting short names, emit `_Info` for each conflict
    - Write generated `.boopIndex` file as sourceable bash with `declare -gA __boop_Index` assignments
    - _Requirements: 5.1, 5.2, 5.3, 15.1, 15.2, 15.3, 15.4_

  - [x] 9.2 Add filesystem fallback diagnostic
    - When a class is resolved via dynamic discovery (not classPath or index), emit `_Info` suggesting `boop.classPath rebuild`
    - Ensure index file is NOT modified by fallback resolution (index is declaration, not cache)
    - _Requirements: 5.4, 5.5_

  - [ ]* 9.3 Write property test: Index rebuild round-trip (Property 7)
    - **Property 7: Index rebuild round-trip**
    - Create 100+ random namespace trees with class files at a temp root
    - Run `rebuild`, source the generated `.boopIndex`, verify mappings match expected short-name → namespace-path
    - Verify generated file is valid sourceable bash
    - **Validates: Requirements 4.2, 5.1, 15.1, 15.2**

  - [ ]* 9.4 Write property test: Index conflict exclusion during rebuild (Property 9)
    - **Property 9: Index conflict exclusion during rebuild**
    - Create roots with intentional short-name conflicts (same short name in multiple namespaces)
    - Run `rebuild`, verify conflicting short names are excluded from `.boopIndex`
    - Verify all non-conflicting short names are still present
    - **Validates: Requirements 5.2, 15.4**

  - [ ]* 9.5 Write property test: Index is a declaration, not a cache (Property 10)
    - **Property 10: Index is a declaration, not a cache**
    - Resolve classes via filesystem fallback, verify `.boopIndex` file is unchanged after resolution
    - **Validates: Requirements 5.4**

- [x] 10. Wire bootstrap into `boop` initialization and final integration
  - [x] 10.1 Integrate `__boop.loader` into the `boop` initialization guard
    - Call `__boop.loader()` inside the `__boop_loaded` guard block, before import arguments are processed
    - Ensure RC chain is sourced before any class imports
    - Set `__boop_loaded=1` after loader completes
    - _Requirements: 2.1, 6.1_

  - [x] 10.2 Update the import arguments section
    - Ensure the section outside the guard that processes `. boop Cube Math::Trig` arguments calls the rewritten `__boop.import`
    - Verify existing class files (Box, Cube, List, Map, Math, etc.) still load correctly
    - _Requirements: 1.5, 2.1_

  - [ ]* 10.3 Write unit tests for end-to-end resolution scenarios
    - Test namespace import: `. boop Collection::List` resolves via namespace convention
    - Test short-name import: `. boop List` resolves via index
    - Test classPath override: registered path takes priority
    - Test raw source fallback and failure crash
    - Test empty class name crashes
    - Test RC file precedence (later tiers override earlier)
    - Test missing RC/CFG files are silently skipped
    - Test version mismatch warning
    - Test non-existent BOOPPATH entries emit `_Info`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.2, 2.3, 2.8, 2.9, 6.1, 6.2, 6.5, 8.2_

- [x] 11. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document using iteration loops with the existing TestSuite framework
- All filesystem tests use temp directories for isolation — no side effects on the real filesystem
- The `boop` file is the single implementation target; all new functions are added there
- Existing class files (Box, Cube, List, Map, Math, TestSuite, etc.) must continue to load after the rewrite
