# boop

**Object-oriented programming for bash 4.3+.**   
Real classes, real objects, single inheritance (with mixins), a
namespace system, and a growing library — all in pure bash, requiring
no third-party tools and no subshells in the dispatch path.

The framework file is called `boop` because fun is a feature.

> **NUL bytes.** Bash variables cannot hold or detect NUL bytes. Any value
> containing a NUL will be silently truncated at the first one — no error,
> no warning. This is a bash limitation that applies throughout the framework.
> See [GOTCHAS.md](docs/GOTCHAS.md) for details.

---

## Why This Exists

Bash is a glue language. It excels at wiring programs together, not at
organizing large amounts of logic. When a script grows past a few hundred
lines, the usual tools — functions, global variables, naming conventions —
can start to fight each other unless you're *very* careful. You often end
up with prefixed globals and parallel arrays and limited ways to pass
structured data between functions without storing it in files, forking 
subshells to return values or chain together pipelines, or leaking state
everywhere and stomping over your own globals.

boop is an answer to that problem. It gives bash some vocabulary it's missing:
objects with conventionally private state, classes with constructors and inherited
methods, a return system that avoids subshells, and a namespace-aware class
loader that scales from a single script to a library of scores of classes.

### Scope 

Boop is not a toy. The framework itself is ~2,500 lines of bash. The included
classes — useful utilities like Config, JSON, Args, Math, SemVer, and others —
are well-tested implementations. The test suite runs 1,300+ tests across
unit, integration, and property-based suites. There are even mixins.

You can use the Collections (List, Map, Stack, Queue, Set, etc) to implement
arbitrary depth complex data structures, or just use complex keys in Map::Fast
to optimize for speed in the hot path. The Math class is *arbitrary precision*
and runs entirely on internal in-memory methods without subshells or pipes or
any calls to `bc` or `awk` or any other language. It might not be the fastest
approach, but it can do Math that chokes most `awk` code, and it has a simple
and convenient method interface. Want PI to a hundred places? Just takes time.

Some of the classes don't really add new functionality; Text::String doesn't
really do much you can't already do in standard bash, but it provides simple,
convenient, memorable methods to do those things on instanced and easily
organizable data. `$s.trim` edits in place; `$s.trimmed` returns an edited
result without altering the original. Those are a lot easier than rolling
your own multiline code.

### Design Principles

A few terms and principles that appear throughout the documentation:

- **LSP (Liskov Substitution Principle):** a subtype should be usable
  wherever its parent type is expected without breaking behavior. In boop,
  this means inherited methods work correctly on subclass instances, and
  when we intentionally *diverge* from a parent's contract (like Stream's
  `read` vs bash's `read` builtin), we document it explicitly as an "LSP
  divergence." See [STANDARDS.md](docs/STANDARDS.md) for the full treatment.

- **Primitives inward, wrappers outward:** the core logic lives in one
  place; variant entry points are thin wrappers that delegate to it.

- **errexit-safe by default:** all framework code must survive `set -e`
  without modification. See [STANDARDS.md](docs/STANDARDS.md#shell-options)
  and [GOTCHAS.md](docs/GOTCHAS.md) for the patterns.

---

## Requirements

- bash 4.3+ (for associative arrays and namerefs)
- bash 5.0+ recommended (for `EPOCHREALTIME` timing in TestSuite)
- That's it.

macOS ships bash 3.2 for GPL reasons. `brew install bash` fixes that. Make
sure `/usr/local/bin/bash` (or wherever Homebrew installs it) is what your
scripts use.

---

## Install

```bash
git clone $repoUrl $boopDir # makes a "boopRoot" install
PATH+=":$pathToBoopDir"     # `. boop` works anywhere
```

No build step. No package manager. Just source the framework and start.

Is there more customization and setup you might want? Sure, see below.
Is it needed? Not usually. You don't even have to add boop to your path
if your script doesn't load any of the default library classes. Just 
source it with a full path and build what you need inline.

---

## Writing a Class

Here's a minimal working class:

```bash
. boop                                        # load the core framework

# inherits default constructor and property methods
# since we didn't need any special behavior for those

Greeter.greet() {
  local _Class="${_Class:-Greeter}"                                     # boilerplate
  local _Self="${_Self:-${_Class}}"                                      # convenience
  local __Greeter_greet_name="I'm a Boop Class"                         # scoped defaults
  [[ "$_Self" == "$_Class" ]] || into=__Greeter_greet_name $_Self.name  # per object name
  boop.pass "Hello, ${__Greeter_greet_name:-World}!" ${into:-}          # standard return
}

boopClass Greeter 'has:name public:greet'     # register the class
```

Use it (this code is in `sayHi` if you want to try it):

```bash
#!/usr/bin/bash

. boop Greeter

Greeter.greet

into=g Greeter name="from Boop"
into=msg $g.greet
printf "%s\n" "$msg"

into=b Greeter
_EOL=" It's nice to meet you!"$'\n' $b.greet

# inline subclass
FancyGreeter.greet() { # overwrite inherited method
  local _Self="${_Self:-}" _Class="${_Class:-FancyGreeter}" __FancyGreeter_greet_tmp
  into=__FancyGreeter_greet_tmp _Super greet                                    # call parent class's method
  boop.pass "✨ ${__FancyGreeter_greet_tmp// Class/ +Subclass+} ✨" ${into:-}  # append a fancy sparkle
}
boopClass FancyGreeter isa:Greeter has:name public:greet

FancyGreeter.greet
into=g FancyGreeter name="from *Fancy*"
into=msg $g.greet
printf "%s\n" "$msg"
into=b FancyGreeter
_EOL=" It's NICER to meet you!"$'\n' $b.greet
```

The output:
```
Hello, I'm a Boop Class!
Hello, from Boop!
Hello, World! It's nice to meet you!
✨ Hello, I'm a Boop +Subclass+! ✨
✨ Hello, from *Fancy*! ✨
✨ Hello, World! ✨ It's NICER to meet you!
```

### What Each Piece Does

**`local _Class="${_Class:-Greeter}"`** reads `_Class` from the calling scope
(set by a baked wrapper) and defaults to `Greeter` if not set. This is how
the constructor knows which class it's building. Subclasses set it to their
own name before calling up the chain, which handles inheritance.

**`local _Self="${_Self:-}" _Class="${_Class:-Greeter}"`** in instance methods
reads both the object ID (`_Self`) and its class (`_Class`) from the dispatch
wrapper. Automatically generated wrappers set these explicitly as inline variables
on object and class method calls.

**`$_Self.name`** reads the property named `name` from the current object.

**`boop.pass value ${into:-}`** is the standard return. If the caller used
`into=varname`, it writes there. Otherwise it falls through to stdout or `_Out`.

**`boopClass`** registers the class. `has:` names the properties that the
constructor will populate from `key=value` constructor arguments. `public:` lists
the methods to expose (method dispatch uses this). Everything else is inheritance.

**`_Super greet`** dispatches to the nearest ancestor that implements `greet`.
`_Self` remains bound to the original object throughout, so the parent method
still operates on the right data. The method resolution order (MRO) cache means
the lookup cost is paid once per class/method pair and then zero thereafter.

See [docs/boop.md](docs/boop.md) for the full dispatch and return system reference.

A few other dispatch helpers worth knowing:

**`_Cast ClassName`** dispatches the next method call through a specific class
in the hierarchy — useful when you need to bypass the MRO and call a particular
ancestor's version directly, without changing `_Self`.

**`_Delegate $other`** redirects all method lookups to a different object. The
method runs in the context of `$other` — its `_Self`, its properties. Useful for
composition patterns where one object borrows another's behavior wholesale.

**`_Bless $obj ClassName`** changes an object's registered class without
reconstructing it. Useful for state machines and type-narrowing after validation.

See [docs/boop.md](docs/boop.md) for the full dispatch reference.

---

## The Import System

### Loading Classes

```bash
# Load framework + classes in one line
. boop List Map Config

# Classes load their own dependencies
. boop Cube                    # automatically loads Box (Cube extends Box)

# Load explicitly, crash if not found
_Require Config

# Load optionally — check the return code
_Load 'Data::JSON' && _json_available=1
```

### Namespace Syntax

Classes live in namespace directories. The directory path maps directly to the
fully-qualified class name:

```
Collection/List/List           →  Collection::List   (short name: List)
Collection/Map/Map             →  Collection::Map    (short name: Map)
Collection/Map/Fast/Fast       →  Collection::Map::Fast
Data/JSON/JSON                 →  Data::JSON
```

Use `::` or `/` interchangeably:

```bash
. boop 'Collection::Map::Fast'
. boop 'Collection/Map/Fast'    # identical
```

### Short Names and Aliasing

When a short name is unambiguous across the loaded library, it resolves
automatically. `List` works because only one class is named `List`. When a name
would be ambiguous, use the qualified form.

Create explicit aliases with `_Import`:

```bash
_Import 'Collection::Map::Fast'            # auto-alias: Fast, Map.Fast, Collection.Map.Fast
_Import 'Collection::Map::Fast' as FastMap # custom alias

into=cache FastMap
```

The `_AutoAlias` variable controls automatic aliasing behavior: `full` (default),
`best` (shortest unambiguous name plus FQN), `short` (short name plus FQN only),
or `none` (explicit only).

### Search Path

For each root in `[ . : BOOPPATH entries : PATH ]`, resolution runs:

1. Explicit `__boop_classPath` override for this name
2. `.boopIndex` short-name lookup → full namespace → filesystem path
3. `ClassName/ClassName` directory convention
4. `ClassName` bare file

```bash
export BOOPPATH="/opt/shared-libs:/home/user/mylib"

# Register a specific file directly
boop.classPath set MyClass /path/to/MyClass

# Inspect effective root list
into=dirs boop.classPath dirs

# Rebuild the short-name index after adding classes
boop.classPath rebuild
```

---

---

## The Return System

Bash has two idiomatic ways to get a value out of a function: print to stdout
and capture with `$()`, or write to a named global variable. The first spawns a
subshell — slow, and it breaks assignments made inside the function. The second
pollutes global scope and is easily clobbered.

boop uses a third way: **namerefs**.

```bash
into=result $obj.someMethod
```

`into=result` passes the variable name `result` as an environment variable.
The method receives it and writes the return value directly into the caller's
`result` variable via a nameref — no subshell, no global side-channel, no copy.
The value is available immediately in the caller's scope.

```bash
# These are all equivalent, but into= is the recommended path:
into=vol $box.volume         # fast: nameref write, no fork
vol=$( $box.volume )         # works, but spawns a subshell
$box.volume; vol="$_Out"     # global side-channel (_Out is overwritten by the next call)
```

**The rule:** use `into=` everywhere. The only exception is contexts where
you're already inside a subshell and don't care about the cost.

One important gotcha: `into=` inside a subshell writes to the subshell's copy
of the variable, not the parent's. The value disappears when the subshell
exits. boop detects this and emits a warning.

## Logging

Six levels. The default fatality threshold is `crash` — only explicit `_Crash`
exits the process unless you change it.

```bash
_Crash "unrecoverable: $reason"    # always exits with stack trace
_Error "something failed"          # logged; fatal if threshold ≤ error
_Warn  "something looks wrong"
_Info  "starting subsystem X"
_Debug "loop iteration: i=$i"
_Trace "inside dispatch: class=$_Class method=$method"
```

Control level globally or per class:

```bash
_LogLevel debug              # global: show debug and above
_LogLevel warn  Math         # Math only shows warnings and above
_FatalLevel warn             # treat warnings as fatal (useful in CI)
```

### Local Variable Naming

All locals in class methods should follow the common naming convention:
`__ClassName_methodName_varname`. This isn't just aesthetic preference — 
it prevents nameref collisions when method calls nest. If two levels of the call
stack both have a local named `name`, a nameref at the inner level will by design
correctly and silently shadow the outer one. The `__ClassName_` prefix makes
collisions essentially impossible, especially when coupled with method name.

The naming convention check in `tests/test_all` checks this.

---

## Objects and Classes

### Creating Objects

All objects are created with the same syntax:

```bash
into=obj ClassName [property=value ...]
```

The constructor sets named properties from the arguments and returns the new
object ID. That ID — something like `_a1b2c3` — is what gets stored in your
variable, and it is also a callable command for method dispatch.

```bash
. boop Cube

into=c Cube size=5 unit=cm
into=vol $c.volume          # 125
$c.toString pretty
# Cube(_a1b2c3) {
#   size   = 5
#   unit   = cm
#   length = 5
#   width  = 5
#   height = 5
# }
```

### Properties

```bash
into=v $c.get size           # "5"
$c.set size 10               # mutate in place
into=v $c.get size           # "10"
```

Properties are bash variables — bash stores everything as strings, so
there are no int, float, or bool types at the storage level. Values are
interpreted by how they're used: `$(( v + 1 ))` treats `v` as an integer,
`[[ $v =~ ^[0-9]+$ ]]` tests it as a string pattern, `${v^^}` transforms
it as text. The same property can legitimately be all three in different
parts of the same script.

### Type Checking

`isa` walks the full inheritance chain:

```bash
$c.isa Cube      # exit 0 — yes
$c.isa Box       # exit 0 — Cube extends Box
$c.isa boop      # exit 0 — everything extends boop
$c.isa List      # exit 1 — no

# Without an argument, isa returns the runtime class name:
into=cls $c.isa
echo "$cls"    # "Cube"
```

---

## Two Kinds of Classes

Not all classes in this framework are the same kind of thing. Understanding
the distinction matters for using the library well, for knowing when to reach
for a class and when to stay with raw bash, and for writing your own.

### Capability Classes

Some classes exist because bash genuinely can't do the thing without them.
`Math` implements arbitrary-precision arithmetic — bash's built-in `$(( ))`
is limited to 64-bit signed integers; there's no inline way to multiply
123456789 by 987654321 and get the right answer. `Data.JSON` implements a
recursive descent parser in pure bash; there's no parameter expansion for
that. `Collection.List`, `Map`, `Set`, `Stack`, `Queue` are *recurseable*
data structures for which bash has no native concept.

These classes keep you from having to roll your own on concepts you'd
otherwise usually just reach for another language to accomplish. Yes,
there's a speed hit for the overhead, but after writing a few scripts
with Args where the parse schema handles both your help screens and all
your argument parsing including a LOT of built-in setup, you may wonder
why you ever bothered with a getopts loop. 

### Convenience Classes

Other classes exist because bash *can* do the thing, but repetition and
inconsistency makes it very tedious.

`Text.String` is the clearest example. Every operation it provides —
trimming whitespace, changing case, padding, finding substrings — is already
available in bash through parameter expansion, built-in operators, and
arithmetic:

```bash
# These do what $s.trim, $s.upcase, $s.contains do:
v="${v#"${v%%[![:space:]]*}"}"
v="${v%"${v##*[![:space:]]}"}"
v="${v^^}"
[[ "$v" == *"$needle"* ]]
```

Using `Text.String` is **strictly slower** than the inline forms for any
individual operation. The overhead comes from multiple layers: object
creation (a descriptor allocation and two property writes), method dispatch
(MRO lookup, function frame entry), and property access (hash operations
rather than variable access). For a single `trim` on a one-off string,
inline parameter expansion beats it by an order of magnitude...for *speed*.

So why does the class exist?

**Code reuse.** If the same trim-downcase-replace pattern appears in five
scripts, those five copies accumulate bugs independently. One single 
implementation tested once and shared everywhere is often worth more than
the cycles saved by inlining.

**Multi-step pipelines.** The `do` method amortizes dispatch overhead across
all operations in the chain:

```bash
# Five -ed chains: five object allocations, five dispatch calls
into=s2 $s.trimmed
into=s3 $s2.downcased
into=s4 $s3.capitalized
into=s5 $s4.replaced "foo" "bar"
into=s6 $s5.rpadded 40

# One -ed do: one object allocation, one do dispatch, five bare calls
into=s2 $s.do "trimmed,downcased,capitalized,replaced:foo:bar,rpadded:40"
```

**Non-hot code paths.** Constructors, configuration loading, output
formatting — these run once or a handful of times. At that frequency the
overhead is immeasurable in practice. The readability and correctness
benefits are real; the performance cost is probably not. 

**Mixin composition.** A class that mixes in `Text.String` inherits the
full manipulation surface on its own string-valued property without having
to reimplement any of it. The overhead is paid once in the class's methods
where string manipulation already dominates the cost.

### When to Avoid Convenience Classes

- **Inside tight loops.** Processing thousands of strings in a loop: use
  parameter expansion if speed matters. The per-call overhead accumulates
  into something notable. If you think an object is worth it, use `do`.
- **Framework internals.** The `boop` runtime, `Args.parse`, and other
  framework-level code avoid framework abstractions to keep their own
  overhead minimal. Using a convenience class inside the plumbing creates
  recursive overhead. If writing classes that need speed, roll your own.
- **For a single one-shot transform.** `${v^^}` is six characters and zero
  overhead. Creating a `Text.String` object to call `upcase` once and
  discard the result is maybe not worth the ceremony.

A rule of thumb: if you'd write a function to avoid repeating logic across
several calls, the convenience class is probably worth it. 

### Naming Reflects Usage Frequency

Convenience classes in this framework follow the same naming principle as
well-designed languages: name length tracks usage frequency. Common
operations get short names (`trim`, `read`, `get`). Rare operations get
longer names (`decapitalize`, `indexOf`, `keysUnder`).

The `Text.String` API illustrates this: `trim` is four characters because
you'll type it often; `decapitalize` is twelve because you won't. The
asymmetry is intentional. A longer name costs reader attention at the
call site, which is the right trade when the operation is uncommon enough
that the longer name aids recognition.

This principle extends to method naming across the framework. When you see a
short method name, it signals high-frequency use. When you see a long one,
it signals that the operation is specialized enough to warrant the explicit
statement. (An exception is internals that you aren't expected to use directly.)

---

## Testing

All tests use the `TestSuite` class. Default output is quiet — failures and a
final summary only. Set `TESTSUITE_VERBOSE=1` for the full pass/fail log.

```bash
bash tests/test_all                  # full suite: unit + integration + naming check
bash tests/test_all smoke            # 11 smoke tests (framework alive?)
bash tests/test_all unit             # all unit tests
bash tests/test_all integration      # integration tests only
```

Individual suites:

```bash
bash tests/smoke/test_smoke
bash tests/unit/test_testsuite_ts    # TestSuite self-test
bash tests/unit/test_box_cube_ts
bash tests/unit/test_containers_ts
bash tests/unit/test_map_fast_ts
bash tests/unit/test_config_ts
bash tests/unit/test_args_ts
bash tests/unit/test_json_ts
bash tests/unit/test_math_ts
bash tests/unit/test_logging_ts
bash tests/unit/test_classpath_ts
bash tests/unit/test_mixin_ts
bash tests/unit/test_terminal_ts
bash tests/visual/test_terminal_visual   # interactive — grades each element y/n
bash tests/integration/test_blackjack
bash tests/integration/test_adversarial_ts
```

---

## Class Hierarchy

```
boop                                    root — new, destroy, get, set, isa, mixes, trueClass, toString, inspect
  ├── Geometry
  │     ├── Box                         3D rectangle — volume, face areas
  │     └── Cube                        equal-sided Box
  ├── Collection
  │     ├── Container                   abstract base for indexed collections
  │     │     ├── List                  ordered array — push/pop/slice/sort/each
  │     │     └── Map                   insertion-ordered key/value store
  │     ├── Map.Fast                    flat compound-key store — O(1) access
  │     ├── Iterator                    stateful cursor for Container subclasses
  │     ├── Stack                       LIFO — push/pop/peek (composition)
  │     │     └── Stack.Fast            LIFO via List inheritance — lighter, faster
  │     ├── Queue                       FIFO — enqueue/dequeue/peek (composition)
  │     │     └── Queue.Fast            FIFO via List inheritance — lighter, faster
  │     └── Set                         unique members — add/has/remove/union/intersect/diffs/minus
  ├── Mixins
  │     ├── Terminal                    ANSI control, named colors, symbol table
  │     ├── Greetable                   demo mixin — greet, identify
  │     └── Taggable                    demo mixin — addTag/hasTag/removeTag
  ├── Text
  │     └── String                      string objects — trim/case/pad/replace, bare and -ed forms, pipeline
  ├── DateTime                          date/time objects — epoch-based, zero-fork arithmetic and formatting
  ├── Data
  │     └── JSON                        JSON ↔ Map.Fast parser/serializer
  ├── Config                            flat + INI config file reader/writer
  ├── Args                              CLI argument parser (getOpts + parse)
  ├── Math                              arbitrary-precision arithmetic
  ├── Games
  │     ├── Card                        generic card base
  │     │     └── PlayingCard           individual playing card — suit, rank, face state
  │     └── Deck                        extends List — shuffle, draw
  └── Testing
        └── TestSuite                   structured test harness
```

---

## Further Reading

| Document | Contents |
|----------|----------|
| [docs/boop.md](docs/boop.md) | Full framework reference — return system internals, dispatch mechanics, naming rules, every public function, known gotchas |
| [docs/SemVer.md](docs/SemVer.md) | Version system — `require:` guard, `_Require` class versions, constraint syntax, architecture |
| [docs/comparison.md](docs/comparison.md) | boop idioms side-by-side with Python, Ruby, and Go equivalents |
| [docs/JSON.md](docs/JSON.md) | JSON class: supported types, key conventions, edge cases |
| [docs/List.md](docs/List.md) | Complete List API reference |
| [docs/Map.md](docs/Map.md) | Complete Map API reference |
| [docs/Math.md](docs/Math.md) | Arithmetic internals, precision, and the chunk algorithm |
| [docs/Container.md](docs/Container.md) | Container and Iterator API |
| [docs/String.md](docs/String.md) | Text.String API reference — mutators, -ed forms, pipelines, mixin usage |
| [docs/DateTime.md](docs/DateTime.md) | DateTime API reference — constructors, formatting, arithmetic, comparison, DST notes |
| [docs/tools.md](docs/tools.md) | CLI tools overview and index — when to reach for each, shared conventions |
| [docs/lens.md](docs/lens.md) | lens reference — text stream inspection (head/tail/grep/cut/wc) |
| [docs/boson.md](docs/boson.md) | boson reference — jq-style JSON query |
| [docs/probe.md](docs/probe.md) | probe reference — minimal plaintext HTTP client |
| [docs/collider.md](docs/collider.md) | collider reference — single-file bundler |
| [docs/TODO.md](docs/TODO.md) | Roadmap and open design questions |


---

## Collections

### List

An indexed array with O(1) access by position. Supports negative indices,
slicing, sorting, and cursor-based iteration.

```bash
. boop List

into=fruits List
$fruits.push apple banana cherry

into=n $fruits.length          # "3"
into=v $fruits.get 1           # "banana"
into=v $fruits.get -1          # "cherry"

$fruits.set 1 mango            # replace index 1
$fruits.remove 0               # remove first element (shifts remaining left)

# Callback iteration
print_item() { printf "  [%s] %s\n" "$1" "$2"; }   # index, value
$fruits.each print_item
#   [0] mango
#   [1] cherry

# Cursor iteration
$fruits.reset
while $fruits.hasNext; do
  into=item $fruits.next
  printf "%s\n" "$item"
done

# Slice a range (inclusive)
into=sub $fruits.slice 0 1     # "mango\ncherry"

# Functional operations
is_short() { (( ${#1} <= 5 )); }
upcase() { _Result="${1^^}"; }
join() { _Result="$1,$2"; }

into=result $fruits.do filter:is_short map:upcase reduce:join
# pipeline: filter → map → reduce, intermediates auto-destroyed
```

### Map

Insertion-ordered associative array. The one thing bash's `declare -A`
can't do natively is guarantee key order — Map tracks it. Object IDs
are strings, so Maps nest naturally into Lists (and vice versa) for
multidimensional structures:

```bash
. boop List Map

# Build a table: list of maps (rows of named columns)
into=table List
for name in Alice Bob Charlie; do
  into=row Map
  $row.set name "$name"
  $row.set role "$(( RANDOM % 2 ? "admin" : "user" ))"
  $table.push "$row"
done

# Access a cell by position + key
into=r $table.get 1
into=v $r.get name              # "Bob"

# Iterate in insertion order — keys come back as added
into=first $table.get 0
show() { printf "  %s=%s" "$1" "$2"; }
$first.each show; printf '\n'   # "  name=Alice  role=admin"
```

See `docs/Map.md` for the full API (get/set/has/delete/keys/values/
toArray/each/clear/toString).

### Map.Fast

When you need O(1) point lookups and don't need insertion order or full
iteration, use Map.Fast. It's designed for config, parsed documents, and
lookup tables where the key is known ahead of time.

```bash
. boop 'Collection::Map::Fast'

into=cache 'Collection::Map::Fast'
$cache.set users.0.name  Alice
$cache.set users.0.email alice@example.com
$cache.set users.1.name  Bob

into=v $cache.get users.0.name    # "Alice" — one hash lookup
into=v $cache.get users.1.name    # "Bob"
$cache.has users.2.name || echo "not found"

# Enumerate all keys (O(n) scan — use sparingly)
into=keys $cache.keys

# Keys under a prefix
into=sub $cache.keysUnder users.0
```

The dotted key path is just a string key — there's no tree traversal, no
nesting. This is what makes lookups fast.

**When to choose which:**
- **Map** when you need insertion order, full `each`/cursor iteration, or
  want to build the structure incrementally and traverse it later.
- **Map.Fast** when you have a flat or compound-key data set and your access
  pattern is mostly reads by known key.

### Nested Structures

Object IDs are strings. Store them as List or Map values to build nested
structures — no special syntax required.

```bash
# A list of maps — like a table of records
into=table List

for name in Alice Bob Charlie; do
  into=row Map
  $row.set name   "$name"
  $row.set active 1
  $table.push "$row"
done

# Access a cell
into=row_id $table.get 1
into=v $row_id.get name   # "Bob"

# Multidimensional list
into=matrix List
for (( r=0; r < 3; r++ )); do
  into=row List
  $row.push "$(( r*3+1 ))" "$(( r*3+2 ))" "$(( r*3+3 ))"
  $matrix.push "$row"
done

into=v $matrix.itemAt 1 2    # "6"   (row 1, col 2)
$matrix.setAt "99" 1 2       # mutate that cell
```

### Stack

LIFO stack. Composes a List internally.

```bash
. boop Stack

into=s Stack
$s.push task1 task2 task3

into=top $s.peek          # "task3" (no removal)
into=v   $s.pop           # "task3"
into=n   $s.size          # "2"
$s.isEmpty                # exits 1 (not empty)
```

**Stack.Fast** — same interface, inherits List directly. Faster (one object,
no delegation), but List methods like `each` and `toArray` are accessible.
`shift`/`unshift` are blocked with `_Error` stubs.

```bash
. boop Collection::Stack::Fast
into=s Collection.Stack.Fast.new
$s.push a b c
into=v $s.pop             # "c"
```

### Queue

FIFO queue. Composes a List internally.

```bash
. boop Queue

into=q Queue
$q.enqueue job1 job2 job3

into=front $q.peek        # "job1" (no removal)
into=v     $q.dequeue     # "job1"
into=n     $q.size        # "2"
```

**Queue.Fast** — same interface, inherits List directly. Faster (one object,
no delegation), but List methods like `each` and `toArray` are accessible.
`pop`/`unshift` are blocked with `_Error` stubs.

```bash
. boop Collection::Queue::Fast
into=q Collection.Queue.Fast.new
$q.enqueue x y z
into=v $q.dequeue         # "x"
```

### Set

Unordered unique-member collection. O(1) membership tests.

```bash
. boop Set

into=a Set; $a.add apple banana cherry
into=b Set; $b.add banana cherry date

$a.has apple               # exits 0 (member)
$a.has grape               # exits 1 (not a member)
$a.add apple               # no-op (already present)
into=n $a.size             # "3"

# All three symmetric operations — order of operands doesn't matter:
into=u $a.union     "$b"   # new Set: {apple, banana, cherry, date}
into=i $a.intersect "$b"   # new Set: {banana, cherry}
into=d $a.diffs     "$b"   # new Set: {apple, date}  ← in exactly one

# Asymmetric subtraction — order matters:
into=m $a.minus "$b"       # new Set: {apple}        ← in a but not b
into=m $b.minus "$a"       # new Set: {date}         ← in b but not a

# Set operations return new objects — call toArray to iterate:
into=arr $u.toArray        # newline-separated members (order undefined)
```

---

## Mixins

Method bundles that compose into any class without inheritance. A mixin
provides functions but owns no instance state — its methods read and write
the host object's properties through the same interface as any class method.

```bash
. boop Greetable Taggable
```

### Defining a mixin

```bash
# Mixins/Printable/Printable
. boop
boop.initMixin Printable || return 0

Printable.print() {
  local __Printable_print_s
  into=__Printable_print_s __boop.toString
  printf '%s\n' "$__Printable_print_s"
}

boopMixin Printable 'public:print'
```

### Using a mixin in a class

```bash
boopClass Widget mixin:Printable mixin:Taggable 'public:new,...'

into=w Widget.new
$w.print                # from Printable
$w.addTag important     # from Taggable
$w.hasTag important     # exits 0
```

### Resolution order

Class-defined methods win. Among mixins, first listed takes priority.
Later mixins are shadowed but always reachable explicitly:

```bash
$w.Taggable::identify   # always routes to Taggable's version
```

### Membership check

```bash
$w.mixes Printable   # exits 0 — has it (walks the inheritance chain)
$w.mixes Comparable  # exits 1 — doesn't have it
```

---

## Config

Read and write structured configuration files. Two formats, one interface.

```bash
. boop Config
```

### Flat Key=Value

```ini
# ~/.myapp.cfg
theme=dark
host=localhost
port=8080
url=http://host:8080/path?foo=bar
```

```bash
into=cfg Config.load ~/.myapp.cfg

into=v $cfg.get theme           # "dark"
into=v $cfg.get url             # "http://host:8080/path?foo=bar" — = in value preserved

$cfg.set theme light
$cfg.save                       # writes back to ~/.myapp.cfg

# Or write to a different file
$cfg.save /tmp/myapp.cfg
```

### INI

```ini
# /etc/myapp.ini
app=myapp

[database]
host=localhost
port=5432
user=admin

[server]
port=8080
workers=4
```

```bash
into=cfg Config.loadINI /etc/myapp.ini

into=v $cfg.get app               # "myapp" (top-level key)
into=v $cfg.get database.host     # "localhost"
into=v $cfg.get server.workers    # "4"

into=keys $cfg.keys database      # "host\nport\nuser"
into=secs $cfg.sections           # "database\nserver"

$cfg.set database.host db.prod.example.com
$cfg.save
```

### From a String

Useful for parsing schema strings, embedded config, or unit tests:

```bash
into=cfg Config.fromString '
[server]
host=localhost
port=8080
'
into=v $cfg.get server.host   # "localhost"
```

### Round-Trip

`toFlat` and `toINI` serialize to a file or return the content as a string:

```bash
into=cfg Config.new
$cfg.set x 1
$cfg.set y 2

into=text $cfg.toFlat          # "x=1\ny=2"
$cfg.toFlat /tmp/out.cfg       # write to file
$cfg.toINI  /tmp/out.ini       # write as INI
```

---

## JSON

Parse JSON into a Map.Fast object for O(1) access. Serialize back when done.
No `jq`, no Python, no subshells in the parser.

```bash
. boop 'Data::JSON'

json='{"user":{"name":"Alice","scores":[10,20,30]}}'
into=doc Data.JSON.parse "$json"

into=v $doc.get user.name         # "Alice"
into=v $doc.get user.scores.0     # "10"
into=v $doc.get user.scores.2     # "30"

# Mutate and serialize
$doc.set user.name Bob
into=out Data.JSON.stringify "$doc"
printf "%s\n" "$out"
# {"user":{"name":"Bob","scores":[10,20,30]}}
```

Keys are dot-separated paths: `user.scores.1` means `document["user"]["scores"][1]`.
Arrays are distinguished from objects by whether their keys are numeric strings.
Nested depth is handled recursively with no practical limit for normal documents.

---

## Args

Parse command-line arguments. Two entry points: a `getopts` wrapper for simple
scripts, and a full GNU long-option + subcommand parser for complex ones.

```bash
. boop Args
```

### Simple: getOpts

```bash
Args.getOpts ":vf:" "$@"
shift $((OPTIND-1))
# $v is "1" if -v was passed
# $f has the value of -f <value>
# Remaining positionals are in $@
```

The optstring follows standard `getopts` convention: a leading `:` enables
silent error mode, and a trailing `:` after a letter means that option takes a value.

### Full: parse

The schema is an INI-style string where the documentation *is* the schema.
You write it once; humans and the parser read the same source.

```bash
Args.parse '
[Use]
  deploy [options] ACTION [args...]

[Options]
  verbose | v                          # enable verbose output
  output  | o = /tmp/out.txt           # output file (default shown)
  : token | t =                        # required — auth token

[Subcommands]
  run   | r                            # run a job
  check | c                            # check status

[run]
  workers | w = 4                      # number of workers

[check]
  : target | T =                       # required for check subcommand
' "$@"

# After parsing, variables are set in current scope:
[[ -n "$verbose" ]] && set -x
echo "token:   $token"
echo "action:  $_Action"      # "run", "check", or ""
echo "workers: $workers"      # "4" if not provided

# Remaining positionals after options and subcommand:
set -- "${_ArgsRemaining[@]}"
```

**Schema syntax:**

| Line form | Meaning |
|-----------|---------|
| `name \| alias \| v` | Variable name is first; remaining entries are CLI aliases |
| `name \| v =` | Takes a value: `--name val` or `--name=val` or `-v val` |
| `name \| v = default` | Takes a value; uses `default` if not provided |
| `: name \| v =` | Required — crashes with an error if not provided |
| `name \| v` | Boolean flag — absent is `""`, present is `"1"` |

Single-character aliases map to `-x`. Multi-character aliases map to `--name`.
Hyphens are allowed in aliases but not in the variable name (which becomes a bash
identifier).

**After parsing:**
- Each option variable is set (to its value, default, or `""`)
- `$_Action` — the matched subcommand's canonical name, or `""`
- `$__Args_orig` — the original argument array before parsing
- `$_ArgsRemaining` — positionals that weren't consumed as options or subcommand

**Object mode** returns a Config object instead of scope variables:

```bash
into=parsed Args.parse "$schema" "$@"
into=v $parsed.get token
into=v $parsed.get _action
```

---

## Math

Arbitrary-precision arithmetic in pure bash. Numbers are stored as digit strings
with tracked sign and decimal position. All arithmetic runs on 9-digit integer
chunks in base 10⁹ using bash's built-in `$(( ))`. No subshells, no forks, no
external tools.

```bash
. boop Math

# Static methods for quick operations
into=v Math.add      1.5 2.3            # "3.8"
into=v Math.subtract 10  3.7            # "6.3"
into=v Math.multiply 123456789 987654321
# "121932631112635269"

# Expression evaluator — handles precedence and parentheses
into=v Math.DO "( 10 + 5 ) / 3"        # "5"
into=v Math.DO "2 ^ 64"                 # "18446744073709551616"

# Object API for multi-step work or high-precision results
into=a Math 355
into=b Math 113
into=r $a.divide $b                     # ratio of 355/113 ≈ pi
into=v $r.val
printf "%.10f\n" ... # result is a string, format as needed

# Pi to arbitrary precision (Machin's formula)
into=pi Math.pi 50
into=v $pi.val
# 3.14159265358979323846264338327950288419716939937510
```
