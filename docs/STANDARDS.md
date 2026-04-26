# boop — Coding Standards

Standards and conventions for the boop framework codebase. These apply
to the framework itself, all class files, and all test files. Comments
are part of the code and must be maintained alongside it.

The goal: a programmer encountering this codebase for the first time
should be able to read any function and understand what it does, what
it expects, and what it returns — without reading the entire framework
first.

---

## API Tiers

Every function in the system belongs to one of three tiers. The tier
largely determines naming, sets validation expectations, and guides
decisions about behavior and interface.

### Tier 1 — Private (`__double_underscore, Mixed Case`)

Internal plumbing. Called under controlled conditions by code that
knows what it's doing. Callers are responsible for passing correct
inputs.

Methods intended for speed and efficiency may be fast and lean with
minimal validation and logging, but should still have an eye toward
ease of future debugging. 

When reasonable, features like lazy evaluation, caching and memoization,
and simple, fast, in-memory built-in tools are always favored.

When heavy, complicated, slow and/or otherwise cumbersome processing is
necessary, it should be carefully documented in the comments (see below),
and have various levels of logging established.

System-specific variables also use the double-leading-underscore.
These should only *EvER* be accessed through the provided methods.  

Examples: `__boop.parse`, `__Math.rawAdd`, `__boop_classPath`

### Tier 2 — Semi-Private (`_single_underscore`)

Management interface. Used to configure, inspect, and control the
framework. These are public-facing but not the primary user API.
Should validate inputs and produce clear error messages.

Methods and variables in this category *manage the system* in some 
way, and/or are used as convenient interfaces to the internals.
Users are expected to use these, but the single underscore indicates
that they are effectively reserved words and should be used only in
the prescribed manner. Improper use voids the warranty. 

Examples: `_Warn`, `_LogLevel`, `_Crash`, `_Self`, `_Class`

Naming: `_MixedCase` for functions and variables

### Tier 3 — Public (`ClassName.method`)

End-user facing. These are the methods people call in scripts and
on the command line. Must be robust, intuitive, and helpful:

- Validate all inputs; reject garbage with clear error messages
- Produce useful output by default (stdout with newline when no
  `into=` is specified)
- Error messages should tell the user what went wrong AND what
  they should have done instead
- Ideally designed to be comfortable in a `.bash_profile` for CLI
  use, but should at least be suitable for semi-casual scripting 

Examples: `Math.DO`, `Math.add`, `$obj.volume`, `$list.push`

---

## Comments

Comments are code. They must be accurate, current, and maintained
alongside the code they describe. Stale comments are worse than no
comments — they actively mislead.

### Function Headers

Every function gets a block comment at the top explaining:

1. What the function does (one or two sentences AT LEAST - more is better)
2. Arguments it expects (name, type, purpose)
3. What it returns or produces (value, side effects, exit code)
4. Any non-obvious behavior or gotchas

Example:

```bash
# Resolve a Math argument to its digits/scale/neg triple.
#
# If the input is an object ID (starts with _ and is in the registry),
# extracts digits, scale, and neg from the object's descriptor.
# Otherwise, parses the input as a literal number string.
#
# Arguments:
#   $1 — input value (object ID or numeric string like "3.14" or "-42")
#   $2 — nameref: receives digit string (no sign, no decimal point)
#   $3 — nameref: receives scale (integer, number of decimal places)
#   $4 — nameref: receives neg flag (0=positive, 1=negative)
#
# Returns: nothing (results via namerefs)
# Crashes: if input is not a valid number or object ID
```

The header should be written for someone who has never seen the
function before. Don't assume the reader knows the internal
representation or the calling conventions — state them.

### Inline Comments

Use `#` for structural comments — section dividers, brief annotations,
and anything that explains *what* the code is doing at a high level.

Use `: "explanation"` (the `:` builtin with a string argument) for
comments inside heavy logic sections. The `:` builtin is effectively
a no-op but its arguments are parsed by bash, which means they appear
in `set -vx` trace output. This makes them visible during debugging
while `#` comments are stripped by the parser and invisible in traces.
There *is* a miniscule performance cost for this; don't embed subshells!

```bash
# Good: structural comment for a section
# === Scale Alignment ===

# Good: colon-comment in a hot loop or complex logic block
: "pad shorter operand with trailing zeros to match scales"
if (( __as_sA < __as_sB )); then
  ...
fi
```

Reserve `:` comments for places where trace visibility has debugging
value — complex algorithms, non-obvious control flow, dispatch logic.
Don't use them for simple one-liners where `#` is fine.

These are *code*. They can only be used where an actual statement can.

### Trailing Inline Comments

Short trailing comments are encouraged for clarity, especially for
bash idioms that less experienced developers might not recognize.
Align the `#` markers at a consistent column so they read as a
clean margin annotation — code on the left, explanation on the right:

```bash
__res_neg=${#BASH_REMATCH[1]}                                # "-" → length 1; empty → 0
local __res_int="${BASH_REMATCH[2]}"                          # digits before the dot
__res_int="${__res_int#"${__res_int%%[!0]*}"}"                # strip leading zeros
: "${__res_int:=0}"                                           # keep at least "0"
```

This reduces visual clutter and lets the eye scan code and comments
independently. Keep them short — if the explanation needs more than
a few words, use a block comment above the line instead.

### Comment Maintenance

When you change code, update the comments. When you read code and
find a comment that's wrong, fix it on the spot. This is not optional.

---

## Variable Naming

### Local Variables

All local variables in methods use the triple-prefix convention:

```bash
__ClassName_methodName_varname
```

This prevents nameref collisions. Bash namerefs resolve by name, not
by lexical scope — if two functions in the call stack both have
`local val`, a nameref in the inner function binds to the outer
function's `val`. The prefix makes every name unique across the
entire call stack.

```bash
# Bad — will collide with any caller that also has "result"
local result

# Good — unique to this function
local __Box_volume_result
```

This is ugly. It is also correct. *Do not skip the prefix.*
*Caveat scriptor*...

### Framework Globals

All framework-level globals use the `__boop_` prefix:

```bash
__boop_registry        # master object/class store
__boop_methodRegistry  # method resolution cache
__boop_logLevel        # global log level
```

### Inherited Identity Variables

`_Self` and `_Class` are the two variables inherited via `local -I`
through the dispatch chain. They are effectively reserved words.

- Every method that needs object identity starts with `local -I _Self _Class`
- Constructors use `local -I _Class` only (no `_Self` yet)
- Internal calls in `boop` should be explicit about setting or
  occluding `_Self`/`_Class` unless inheritance is intentional

### User-Facing Variables

Semi-private variables use single underscore with mixed case: `_Self`,
`_Class`, `_LogLevel`. See `Tier 2 — Semi-Private ` above.

These are generally used for very specific things. For example, if you
explicitly want an object to use a parent's method instead of its own
overridden version, you can effectively "typecast" the method call -
`_Class=$ParentClass $obj.method`
This will attempt to use `method` from `$ParentClass` instead of the 
actual class of `$obj`. 

While the system is designed to be *useful* on the CLI with convenient
tools like `Math.DO "1/(2+3)x4"`, it's still built to work as an actual
OOP system, too.

---

## Output

### `printf`, Never `echo`

`echo` interprets backslash escapes on some platforms and has
inconsistent behavior across bash versions. `printf` is predictable
everywhere. Use it for all output.

```bash
# Bad
echo "$value"

# Good
printf "%s\n" "$value"
```

### Characters and Encoding

Never use em-dashes or other non-ASCII punctuation in code or
generated output. Use plain ASCII `--` (double hyphen) instead.
Em-dashes cause problems with some terminal encodings and are
visually ambiguous in monospace fonts.

For everything else, be contextual. Mathematical symbols like
`x`, `^2`, `pi` in comments are fine -- they make algorithm
documentation more readable and are never parsed by bash.
Unicode card suits in PlayingCard output are fine -- they're
the natural representation.

The rule: prefer simple ASCII in strings the framework generates
for others to consume (error messages, log output, serialized
data). Use whatever's appropriate in comments, documentation,
and domain-specific display output where the character serves
a clear purpose.

### Value Returns

All value-producing functions route through `boop.pass`:

```bash
boop.pass "$value" ${into:-}
```

The `${into:-}` passes the caller's nameref target if one was
provided. If not, the return system uses the current mode (auto,
stdout, global, etc.) to deliver the value.

---

## Shell Options

boop does NOT set shell options (`set -e`, `set -u`, `set -o pipefail`,
etc.). The framework must never alter the caller's shell environment.

If boop ever needs to temporarily change a shell option internally,
it must save and restore it. The caller's shell options are their
business.

All code in the framework should operate under the assumption that the 
user *might* set such options. It should run as cleanly from a script
that uses `set -eu` as one which blithely uses unset vars because they
will return "nothing".

---

## Error Handling

### Crash, Don't Silently Continue

When something is wrong, crash with a clear message. Do not silently
return empty strings, default values, or success codes for invalid
input. The user needs to know what happened and where.

```bash
# Bad — silently returns empty on invalid input, dies under `set -eu`
[[ -z "$input" ]] && return

# Better — safely tells the user at least SOME of what went wrong
[[ -z "${input:-}" ]] && _Crash "Math.add: missing operand"
```

### Tier-Appropriate Validation

- Tier 1 (private): minimal validation. Callers are trusted.
                    Should consider context; lazy private code that *creates*
                    public code should validate appropriately!
- Tier 2 (semi-private): validate inputs, crash with clear messages.
- Tier 3 (public): validate everything. Error messages should say
  what was wrong AND suggest the correct usage.

```bash
# Tier 3 error message — helpful
_Crash "Math.add: invalid number '${input:-}' — expected a numeric value like '3.14' or '-42'"
```

### `2>/dev/null` Policy

Only suppress stderr when ALL of these are true:

1. You know exactly what error will be produced
2. You are expecting that specific error
3. The error content has no debugging value

Every `2>/dev/null` in the codebase should be reviewable against
these criteria. If it doesn't pass all three, remove it.

---

## Class File Structure

Every class file follows this structure:

```bash
#!/bin/bash

# ClassName — one-line description
#
# Longer description if needed. Explain what the class does, what
# it's for, and any important design decisions.

# Load guard — skip if already registered
# NOTE: This pattern is under review for refactoring. The 2>/dev/null
# suppresses "return outside function" when the file is executed
# directly instead of sourced, which is a debugging hazard under
# set -e. A boop.init replacement is planned.
[[ -n "${__boop_registry[ClassName]+set}" ]] && return 2>/dev/null

. boop [Dependencies]

# Class descriptor
__boop_registry["ClassName"]="..."

# Method implementations (each with a function header comment)

# Method registration
__boop.registerMethod ClassName method ClassName.method

# Finalize
__boop.registerClass ClassName
```

---

## API Shape

### Primitives Inward, Wrappers Outward

When a class exposes the same operation over multiple input forms (a
string, a file path, a stream), the **reduced form is the primitive**.
Other entry points are thin wrappers that produce the reduced form and
delegate.

For text parsing the reduced form is "lines on stdin." `loadFile` reads
the file and pipes into the parser; `fromString` feeds the string in
via `<<<`; `fromStdin` is the parser itself. The parsing logic exists
exactly once.

The inverse — making the file variant the primitive and routing
in-memory data through `mktemp`, `printf >`, and `rm` to reuse it —
is forbidden. It pays for a subshell, two syscalls of disk I/O, and a
tmpfile leak window on `_Crash`, all to skip a one-function refactor.
A `while read; done < "$file"` loop and a `while read; done <<< "$str"`
loop are the *same loop* — extract it.

The same shape applies elsewhere:

- **Serializers**: the in-memory form (`toString`) is the primitive;
  `save <file>` writes its output. Never `save` to a tmpfile then
  `cat` it back to stdout.
- **Iteration**: a callback/visitor primitive is the core; `forEach`,
  `map`, `filter` wrap it. Never reimplement the walk.
- **Constructors**: `new` (empty) is the primitive; `fromString`,
  `fromFile`, `fromArray` build empty then populate via public methods.

### Cost of an I/O Round-Trip

For reference, when judging whether to "just route through the existing
function":

| Operation              | Approximate cost      |
|------------------------|-----------------------|
| `mktemp`               | fork + syscalls       |
| `printf '%s' >file`    | open/write/close      |
| `done < file` (re-read)| open/read/close       |
| `rm -f file`           | fork + unlink         |
| Subshell `$(...)`      | fork + pipe + wait    |

Compare to extracting the loop body into a private helper: zero. The
refactor is cheaper than one invocation of the wrong design.

---

## Test Files

All tests use the TestSuite class. Test files should be thorough,
especially for infrastructure code (logging, dispatch, return system).

### Naming

Test files are named `test_<subject>_ts` (the `_ts` suffix indicates
TestSuite-based tests). Benchmark and non-TestSuite files omit the
suffix (e.g., `test_pi_growth`, `test_matrix`).

### Zero-Fork Where Possible

Prefer `$(<file)` (zero-fork builtin read) over `$(command)` subshell
capture in test helpers. Use `bash -c` only for tests that need
process isolation (crash tests, exit code tests).

### Verbosity

Default output is quiet (failures + summary only). Full output is
available via `TESTSUITE_VERBOSE=1`. Tests should work correctly in
both modes.

---

## Refactoring Policy

### Sanitize on Sight

Every file touched for other work gets scanned for:

- Unlocalized variables that could inherit unexpected values
- Stale comments that no longer match the code
- `$self`/`$class` references (should be `$_Self`/`$_Class`)
- Missing function header comments

Fix these on the spot. Don't create TODO items for them.

### Don't Break the Tests

All changes must pass the full test suite before committing.
Currently 514 assertions across 6 TestSuite files.


