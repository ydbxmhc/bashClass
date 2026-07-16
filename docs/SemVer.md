# SemVer — Semantic Version Comparison

Semantic version parsing, comparison, and constraint checking. Pure bash — no
`sort -V`, no `awk`, no subshells. Static API: no constructor, no objects.

The comparison engine lives in **boop core**, not in this class. SemVer exposes
it as a clean public API. This design is not an accident — read the architecture
section before using the class.

## Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
  - [The bootstrapping problem](#the-bootstrapping-problem)
  - [The SemVer class](#the-semver-class)
  - [Consequence for user code](#consequence-for-user-code)
- [Version Strings](#version-strings)
- [Constraint Syntax](#constraint-syntax)
- [SemVer.compare](#semvercompare)
- [SemVer.satisfies](#semversatisfies)
  - [In scripts](#in-scripts)
- [The boop Version Guard](#the-boop-version-guard)
  - [What happens when the constraint is not satisfied](#what-happens-when-the-constraint-is-not-satisfied)
  - [Why `require:` and not a flag or variable](#why-require-and-not-a-flag-or-variable)
- [Class Version Declarations](#class-version-declarations)
  - [Enforcing class versions with `_Require`](#enforcing-class-versions-with-_require)
  - [Classes with no version declaration](#classes-with-no-version-declaration)
- [Design Notes](#design-notes)
  - [Why the comparison engine is in boop core](#why-the-comparison-engine-is-in-boop-core)
  - [Why SemVer is a separate class at all](#why-semver-is-a-separate-class-at-all)
  - [Pre-release tags](#pre-release-tags)
  - [What is not here](#what-is-not-here)

---

## Quick Start

```bash
. boop SemVer

SemVer.satisfies "1.3.0" "1.2+" && echo "ok"    # passes  (1.3.0 >= 1.2.0)
SemVer.satisfies "1.1.9" "1.2+" && echo "ok"    # silent  (1.1.9 < 1.2.0)

into=r SemVer.compare "1.10.0" "1.9.0"          # r="1"  (numeric: 10 > 9, not string sort)

# boop version guard — no SemVer class needed
. boop require:1.2+         # crashes if boop < 1.2.0
```

---

## Architecture

### The bootstrapping problem

boop core is what loads classes. If the version comparison engine lived in the
SemVer class, boop could not check its own version — it would need to load
a class before the framework was running. Circular.

The solution: the comparison engine is inlined in boop core as two private
functions:

| Function | Lives in | What it does |
|---|---|---|
| `__boop.versionCompare a b` | boop core | Returns -1 / 0 / 1 |
| `__boop.versionSatisfies ver constraint` | boop core | Returns exit 0/1 |

These are `__`-prefixed private functions, not part of the public API.
**Do not call them from user code.** SemVer exposes them cleanly.

### The SemVer class

`SemVer.compare` and `SemVer.satisfies` are thin wrappers that validate
arguments, log at `_Trace`, and delegate to the core functions:

```bash
SemVer.satisfies() { ... __boop.versionSatisfies "$ver" "$constraint"; }
SemVer.compare()   { ... __boop.versionCompare "$a" "$b"; }
```

The comparison logic exists **exactly once**. There is no duplication between
boop core and the class. If the algorithm changes, it changes in one place and
both callers benefit.

### Consequence for user code

Use `SemVer.satisfies` and `SemVer.compare` in your classes and scripts — not
the `__boop.*` primitives. The `__` prefix is a framework-wide signal meaning
"implementation detail, not API."

---

## Version Strings

SemVer parses versions in `major.minor.patch` form. Missing components default
to zero. Pre-release suffixes are stored but ignored in comparisons.

| Input | Interpreted as | Notes |
|---|---|---|
| `"1"` | `1.0.0` | patch and minor default to 0 |
| `"1.2"` | `1.2.0` | patch defaults to 0 |
| `"1.2.3"` | `1.2.3` | fully specified |
| `"1.2.3-beta"` | `1.2.3` | pre-release tag stripped before comparison |
| `"1.2.3-rc.1"` | `1.2.3` | same — anything after `-` is stripped |

Comparison is numeric per component, not lexicographic. `1.10.0` is greater
than `1.9.0` because `10 > 9`, not because of string sort order.

---

## Constraint Syntax

A constraint is a string that expresses a requirement on a version. All
constraints understood by `SemVer.satisfies` and the `require:` guard use the
same syntax.

| Constraint | Meaning | Example |
|---|---|---|
| `N.M+` | >= N.M.0 | `1.2+` — at least 1.2, any patch |
| `>=N.M.P` | >= N.M.P | `>=1.2.3` |
| `>N.M` | > N.M.0 | `>1.2` — strictly after 1.2.0 |
| `<=N.M` | <= N.M.0 | `<=2.0` — up to and including 2.0.0 |
| `<N.M.P` | < N.M.P | `<2.0.0` — before 2.0.0 |
| `N.M.P` | exactly N.M.P | `1.2.3` |

The `N.M+` shorthand is the most common form. It means "this version or
anything later" — equivalent to `>=N.M.0`. It reads naturally at call sites:
`require:1.2+` is "I need boop 1.2 or better."

---

## SemVer.compare

```bash
into=r SemVer.compare "A" "B"
```

Compares two version strings. Returns `-1` (A < B), `0` (A == B), or `1`
(A > B) via `into=` or stdout.

```bash
into=r SemVer.compare "1.2.0" "1.3.0"    # "-1"
into=r SemVer.compare "2.0.0" "2.0.0"    # "0"
into=r SemVer.compare "3.1.0" "2.9.9"    # "1"
into=r SemVer.compare "1.10.0" "1.9.0"   # "1"  — numeric, not string sort
into=r SemVer.compare "1.2" "1.2.0"      # "0"  — missing patch = 0
into=r SemVer.compare "1.2.3-beta" "1.2.3"  # "0" — pre-release stripped
```

Returns non-zero with an error if either argument is missing.

---

## SemVer.satisfies

```bash
SemVer.satisfies "version" "constraint"
```

Returns exit code 0 if `version` satisfies `constraint`, 1 if not.
Prints nothing either way.

```bash
SemVer.satisfies "1.3.0"  "1.2+"    && echo "ok"   # passes
SemVer.satisfies "1.1.9"  "1.2+"    || echo "fail" # fails
SemVer.satisfies "1.2.3"  ">=1.2.0" && echo "ok"   # passes
SemVer.satisfies "2.0.0"  "<2.0"    || echo "fail" # fails — 2.0.0 is not < 2.0.0
SemVer.satisfies "2.0.0"  "<=2.0"   && echo "ok"   # passes — 2.0.0 <= 2.0.0
SemVer.satisfies "1.2.3"  "1.2.3"   && echo "ok"   # exact match
```

Returns non-zero with an error if either argument is missing.

### In scripts

```bash
. boop SemVer

tool_ver=$(mytool --version | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' | head -1)
SemVer.satisfies "$tool_ver" "2.4+" || {
  printf "mytool >= 2.4.0 required (have %s)\n" "$tool_ver" >&2
  exit 1
}
```

---

## The boop Version Guard

The most frequent use of version constraints is guarding framework
compatibility at script load time. This requires no SemVer class — it runs
before any classes load.

```bash
. boop require:1.2+         # script needs boop 1.2 or later
. boop require:>=1.1.0      # explicit form
. boop require:1.2+ List Map # version guard + class loads in one line
```

### What happens when the constraint is not satisfied

1. boop compares `__boop_version` against the constraint using the inlined
   core functions (no class involved).
2. If the running boop does not satisfy it, boop searches for a compatible
   boop on `. + BOOPPATH + PATH` by reading each candidate file's version
   line directly (no sourcing — just a grep through the file).
3. If a compatible boop is found, the crash message includes its path so
   you know where to look.
4. If none is found, the crash message says so.
5. Either way, the script does not run. There is no silent degradation.

```
boop '1.2+' required (running v0.9.0) -- compatible version found at: /opt/boop-new/boop (v1.2.1)
boop '1.2+' required (running v0.9.0) -- none found on BOOPPATH/PATH
```

### Why `require:` and not a flag or variable

The guard is expressed as an argument to the source line because it belongs
with the load statement. It reads as a declaration: "to source this, I need
boop 1.2+." This is the same principle as dependency declarations in every
other package system — the requirement travels with the thing that has it,
not in a separate config file.

---

## Class Version Declarations

Classes can declare their own version in the `boopClass` statement:

```bash
boopClass Math version:1.3.0 '
  public:add,subtract,multiply,divide,...
'
```

The version is stored in the class registry descriptor. It does not affect
class loading behavior on its own — it is metadata that `_Require` can
optionally enforce.

### Enforcing class versions with `_Require`

```bash
_Require Math 1.2+          # load Math; crash if version < 1.2.0
_Require SemVer Math 1.2+   # load SemVer first, then enforce Math version
_Require Config             # no version constraint — current behavior unchanged
```

( See [Math](Math) and [Config](Config) )

A version constraint in `_Require` is any argument that starts with a digit,
`>`, or `<`, or ends with `+`. Class names start with uppercase letters, so
there is no ambiguity.

**SemVer must be loaded for class version enforcement to work.** If SemVer is
not in the registry when `_Require` checks a class version, it warns and
continues rather than crashing. This is intentional graceful degradation —
a script that does not load SemVer cannot reasonably be expected to enforce
class versions, and crashing silently would be worse than warning and
proceeding.

The practical implication: always load SemVer before any `_Require` call that
includes a version constraint:

```bash
. boop SemVer Math 1.2+          # SemVer loads first (leftmost); Math checks against it
```

Or explicitly:

```bash
_Require SemVer                  # load SemVer
_Require Math 1.2+ Config 3.0+   # now version constraints are enforced
```

### Classes with no version declaration

A class that omits `version:` from its `boopClass` statement has no version
metadata. `_Require Class 1.2+` will warn and skip the version check rather
than crash. To enforce version constraints on a class, that class must
explicitly declare a version.

---

## Design Notes

### Why the comparison engine is in boop core

If version comparison lived in SemVer, the `require:` guard would need to load
SemVer before checking boop's own version. But loading a class requires the
framework to already be running. The guard must fire during framework
initialization — before any class can load. Inlining is the only correct
answer.

The functions are named `__boop.*` (double-underscore prefix) rather than
given a public name, because they are implementation details of the version
system, not general-purpose utilities. The public API is `SemVer.satisfies`
and `SemVer.compare`. Internal boop code uses the `__boop.*` forms where
it must; everything else goes through SemVer.

### Why SemVer is a separate class at all

If the comparison engine is already in core, why have a SemVer class?

1. **Validation and tracing.** The `__boop.*` primitives are minimal — they
   take arguments and compute. `SemVer.satisfies` validates that both arguments
   are present, logs at `_Trace`, and exposes the call in stack traces.
2. **The public API contract.** `__boop.*` names are internal and may change.
   `SemVer.satisfies` is a stable API that user code can depend on.
3. **Class version enforcement.** `__boop.checkClassVersion` uses
   `SemVer.satisfies` because class version checking is a user-facing operation
   that deserves the full API surface (argument validation, tracing, stable
   name). It also serves as a signal: if SemVer is loaded, class versions are
   enforced; if not, they are not. Loading SemVer is the opt-in.
4. **Future extensibility.** The SemVer class can grow — range sets,
   pre-release ordering, version parsing into properties — without touching
   boop core.

### Pre-release tags

The SemVer specification defines ordering rules for pre-release tags
(`1.2.3-alpha < 1.2.3-beta < 1.2.3`). This implementation ignores pre-release
tags entirely: `1.2.3-beta` compares as `1.2.3`. The use case for
pre-release ordering in a shell framework is narrow enough that the complexity
is not justified. If you need to compare pre-release tags, strip and compare
the suffix yourself.

### What is not here

**Range sets** (`>=1.2.0 <2.0.0`, `^1.2`, `~1.2.3`) are not implemented.
Each constraint in this system is a single expression. If you need to express
a version window, test two constraints:

```bash
SemVer.satisfies "$v" "1.2+" && SemVer.satisfies "$v" "<2.0"
```

**Version parsing into an object** is not implemented. There is no
`SemVer.parse "1.2.3"` that returns an object with `.major`, `.minor`,
`.patch` properties. The static API covers all current use cases.

---

[↑ Site map](index)
