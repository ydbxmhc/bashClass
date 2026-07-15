# Iterator

A stateful cursor over a Container (List, Map, or any subclass).
Holds a reference to a container and a current position.
Does not own data — it reads from its target.

**Iterator is defined in `Collection/Container/Container`, not in its own file.**
It lives there because it was designed alongside Container and has no meaning
without one. Loading Container (directly or via List/Map/Deck) makes Iterator available.

## Dependencies

```bash
. boop Container    # also loads Iterator; no separate file needed
```

---

## Two Ways to Get an Iterator

### 1. Implicit (internal) iterator

Every Container has a built-in iterator created lazily on first use.
Access it via the delegation methods on the container itself:

```bash
into=list Collection.List
$list.push "alpha" "beta" "gamma"

while $list.hasNext; do
  into=val $list.next
  printf "%s\n" "$val"
done
```

The internal iterator is shared — calling `next` from two different parts
of the code advances the same cursor. Call `$list.iterReset` to start over.

### 2. Explicit (independent) iterator

Create a fresh Iterator with its own position:

```bash
into=iter $list.iterator
while $iter.hasNext; do
  into=val $iter.next
  printf "%s\n" "$val"
done
```

Explicit iterators are independent. You can have multiple iterators on the
same container simultaneously.

Create one directly with `Iterator` (requires setting `target` and `target_class`):

```bash
into=iter Iterator target="$list" target_class="Collection.List"
```

---

## Methods

### `$iter.hasNext`

Exit code 0 if there is a next element (current position is before the last).

```bash
while $iter.hasNext; do
  into=v $iter.next
  # ...
done
```

### `$iter.next`

Advance to the next position and return the value there.
Crashes if there is no next element (call `hasNext` first).

```bash
into=v $iter.next
```

### `$iter.hasPrev`

Exit code 0 if there is a previous element (current position is past the first).

```bash
while $iter.hasPrev; do
  into=v $iter.prev
  # ...
done
```

### `$iter.prev`

Move to the previous position and return the value there.
Crashes if there is no previous element.

```bash
into=v $iter.prev
```

### `$iter.current`

Return the value at the current position without moving the cursor.

```bash
into=v $iter.current
```

The cursor has no current value before the first `next` (or after `reset`).
Call `next` at least once before `current`.

### `$iter.index`

Return the key or index at the current position.

```bash
# On a List:
into=i $iter.index    # i="0", "1", "2", ...

# On a Map:
into=k $iter.index    # k="host", "port", ...
```

### `$iter.reset`

Reset the cursor to before the first element, as if newly created.

```bash
$iter.reset
while $iter.hasNext; do
  into=v $iter.next
  # ...
done
```

---

## Patterns

### Index-value pairs

```bash
into=iter $list.iterator
while $iter.hasNext; do
  into=v $iter.next
  into=i $iter.index
  printf "[%s] %s\n" "$i" "$v"
done
```

### Bidirectional scan

```bash
# Forward
while $iter.hasNext; do into=v $iter.next; done
# Now at the end — scan backward
while $iter.hasPrev; do
  into=v $iter.prev
  printf "reverse: %s\n" "$v"
done
```

### Parallel iteration over two lists

```bash
into=ai $list_a.iterator
into=bi $list_b.iterator

while $ai.hasNext && $bi.hasNext; do
  into=a $ai.next
  into=b $bi.next
  printf "%s vs %s\n" "$a" "$b"
done
```

### Find-first (early exit)

```bash
into=iter $list.iterator
found=""
while $iter.hasNext; do
  into=v $iter.next
  if [[ "$v" == "target" ]]; then
    found="$v"
    break
  fi
done
[[ -n "$found" ]] && echo "found it"
```

---

## Container Delegation Methods

All Container subclasses (List, Map, Deck, ...) expose these delegation
methods that forward to the internal implicit iterator:

| Container method | Forwards to |
|-----------------|-------------|
| `$c.next` | internal iterator `next` |
| `$c.prev` | internal iterator `prev` |
| `$c.hasNext` | internal iterator `hasNext` |
| `$c.hasPrev` | internal iterator `hasPrev` |
| `$c.current` | internal iterator `current` |
| `$c.iterIndex` | internal iterator `index` |
| `$c.iterReset` | internal iterator `reset` |
| `$c.iterator` | create a new explicit Iterator |

---

## Design Notes

**Iterator is not a Container.** It doesn't hold data and doesn't implement
the Container contract. It exists because of Container and is useless without one.

**Lazy creation.** The internal iterator is not created until the first call
to a delegation method. Zero cost if never used.

**Separate cursor per explicit iterator.** Each `$container.iterator` call
returns a new object with its own position. Explicit iterators do not interfere
with each other or with the implicit one.

**target and target_class.** The `target` property holds the container's object
ID; `target_class` holds its class name. Both are needed for dispatch.

---

[↑ Site map](index)
