# List

Indexed array container. Wraps a bash indexed array with object semantics.
Supports push/pop, shift/unshift, random access, negative indices, and slicing.

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
into=val $l.get 0          # first element
into=val $l.get -1         # last element (Python-style negative index)
$l.set 0 "new_first"       # replace first element
$l.set -1 "new_last"       # replace last element
$l.has 0 && echo "exists"  # bounds check (exit code)
```

Out-of-range `get` returns empty string. Out-of-range `set` and `delete` crash.

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

### Utility

```bash
into=n $l.length            # element count
$l.clear                    # remove all elements
$l.delete 2                 # remove element at index, re-index
$l.isEmpty && echo "empty"  # boolean check
$l.destroy                  # clean up companion array + registry
```

### Serialization

```bash
into=s $l.toString          # List(_id)[ "alpha", "beta", "gamma" ]
into=s $l.toArray           # newline-delimited values
```

## Composition

List elements can be any string, including object IDs:

```bash
into=inner List
$inner.push "a" "b"

into=outer List
$outer.push "$inner"        # nested list

into=val $outer.itemAt 0 1  # "b" — traverses into inner list
```

## Example

```bash
. boop List

into=l List
$l.push "hello" "world" "foo"
into=v $l.get 0
echo "$v"                   # hello

into=v $l.pop
echo "$v"                   # foo

into=n $l.length
echo "$n"                   # 2
```

