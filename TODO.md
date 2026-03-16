# boop Framework — TODO

Collected future work items. Inline TODOs in source files should
reference entries here by section name.

---

## Typecast Interface Variables

Short names (`input`, `type`, `self`, `class`) used for typecast
interface variables may collide with user locals. Evaluate naming
convention: `_Input`, `_Type`, leading underscore + mixed case,
all caps, etc. Needs ergonomic + safe balance.

Source: `boop` globals section.

---

## Configurable Baked-Wrapper Typecast Behavior

When a baked wrapper detects an ambient class that is neither an exact
match nor in the baked class's inheritance chain (e.g., `class=Hand`
leaking into a Card method via `local -I`), the current behavior
silently ignores it and uses the baked class (fast path). This is safe
but hides potential user errors.

Desired: a per-class setting (inherited, with a global default) that
controls the response to unrelated-class leakage in baked wrappers:

- `silent` — ignore and use baked class (current behavior)
- `warn` — use baked class but emit a diagnostic to stderr
- `strict` — crash with an informative message

The setting should be resolvable at bake time (not every call) so the
behavior can be hardcoded into the wrapper. Needs a registry walk for
the first class-specific value in the inheritance chain, falling back
to the global default. Something like `__bashClass_typecastMode` or a
class property like `implicitSelfTypecast`.

Source: `boop` dispatch/bake section.

---

## Framework-Wide LOGLEVEL System

A global default log level with per-class overrides (inherited via the
class chain). Would support the typecast warning above and provide a
general diagnostic facility for class authors.

Levels: `silent`, `warn`, `info`, `debug`, `trace`.

Output to stderr with structured prefix (class/method/object ID).
Per-class overrides walk the inheritance chain for the first
class-specific value, falling back to the global default.

---

## Argument-Parsing Object

A reusable class for parsing `key=value`, positional, and flag
arguments in constructors and methods. Would replace the ad-hoc
`for/case` loops in every `.new()` method.

Sketch:
```bash
into=args ArgParser "suit= rank= faceUp=0" "$@"
$args.get suit   # → "♠"
$args.get faceUp # → "0" (default)
```

Needs to handle: required vs optional, defaults, type validation,
positional fallback, unknown-key rejection.

---

## Class File Execution Guard & Help System

Class files like `Box`, `List`, etc. are meant to be sourced, not
executed directly. Currently running `bash Box` silently succeeds and
does nothing — confusing for users.

### Execution Guard

`__bashClass.registerClass` could detect when the class file is being
executed directly (`BASH_SOURCE` == `$0`) and respond appropriately:

- If the class has a flag indicating it's NOT meant to be executed
  directly (the common case), print a usage message and exit:
  `"Box is a class file. Source it with: . boop Box"`

- If the class IS meant to be executable (like `blackjack`), skip the
  guard and let the script continue to its main logic.

Flag could be a class property (`executable=false`) or a parameter to
`registerClass`.

### Help System

Classes should support a standard help interface. Running a class file
directly (or calling `ClassName --help` or `ClassName.help`) should
print a synopsis:

```
Box — 3D rectangular container

Properties:
  length, width, height — dimensions (integers)
  unit — measurement unit (optional)
  color — display color (optional)

Methods:
  volume  — returns length × width × height
  area    — returns 2D area of given dimensions
  top     — returns area of top face
  ...

Usage:
  . boop Box
  into=b Box length=5 width=3 height=7
  $b.volume  # → 105
```

This could be:
- Auto-generated from the class descriptor (methods, properties)
- Enhanced with a `description` property and per-method docstrings
- Stored in a `__bashClass_help` registry or inline in the descriptor

---

## Binary-Safe Encode/Decode Output Mode

`__bashClass.bdecode` currently returns decoded data via the standard
return mechanism, but bash variables silently drop null bytes. For true
binary-safe round-trip, need `output=file` support that writes decoded
data directly to a file without passing through a variable.

Source: `boop` bencode/bdecode section.

---

## Stderr Redirection Audit

Several places in the codebase use `2>/dev/null` to suppress errors.
Each should be reviewed:

- **Class file load guards** (`&& return 2>/dev/null`): Currently
  suppresses "return outside function" error. Should be replaced with
  `BASH_SOURCE` vs `$0` check to only return when sourced. See
  "Class File Execution Guard" above.

- **TestSuite assert_ok/assert_fail**: Suppresses stderr from the
  command being tested. This hides real errors — should probably let
  stderr through and capture it for the failure message.

- **boop import fallback** (`. "$__import_class" 2>/dev/null`):
  Suppresses "file not found" before the crash message. Borderline —
  crash message is more informative, but original error has path info.

Principle: Only suppress stderr when you know exactly what the error
will be, you're expecting it, and the content has no debugging value.

---

## Inline Class Definitions in Executable Scripts

Currently, class files must be separate files to be both sourceable
(for testing/reuse) and executable (for standalone scripts). The
blackjack example originally defined all classes inline, but this
prevented sourcing just the classes without running the game loop.

Investigate a pattern for defining classes inline in an executable
script while still allowing them to be sourced separately. Options:

- `BASH_SOURCE` vs `$0` guard before the main logic
- A `__bashClass.main` convention that registerClass can detect
- A flag/property on the class that marks the file as executable

Related: "Class File Execution Guard" section above.

---

## Generalize Card/Deck/Hand Classes

Card, Deck, and Hand currently have blackjack-specific logic (ace
rules, 52-card fill, etc.). These concepts are reusable beyond
blackjack — tarot decks, index cards, any collection of items with
a "hand" metaphor.

Consider splitting into generic base classes and game-specific
subclasses:

- `Card` — generic card with arbitrary properties
- `PlayingCard extends Card` — suit/rank/faceUp, 52-card standard
- `Deck` — generic ordered collection with shuffle/draw
- `PlayingDeck extends Deck` — fills with 52 PlayingCards
- `Hand` — generic scored collection
- `BlackjackHand extends Hand` — ace adjustment, bust/blackjack logic
