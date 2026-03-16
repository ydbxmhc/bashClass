# Container

Virtual base class for all collection types. Defines the interface
contract that List, Map, and future containers (Stack, Queue, etc.)
must implement. Also defines the Iterator companion class for stateful
cursor traversal.

## Dependencies

```bash
. boop Container    # loaded automatically by List or Map
```

You typically don't use Container directly — use List or Map instead.

## Architecture

Container data lives in companion bash arrays, not in the pipe-delimited
descriptor. Each instance owns a global array named `__bashClass_data_${self}`.
Child constructors declare it as indexed (`-ga` for List) or associative
(`-gA` for Map).

This avoids encoding arrays inside the descriptor string, which would be
fragile and slow. Companion arrays give native bash performance for element
access while the object system handles identity, dispatch, and lifecycle.

## Virtual Methods

These crash with a descriptive error if a child class forgets to override:

| Method   | Contract                                    |
|----------|---------------------------------------------|
| get      | Retrieve element by key/index               |
| set      | Store element at key/index                  |
| delete   | Remove element by key/index                 |
| length   | Return element count                        |
| clear    | Remove all elements                         |
| has      | Check if key/index exists (exit code)       |
| toArray  | Serialize all elements to string            |
| each     | Iterate with callback: `callback key value` |

## Provided Methods

These work for all containers via delegation to the virtual methods:

```bash
$container.isEmpty && printf "empty\n"    # delegates to length
$container.destroy                         # cleans up companion array + registry
into=s $container.toString                 # class, ID, type, length
```

## Callback Iteration: `each`

Every container implements `each`, which calls a user function for
every element. No subshells, no forks — the callback runs in the
current shell and can read/write variables in the caller's scope.

```bash
my_callback() { printf "[%s] = %s\n" "$1" "$2"; }

$list.each my_callback     # calls: my_callback 0 "alpha"
                            #        my_callback 1 "beta"

$map.each my_callback      # calls: my_callback "host" "localhost"
                            #        my_callback "port" "8080"
```

If the callback returns non-zero, iteration stops immediately (early exit).

## Deep Traversal

Container provides methods for walking nested structures:

```bash
# itemAt — read through nested containers
into=val $matrix.itemAt 1 2            # matrix[1][2]
into=val $config.itemAt "db" "host"    # config["db"]["host"]

# setAt — write through nested containers
$matrix.setAt "99" 1 2                 # matrix[1][2] = "99"
```

When Container is loaded, it also augments bashClass with `itemFrom`
and `setOn`, which start from a named property on any object:

```bash
into=val $obj.itemFrom "tags" 0        # obj.tags → List → get 0
$obj.setOn "tags" "urgent" 0           # obj.tags → List → set 0 "urgent"
```

## Iterator: Stateful Cursor

Iterator is a companion class defined inside the Container source file.
It inherits from `bashClass` (not Container) — it doesn't hold data,
it holds a reference to a container and a cursor position.

### Lazy Delegation (Implicit Iterator)

Every Container instance has iterator methods that auto-create an
internal Iterator on first use:

```bash
into=l List
$l.push "a" "b" "c"

while $l.hasNext; do
  into=val $l.next
  into=idx $l.iterIndex
  printf "[%s] %s\n" "$idx" "$val"
done
# [0] a
# [1] b
# [2] c

$l.iterReset                    # back to before-first
into=val $l.next                # "a" again
```

The internal Iterator is created lazily — if you never call `$l.next`
or any other iterator delegation method, no Iterator object is created.

Delegation methods on Container:

| Method      | Delegates to       | Description                          |
|-------------|--------------------|--------------------------------------|
| `next`      | `Iterator.next`    | Advance cursor, return value         |
| `prev`      | `Iterator.prev`    | Move cursor back, return value       |
| `hasNext`   | `Iterator.hasNext` | True if more elements ahead          |
| `hasPrev`   | `Iterator.hasPrev` | True if elements behind              |
| `current`   | `Iterator.current` | Value at current position            |
| `iterIndex` | `Iterator.index`   | Key/index at current position        |
| `iterReset` | `Iterator.reset`   | Reset cursor to before-first         |

### Explicit Iterators (Independent Cursors)

For multiple independent cursors on the same container, create
Iterator objects explicitly:

```bash
into=l List
$l.push "x" "y" "z"

into=iter1 $l.iterator
into=iter2 $l.iterator

into=v1 $iter1.next             # "x" — advances iter1 only
into=v2 $iter2.next             # "x" — iter2 is independent
into=v3 $iter1.next             # "y"
into=v4 $iter2.next             # "y"
```

Methods on Iterator objects:

| Method    | Description                                    |
|-----------|------------------------------------------------|
| `next`    | Advance cursor and return value                |
| `prev`    | Move cursor backward and return value          |
| `hasNext` | True if more elements ahead (exit code)        |
| `hasPrev` | True if elements behind (exit code)            |
| `current` | Value at current position (no movement)        |
| `index`   | Key (Map) or integer index (List) at position  |
| `reset`   | Reset cursor to before-first (position -1)     |

Position semantics: -1 = before first element (initial state),
0..length-1 = on an element.

### Map Iterator Snapshots

For Map iterators, the ordered key list is snapshotted at creation
time into a companion array (`__bashClass_iterkeys_${iteratorID}`).
Mutations to the Map after the iterator is created don't affect the
snapshot. This is a deliberate trade-off — predictable traversal over
live-view consistency.

```bash
into=m Map
$m.set "a" "1"
$m.set "b" "2"

into=iter $m.iterator
$m.set "c" "3"                  # added after iterator creation

__count=0
while $iter.hasNext; do
  $iter.next; (( __count++ ))
done
printf "%d\n" "$__count"        # 2 (not 3 — snapshot has a, b only)
```

### Opting Out: `noIterators`

Subclasses that don't want iterator support call `$_Self.noIterators`
in their constructor. This replaces all iterator methods with stubs
that crash with a clear message:

```bash
MyStack.new() {
  local -I _Class; : "${_Class:=MyStack}"
  local __MyStack_new_self
  into=__MyStack_new_self __bashClass.new "$@"
  declare -ga "__bashClass_data_${__MyStack_new_self}"
  $__MyStack_new_self.noIterators
  __bashClass.return "$__MyStack_new_self" ${into:-}
}

# Later:
$stack.next    # CRASH: "MyStack does not support iterators"
```

## Inheritance Hierarchy

```
bashClass → Container → List  (indexed array)
                      → Map   (insertion-ordered associative array)
                      → Stack, Queue, etc. (future)

bashClass → Iterator  (companion to Container — stateful cursor)
```
