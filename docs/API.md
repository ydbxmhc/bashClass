# boop API Reference

Complete reference for every publicly exposed method in the boop framework.

---

## Conventions

### Returning values — `boop.pass` and `into=`

Methods that produce a value use `boop.pass` internally and are consumed with the `into=` prefix variable:

```bash
into=result $obj.method arg   # result holds the return value
into=n $list.length           # n holds the length as a string
```

If `into=` is omitted the value is printed to stdout (useful in subshell substitution,
but prefer `into=` in hot paths to avoid forking).

### Exit codes — predicate methods

Methods used as boolean tests return an exit code and produce no value output:

```bash
$list.isEmpty && echo "empty"
$obj.isa Collection.List || echo "not a list"
$set.has "foo"             # 0 = member, 1 = not
```

### Property initialization — `has:` and `key=value` args

A class declares its properties with `has:` in `boopClass`. Properties are passed as
`key=value` arguments to the constructor:

```bash
into=b Geometry.Box length=10 width=5 height=3
into=s $b.length    # s="10"
```

All property values are stored and returned as strings.

### Crash behavior

Methods that receive invalid input call `_Crash` and terminate the process with a
descriptive error message. There is no exception catching — guard your inputs before
calling, or let the crash surface the bug.

### `_Delimiter`

`toArray` and similar methods join multiple values with `_Delimiter` (default: newline `$'\n'`).
Set it in the caller's scope before the call to change the separator:

```bash
_Delimiter="," into=csv $list.toArray
```

---

## boop root

Every object inherits from `boop`. These methods are available on all objects.

| Method | Returns | Description |
|--------|---------|-------------|
| `$obj.get key` | `into=` | Read a property by name |
| `$obj.set key value` | — | Write a property by name |
| `$obj.isa ClassName` | exit code | 0 if object is an instance of (or inherits from) ClassName |
| `$obj.mixes MixinName` | exit code | 0 if the object's class (or any ancestor) mixes in MixinName |
| `$obj.trueClass` | `into=` | The concrete class name of the object |
| `$obj.toString` | `into=` | Human-readable representation (default: object ID) |
| `$obj.inspect` | `into=` | Raw pipe-delimited descriptor string |
| `$obj.itemFrom container key [key...]` | `into=` | Deep-read a nested container path starting from `container` |
| `$obj.setOn container key [key...] value` | — | Deep-write a nested container path starting from `container` |

**`isa` walks the full inheritance chain.** `$obj.isa boop` is always true.

**`mixes` walks the inheritance chain.** A subclass of a class that mixes a mixin
also reports `mixes` as true for that mixin.

---

## Geometry

### Geometry.Box

`boopClass Geometry.Box has:length,width,height,unit,color`

A rectangular box. All dimensions are plain numeric strings.

**Constructor**

```bash
into=b Geometry.Box length=10 width=5 height=3 unit=cm
```

**Properties** (read/write via `$b.get`/`$b.set`): `length`, `width`, `height`, `unit`, `color`

| Method | Returns | Description |
|--------|---------|-------------|
| `$b.calc [d1 [d2]]` | `into=` | Product of the given dimensions. 0 args → 1, 1 arg → single dim, 2+ args → product |
| `$b.area` | `into=` | `length × width` |
| `$b.top` | `into=` | Area of the top face (`length × width`) |
| `$b.bottom` | `into=` | Alias for `top` |
| `$b.end` | `into=` | Area of an end face (`height × width`) |
| `$b.side` | `into=` | Area of a side face (`height × length`) |
| `$b.volume` | `into=` | `length × width × height` |

**Inheritance:** `boop → Geometry.Box`

---

### Geometry.Cube

`boopClass Geometry.Cube isa:Geometry.Box has:size`

A cube (all sides equal). Inherits all Box methods.

**Constructor**

```bash
into=c Geometry.Cube size=4
```

The `size` property sets `length`, `width`, and `height` uniformly.

**Inherited methods:** all of `Geometry.Box` (`calc`, `area`, `top`, `bottom`, `end`, `side`, `volume`)

**Inheritance:** `boop → Geometry.Box → Geometry.Cube`

---

## Collection

### Collection.Container *(abstract)*

`boopClass Collection.Container has:type`

Virtual base class. Not instantiated directly. Defines the contract all containers must fulfill.

**Virtual methods** — child classes must override (crash if called on base):
`getAt`, `setAt`, `delete`, `length`, `clear`, `has`, `toArray`, `each`

**Provided methods** (implemented on Container, inherited by all):

| Method | Returns | Description |
|--------|---------|-------------|
| `$c.new [key=val...]` | `into=` | Create a new container instance |
| `$c.destroy` | — | Free the companion data array and remove from registry |
| `$c.isEmpty` | exit code | 0 if length == 0 |
| `$c.toString [pretty]` | `into=` | Summary string; pass `pretty` for multi-line format |
| `$c.deepGet key [key...]` | `into=` | Walk a nested container path, reading the final value |
| `$c.deepSet value key [key...]` | — | Walk a nested container path, writing the final value |
| `$c.iterator` | `into=` | Create an independent Iterator over this container |
| `$c.next` | `into=` | Advance internal iterator, return next value |
| `$c.prev` | `into=` | Move internal iterator back, return previous value |
| `$c.hasNext` | exit code | 0 if internal iterator has a next element |
| `$c.hasPrev` | exit code | 0 if internal iterator has a previous element |
| `$c.current` | `into=` | Value at the internal iterator's current position |
| `$c.iterIndex` | `into=` | Key/index at the internal iterator's current position |
| `$c.iterReset` | — | Reset internal iterator to before the first element |

**Internal iterator** is created lazily on first use. For independent cursors, use
`$c.iterator` to get an explicit `Iterator` object.

**Inheritance:** `boop → Collection.Container`

---

### Iterator

`boopClass Iterator has:target,target_class`

A cursor over a Container. Created explicitly via `$container.iterator` or via `Iterator` directly.

```bash
into=iter $list.iterator
while $iter.hasNext; do
  into=val $iter.next
  echo "$val"
done
```

| Method | Returns | Description |
|--------|---------|-------------|
| `$iter.hasNext` | exit code | 0 if there is a next element |
| `$iter.hasPrev` | exit code | 0 if there is a previous element |
| `$iter.next` | `into=` | Advance and return the next value |
| `$iter.prev` | `into=` | Move back and return the previous value |
| `$iter.current` | `into=` | Value at the current position (no movement) |
| `$iter.index` | `into=` | Key or index at the current position |
| `$iter.reset` | — | Reset to before the first element |

**`target`** — ID of the Container this iterator wraps.  
**`target_class`** — class name of that Container (e.g. `Collection.List`).

**Inheritance:** `boop → Iterator`

---

### Collection.List

`boopClass Collection.List isa:Collection.Container has:type`

Ordered, indexed array. Supports negative indices (Python-style: `-1` = last element).

**Constructor**

```bash
into=list Collection.List
```

| Method | Returns | Description |
|--------|---------|-------------|
| `$list.length` | `into=` | Number of elements |
| `$list.clear` | — | Remove all elements |
| `$list.has index` | exit code | 0 if the index exists (negative indices supported) |
| `$list.getAt index` | `into=` | Element at index (crashes if out of range) |
| `$list.setAt index value` | — | Overwrite element at index |
| `$list.delete index` | — | Remove element; remaining elements shift down |
| `$list.push val [val...]` | — | Append one or more values to the end |
| `$list.pop` | `into=` | Remove and return the last element (crashes if empty) |
| `$list.shift` | `into=` | Remove and return the first element (crashes if empty) |
| `$list.unshift val [val...]` | — | Prepend one or more values to the front |
| `$list.slice start [end]` | `into=` | `_Delimiter`-joined substring of elements |
| `$list.toArray` | `into=` | All elements joined by `_Delimiter` |
| `$list.toString` | `into=` | JSON-array-style representation: `[ "a", "b" ]` |
| `$list.each callback` | — | Call `callback index value` for each element in order |

`each` runs the callback in the current shell — it can read and write the caller's variables.
Return nonzero from the callback to stop early.

Inherits `destroy`, `isEmpty`, `deepGet`, `deepSet`, `iterator`, `next`, `prev`,
`hasNext`, `hasPrev`, `current`, `iterIndex`, `iterReset` from Container.

**Inheritance:** `boop → Collection.Container → Collection.List`

---

### Collection.Map

`boopClass Collection.Map isa:Collection.Container has:type`

Insertion-ordered associative array. Keys maintain the order they were first inserted.

**Constructor**

```bash
into=map Collection.Map
```

| Method | Returns | Description |
|--------|---------|-------------|
| `$map.length` | `into=` | Number of key-value pairs |
| `$map.clear` | — | Remove all entries |
| `$map.has key` | exit code | 0 if key exists |
| `$map.getAt key` | `into=` | Value for key (empty string if absent) |
| `$map.setAt key value` | — | Insert or overwrite a key-value pair |
| `$map.delete key` | — | Remove a key; order of remaining keys is preserved |
| `$map.keys` | `into=` | All keys joined by `_Delimiter`, in insertion order |
| `$map.values` | `into=` | All values joined by `_Delimiter`, in insertion order |
| `$map.toArray` | `into=` | All `key=value` pairs joined by `_Delimiter`, in insertion order |
| `$map.toString` | `into=` | JSON-object-style representation: `{ "k": "v", ... }` |
| `$map.each callback` | — | Call `callback key value` for each pair in insertion order |

Inherits `destroy`, `isEmpty`, `deepGet`, `deepSet`, `iterator`, `next`, `prev`,
`hasNext`, `hasPrev`, `current`, `iterIndex`, `iterReset` from Container.

**Inheritance:** `boop → Collection.Container → Collection.Map`

---

### Collection.Map.Fast

`boopClass Collection.Map.Fast has:sep`

Flat compound-key store. Keys are dot-delimited paths into a single associative array.
O(1) point lookups; no insertion order; no subtree objects.

Use Fast for config data, parsed documents, and lookup tables where you need quick
point access into flat or nested data. Use Map when you need insertion order or
per-level object identity.

**Constructor**

```bash
into=doc Collection.Map.Fast          # default separator "."
into=doc Collection.Map.Fast sep="/"  # custom separator
```

| Method | Returns | Description |
|--------|---------|-------------|
| `$doc.get key` | `into=` | Value at key (empty if absent) |
| `$doc.set key value` | — | Store value at key |
| `$doc.has key` | exit code | 0 if key exists |
| `$doc.delete key` | — | Remove a single key |
| `$doc.length` | `into=` | Total number of stored keys |
| `$doc.clear` | — | Remove all keys |
| `$doc.keys` | `into=` | All keys joined by `_Delimiter` (order undefined) |
| `$doc.keysUnder prefix` | `into=` | All keys starting with `prefix` + separator |
| `$doc.deleteUnder prefix` | — | Delete all keys under a prefix subtree |
| `$doc.toString` | `into=` | All `key=value` pairs, one per line |

Compound key example:

```bash
$doc.set "users.0.name" "Alice"
$doc.set "users.0.age"  "30"
into=name $doc.get "users.0.name"   # name="Alice"
into=keys $doc.keysUnder "users.0"  # keys="users.0.name\nusers.0.age"
```

**Inheritance:** `boop → Collection.Map.Fast`

---

### Collection.Stack

`boopClass Collection.Stack`

LIFO stack. Internally backed by a List; exposes only the stack surface.

**Constructor**

```bash
into=s Collection.Stack
```

| Method | Returns | Description |
|--------|---------|-------------|
| `$s.push val [val...]` | — | Add one or more values to the top |
| `$s.pop` | `into=` | Remove and return the top value (crashes if empty) |
| `$s.peek` | `into=` | Return the top value without removing it (crashes if empty) |
| `$s.size` | `into=` | Number of elements |
| `$s.isEmpty` | exit code | 0 if empty |

**Inheritance:** `boop → Collection.Stack`

---

### Collection.Queue

`boopClass Collection.Queue`

FIFO queue. Internally backed by a List; exposes only the queue surface.
`dequeue` is O(n) due to shift.

**Constructor**

```bash
into=q Collection.Queue
```

| Method | Returns | Description |
|--------|---------|-------------|
| `$q.enqueue val [val...]` | — | Add one or more values to the back |
| `$q.dequeue` | `into=` | Remove and return the front value (crashes if empty) |
| `$q.peek` | `into=` | Return the front value without removing it (crashes if empty) |
| `$q.size` | `into=` | Number of elements |
| `$q.isEmpty` | exit code | 0 if empty |

**Inheritance:** `boop → Collection.Queue`

---

### Collection.Set

`boopClass Collection.Set`

Unordered collection of unique values. Backed by a bash associative array.
Membership tests, add, and remove are O(1). Iteration order is hash-defined (undefined).
Set operations return new Set objects.

**Constructor**

```bash
into=s Collection.Set
```

| Method | Returns | Description |
|--------|---------|-------------|
| `$s.add val [val...]` | — | Add one or more members (duplicates ignored) |
| `$s.has val` | exit code | 0 if val is a member |
| `$s.remove val [val...]` | — | Remove one or more members (no-op if absent) |
| `$s.size` | `into=` | Number of members |
| `$s.isEmpty` | exit code | 0 if empty |
| `$s.toArray` | `into=` | Members joined by `_Delimiter` (order undefined) |
| `$s.union other` | `into=` | New Set: members present in self or other |
| `$s.intersect other` | `into=` | New Set: members present in both self and other |
| `$s.difference other` | `into=` | New Set: members of self not present in other |

`other` is a Set object ID, not a value.

**Inheritance:** `boop → Collection.Set`

---

## Data

### Data.JSON

`boopClass Data.JSON public:new,parse,stringify`

JSON parser and serializer. Produces and consumes nested Map/List/Map.Fast object trees.
Pure bash — no external tools, no `eval`, no `jq`.

**Constructor**

```bash
into=j Data.JSON
```

| Method | Returns | Description |
|--------|---------|-------------|
| `$j.parse jsonString` | `into=` | Parse a JSON string; returns a Map, List, or scalar |
| `$j.stringify object` | `into=` | Serialize a Map/List/scalar back to a JSON string |

`parse` returns a `Collection.Map` for objects, a `Collection.List` for arrays, or a
plain string for scalars (`"string"`, `42`, `true`, `false`, `null`).

`stringify` accepts either an object ID or a plain string. Nested Maps and Lists are
serialized recursively.

```bash
into=j Data.JSON
into=doc $j.parse '{"name":"Alice","scores":[10,20]}'
into=name $doc.getAt name        # name="Alice"
into=json $j.stringify "$doc"    # back to JSON
```

**Inheritance:** `boop → Data.JSON`

---

## Config

`boopClass Config has:file,format`

Structured config file reader/writer. Supports two formats:

- **Flat** — `key=value` lines, `#` comments, blank lines ignored.
- **INI** — `[section]` headers group `key=value` pairs. Keys stored as `"section.key"`.
  Top-level keys (before any section header) have no prefix.

Pure bash parsing — zero forks.

**Constructor**

```bash
into=cfg Config.new
```

| Method | Returns | Description |
|--------|---------|-------------|
| `$cfg.load file` | — | Load and parse `file`; auto-detects flat vs INI by presence of `[` headers |
| `$cfg.loadINI file` | — | Force INI parsing of `file` |
| `$cfg.fromString str` | — | Parse a flat key=value string (not a file) |
| `$cfg.fromFlatString str` | — | Alias for `fromString` |
| `$cfg.get key` | `into=` | Read a value (empty string if absent) |
| `$cfg.set key value` | — | Write or overwrite a key |
| `$cfg.has key` | exit code | 0 if key exists |
| `$cfg.keys` | `into=` | All keys joined by `_Delimiter`, in insertion order |
| `$cfg.sections` | `into=` | Unique section prefixes joined by `_Delimiter` (INI only) |
| `$cfg.save [file]` | — | Write back to `file` (defaults to the loaded file) |
| `$cfg.toFlat` | `into=` | Serialize to flat `key=value` string |
| `$cfg.toINI` | `into=` | Serialize to INI-format string |

INI key access uses dot notation:

```bash
$cfg.load settings.ini
into=port $cfg.get "server.port"
into=user $cfg.get "db.user"
into=top  $cfg.get "topLevelKey"     # no prefix for pre-section keys
```

**Inheritance:** `boop → Config`

---

## Args

`boopClass Args public:getOpts,parse`

CLI argument parser. Two entry points: a thin POSIX `getopts` wrapper and a
full schema-driven GNU-style long-option + subcommand parser.

### Args.getOpts

```bash
Args.getOpts ":v:f:" "$@"
# Sets $v, $f for recognized options. Caller must: shift $((OPTIND-1))
```

Thin wrapper around bash `getopts`. Option letters followed by `:` take a value string;
others set `1` (boolean). The leading `:` in the optstring enables silent error handling.

### Args.parse — schema format

```bash
Args.parse 'schema' "$@"
```

Schema is an INI-style string. Anything after `#` on a line is ignored.

```
[Use]
  myapp [options] [subcommand]    # synopsis; documentation only

[Options]
  verbose | v                     # boolean; sets $verbose="1" if present
  : output | o  = /tmp/out        # required; value arg; default /tmp/out
  file | f  :                     # optional; value arg; no default

[Subcommands]
  build | b   # subcommand with alias
  deploy

[build]
  target | t  = release           # option scoped to "build" subcommand
```

**Scope-write mode** (no `into=`):  
Sets `$varName` for each option, `$_Action` for the active subcommand,
`$__Args_orig` with original args, and `$_ArgsRemaining` with remaining positionals.
Restore positionals: `set -- "${_ArgsRemaining[@]}"`.

**Object mode** (`into=`):  
Returns a `Config` object. Requires Config loaded. Access via `$obj.get varName`,
`$obj.get _action`, `$obj.get _remaining`.

**Option line syntax:**

| Pattern | Meaning |
|---------|---------|
| `name \| alias` | boolean flag |
| `name \| alias :` | value argument, no default |
| `name \| alias = default` | value argument with default |
| `: name ...` | required argument (crashes if absent) |

Single-character entries map to `-x`; multi-character entries map to `--name`.

**Inheritance:** `boop → Args`

---

## Math

`boopClass Math has:digits,scale,neg`

Arbitrary-precision decimal arithmetic in pure bash. No `bc`, `awk`, or other external tools.
Supports both **static** (class-level, returns a string) and **instance** (object-level,
returns a Math object) calling styles.

**Constructor**

```bash
into=n Math.new "3.14"       # instance from literal
into=n Math.new              # defaults to 0
```

### Static API — returns a formatted decimal string

```bash
into=r Math.add      "1.5" "2.3"      # r="3.8"
into=r Math.subtract "10"  "3.7"      # r="6.3"
into=r Math.multiply "2.5" "4"        # r="10"
into=r Math.divide   "10"  "3"        # r="3.333333" (default 6 decimal places)
into=r Math.mod      "10"  "3"        # r="1"
into=r Math.pow      "2"   "10"       # r="1024"
into=r Math.abs      "-5"             # r="5"
into=r Math.neg      "3"              # r="-3"
into=r Math.square   "4"             # r="16"
```

Short aliases: `Math.x` = multiply. Symbol aliases: `Math.+`, `Math.-`, `Math.*`, `Math./`.

### Instance API — returns a new Math object

```bash
into=a Math.new "10"
into=b Math.new "3"
into=r $a.add    "$b"      # r = Math object containing 13
into=v $r.val              # v = "13" (string)
```

### Comparison (instance only)

All return exit code: `0` = true, `1` = false (except `cmp`).

| Method | Description |
|--------|-------------|
| `$a.cmp other` | Returns 0 (equal), 1 (a>b), 2 (a<b) as exit code |
| `$a.eq other` | 0 if equal |
| `$a.lt other` | 0 if self < other |
| `$a.gt other` | 0 if self > other |
| `$a.le other` | 0 if self <= other |
| `$a.ge other` | 0 if self >= other |
| `$a.isZero` | 0 if value == 0 |

### Formatting and conversion (instance)

| Method | Returns | Description |
|--------|---------|-------------|
| `$n.val` | `into=` | Value as a plain decimal string (trailing zeros stripped) |
| `$n.toString` | `into=` | Same as `val` |
| `$n.toInt` | `into=` | Integer part only (truncates, does not round) |
| `$n.round places` | `into=` | Round to given decimal places; returns new Math object |
| `$n.toScale places` | `into=` | Zero-pad to exactly `places` decimal places; returns new Math object |
| `$n.format [places [sep [dec]]]` | `into=` | Locale-style formatting with thousands separator and decimal point |

### Expression evaluators (static)

```bash
into=r Math.DO "( 2 + 3 ) * 4"   # r="20"  — infix with precedence and parens
into=r Math.RPN "2 3 + 4 *"      # r="20"  — reverse Polish notation
```

Operators: `+`, `-`, `*`, `/`, `^` (power), `%` (mod). Parens in `DO`. No leading zeros required.

```bash
into=r Math.pi 50      # r= pi to 50 decimal places (Machin formula)
```

**Inheritance:** `boop → Math`

---

## SemVer

`boopClass SemVer version:1.0.0`

Semantic version parsing and constraint checking. Delegates to the version comparison
primitives built into boop core.

All methods are static (no instance needed).

| Method | Returns | Description |
|--------|---------|-------------|
| `SemVer.satisfies ver constraint` | exit code | 0 if `ver` satisfies the constraint |
| `SemVer.compare verA verB` | `into=` | `-1` (A<B), `0` (equal), `1` (A>B) |

**Constraint syntax:**

| Syntax | Meaning |
|--------|---------|
| `1.2+` | >= 1.2.0 |
| `>=1.2.3` | >= 1.2.3 |
| `>1.2` | > 1.2.0 |
| `<=2.0` | <= 2.0.0 |
| `<2.0` | < 2.0.0 |
| `1.2.3` | exact match |

Missing minor/patch components default to 0: `"1"` == `"1.0.0"`.
Pre-release suffixes (e.g. `1.2.3-beta`) are stored but ignored in comparisons.

```bash
SemVer.satisfies "1.3.0" "1.2+" && echo "ok"
into=r SemVer.compare "1.2.0" "1.3.0"    # r="-1"
```

**Inheritance:** `boop → SemVer`

---

## Games

### Games.Card

`boopClass Games.Card public:new,toString`

Generic card base class. A property bag — no game logic or assumptions about content.
Subclasses add domain-specific properties and behavior.

**Constructor**

```bash
into=c Games.Card key=value ...
```

| Method | Returns | Description |
|--------|---------|-------------|
| `$c.toString` | `into=` | Returns the object's own ID (override in subclasses) |

**Inheritance:** `boop → Games.Card`

---

### Games.PlayingCard

`boopClass Games.PlayingCard isa:Games.Card has:suit,rank`

A standard playing card with `suit` (♠ ♥ ♦ ♣) and `rank` (A 2-10 J Q K).
Does not assign numeric values — that is game logic belonging in the consumer.

**Constructor**

```bash
into=c Games.PlayingCard suit="♠" rank="A"
```

| Method | Returns | Description |
|--------|---------|-------------|
| `$c.toString` | `into=` | Rank concatenated with suit — e.g. `A♠`, `10♥` |
| `$c.newDeck` | `into=` | Class method: create a shuffled 52-card `Games.Deck` of this card type |

`newDeck` respects `_Class` — subclasses that inherit it get a deck filled with
their own type.

**Inheritance:** `boop → Games.Card → Games.PlayingCard`

---

### Games.Deck

`boopClass Games.Deck isa:Collection.List has:type`

A List you can shuffle and draw from. No opinion about what's in it — the consumer
(typically a card class's `newDeck` method) populates it.

**Constructor**

```bash
into=d Games.Deck
# or via PlayingCard:
into=d Games.PlayingCard.newDeck
```

| Method | Returns | Description |
|--------|---------|-------------|
| `$d.shuffle` | — | Fisher-Yates shuffle in place |
| `$d.draw` | `into=` | Remove and return the top card (pop from end) |

Inherits all `Collection.List` methods: `push`, `pop`, `shift`, `unshift`, `getAt`,
`length`, `isEmpty`, `each`, etc.

**Inheritance:** `boop → Collection.Container → Collection.List → Games.Deck`

---

## Testing

### Testing.TestSuite

`boopClass Testing.TestSuite has:name,mode,verbose,passed,failed,...`

Test runner with section grouping, assertion methods, and a summary report.
Used by all boop test suites.

**Constructor**

```bash
into=t TestSuite name="My Suite"
# or with verbose output:
TESTSUITE_VERBOSE=1 into=t TestSuite name="My Suite"
```

`TestSuite` resolves to `Testing.TestSuite` via the `.boopIndex` alias.

| Method | Returns | Description |
|--------|---------|-------------|
| `$t.section "name"` | — | Begin a named section; groups the assertions that follow |
| `$t.run label command [args...]` | — | Run a command; record pass or fail based on exit code |
| `$t.assert_ok label command [args...]` | — | Pass if command exits 0 |
| `$t.assert_fail label command [args...]` | — | Pass if command exits non-zero |
| `$t.assert_eq label actual expected` | — | Pass if `actual == expected` (string comparison) |
| `$t.assert_ne label actual expected` | — | Pass if `actual != expected` |
| `$t.assert_match label actual pattern` | — | Pass if `actual` matches glob `pattern` |
| `$t.assert_contains label actual substring` | — | Pass if `actual` contains `substring` |
| `$t.info message` | — | Print an informational line (not counted as a test) |
| `$t.summary` | — | Print the final pass/fail counts and exit nonzero if any failures |

Each assertion prints `PASS` or `FAIL` with the label. In verbose mode (`TESTSUITE_VERBOSE=1`)
every pass is shown; otherwise only failures are printed until `summary`.

`$t.run` and `$t.assert_ok` are equivalent — both pass if the command exits 0.

**Inheritance:** `boop → Testing.TestSuite`

---

## Mixins

Mixins are method bundles composed into classes at declaration time with the `mixin:` token:

```bash
boopClass MyClass mixin:Terminal mixin:Taggable public:new,...
```

Methods are available on every instance of the class. The first mixin listed wins when
two mixins provide the same method name. A class's own method always takes priority.

To call a specific mixin's version explicitly:

```bash
$obj.Terminal::fg red         # always calls Terminal's fg
$obj.Taggable::identify       # provenance dispatch
```

Classes that use a mixin report `mixes` as true for that mixin (and for all ancestor
classes that composed it):

```bash
$obj.mixes Terminal && echo "has terminal support"
```

---

### Mixin: Terminal

Methods for ANSI terminal output, input, and a named symbol table.

Mix in with: `mixin:Terminal`

Global arrays available to all code after Terminal loads (direct access, no method call needed):

- `__Terminal_chars[name]` — named Unicode characters (see table below)
- `__Terminal_fg[name]` — ANSI foreground color codes
- `__Terminal_bg[name]` — ANSI background color codes

#### Screen control

| Method | Description |
|--------|-------------|
| `$obj.clear` | Erase screen and move cursor to home |
| `$obj.home` | Move cursor to top-left (0,0) without clearing |
| `$obj.move row col` | Move cursor to row, col (1-based) |
| `$obj.hideCursor` | Hide the terminal cursor |
| `$obj.showCursor` | Show the terminal cursor |

#### Text style — write escape sequence to stdout

| Method | Description |
|--------|-------------|
| `$obj.bold` | Enable bold |
| `$obj.dim` | Enable dim |
| `$obj.italic` | Enable italic |
| `$obj.underline` | Enable underline |
| `$obj.reverse` | Enable reverse video (swap fg/bg) |
| `$obj.reset` | Reset all attributes |
| `$obj.fg colorname` | Set foreground color by name (crashes on unknown) |
| `$obj.bg colorname` | Set background color by name (crashes on unknown) |

**Color names** (fg and bg): `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`,
`bright_black`, `bright_red`, `bright_green`, `bright_yellow`, `bright_blue`, `bright_magenta`,
`bright_cyan`, `bright_white`.

#### Terminal size

| Method | Returns | Description |
|--------|---------|-------------|
| `$obj.width` | `into=` | Terminal width in columns (falls back to 80) |
| `$obj.height` | `into=` | Terminal height in rows (falls back to 24) |

#### Raw input

| Method | Description |
|--------|-------------|
| `$obj.raw` | Enter raw mode (no echo, no line buffering). Trap EXIT to call `restore`. |
| `$obj.restore` | Restore normal terminal mode |
| `$obj.readKey` | Read one keypress (via `into=`). Requires raw mode for no-Enter behavior. |

#### Named character lookup

```bash
into=c $obj.char topLeft    # c='┌'
```

| Method | Returns | Description |
|--------|---------|-------------|
| `$obj.char name` | `into=` | Character from the symbol table (crashes on unknown name) |

**Single-line box drawing:** `topLeft` `topRight` `bottomLeft` `bottomRight` `horiz` `vert`
`cross` `teeDown` `teeUp` `teeRight` `teeLeft`

**Double-line box drawing:** `dTopLeft` `dTopRight` `dBottomLeft` `dBottomRight` `dHoriz`
`dVert` `dCross` `dTeeDown` `dTeeUp` `dTeeRight` `dTeeLeft`

**Card suits:** `spade` `heart` `diamond` `club`

**Block/shade:** `block` `darkShade` `medShade` `shade`

**Arrows:** `arrowLeft` `arrowRight` `arrowUp` `arrowDown`

**Misc:** `bullet` `ellipsis` `check` `ballotX` `star` `circle` `square`

---

### Mixin: Greetable

Demo/test mixin. Used primarily to exercise the mixin system.

Mix in with: `mixin:Greetable`

| Method | Returns | Description |
|--------|---------|-------------|
| `$obj.greet` | `into=` | Returns `"Hello from <ClassName>"` |
| `$obj.identify` | `into=` | Returns `"Greetable::identify"` (used to test conflict resolution) |

---

### Mixin: Taggable

Tag/untag/query methods backed by the host object's descriptor.
The host class does **not** need to declare `_tags` with `has:`.

Mix in with: `mixin:Taggable`

| Method | Returns | Description |
|--------|---------|-------------|
| `$obj.addTag tag [tag...]` | — | Add one or more tags; duplicates are silently ignored |
| `$obj.hasTag tag` | exit code | 0 if the object has the tag |
| `$obj.removeTag tag` | — | Remove a tag; no-op if absent |
| `$obj.getTags` | `into=` | Comma-separated tag list, or empty string |
| `$obj.tagCount` | `into=` | Number of tags as an integer |
| `$obj.identify` | `into=` | Returns `"Taggable::identify"` (conflict resolution test) |

```bash
$obj.addTag "archived" "reviewed"
$obj.hasTag "archived" && echo "yes"
into=n $obj.tagCount        # n="2"
into=s $obj.getTags         # s="archived,reviewed"
$obj.removeTag "reviewed"
```

---

## Loading Classes

Classes are loaded automatically when referenced if a `.boopIndex` entry exists.
You can also load explicitly:

```bash
. boop ClassName             # load one class by its index name
. boop Class::SubClass       # load via path (converts :: to /)
. boop Foo Bar Baz           # load multiple at once
```

Available index names: `TestSuite`, `Math`, `SemVer`, `Args`, `Config`,
`Container`, `List`, `Map`, `Stack`, `Queue`, `Set`, `JSON`,
`Box`, `Cube`, `Card`, `PlayingCard`, `Deck`,
`Terminal`, `Greetable`, `Taggable`.

---

## Inheritance Hierarchy Summary

```
boop
├── Geometry.Box
│   └── Geometry.Cube
├── Collection.Container
│   ├── Collection.List
│   │   └── Games.Deck
│   └── Collection.Map
├── Collection.Map.Fast
├── Collection.Stack
├── Collection.Queue
├── Collection.Set
├── Data.JSON
├── Config
├── Args
├── Math
├── SemVer
├── Games.Card
│   └── Games.PlayingCard
├── Testing.TestSuite
└── Iterator
```

Mixins (composable into any class):

```
Terminal   — ANSI output, raw input, named symbols
Greetable  — demo/test greeting methods
Taggable   — tag/untag/query backed by descriptor
```
