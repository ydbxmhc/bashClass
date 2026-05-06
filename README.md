# boop

**Object-oriented programming for bash 5+.** Real classes, real objects, single
inheritance, a namespace system, and a collection library — all in pure bash,
with no external dependencies and no subshells in the hot path.

The framework file is called `boop` because fun is a feature.

---

## Why This Exists

Bash is a glue language. It excels at wiring programs together, not at
organizing large amounts of logic. When a script grows past a few hundred
lines, the usual tools — functions, global variables, naming conventions —
start to fight each other. You end up with prefixed globals and parallel
arrays and no way to pass structured data between functions without either
forking a subshell or leaking state everywhere.

boop is an answer to that problem. It gives bash the vocabulary it's missing:
objects with encapsulated state, classes with typed constructors and inherited
methods, a return system that avoids subshells, and a namespace-aware class
loader that scales from a single script to a library of dozens of classes.

It is not a toy. The framework itself is ~2,200 lines of bash. The included
classes — List, Map, Config, JSON, Args, Math — are production-quality
implementations. The test suite runs 1,400+ assertions across unit,
integration, and property-based tests.

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
git clone <repo-url> /usr/local/lib/boop
# Add to PATH so `. boop` works from anywhere:
export PATH="/usr/local/lib/boop:$PATH"
```

No build step. No package manager. Just source the framework file and start.

---

## Five-Minute Tour

```bash
. boop List Map Config
```

That one line loads the framework and three classes. Now:

```bash
# Create a list and push some values
into=colors List
$colors.push red green blue

# Get elements by index (negative indices count from the end)
into=first $colors.get 0     # "red"
into=last  $colors.get -1    # "blue"

# Create a map (insertion-ordered associative array)
into=cfg Map
$cfg.set host localhost
$cfg.set port 8080

# Retrieve values
into=h $cfg.get host          # "localhost"

# Type-check any object — walks the full inheritance chain
$colors.isa List  && echo "yes"   # yes
$colors.isa boop  && echo "yes"   # yes (everything inherits from boop)
$colors.isa Map   && echo "no"    # (no output — wrong type)
```

The `into=varname command` syntax is how boop returns values. It is the central
pattern of the framework and the first thing worth understanding properly.

---

## The Return System

Standard bash has two ways to get a value out of a function: print to stdout
and capture with `$()`, or write to a global variable. The first spawns a
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

Properties are typed as strings. All values are strings. If you need to treat
a value as a number, use it in arithmetic context: `$(( v + 1 ))`.

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
```

### Map

An insertion-ordered associative array. Keys come back in the order they
were added — not in hash order, always insertion order.

```bash
. boop Map

into=m Map
$m.set host localhost
$m.set port  5432
$m.set user  admin

into=h $m.get host             # "localhost"
$m.has port && echo "found"    # found

# Keys in insertion order
into=k $m.keys                 # "host\nport\nuser"

# Callback iteration — receives key, then value
show() { printf "  %s = %s\n" "$1" "$2"; }
$m.each show
#   host = localhost
#   port = 5432
#   user = admin
```

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

---

## Writing a Class

Here's a minimal working class:

```bash
#!/bin/bash

# Load guard — prevents double-sourcing and double-registration
[[ -n "${__boop_registry[Greeter]+set}" ]] && return 2>/dev/null
. boop

Greeter.new() {
  local _Class="${_Class:-Greeter}"
  local __Greeter_new_self
  into=__Greeter_new_self __boop.new "$@"
  boop.pass "$__Greeter_new_self" ${into:-}
}

Greeter.greet() {
  local _Self="${_Self:-}" _Class="${_Class:-Greeter}"
  local __Greeter_greet_name
  into=__Greeter_greet_name __boop.get name
  boop.pass "Hello, ${__Greeter_greet_name}!" ${into:-}
}

boopClass Greeter 'has:name public:new,greet'
```

Use it:

```bash
. boop Greeter
into=g Greeter name=World
into=msg $g.greet
printf "%s\n" "$msg"   # Hello, World!
```

### What Each Piece Does

**The load guard** prevents the class from being registered twice if the file
is sourced more than once. The pattern checks the `__boop_registry` associative
array and returns immediately if the class is already there.

**`local _Class="${_Class:-Greeter}"`** reads `_Class` from the calling scope
(set by the baked wrapper) and defaults to `Greeter` if not set. This is how
the constructor knows which class it's building. Subclasses set it to their
own name before calling up the chain.

**`local _Self="${_Self:-}" _Class="${_Class:-Greeter}"`** in instance methods
reads both the object ID (`_Self`) and its class (`_Class`) from the dispatch
wrapper. The wrapper sets these explicitly as environment variable prefixes on
the function call -- they don't flow through dynamic scope inheritance.

**`__boop.new "$@"`** creates the object in the registry, parses constructor
arguments (`name=World`) into properties, and returns the object ID.

**`__boop.get name`** reads the property named `name` from the current object.
It uses `_Self` from the inherited scope.

**`boop.pass value ${into:-}`** is the standard return. If the caller used
`into=varname`, it writes there. Otherwise it falls through to stdout or `_Out`.

**`boopClass`** registers the class. `has:` names the properties that the
constructor will populate from `key=value` constructor arguments. `public:` lists
the methods to expose (method dispatch uses this).

### Local Variable Naming

All locals in class methods must follow `__ClassName_methodName_varname`. This
isn't an aesthetic preference — it prevents nameref collisions when method calls
nest. If two levels of the call stack both have a local named `name`, a nameref
at the inner level will silently shadow the outer one. The `__ClassName_` prefix
makes collisions essentially impossible.

The naming convention check in `tests/test_all` enforces this across all
framework files.

### Subclassing

```bash
FancyGreeter.new() {
  local _Class="${_Class:-FancyGreeter}"
  local __FancyGreeter_new_self
  into=__FancyGreeter_new_self __boop.new "$@"
  boop.pass "$__FancyGreeter_new_self" ${into:-}
}

FancyGreeter.greet() {
  local _Self="${_Self:-}" _Class="${_Class:-FancyGreeter}"
  local __FancyGreeter_greet_base
  into=__FancyGreeter_greet_base _Super greet   # call parent implementation
  boop.pass "✨ ${__FancyGreeter_greet_base} ✨" ${into:-}
}

boopClass FancyGreeter isa:Greeter 'public:new,greet'
```

`_Super greet` dispatches to the nearest ancestor that implements `greet`.
`_Self` remains bound to the original object throughout, so the parent method
still operates on the right data. The method resolution order (MRO) cache means
the lookup cost is paid once per class/method pair and then zero thereafter.

You can also use `_Cast` to dispatch as a specific class, and `_Delegate` to
redirect method calls to another object entirely.

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

## Logging

Six levels. The default fatality threshold is `error` — only `_Crash` exits the
process unless you change it.

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
bash tests/integration/test_blackjack
bash tests/integration/test_stress_ts
```

---

## Class Hierarchy

```
boop                                    root — new, get, set, isa, toString
  ├── Geometry
  │     ├── Box                         3D rectangle — volume, face areas
  │     └── Cube                        equal-sided Box
  ├── Collection
  │     ├── Container                   abstract base for indexed collections
  │     │     ├── List                  ordered array — push/pop/slice/sort/each
  │     │     └── Map                   insertion-ordered key/value store
  │     ├── Map.Fast                    flat compound-key store — O(1) access
  │     └── Iterator                    stateful cursor for Container subclasses
  ├── Data
  │     └── JSON                        JSON ↔ Map.Fast parser/serializer
  ├── Config                            flat + INI config file reader/writer
  ├── Args                              CLI argument parser (getOpts + parse)
  ├── Math                              arbitrary-precision arithmetic
  ├── Games
  │     ├── Card                        generic card base
  │     │     └── PlayingCard           standard 52-card deck (suit/rank/faceUp)
  │     └── Deck                        extends List — shuffle, draw
  └── Testing
        └── TestSuite                   structured test harness
```

---

## Further Reading

| Document | Contents |
|----------|----------|
| [docs/boop.md](docs/boop.md) | Full framework reference — return system internals, dispatch mechanics, naming rules, every public function, known gotchas |
| [docs/comparison.md](docs/comparison.md) | boop idioms side-by-side with Python, Ruby, and Go equivalents |
| [docs/JSON.md](docs/JSON.md) | JSON class: supported types, key conventions, edge cases |
| [docs/List.md](docs/List.md) | Complete List API reference |
| [docs/Map.md](docs/Map.md) | Complete Map API reference |
| [docs/Math.md](docs/Math.md) | Arithmetic internals, precision, and the chunk algorithm |
| [docs/Container.md](docs/Container.md) | Container and Iterator API |
| [TODO.md](TODO.md) | Roadmap and open design questions |

---

*Active development. Core framework and included classes are stable. The
namespace aliasing system (`_Import`, FQN resolution, auto-aliasing) is newly
implemented and may have rough edges — file issues if something unexpected
happens.*
