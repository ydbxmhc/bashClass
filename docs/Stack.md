# Collection.Stack

LIFO (last-in, first-out) stack. Backed internally by a List; exposes only
the stack surface. Push to the top, pop from the top.

## Dependencies

```bash
. boop Stack    # also loads List and Container
```

---

## Constructor

```bash
into=s Collection.Stack
```

No arguments. The internal List is created automatically.

---

## Basic Usage

```bash
into=s Collection.Stack

$s.push "first"
$s.push "second"
$s.push "third"

into=top  $s.peek          # top="third" — does not remove
into=top  $s.pop           # top="third" — removes it
into=top  $s.pop           # top="second"
into=n    $s.size          # n="1"
$s.isEmpty && echo "empty" # silent — still has "first"
```

---

## Methods

### `$s.push val [val...]`

Add one or more values to the top of the stack.

```bash
$s.push "alpha"
$s.push "beta" "gamma"   # two pushes in one call
```

Multiple values are pushed left-to-right, so `"gamma"` ends up on top.

### `$s.pop`

Remove and return the top value. Crashes if the stack is empty.

```bash
into=v $s.pop
```

### `$s.peek`

Return the top value without removing it. Crashes if the stack is empty.

```bash
into=v $s.peek
```

### `$s.size`

Number of elements.

```bash
into=n $s.size
```

### `$s.isEmpty`

Exit code: 0 if empty, 1 if not.

```bash
$s.isEmpty && echo "nothing left"
while ! $s.isEmpty; do
  into=v $s.pop
  printf "popped: %s\n" "$v"
done
```

---

## Common Patterns

### Undo stack

```bash
into=undo Collection.Stack

# User does action:
do_action "create foo"
$undo.push "delete foo"

# User hits undo:
if ! $undo.isEmpty; then
  into=cmd $undo.pop
  eval "$cmd"
fi
```

### Depth-first traversal

```bash
into=work Collection.Stack
$work.push "$root_node"

while ! $work.isEmpty; do
  into=node $work.pop
  process "$node"
  for child in $(children "$node"); do
    $work.push "$child"
  done
done
```

### Reversing a list

```bash
into=src Collection.List
$src.push "a" "b" "c"

into=stk Collection.Stack
$stk.push "a" "b" "c"

while ! $stk.isEmpty; do
  into=v $stk.pop
  printf "%s\n" "$v"   # c, b, a
done
```

---

## Design Notes

**Composition over inheritance.** Stack holds a List internally rather than
extending it. This hides `push`/`shift`/`getAt`/`each` and all the other
List methods — a Stack only exposes what a Stack should expose. The internal
List is not accessible from outside the object.

**No iteration.** If you need to iterate a stack without destroying it, use
a List directly. Stack is deliberately opaque.

**Crash on underflow.** Both `pop` and `peek` call `_Crash` on an empty
stack. Check `isEmpty` before calling if underflow is possible.
