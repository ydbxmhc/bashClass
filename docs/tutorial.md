# boop Tutorial

A complete walkthrough of boop from first principles. By the end you
will have written real classes, used the standard library, wired up
signals, queried JSON, and tested everything with the built-in test
runner. No prior OOP-in-bash experience required.

---

## Table of Contents

1. [What boop actually is](#1-what-boop-actually-is) — and what it is not
2. [Setup and first source](#2-setup-and-first-source)
3. [Your first class](#3-your-first-class)
4. [Returning values — the `into=` system](#4-returning-values--the-into-system)
5. [Constructors and properties](#5-constructors-and-properties)
6. [Instance methods](#6-instance-methods)
7. [Inheritance and `_Super`](#7-inheritance-and-_super)
8. [Mixins](#8-mixins)
9. [The standard library](#9-the-standard-library)
10. [Error handling](#10-error-handling)
11. [Signals](#11-signals)
12. [Testing with TestSuite](#12-testing-with-testsuite)
13. [CLI tools](#13-cli-tools)
14. [Complete example: a task list app](#14-complete-example-a-task-list-app)

---

## 1. What boop actually is

boop is an OOP layer for bash. It is a single sourceable file (~2 500
lines) that, when sourced, gives you:

- **Real classes.** `boopClass` registers a class with properties,
  method visibility, and a parent class (optional).
- **Real objects.** `ClassName [key=val ...]` creates an instance and
  returns its object ID.
- **Dispatch wrappers.** `$obj.method arg…` dispatches with `_Self`
  and `_Class` set correctly — no subshells, no forks.
- **A return system.** `boop.pass value ${into:-}` writes a return
  value into a named variable instead of stdout. This keeps the hot
  path free of `$()` subshells.
- **Inheritance + MRO.** Single parent, cached method resolution.
- **Mixins.** `boopMixin` lets you share behaviour across unrelated
  classes without forcing inheritance.
- **A class loader.** `. boop ClassName` finds and sources the right
  file automatically.

Everything is pure bash. Nothing compiles. There are no C extensions,
no subprocesses in the dispatch path, and no package manager
requirements.

### Why OOP in bash at all?

The primitives OOP gives you — encapsulation, inheritance, object
identity — aren't just aesthetics. They solve real bash pain:

- **Data isolation.** A bash script's default state is one giant pile
  of globals. Objects let you attach state to a named thing and pass
  that thing around, rather than threading prefixed variables through
  every function call.
- **Code reuse.** Inheritance and mixins let you define behaviour once
  and graft it onto multiple classes. Without this you copy-paste, or
  invent yet another naming convention and hope everyone follows it.
- **Boundaries.** A method that operates on `_Self` can only reach
  what its class gives it. That constraint makes large scripts easier
  to reason about and refactor.

None of this is magic. It is convention — carefully maintained,
enforced by the framework rather than by discipline alone.

### What boop is not

Be honest with yourself before you commit:

**It is not fast.** Every method call goes through dispatch wrappers
and associative-array lookups. It avoids `$()` subshells in the hot
path, which helps, but it is still bash. If you need to process
millions of records per second, reach for a compiled tool. boop is
for the logic that *orchestrates* — not the loop that burns CPU.

**It is not for binary data.** Bash variables cannot hold NUL bytes.
If your data contains embedded NULs (binary blobs, certain compressed
formats) it will be silently truncated. See
[GOTCHAS.md](GOTCHAS.md#nul-bytes--silent-truncation-no-detection).

**It is not a showcase of exemplary bash.** It is a thought experiment
that turned out to be useful — a deliberate answer to the question
"what *would* OOP in pure bash look like?" The internals use
namerefs, associative arrays, `eval`, and dynamic dispatch in ways
that would get a normal script rejected in code review. The framework
earns those tricks; your code using the framework does not need to.

**It is not a general replacement for a real language.** If you have
Python, Ruby, or Go available and time is not the constraint, use
them. boop earns its keep in the niche where you need structured logic
*in bash specifically* — deployment hooks, system configuration,
scripts that live next to the tools they orchestrate and cannot take
on a runtime dependency.

If you are still here: good. You found the niche.

---

## 2. Setup and first source

### Install

```bash
git clone <repo-url> ~/boop
export PATH="$PATH:$HOME/boop"   # makes `. boop` work from anywhere
```

Nothing else is required. The `PATH` addition lets `. boop` (and
`. boop ClassName`) find the framework file by name.

### Source the framework

In any bash script:

```bash
#!/usr/bin/env bash
. boop            # load core framework only
```

Or load the core plus one or more library classes in a single line:

```bash
. boop Args List Config
```

Each name after `boop` is a class to load. You can also load
additional classes later with the same syntax — boop's framework
initialization is guarded and won't re-run, but the import step
runs every time:

```bash
. boop         # load framework
# ... later ...
. boop Foo Bar # framework init skipped; Foo and Bar are loaded now
```

Each class file has its own idempotence guard (`boop.init ClassName`),
so sourcing an already-loaded class is a no-op.

### Other ways to load classes

`. boop ClassName` is the idiomatic entry point for scripts, but there
are two lower-level loaders you will encounter inside class files:

**`_Require ClassName`** — fatal hard dependency. Crashes with a clear
error if the class cannot be found or fails to source. This is what
`. boop ClassName` uses internally, and it is the right choice when
your code cannot function without the dependency.

```bash
_Require Config             # crash if Config unavailable
_Require Math Config List   # crash if any are unavailable
```

**`_Load ClassName`** — non-fatal soft dependency. Returns 1 if the
class is unavailable; never crashes. Use it when you want to try for
a dependency and gracefully degrade if it is missing.

```bash
_Load Math || { printf 'precision math unavailable\n'; return 1; }
if _Load Prometheus; then Prometheus.record "$metric" "$value"; fi
```

Both functions are idempotent — calling them for an already-loaded
class is a cheap no-op (registry check, no file I/O).

### Class resolution and `BOOPPATH`

When boop looks for a class file it searches in order: the current
directory, entries in `BOOPPATH` (colon-separated, like `PATH`), and
finally entries from `PATH` itself. You can also register an explicit
path for a class:

```bash
__boop_classPath["MyClass"]="/opt/lib/myproject/MyClass"
```

For most use cases — running from the repo root or with `PATH` set as
shown above — the defaults work without any configuration.

### Verify it loaded

```bash
. boop
printf 'boop %s\n' "$__boop_version"   # prints: boop 1.0.0
```

---

## 3. Your first class

A class is: one or more bash functions following the `ClassName.method`
naming convention, closed with a `boopClass` declaration.

```bash
#!/usr/bin/env bash
. boop

# --- Counter class ---

Counter.increment() {
  local _Class="${_Class:-Counter}" _Self="${_Self:-}"
  local __Counter_increment_val
  into=__Counter_increment_val _Self.count   # read current count
  (( __Counter_increment_val++ )) || true    # increment
  _Self.count="$__Counter_increment_val"     # write back
}

Counter.value() {
  local _Class="${_Class:-Counter}" _Self="${_Self:-}"
  local __Counter_value_val
  into=__Counter_value_val _Self.count
  boop.pass "$__Counter_value_val" "${into:-}"
}

boopClass Counter 'has:count public:increment,value'
```

Use it:

```bash
into=c Counter count=0    # create a Counter with count=0; c = object ID

$c.increment
$c.increment
$c.increment

into=n $c.value
printf 'Count: %s\n' "$n"   # Count: 3
```

### What each line does

**`local _Class="${_Class:-Counter}" _Self="${_Self:-}"`**
Every method needs these two lines at the top. `_Class` is the class
name (used by `_Super` and `_Cast`). `_Self` is the object ID (used
by property access and dispatch). boop sets them via inline env vars
on every call — these locals capture and protect them from leaking.

**`into=__Counter_increment_val _Self.count`**
Reads the `count` property of the current object into a local variable.
`into=` is the return-target prefix; anything that uses `boop.pass`
respects it.

**`_Self.count="$__Counter_increment_val"`**
Writes a property. Property setters are auto-generated for every name
listed in `has:`.

**`boop.pass "$__Counter_value_val" "${into:-}"`**
Standard return. If the caller set `into=varname`, the value goes
there. If the caller used plain `$c.value`, the value goes to stdout
via `_Out` (which by default calls `printf '%s\n'`).

**`boopClass Counter 'has:count public:increment,value'`**
Registers the class. `has:count` tells boop that `count` is a
settable property (getter and setter auto-generated). `public:` names
the methods that become dispatchable.

---

## 4. Returning values — the `into=` system

boop avoids `$()` subshells for performance. Instead of:

```bash
result="$(some_function)"   # forks a subshell — expensive
```

boop uses:

```bash
into=result some_function   # no fork — writes directly into 'result'
```

This is the **return-target prefix** pattern. The called function reads
`${into:-}` inside `boop.pass` to decide where to write.

### Inline prefix vs. export

```bash
into=x $obj.method          # CORRECT: inline prefix, visible to method
export into=x               # WRONG: turns 'into' into an env variable
```

Always use the inline (no-export) form.

### Chaining returns

```bash
into=a $obj.firstName
into=b $obj.lastName
printf '%s %s\n' "$a" "$b"
```

### When to use stdout

If you genuinely want stdout (piping to another tool, printing to the
user), just don't use `into=`:

```bash
$obj.describe          # prints to stdout
$obj.describe | head   # pipes correctly
```

### `_EOL=` — custom line ending

`_EOL` is a sibling of `into=`. It controls what `_Out` appends after
the value when writing to stdout (default: newline). Override inline:

```bash
_EOL=' (done)\n' $obj.label   # prints: SomeLabel (done)
_EOL=''          $obj.label   # prints without trailing newline
```

---

## 5. Constructors and properties

The default constructor is provided by boop. You do not need to write
one unless you need custom initialization logic.

### Default constructor: `has:` properties

```bash
boopClass Person 'has:name,age public:greet'
```

This generates:
- a constructor that accepts `name=` and `age=` keyword arguments
- getter methods `$obj.name` and `$obj.age`
- setter syntax `$obj.name="value"` and `$obj.age="value"`

```bash
into=p Person name="Alice" age=30
into=n $p.name         # n = "Alice"
into=a $p.age          # a = "30"
$p.name="Bob"          # update name
```

### Custom constructor

Override `ClassName.new` to add initialization logic:

```bash
Rectangle.new() {
  local _Class="${_Class:-Rectangle}" _Self="${_Self:-}"

  # Let the default constructor handle keyword args (width=, height=)
  __boop.new "$@"

  # Post-construction validation
  local __Rectangle_new_w __Rectangle_new_h
  into=__Rectangle_new_w _Self.width
  into=__Rectangle_new_h _Self.height
  if (( __Rectangle_new_w <= 0 || __Rectangle_new_h <= 0 )); then
    _Error "Rectangle: width and height must be positive"; return 1
  fi
}

Rectangle.area() {
  local _Class="${_Class:-Rectangle}" _Self="${_Self:-}"
  local __Rectangle_area_w __Rectangle_area_h
  into=__Rectangle_area_w _Self.width
  into=__Rectangle_area_h _Self.height
  boop.pass "$(( __Rectangle_area_w * __Rectangle_area_h ))" "${into:-}"
}

boopClass Rectangle 'has:width,height public:area'
```

```bash
into=r Rectangle width=4 height=5
into=a $r.area
printf 'Area: %s\n' "$a"   # Area: 20
```

### `_Self` shortcuts

Inside any method, `_Self.propname` is shorthand for `$(_Self).propname`.
Use `into=var _Self.prop` to read and `_Self.prop="value"` to write.

---

## 6. Instance methods

Instance methods receive `_Self` (the object ID) and can call other
methods on it, call `_Super`, or dispatch to other objects.

### Calling methods on `_Self`

```bash
Widget.render() {
  local _Class="${_Class:-Widget}" _Self="${_Self:-}"
  local __Widget_render_label __Widget_render_size
  into=__Widget_render_label _Self.label
  into=__Widget_render_size  _Self.size
  printf '[%s:%s]' "$__Widget_render_label" "$__Widget_render_size"
  boop.pass "" "${into:-}"  # no meaningful return value — side effect only
}
```

### Calling methods on other objects

```bash
Dashboard.show() {
  local _Class="${_Class:-Dashboard}" _Self="${_Self:-}"
  local __Dashboard_show_w
  into=__Dashboard_show_w _Self.widget    # get the sub-object ID
  $__Dashboard_show_w.render              # dispatch on it
}
```

### Class-level (static) methods

Methods called directly on the class name (not an instance) still
receive `_Class` and `_Self` — `_Self` equals `_Class` for static calls.

```bash
MathHelper.square() {
  local _Class="${_Class:-MathHelper}" _Self="${_Self:-}"
  local __MathHelper_square_n="${1:-0}"
  boop.pass "$(( __MathHelper_square_n * __MathHelper_square_n ))" "${into:-}"
}

boopClass MathHelper 'public:square'

into=r MathHelper.square 7   # r = "49"
```

### `_Delegate`

`_Delegate $obj.method args…` dispatches a method with all the calling
method's context forwarded. Useful when a method on one object needs to
run a method on another with the same `into=` target:

```bash
Wrapper.process() {
  local _Class="${_Class:-Wrapper}" _Self="${_Self:-}"
  local __Wrapper_process_inner
  into=__Wrapper_process_inner _Self.inner  # get inner object
  _Delegate $__Wrapper_process_inner.doWork "$@"
}
```

---

## 7. Inheritance and `_Super`

### Single inheritance

```bash
boopClass Animal      'has:name public:speak'
boopClass Dog isa:Animal 'public:speak,fetch'
```

`isa:Animal` makes `Dog` inherit from `Animal`. The MRO is: Dog →
Animal → boop (root).

### Overriding a method

```bash
Animal.speak() {
  local _Class="${_Class:-Animal}" _Self="${_Self:-}"
  boop.pass "..." "${into:-}"
}

Dog.speak() {
  local _Class="${_Class:-Dog}" _Self="${_Self:-}"
  boop.pass "Woof!" "${into:-}"
}
```

### Calling the parent with `_Super`

`_Super method args…` calls the nearest ancestor implementation of
`method`. `_Self` stays bound to the current object.

```bash
GoldenRetriever.speak() {
  local _Class="${_Class:-GoldenRetriever}" _Self="${_Self:-}"
  local __GR_speak_parent
  into=__GR_speak_parent _Super speak    # calls Dog.speak → "Woof!"
  boop.pass "${__GR_speak_parent} (very happily)" "${into:-}"
}
```

### `isa` checking

```bash
into=d Dog name="Rex"
$d.isa Dog         # returns 0 (true)
$d.isa Animal      # returns 0 (true — ancestor)
$d.isa boop        # returns 0 (true — root)
$d.isa Cat         # returns 1 (false)
```

### `_Cast`

`_Cast ClassName method args…` calls `method` through a specific class
in the hierarchy, bypassing the MRO. `_Self` is unchanged.

```bash
# Call Animal.speak on a Dog object, skipping Dog's override:
_Cast Animal speak   # inside a Dog method
```

---

## 8. Mixins

A mixin is a bundle of methods that can be grafted onto any class
without changing its inheritance chain. Declare with `boopMixin`:

```bash
# Define the mixin
boopMixin Serializable 'public:serialize,deserialize'

Serializable.serialize() {
  local _Class="${_Class:-}" _Self="${_Self:-}"
  # ... implementation ...
}

# Apply to a class
boopClass Config isa:Map has:name '
  public:get,set
  with:Serializable
'
```

The `with:Serializable` applies the mixin. Every `Config` instance now
has `.serialize` and `.deserialize` without Config needing to inherit
from Serializable.

### Mixin method resolution

Mixin methods are tried after the class's own methods but before the
parent class. If both the mixin and the parent define the same method,
the mixin wins for classes that declare `with:MixinName`.

---

## 9. The standard library

boop ships a library of tested classes. Load any of them with:

```bash
. boop ClassName         # from boopRoot
```

### Args — argument parsing

Parse a rich DSL that describes your CLI:

```bash
#!/usr/bin/env bash
. boop Args

Args.parse '
[Use]
myscript [options] FILE...

[Options]
verbose | v          # enable verbose output
output  | o  =       # output file
count   | n  = 1     # number of iterations (default 1)
' "$@"

(( _verbose )) && printf 'verbose mode on\n'
printf 'output: %s\n' "${_output:-stdout}"
printf 'count:  %s\n' "$_count"
```

Boolean flags become `_flagname` (0 or 1). Options with `=` become
`_optname` (string). Remaining positional args go into `_ArgsRemaining`.

See `docs/boop.md` for the full Args reference.

### Config — key/value store

```bash
. boop Config

into=cfg Config
$cfg.set database.host "localhost"
$cfg.set database.port "5432"

into=host $cfg.get database.host
printf 'host: %s\n' "$host"
```

Config supports nested keys (dot-separated), defaults, and iteration.

### List — ordered collection

```bash
. boop List

into=lst List
$lst.push "alpha"
$lst.push "beta"
$lst.push "gamma"

into=n $lst.length    # n = 3
into=v $lst.get 1     # v = "beta" (0-indexed)

$lst.each my_callback_function   # calls my_callback_function item index

# Pipeline (functional-style chaining):
$lst.do | filter 'alpha' | count
```

### Map — key/value object store

```bash
. boop Collection::Map

into=m Map
$m.set name  "Alice"
$m.set score "42"

into=n $m.get name     # n = "Alice"
$m.has score           # returns 0 (true)
$m.delete score
$m.has score           # returns 1 (false)

$m.each my_callback    # calls my_callback key value
```

### Map.Fast — high-performance flat map

For hot paths where you need key/value storage without object overhead:

```bash
. boop Collection::Map::Fast

declare -A mymap
Map.Fast.set mymap key "value"
Map.Fast.get mymap key   # returns via boop.pass / into=
```

### Stack and Queue

```bash
. boop Collection::Stack Collection::Queue

into=stk Stack
$stk.push "first"
$stk.push "second"
into=top $stk.pop   # top = "second"  (LIFO)

into=q Queue
$q.enqueue "first"
$q.enqueue "second"
into=front $q.dequeue  # front = "first"  (FIFO)
```

### Set

```bash
. boop Collection::Set

into=s Set
$s.add "apple"
$s.add "banana"
$s.add "apple"   # duplicate — silently ignored

into=n $s.size   # n = 2
$s.has "apple"   # returns 0 (true)
$s.has "cherry"  # returns 1 (false)
```

### SemVer — version handling

```bash
. boop SemVer

into=v SemVer "2.4.1"
into=major $v.major   # 2
into=minor $v.minor   # 4
into=patch $v.patch   # 1

into=v2 SemVer "3.0.0"
$v.lessThan $v2       # returns 0 (true — 2.4.1 < 3.0.0)

# Version constraint guard (fails load if constraint not satisfied)
require: ">=1.0.0"    # in a class file, guards against old boop
```

### Math — arbitrary-precision arithmetic

```bash
. boop Math

into=r Math.add 1.23 4.56       # r = "5.79"
into=r Math.mul 3.14 2          # r = "6.28"
into=r Math.div 22 7 scale=10   # r = "3.1428571428"
into=r Math.pow 2 64            # r = "18446744073709551616"

# Chained expression
into=r Math.eval '(3 + 4) * 2'  # r = "14"
```

Math is pure bash — no `bc`, no `awk`, no subshells. It handles
integers and decimals to arbitrary precision.

### Text.String — string manipulation

```bash
. boop Text::String

into=s Text.String "  Hello, World!  "
$s.trim             # edits in place → "Hello, World!"
into=u $s.upper     # u = "HELLO, WORLD!" (original unchanged)

$s.replace "World" "boop"
into=result $s.value   # result = "Hello, boop!"

# Pipeline
into=s Text.String "foo bar baz"
$s.do | upper | replace 'BAR' 'BAZ' | trimmed
```

### Data.JSON — JSON parsing

```bash
. boop Data::JSON

input='{"name":"Alice","scores":[10,20,30]}'

into=doc Data.JSON.parse "$input"
into=name  $doc.get name             # name = "Alice"
into=score $doc.get 'scores[1]'      # score = "20"
```

### DateTime — date/time handling

```bash
. boop DateTime

into=now DateTime              # current time
into=ts  $now.timestamp        # Unix epoch
into=fmt $now.format "%Y-%m-%d %H:%M:%S"

into=d DateTime "2026-01-01"
into=tomorrow $d.addDays 1
into=result $tomorrow.format "%Y-%m-%d"   # result = "2026-01-02"
```

### Stream — line-oriented file/stdin processing

```bash
. boop Stream

into=s Stream.new -P "data.csv" -f ','   # file, comma-delimited fields

while $s.next; do
  into=n $s.fieldCount
  for (( i=0; i<n; i++ )); do
    into=field $s.field $i
    printf 'col %d: %s\n' "$i" "$field"
  done
done
```

Stream handles large files without reading them all into memory. It
supports custom record delimiters, field delimiters, paragraph mode,
array mode, and more.

---

## 10. Error handling

boop has two error levels:

| Function | Behaviour |
|----------|-----------|
| `_Error "message"` | Prints the message to stderr, returns 1 |
| `_Crash "message"` | Prints the message to stderr, kills the process |

**Use `_Error` + `return 1` for everything recoverable.** Only use
`_Crash` for security violations, framework corruption, or situations
where the process genuinely cannot continue.

### Propagating errors

```bash
MyClass.doThing() {
  local _Class="${_Class:-MyClass}" _Self="${_Self:-}"

  # Call a method that might fail
  $other.validate || { _Error "MyClass.doThing: validation failed"; return 1; }

  # ... rest of method ...
}
```

### Strict vs lenient: `_FatalLevel`

By default, `_Error` prints and returns 1. You can escalate to process
exit by setting `_FatalLevel`:

```bash
_FatalLevel=error   # _Error now kills the process
_FatalLevel=warn    # _Warn also kills
_FatalLevel=crash   # only _Crash kills (default)
```

This lets callers decide how fatal errors should be for their context.

### Warning and info

```bash
_Warn "this is suspicious"    # printed at warn level and above
_Info "this is informational" # printed at info level and above
_Debug "deep tracing"         # printed only at debug level
```

Control verbosity with `__boop.setLogLevel`:

```bash
__boop.setLogLevel warn    # show warnings and above (default)
__boop.setLogLevel debug   # show everything
__boop.setLogLevel silent  # show nothing
```

---

## 11. Signals

The `Signal` class layers a LIFO callback stack on top of bash's
single-slot `trap`. Multiple components can register handlers without
stomping each other.

```bash
. boop Signal

# Register a cleanup handler for EXIT
cleanup_handler() {
  local sig="$1"
  printf 'Cleaning up on %s...\n' "$sig"
  rm -f /tmp/myapp_*
}

Signal.on EXIT cleanup_handler

# Register a second EXIT handler (will fire BEFORE cleanup_handler)
log_exit() {
  printf 'Exiting.\n'
}
Signal.on EXIT log_exit

# Signal.dispatch fires all handlers in LIFO order:
# log_exit fires first, then cleanup_handler
```

### Available methods

```bash
Signal.on  SIGNAME callback    # push callback (fires first)
Signal.off SIGNAME callback    # remove first occurrence
Signal.pop SIGNAME             # remove and return last-pushed
Signal.clear SIGNAME           # remove all, uninstall trap
into=list Signal.list SIGNAME  # newline-joined list of callbacks
Signal.dispatch SIGNAME [args] # fire all callbacks manually
```

### Restrictions

Signal refuses to manage `KILL`, `STOP`, `DEBUG`, and `RETURN`:
- `KILL`/`STOP`: unblockable by the OS — handlers never fire.
- `DEBUG`/`RETURN`: bash pseudo-signals that fire per-command/per-return.
  Incompatible with the callback-stack model.

---

## 12. Testing with TestSuite

boop's `TestSuite` class provides a structured test runner with
sections, assertions, and summary reporting.

### Basic test structure

```bash
#!/usr/bin/env bash
. boop TestSuite

into=t TestSuite name="My Tests"

# ── First section ──────────────────────────────────────────────────
$t.section "Basic math"

into=r Math.add 2 2
$t.assert_eq "2+2=4" "$r" "4"

into=r Math.mul 3 4
$t.assert_eq "3*4=12" "$r" "12"

# ── Failure testing ────────────────────────────────────────────────
$t.section "Error handling"

$t.assert_fail "negative sqrt fails" Math.sqrt -1
$t.assert_ok   "positive sqrt works" Math.sqrt  4

# ── Summary ────────────────────────────────────────────────────────
$t.results
```

### Assertion methods

| Method | What it checks |
|--------|---------------|
| `$t.assert_eq "label" got want` | string equality |
| `$t.assert_ne "label" got want` | string inequality |
| `$t.assert_ok "label" cmd…` | command exits 0 |
| `$t.assert_fail "label" cmd…` | command exits non-zero |
| `$t.assert_match "label" str pattern` | glob match |
| `$t.assert_contains "label" haystack needle` | substring |

### Sections

`$t.section "label"` groups assertions visually and in the report.

### Exit code

`$t.results` exits 0 if all assertions passed, 1 otherwise. Pipe your
test runner output through `tests/test_all` or call suites directly:

```bash
bash tests/unit/test_myclass_ts
```

### Verbose mode

Set `TESTSUITE_VERBOSE=1` in the environment to print every PASS line.
Default is to print only failures.

```bash
TESTSUITE_VERBOSE=1 bash tests/unit/test_signal_ts
```

---

## 13. CLI tools

The tools live in `bin/`. Run them from the repo root:

```bash
./bin/lens    --help
./bin/boson   --help
./bin/probe   --help
./bin/collider --help
```

### lens — text stream inspection

`lens` is a composable replacement for `head`, `tail`, `grep`, `cut`,
and `wc`. One axis per invocation; axes compose naturally in a pipeline.

```bash
# First 10 lines
cat file | ./bin/lens --first 10

# Last 5 lines that match a pattern
cat file | ./bin/lens --last 5 --match 'ERROR'

# Fields 1 and 3 from a colon-delimited file
cat /etc/passwd | ./bin/lens --fields 1,3 -f :

# Count matching lines
cat file | ./bin/lens --match 'WARN' --count

# Lines from the 20th to the 30th
cat file | ./bin/lens --from 20 --to 30

# With line numbers
cat file | ./bin/lens --first 5 --number
```

### boson — JSON query

`boson` queries JSON with a jq-style path syntax, backed by
`Data.JSON`. No external dependencies.

```bash
echo '{"name":"Alice","age":30}' | ./bin/boson '.name'
# Alice

echo '{"users":[{"id":1,"name":"Alice"},{"id":2,"name":"Bob"}]}' \
  | ./bin/boson '.users[].name'
# Alice
# Bob

# Raw output (no quoting)
echo '{"x":42}' | ./bin/boson -r '.x'
# 42
```

### probe — HTTP client

`probe` makes plaintext HTTP requests (no TLS — use `curl` for HTTPS).
Useful for testing local services and APIs.

```bash
./bin/probe http://localhost:8080/api/status
./bin/probe -X POST -d '{"key":"val"}' http://localhost:3000/data
./bin/probe -i http://localhost:8080/    # include response headers
./bin/probe -s http://localhost:8080/    # status line only
```

### collider — single-file bundler

`collider` bundles a tool and all its boop dependencies into one
portable executable. The output runs on any machine with bash 4.3+
and no boop installation.

```bash
./bin/collider bin/lens -o lens.bundle
chmod +x lens.bundle
./lens.bundle --help   # no boop installation needed
```

---

## 14. Complete example: a task list app

This example brings together classes, inheritance, properties, the
return system, Config, List, and a basic test suite.

### `tasks.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
. boop List Config Args

# ── Task class ────────────────────────────────────────────────────────

Task.describe() {
  local _Class="${_Class:-Task}" _Self="${_Self:-}"
  local __Task_describe_id __Task_describe_title __Task_describe_done
  into=__Task_describe_id    _Self.id
  into=__Task_describe_title _Self.title
  into=__Task_describe_done  _Self.done
  local __Task_describe_mark="[ ]"
  [[ "$__Task_describe_done" == "1" ]] && __Task_describe_mark="[x]"
  boop.pass "${__Task_describe_mark} #${__Task_describe_id}: ${__Task_describe_title}" "${into:-}"
}

Task.complete() {
  local _Class="${_Class:-Task}" _Self="${_Self:-}"
  _Self.done="1"
}

boopClass Task 'has:id,title,done public:describe,complete'

# ── TaskList class ────────────────────────────────────────────────────

TaskList.new() {
  local _Class="${_Class:-TaskList}" _Self="${_Self:-}"
  __boop.new "$@"
  into=__TaskList_new_lst List
  _Self.tasks="$__TaskList_new_lst"
  _Self.nextId="1"
}

TaskList.add() {
  local _Class="${_Class:-TaskList}" _Self="${_Self:-}"
  local __TaskList_add_title="${1:-}" __TaskList_add_id __TaskList_add_lst
  [[ -n "$__TaskList_add_title" ]] || { _Error "TaskList.add: title required"; return 1; }
  into=__TaskList_add_id  _Self.nextId
  into=__TaskList_add_lst _Self.tasks
  into=task Task id="$__TaskList_add_id" title="$__TaskList_add_title" done="0"
  $__TaskList_add_lst.push "$task"
  _Self.nextId="$(( __TaskList_add_id + 1 ))"
  boop.pass "$task" "${into:-}"
}

TaskList.show() {
  local _Class="${_Class:-TaskList}" _Self="${_Self:-}"
  local __TaskList_show_lst __TaskList_show_n __TaskList_show_i
  local __TaskList_show_task __TaskList_show_desc
  into=__TaskList_show_lst _Self.tasks
  into=__TaskList_show_n   $__TaskList_show_lst.length
  for (( __TaskList_show_i=0; __TaskList_show_i<__TaskList_show_n; __TaskList_show_i++ )); do
    into=__TaskList_show_task $__TaskList_show_lst.get "$__TaskList_show_i"
    into=__TaskList_show_desc $__TaskList_show_task.describe
    printf '%s\n' "$__TaskList_show_desc"
  done
}

TaskList.pending() {
  local _Class="${_Class:-TaskList}" _Self="${_Self:-}"
  local __TaskList_pending_lst __TaskList_pending_n
  local __TaskList_pending_i __TaskList_pending_task __TaskList_pending_done
  local -i __TaskList_pending_count=0
  into=__TaskList_pending_lst _Self.tasks
  into=__TaskList_pending_n   $__TaskList_pending_lst.length
  for (( __TaskList_pending_i=0;
         __TaskList_pending_i<__TaskList_pending_n;
         __TaskList_pending_i++ )); do
    into=__TaskList_pending_task $__TaskList_pending_lst.get "$__TaskList_pending_i"
    into=__TaskList_pending_done $__TaskList_pending_task.done
    [[ "$__TaskList_pending_done" == "0" ]] && (( __TaskList_pending_count++ )) || true
  done
  boop.pass "$__TaskList_pending_count" "${into:-}"
}

boopClass TaskList 'public:add,show,pending'

# ── Main ──────────────────────────────────────────────────────────────

into=tl TaskList

into=t1 $tl.add "Write the tutorial"
into=t2 $tl.add "Add tests"
into=t3 $tl.add "Ship it"

$t1.complete

printf '=== Tasks ===\n'
$tl.show

into=remaining $tl.pending
printf '\n%s task(s) remaining.\n' "$remaining"
```

Run it:

```bash
bash tasks.sh
```

Expected output:

```
=== Tasks ===
[x] #1: Write the tutorial
[ ] #2: Add tests
[ ] #3: Ship it

2 task(s) remaining.
```

### Adding a test suite

```bash
#!/usr/bin/env bash
set -euo pipefail
. boop TestSuite

# source the app (class definitions only — no main block if you guard with
# [[ "${BASH_SOURCE[0]}" == "$0" ]] around your main logic)
. tasks.sh

into=t TestSuite name="TaskList Tests"

# ── Creation ────────────────────────────────────────────────────────
$t.section "TaskList creation"

into=tl TaskList
into=n $tl.pending
$t.assert_eq "new list has 0 pending" "$n" "0"

# ── Adding tasks ─────────────────────────────────────────────────────
$t.section "Adding tasks"

into=task1 $tl.add "First task"
$t.assert_ok  "add returns object ID" test -n "$task1"

into=desc $task1.describe
$t.assert_contains "describe includes title" "$desc" "First task"
$t.assert_contains "describe shows pending"  "$desc" "[ ]"

into=n $tl.pending
$t.assert_eq "one pending after add" "$n" "1"

# ── Completing tasks ──────────────────────────────────────────────────
$t.section "Completing tasks"

$task1.complete
into=desc $task1.describe
$t.assert_contains "complete marks done" "$desc" "[x]"

into=n $tl.pending
$t.assert_eq "zero pending after complete" "$n" "0"

# ── Error handling ────────────────────────────────────────────────────
$t.section "Error handling"

$t.assert_fail "add without title fails" $tl.add ""

$t.results
```

---

## Next steps

- Read **[docs/boop.md](boop.md)** — full dispatch, return system,
  naming rules, every public function.
- Read **[docs/STANDARDS.md](STANDARDS.md)** — coding conventions,
  shell option requirements, error handling contract.
- Browse **[docs/GOTCHAS.md](GOTCHAS.md)** — surprising bash
  behaviours that affect boop code.
- Explore the library classes in the source tree — every class is a
  working example of boop conventions.
- Run the included test suites:
  ```bash
  bash tests/test_all
  ```
- Try `./bin/boopShell` for an interactive boop playground.
