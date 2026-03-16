# Map

Insertion-ordered associative array container. Wraps a bash associative
array with object semantics. Key-value storage with string keys that
preserves the order in which keys were first added.

## Dependencies

```bash
. boop Map    # automatically loads Container
```

## Constructor

```bash
into=m Map
```

Creates an empty map. Populate it with `set`.

## Insertion Order

Map maintains a companion indexed array (`__bashClass_keys_${self}`)
that tracks the order keys were first inserted. All traversal methods
— `keys`, `values`, `toArray`, `toString`, `each`, and iterators —
walk keys in insertion order.

- Overwriting an existing key updates the value but preserves its
  position in the order.
- Deleting a key removes it from the ordered list.
- Re-inserting a deleted key places it at the end.
- `clear` resets both the data and the key order.

```bash
into=m Map
$m.set "charlie" "3"
$m.set "alpha" "1"
$m.set "bravo" "2"

into=k $m.keys
printf "%s\n" "$k"
# charlie
# alpha
# bravo

$m.set "alpha" "99"            # overwrite — order unchanged
into=k $m.keys                 # still: charlie, alpha, bravo

$m.delete "alpha"
$m.set "alpha" "1"             # re-insert — goes to end
into=k $m.keys                 # charlie, bravo, alpha
```

## Methods

### Element Access

```bash
$m.set "host" "localhost"       # store key-value pair
into=val $m.get "host"          # retrieve by key
$m.has "host" && printf "exists\n"  # key existence check (exit code)
$m.delete "host"                # remove key-value pair
```

Missing key `get` returns empty string. `delete` on a missing key is
a silent no-op (idempotent).

### Enumeration (Insertion Order)

```bash
into=k $m.keys              # newline-delimited key list (insertion order)
into=v $m.values            # newline-delimited value list (same order)
into=e $m.toArray           # newline-delimited "key=value" lines
```

`keys` and `values` correspond positionally — the Nth value matches
the Nth key.

### Callback Iteration

```bash
my_callback() { printf "%s = %s\n" "$1" "$2"; }
$m.each my_callback         # calls callback with key, value for each entry
```

Iteration follows insertion order. If the callback returns non-zero,
iteration stops immediately.

### Iterator (Stateful Cursor)

```bash
# Lazy delegation — auto-created on first use
while $m.hasNext; do
  into=val $m.next
  into=key $m.iterIndex
  printf "%s: %s\n" "$key" "$val"
done
$m.iterReset

# Explicit — independent cursor
into=iter $m.iterator
while $iter.hasNext; do
  into=val $iter.next
  into=key $iter.index
  printf "%s: %s\n" "$key" "$val"
done
```

Map iterators snapshot the ordered key list at creation time. Mutations
to the Map after the iterator is created don't affect the snapshot.
See [Container.md](Container.md) for full iterator documentation.

### Utility

```bash
into=n $m.length            # number of key-value pairs
$m.clear                    # remove all entries (resets key order)
$m.isEmpty && printf "empty\n"  # boolean check
$m.destroy                  # clean up companion array + registry
```

### Serialization

```bash
into=s $m.toString          # Map(_id){ host="localhost", port="8080" }
```

Entries appear in insertion order in the toString output.

## Composition

Map values can be object IDs, enabling nested structures:

```bash
into=db Map
$db.set "host" "localhost"
$db.set "port" "5432"

into=config Map
$config.set "db" "$db"

into=val $config.itemAt "db" "host"   # "localhost"
$config.setAt "newhost" "db" "host"   # update nested value
```

## Example

```bash
. boop Map

into=m Map
$m.set "name" "myapp"
$m.set "version" "1.0"
$m.set "debug" "true"

into=v $m.get "name"
printf "%s\n" "$v"              # myapp

$m.has "version" && printf "versioned\n"   # versioned

# Keys come back in insertion order
into=k $m.keys
printf "%s\n" "$k"
# name
# version
# debug

# Iterate with callback
show_entry() { printf "  %s = %s\n" "$1" "$2"; }
$m.each show_entry
#   name = myapp
#   version = 1.0
#   debug = true
```
