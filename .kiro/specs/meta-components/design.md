# Meta-Components Design Spec

## Overview

Meta-components are optional framework extensions that enhance boop when present and
degrade gracefully when absent. The core (`__boop.import`, `_Load`) never hard-depends
on them.

Phase 1 covers: **boop version guard** and **SemVer** (class version checking).
ArgParser and Help are deferred to future phases.

---

## Phase 1: Version Guards

### boop version guard -- `. boop require:1.2+`

Declares that the sourcing script requires boop >= 1.2+. Checked at source time,
before any class loading happens.

Syntax: one or more `require:constraint` tokens in the `. boop` arg list.

```bash
. boop require:1.2+            # need boop >= 1.2
. boop require:1.2+ Math List  # need boop >= 1.2, then load Math and List
```

Behavior if the running boop does NOT satisfy the constraint:
1. Walk BOOPPATH (and PATH) looking for a `boop` file whose `__boop_version`
   satisfies the constraint (read directly from the file, no sourcing)
2. If found: include its path in the crash message so the user knows where to get it
3. `_Crash` either way -- re-loading a different boop core at runtime is deferred
   (see "Bless It In" below)

Implementation: `__boop.requireVersion constraint` -- called from the import-args
block at the bottom of `boop`, before `_Require` sees the remaining args.

### Class version guard -- `_Require Math 1.2+`

Declares that a specific class must meet a version floor. SemVer is the check engine;
if SemVer is not loaded, `_Require` warns and continues (graceful degradation).

```bash
_Require SemVer          # load SemVer (no version check)
_Require Math 1.2+       # load Math, crash if < 1.2
_Require Math Config     # load both, no version checks
```

Parsing: a version constraint is any arg that starts with a digit or comparison
operator (`>=`, `>`, `<=`, `<`) or ends with `+`. Class names always start with
an uppercase letter, so there is no ambiguity.

Behavior:
- Load class via `_Load` as before
- If a version constraint follows, extract `version=` from the registry descriptor
- If class declares no version: `_Warn` and continue
- If SemVer loaded: call `SemVer.satisfies`; `_Crash` if not satisfied
- If SemVer not loaded: `_Warn` and continue

---

## Version Constraint Syntax

Both `require:` and `_Require` use the same constraint grammar:

| Constraint | Meaning |
|---|---|
| `1.2+` | >= 1.2.0 (shorthand) |
| `>=1.2.3` | >= 1.2.3 |
| `>1.2` | > 1.2.0 |
| `<=2.0` | <= 2.0.0 |
| `<2.0` | < 2.0.0 |
| `1.2.3` | exact match |

Pre-release suffixes (`1.2.3-beta`) are stored but ignored in comparisons.
Missing minor/patch components default to 0.

---

## Version Declaration in Class Files

Classes declare their version via a `version:` token in the `boopClass` call:

```bash
boopClass Math version:1.3.0 'public:...'
```

This stores `version=1.3.0` in the registry descriptor. Nothing in the framework
uses this field yet except `_Require`'s version checking.

---

## SemVer Class Interface

`SemVer/SemVer` -- pure bash, no external tools.

```bash
SemVer.satisfies "1.3.0" "1.2+"    # exit 0 = satisfied, exit 1 = not
SemVer.compare  "1.2.3" "1.3.0"   # into= or stdout: -1 / 0 / 1
```

Delegates to `__boop.versionSatisfies` / `__boop.versionCompare` (inlined in boop
for the bootstrapping case). SemVer wraps these as public Tier-3 methods.

---

## Deferred: boop Core Reload ("Bless It In")

If a compatible boop is found on BOOPPATH during a version guard failure, re-sourcing
it over the live framework is risky (registry/object state may be incompatible with a
different boop version). Current behavior: find and report, crash either way.

Revisit if a compelling use case emerges.

---

## Future Phases

- **ArgParser meta-component** -- key=value parsing for constructors and `_loadClass`
- **Help meta-component** -- `ClassName --help` from class descriptors
- **`_Import` version checking** -- non-fatal mirror of `_Require Math 1.2+`
- **Per-class version floor in `.boopIndex`** -- index declares minimum version
