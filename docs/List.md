# List

Indexed array container. Wraps a bash indexed array with object semantics.
Supports push/pop, shift/unshift, random access, negative indices, and slicing.

## Contents

- [Dependencies](#dependencies)
- [Constructor](#constructor)
- [Methods](#methods)
  - [Element Access](#element-access)
  - [Stack Operations (LIFO)](#stack-operations-lifo)
  - [Queue Operations (FIFO)](#queue-operations-fifo)
  - [Slicing](#slicing)
  - [Callback Iteration](#callback-iteration)
  - [Search](#search)
  - [Iterator (Stateful Cursor)](#iterator-stateful-cursor)
  - [Utility](#utility)
  - [Serialization](#serialization)
  - [Functional Operations](#functional-operations)
    - [filter](#filter)
    - [map](#map)
    - [reduce](#reduce)
    - [do (pipeline)](#do-pipeline)
- [Composition](#composition)
- [Example](#example)

---

## Dependencies

```bash
. boop List    # automatically loads Container
```

## Constructor

```bash
into=l List
```

Creates an empty list. Populate it with `push`, `set`, or `unshift`.

## Methods

### Element Access

```bash
into=val $l.getAt 0          # first element
into=val $l.getAt -1         # last element (Python-style negative index)
$l.setAt 0 "new_first"       # replace first element
$l.setAt -1 "new_last"       # replace last element
$l.has 0 && printf "exists\n"  # bounds check (exit code)
```

Out-of-range `getAt` returns empty string. Out-of-range `setAt` and `delete` return
non-zero with an error message.

### Stack Operations (LIFO)

```bash
$l.push "alpha"             # append to end
$l.push "a" "b" "c"        # append multiple
into=val $l.pop             # remove and return last element
```

### Queue Operations (FIFO)

```bash
$l.unshift "first"          # prepend to beginning
into=val $l.shift           # remove and return first element
```

`shift` and `unshift` are O(n) — they rebuild the array. For heavy
queue work, consider the access pattern cost.

### Slicing

```bash
into=s $l.slice 1 3         # elements at index 1, 2 (end exclusive)
into=s $l.slice 2           # index 2 through end
into=s $l.slice -2          # last two elements
```

Returns a newline-delimited string.

### Callback Iteration

```bash
my_callback() { printf "[%s] %s\n" "$1" "$2"; }
$l.each my_callback         # calls: my_callback 0 "alpha"
                             #        my_callback 1 "beta"
```

If the callback returns non-zero, iteration stops immediately.

### Search

```bash
$l.contains "banana"             # exit 0 if found, 1 if not
into=pos $l.indexOf "banana"     # pos="1" (or exit 1 if not found)
```

Both are O(n) linear scans. `contains` is a thin wrapper over `indexOf`
that discards the position and returns only the exit code.

### Iterator (Stateful Cursor)

```bash
# Lazy delegation — auto-created on first use
while $l.hasNext; do
  into=val $l.next
  into=idx $l.iterIndex
  printf "[%s] %s\n" "$idx" "$val"
done
$l.iterReset                # back to start

# Explicit — independent cursor
into=iter $l.iterator
while $iter.hasNext; do
  into=val $iter.next
  printf "%s\n" "$val"
done
```

See [Container.md](Container.md) for full iterator documentation,
including multiple independent cursors and Map snapshot behavior.

### Utility

```bash
into=n $l.length            # element count
$l.clear                    # remove all elements
$l.delete 2                 # remove element at index, re-index
$l.isEmpty && printf "empty\n"  # boolean check
$l.destroy                  # clean up companion array + registry
```

### Serialization

```bash
into=s $l.toString          # List(_id)[ "alpha", "beta", "gamma" ]
into=s $l.toArray           # newline-delimited values
```

### Functional Operations

#### filter

Return a new List containing only elements for which the callback returns 0.

```bash
is_long() { (( ${#1} > 3 )); }

into=names List
$names.push "Al" "Bob" "Charlie" "Dave" "Elizabeth"

into=long $names.filter is_long
# long is a new List: ["Charlie", "Dave", "Elizabeth"]
# $names is unchanged
```

Callback signature: `callback value` → exit 0 to keep, non-zero to discard.

On an empty list, returns a new empty List (exit 0).

#### map

Return a new List with each element transformed by the callback.

```bash
upcase() { _Result="${1^^}"; }

into=words List
$words.push "hello" "world"

into=shouting $words.map upcase
# shouting is a new List: ["HELLO", "WORLD"]
```

Callback signature: `callback value` → sets `_Result` to the transformed value.

On an empty list, returns a new empty List (exit 0).

#### reduce

Collapse the list to a single scalar by applying a combining callback
across all elements. The first element is the starting value; the callback
begins combining from the second element onward.

```bash
add() { _Result=$(( $1 + $2 )); }

into=nums List
$nums.push 10 20 30 40

into=total $nums.reduce add    # total="100"
```

Callback signature: `callback running_total current_value` → sets `_Result`
to the new running total.

On an empty list: returns empty string, exit code 1.
On a single-element list: returns that element directly (callback not called).

#### do (pipeline)

Apply a sequence of operations in one call. Intermediates are created and
destroyed automatically — the caller only sees the final result.

```bash
is_even() { (( $1 % 2 == 0 )); }
double_it() { _Result=$(( $1 * 2 )); }
add() { _Result=$(( $1 + $2 )); }

into=nums List
$nums.push 5 10 15 20 25 30 35 40 45

into=result $nums.do filter:is_even map:double_it reduce:add
# result="200"
```

Operations are `op:callback` pairs. Recognized ops: `filter`, `map`, `reduce`.

Syntax is flexible — all of these are equivalent:

```bash
$list.do "filter:is_even,map:double_it,reduce:add"
$list.do "filter:is_even, map:double_it, reduce:add"
$list.do filter:is_even map:double_it reduce:add
$list.do "filter : is_even" "map : double_it" "reduce : add"
```

Commas, spaces around colons, and multiple arguments are all accepted.
The original list is never modified or destroyed.

## Composition

List elements can be any string, including object IDs:

```bash
into=inner List
$inner.push "a" "b"

into=outer List
$outer.push "$inner"           # nested list

into=val $outer.deepGet 0 1    # "b" — traverses into inner list
```

## Example

```bash
. boop List

into=l List
$l.push "hello" "world" "foo"
into=v $l.get 0
printf "%s\n" "$v"              # hello

into=v $l.pop
printf "%s\n" "$v"              # foo

into=n $l.length
printf "%s\n" "$n"              # 2

# Walk with each
show() { printf "  [%s] %s\n" "$1" "$2"; }
$l.each show
#   [0] hello
#   [1] world

# Walk with iterator
while $l.hasNext; do
  into=val $l.next
  printf "-> %s\n" "$val"
done
# -> hello
# -> world
```

---

[↑ Site map](index)
