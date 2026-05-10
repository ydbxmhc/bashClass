# Collection.Map.Fast

Flat compound-key store for O(1) point lookups into nested data.
Keys are dot-delimited paths into a single bash associative array.
No insertion order, no per-level objects, no subtree pass-by-reference —
just fast get/set on fully-qualified paths.

## Dependencies

```bash
. boop Collection::Map::Fast
```

---

## Fast vs Map

Use **Fast** when you need:
- Quick point lookups into config or parsed data
- A flat store keyed by paths (`"users.0.name"`, `"server.port"`)
- Minimal overhead per node

Use **Map** when you need:
- Insertion-ordered iteration
- Subtrees as objects you can pass around
- Per-level `getAt`/`setAt` with real object dispatch

---

## Constructor

```bash
into=doc Collection.Map.Fast          # default separator "."
into=doc Collection.Map.Fast sep="/"  # custom separator
```

The separator is stored in the `sep` property and used by `keysUnder`
and `deleteUnder` to identify path boundaries.

---

## Getting and Setting

```bash
$doc.set "server.host"     "localhost"
$doc.set "server.port"     "8080"
$doc.set "database.host"   "db.internal"
$doc.set "database.name"   "myapp"

into=h $doc.get "server.host"    # h="localhost"
into=p $doc.get "server.port"    # p="8080"
into=x $doc.get "missing.key"    # x=""  — no crash, empty string
```

### `$doc.set key value`

Store any string value at any string key. Keys are arbitrary strings;
the separator character has no special meaning in `get`/`set` —
it is just part of the key. Hierarchy is a naming convention,
not a structural constraint.

```bash
$doc.set "some.deep.path" "value"
$doc.set "no/separator/needed" "also works if sep='|'"
```

### `$doc.get key`

Retrieve the value at `key`. Returns empty string for unknown keys.

### `$doc.has key`

Exit code: 0 if the key exists, 1 if not.

```bash
$doc.has "server.port" || { echo "port not configured"; exit 1; }
```

### `$doc.delete key`

Remove a single key. No-op if absent.

```bash
$doc.delete "database.password"
```

---

## Counting and Clearing

```bash
into=n $doc.length    # total keys stored
$doc.clear            # remove all keys
```

---

## Enumeration

### All keys

```bash
_Delimiter=$'\n' into=all $doc.keys
while IFS= read -r k; do
  into=v $doc.get "$k"
  printf "%s = %s\n" "$k" "$v"
done <<< "$all"
```

Keys are returned in hash-defined order (not insertion order).

### Keys under a prefix

```bash
_Delimiter=$'\n' into=skeys $doc.keysUnder "server"
# skeys = "server.host\nserver.port"
```

`keysUnder prefix` returns all keys that start with `prefix` followed
by the separator. The prefix itself is not returned.

```bash
# With sep="/"
$doc.set "a/b/c" "1"
$doc.set "a/b/d" "2"
$doc.set "a/x"   "3"

_Delimiter=$'\n' into=ab $doc.keysUnder "a/b"
# ab = "a/b/c\na/b/d"
```

### Delete a subtree

```bash
$doc.deleteUnder "database"    # removes all keys starting with "database."
```

---

## Serialization

```bash
into=s $doc.toString   # "key=value\n..." one per line, order undefined
```

---

## Loading from JSON

`Data.JSON` produces `Collection.Map` trees (nested objects, insertion-ordered).
If you parse JSON and want Fast's O(1) access, flatten it:

```bash
. boop JSON Collection::Map::Fast

into=j Data.JSON
into=parsed $j.parse "$json_str"   # gives Collection.Map tree

into=fast Collection.Map.Fast

# Flatten manually for the keys you care about
into=host $parsed.getAt "server"   # get the "server" sub-map
into=host $host.getAt "host"
$fast.set "server.host" "$host"
```

---

## Full Example

```bash
. boop Collection::Map::Fast

into=cfg Collection.Map.Fast

# Populate
$cfg.set "app.name"     "myapp"
$cfg.set "app.version"  "2.1.0"
$cfg.set "db.host"      "localhost"
$cfg.set "db.port"      "5432"
$cfg.set "db.name"      "myapp_prod"

# Query
into=v $cfg.get "app.version"       # v="2.1.0"
$cfg.has "db.password" || echo "no db password set"

# Enumerate a subtree
_Delimiter=$'\n' into=dbkeys $cfg.keysUnder "db"
printf "DB keys:\n%s\n" "$dbkeys"

# Remove a subtree
$cfg.deleteUnder "app"
into=n $cfg.length   # n="3" (only db.* remain)
```

---

## Design Notes

**All keys are flat.** There are no nested objects inside a Fast instance.
`"a.b.c"` is just a string key. `keysUnder "a.b"` is a prefix search, not
a structural traversal.

**O(1) for everything except enumeration.** `get`, `set`, `has`, `delete`
are all single associative-array operations. `keys` and `keysUnder` scan
all keys linearly — fine for small stores, slow for very large ones.

**No insertion order.** If you need keys in a predictable order, use a
`Collection.Map` or build your own ordered list alongside the store.
