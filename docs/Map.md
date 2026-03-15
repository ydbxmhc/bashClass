# Map

Associative array container. Wraps a bash associative array with object
semantics. Key-value storage with string keys.

## Dependencies

```bash
. boop Map    # automatically loads Container
```

## Constructor

```bash
into=m Map
```

Creates an empty map. Populate it with `set`.

## Methods

### Element Access

```bash
$m.set "host" "localhost"       # store key-value pair
into=val $m.get "host"          # retrieve by key
$m.has "host" && echo "exists"  # key existence check (exit code)
$m.delete "host"                # remove key-value pair
```

Missing key `get` returns empty string. `delete` on a missing key is
a silent no-op (idempotent).

### Enumeration

```bash
into=k $m.keys              # newline-delimited key list
into=v $m.values            # newline-delimited value list
into=e $m.toArray           # newline-delimited "key=value" lines
```

Key ordering is bash's internal hash order (effectively random, not
insertion order). `keys` and `values` correspond positionally.

### Utility

```bash
into=n $m.length            # number of key-value pairs
$m.clear                    # remove all entries
$m.isEmpty && echo "empty"  # boolean check
$m.destroy                  # clean up companion array + registry
```

### Serialization

```bash
into=s $m.toString          # Map(_id){ host="localhost", port="8080" }
```

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

into=v $m.get "name"
echo "$v"                   # myapp

$m.has "version" && echo "versioned"   # versioned

into=k $m.keys
echo "$k"                   # name\nversion (hash order)
```

