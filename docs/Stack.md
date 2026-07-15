# Collection.Stack

LIFO (last-in, first-out) stack. Backed internally by a [List](List); exposes
only the stack surface. Push to the top, pop from the top.

## Contents

- [Dependencies](#dependencies)
- [Constructor](#constructor)
- [Basic Usage](#basic-usage)
- [Methods](#methods)
  - [$s.push val [val...]](#s-push-val-val)
  - [$s.pop](#s-pop)
  - [$s.peek](#s-peek)
  - [$s.size](#s-size)
  - [$s.isEmpty](#s-isempty)
- [Common Patterns](#common-patterns)
  - [Undo stack](#undo-stack)
  - [Depth-first traversal](#depth-first-traversal)
  - [Reversing a list](#reversing-a-list)
- [Design Notes](#design-notes)
- [Collection.Stack.Fast](#collectionstackfast)
  - [When to Use Fast](#when-to-use-fast)
  - [When to Use the Composition Version](#when-to-use-the-composition-version)
  - [Usage](#usage)
  - [Blocked Methods](#blocked-methods)

---

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

Remove and return the top value. Returns non-zero with an error if the stack is empty.

```bash
into=v $s.pop
```

### `$s.peek`

Return the top value without removing it. Returns non-zero with an error if the stack is empty.

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

**Error on underflow.** Both `pop` and `peek` call `_Error` on an empty
stack and return non-zero. Check `isEmpty` before calling if underflow is possible.

---

## Collection.Stack.Fast

Inheritance-based alternative. Extends List directly instead of wrapping
one via composition. Faster (one object, no delegation), but the full
List API is accessible if a caller ignores the stack contract.

### When to Use Fast

- Performance matters (tight loops, many stack objects)
- You trust callers to respect the stack interface
- You want `each`, `toArray`, `toString`, `clear` available on the stack
- Destroy is simpler (no cascading — it's just one object)

### When to Use the Composition Version

- You need strict encapsulation (internal List is unreachable)
- You want to guarantee no one calls `shift` or `getAt` by accident
- API surface discipline matters more than speed

### Usage

```bash
. boop Collection::Stack::Fast

into=s Collection.Stack.Fast
$s.push "a" "b" "c"
into=v $s.peek              # "c"
into=v $s.pop               # "c"
into=n $s.size              # 2

# Inherited from List — available on Fast, hidden on composition Stack:
$s.each my_callback
into=all $s.toArray

# Blocked — errors with a clear message:
$s.shift                    # ERROR: not a valid stack operation
$s.unshift "x"             # ERROR: not a valid stack operation
```

### Blocked Methods

| Method | Why |
|--------|-----|
| `shift` | Removes from the bottom — violates LIFO |
| `unshift` | Inserts at the bottom — violates LIFO |
| `getAt` | Random access — violates LIFO |
| `setAt` | Random access — violates LIFO |
| `delete` | Random access — violates LIFO |
| `slice` | Random access — violates LIFO |

All return exit code 1 and emit `_Error` with guidance on the correct
method to use.

---

[↑ Site map](index)
