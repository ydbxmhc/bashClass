# boop API Reference

Complete index and conventions guide. Each class has a dedicated doc —
this page covers the common patterns, the base `boop` object, and where to find everything.

---

## Conventions

### Returning values — `into=` and `boop.pass`

Methods that produce a value use `boop.pass` internally. The caller captures
the result with the `into=` prefix variable:

```bash
into=result $obj.method arg   # result holds the returned string
into=n      $list.length      # n="5"
into=s      $obj.toString     # s="MyClass(id123){...}"
```

If `into=` is omitted the value is written to stdout. Useful in pipelines,
wasteful in hot paths (it forks a subshell):

```bash
echo "length: $( $list.length )"    # works but slower
```

### Exit codes — predicate methods

Methods used as booleans return an exit code and produce no value output:

```bash
$list.isEmpty && echo "nothing here"
$obj.isa Collection.List || echo "not a list"
$set.has "foo" && echo "member"
$obj.mixes Terminal && echo "has terminal"
```

Exit 0 = true, exit 1 = false — the standard bash convention.

### Property initialization — `has:` and `key=value`

A class declares its properties with `has:` in `boopClass`. Properties are
passed as `key=value` arguments to the constructor and stored as strings:

```bash
boopClass Box has:length,width,height public:new,...

into=b Box length=10 width=5 height=3
into=l $b.get length    # l="10"
$b.set length 20
into=l $b.get length    # l="20"
```

All values are strings. There is no numeric type — use Math for arithmetic.

### Delimiter for multi-value returns

Methods that return multiple values (like `toArray`, `keys`) join them with
`_Delimiter` (default: newline `$'\n'`). Set it in the caller's scope:

```bash
_Delimiter="," into=csv $list.toArray      # "a,b,c"
_Delimiter=" " into=spc $map.keys          # "host port debug"
```

### Crash behavior

Invalid input crashes with a descriptive message via `_Crash`. There is no
exception handling — guard your inputs or let the crash surface the bug.

```bash
$obj.fg notacolor   # crashes: "Terminal.fg: unknown color 'notacolor'"
$stack.pop          # crashes if empty: "pop on empty Stack"
```

---

## Loading Classes

Classes are loaded on demand from the filesystem. The framework searches
`BOOPPATH` (colon-separated directory list, default: the parent dir of `boop`).

```bash
. boop                           # framework only
. boop Math                      # framework + Math
. boop Math Config Args          # multiple at once
. boop Collection::Map           # :: maps to / on disk
. boop require:1.2+              # assert boop version >= 1.2.0
```

Classes declare their own dependencies. Loading `Cube` automatically loads
`Box`. Loading `Deck` loads `List` and `Container`.

### Index names (shorthand)

The `.boopIndex` file maps short names to directory paths:

| Name | Class |
|------|-------|
| `Math` | `Math/Math` |
| `Config` | `Config/Config` |
| `Args` | `Args/Args` |
| `SemVer` | `SemVer/SemVer` |
| `TestSuite` | `Testing/TestSuite/TestSuite` |
| `Box` | `Geometry/Box/Box` |
| `Cube` | `Geometry/Cube/Cube` |
| `Container` | `Collection/Container/Container` |
| `List` | `Collection/List/List` |
| `Map` | `Collection/Map/Map` |
| `Stack` | `Collection/Stack/Stack` |
| `Queue` | `Collection/Queue/Queue` |
| `Set` | `Collection/Set/Set` |
| `JSON` | `Data/JSON/JSON` |
| `Card` | `Games/Card/Card` |
| `PlayingCard` | `Games/PlayingCard/PlayingCard` |
| `Deck` | `Games/Deck/Deck` |
| `Terminal` | `Mixins/Terminal/Terminal` |
| `Greetable` | `Mixins/Greetable/Greetable` |
| `Taggable` | `Mixins/Taggable/Taggable` |

---

## boop root — Universal Base Object

Every object inherits from `boop`. These methods are available on all objects.

### Properties — `get` / `set`

```bash
$obj.get key          # read a property; returns "" if not declared/set
$obj.set key value    # write a property
```

Only properties declared with `has:` in `boopClass` are semantically owned
by the class. You can `set` any key, but undeclared ones are not listed in
`toString`, `inspect`, etc.

### Type checking — `isa` / `mixes`

```bash
$obj.isa ClassName    # 0 if obj is an instance of (or inherits from) ClassName
$obj.mixes MixinName  # 0 if obj's class composes MixinName (anywhere in chain)
```

`isa` walks the full inheritance chain. `$obj.isa boop` is always true.
`mixes` walks the inheritance chain checking `mixins=` on each level.

```bash
into=deck Games.Deck
$deck.isa Games.Deck        # 0 — true
$deck.isa Collection.List   # 0 — true (inherited)
$deck.isa boop              # 0 — always true
$deck.isa Collection.Map    # 1 — false

into=r Renderer mixin:Terminal
$r.mixes Terminal            # 0 — true
$r.mixes Taggable            # 1 — false
```

### Introspection

```bash
into=cls $obj.trueClass     # concrete class name: "Collection.List"
into=s   $obj.toString      # human-readable; each class overrides this
into=s   $obj.inspect       # raw pipe-delimited descriptor
```

### Lifecycle

```bash
$obj.destroy                # tear down: class hook → static keys → wrappers → registry
```

After `destroy`, the object ID is dead. Class-level cleanup hooks are
private functions named `ClassName._destroy()` — see docs/boop.md for
the full protocol.

---

## Quick Reference by Class

### Geometry

| Class | Doc | One-liner |
|-------|-----|-----------|
| `Geometry.Box` | [Box.md](Box.md) | Rectangular box; area, volume, face areas |
| `Geometry.Cube` | [Cube.md](Cube.md) | Cube (equal sides); inherits Box |

```bash
into=b Box length=10 width=5 height=3
into=v $b.volume    # v="150"
into=a $b.top       # a="50"  (length × width)

into=c Cube size=4
into=v $c.volume    # v="64"
```

---

### Collection

| Class | Doc | One-liner |
|-------|-----|-----------|
| `Collection.Container` | [Container.md](Container.md) | Abstract base; defines the contract |
| `Iterator` | [Iterator.md](Iterator.md) | Stateful cursor over any Container |
| `Collection.List` | [List.md](List.md) | Ordered indexed array |
| `Collection.Map` | [Map.md](Map.md) | Insertion-ordered key-value store |
| `Collection.Map.Fast` | [Map.Fast.md](Map.Fast.md) | Flat compound-key store, O(1) point lookups |
| `Collection.Stack` | [Stack.md](Stack.md) | LIFO stack (composition) |
| `Collection.Stack.Fast` | [Stack.md](Stack.md) | LIFO stack (List inheritance — lighter) |
| `Collection.Queue` | [Queue.md](Queue.md) | FIFO queue (composition) |
| `Collection.Queue.Fast` | [Queue.md](Queue.md) | FIFO queue (List inheritance — lighter) |
| `Collection.Set` | [Set.md](Set.md) | Unordered unique-value collection |

```bash
# List
into=list Collection.List
$list.push "a" "b" "c"
into=v $list.getAt -1      # v="c" (negative index)
into=v $list.pop           # v="c", list now has "a","b"

# Functional: filter, map, reduce, do (pipeline)
into=nums List; $nums.push 1 2 3 4 5 6
is_even() { (( $1 % 2 == 0 )); }
double() { _Result=$(( $1 * 2 )); }
add() { _Result=$(( $1 + $2 )); }
into=result $nums.do filter:is_even map:double reduce:add  # result="24"

# Map
into=map Collection.Map
$map.setAt "host" "localhost"
$map.setAt "port" "5432"
_Delimiter="," into=keys $map.keys    # keys="host,port" (insertion order)

# Stack / Queue
into=s Collection.Stack; $s.push "x"; into=v $s.pop    # v="x"
into=q Collection.Queue; $q.enqueue "j1"; into=v $q.dequeue  # v="j1"

# Set
into=set Collection.Set; $set.add "a" "b" "a"   # "a" deduplicated
into=n $set.size            # n="2"
$set.has "b" && echo "yes"
```

---

### Data

| Class | Doc | One-liner |
|-------|-----|-----------|
| `Data.JSON` | [JSON.md](JSON.md) | Parse and stringify JSON; returns Map/List trees |

```bash
into=j Data.JSON
into=doc $j.parse '{"host":"localhost","port":5432}'
into=h $doc.getAt "host"     # h="localhost"
into=s $j.stringify "$doc"   # s='{"host":"localhost","port":5432}'
```

---

### Config

| Class | Doc | One-liner |
|-------|-----|-----------|
| `Config` | [Config.md](Config.md) | Flat key=value and INI config files |

```bash
into=cfg Config.new
$cfg.load settings.ini
into=host $cfg.get "database.host"
$cfg.set "database.port" "5433"
$cfg.save
```

---

### Args

| Class | Doc | One-liner |
|-------|-----|-----------|
| `Args` | [Args.md](Args.md) | POSIX short options and GNU long-option + subcommand parser |

```bash
Args.parse '
[Options]
  verbose | v
  output  | o = ./out.txt
[Subcommands]
  build
  deploy
' "$@"

printf "verbose=%s output=%s action=%s\n" "$verbose" "$output" "$_Action"
```

---

### Math

| Class | Doc | One-liner |
|-------|-----|-----------|
| `Math` | [Math.md](Math.md) | Arbitrary-precision decimal arithmetic; static and instance API |

```bash
# Static — returns a string
into=r Math.add "1.5" "2.3"          # r="3.8"
into=r Math.divide "10" "3"          # r="3.333333333..."
into=r Math.DO "( 2 + 3 ) * 4"      # r="20"
into=r Math.pi 30                    # r= pi to 30 decimal places

# Instance — returns a Math object
into=a Math.new "10"
into=b Math.new "3"
into=c $a.add "$b"
into=v $c.val                        # v="13"
$a.gt "$b" && echo "a > b"
```

---

### SemVer

| Class | Doc | One-liner |
|-------|-----|-----------|
| `SemVer` | [SemVer.md](SemVer.md) | Semantic version comparison and constraint checking |

```bash
SemVer.satisfies "1.3.0" "1.2+" && echo "ok"    # >= 1.2.0 — passes
into=r SemVer.compare "2.0.0" "1.9.9"           # r="1"  (A > B)
```

---

### Games

| Class | Doc | One-liner |
|-------|-----|-----------|
| `Games.Card` | [Card.md](Card.md) | Generic card base |
| `Games.PlayingCard` | [Card.md](Card.md) | Standard suit+rank card |
| `Games.Deck` | [Card.md](Card.md) | Shuffleable, drawable List of cards |

```bash
into=deck Games.PlayingCard.newDeck   # 52-card shuffled deck
into=c1   $deck.draw
into=c2   $deck.draw
into=s1   $c1.toString    # e.g. "A♠"
into=s2   $c2.toString    # e.g. "7♥"
printf "%d cards remain\n" "$($deck.length)"
```

---

### Testing

| Class | Doc | One-liner |
|-------|-----|-----------|
| `Testing.TestSuite` | [TestSuite.md](TestSuite.md) | Section-grouped test runner with assertions |

```bash
into=t TestSuite name="My Tests"

$t.section "basics"
into=obj MyClass name="x"
$t.assert_ok   "creates ok"         test -n "$obj"
$t.assert_eq   "name round-trips"   "$($obj.get name)" "x"
$t.assert_fail "bad input crashes"  MyClass name=""

$t.summary
```

---

### Mixins

| Mixin | Doc | One-liner |
|-------|-----|-----------|
| `Terminal` | [Terminal.md](Terminal.md) | ANSI output, raw input, named Unicode symbols |
| `Taggable` | [Taggable.md](Taggable.md) | Tag/untag/query labels on any object |
| `Greetable` | [Greetable.md](Greetable.md) | Demo mixin (greet, identify) |

```bash
# Terminal
boopClass MyApp mixin:Terminal public:new

$app.fg red; printf "Error!\n"; $app.reset
$app.move 1 1; $app.clear
into=c $app.char spade   # c="♠"

# Taggable
boopClass Article mixin:Taggable has:title public:new
into=a Article title="Hello"
$a.addTag "published" "featured"
$a.hasTag "published" && echo "live"
into=n $a.tagCount           # n="2"
```

---

## Inheritance Hierarchy

```
boop
├── Geometry.Box
│   └── Geometry.Cube
├── Collection.Container
│   ├── Collection.List
│   │   └── Games.Deck
│   └── Collection.Map
├── Collection.Map.Fast
├── Collection.Stack          (holds a List internally)
├── Collection.Queue          (holds a List internally)
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

Mixins (composable into any class, do not appear in `isa` chain):

```
Terminal   — screen control, colors, styles, symbols, raw input
Taggable   — tag/untag/query string labels on any object
Greetable  — demo/test mixin
```

See [mixin.md](mixin.md) for how to write and compose mixins.
