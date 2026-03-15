# Container

Virtual base class for all collection types. Defines the interface
contract that List, Map, and future containers (Stack, Queue, etc.)
must implement.

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

## Provided Methods

These work for all containers via delegation to the virtual methods:

```bash
$container.isEmpty && echo "empty"    # delegates to length
$container.destroy                     # cleans up companion array + registry
into=s $container.toString             # class, ID, type, length
```

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

## Inheritance Hierarchy

```
bashClass → Container → List  (indexed array)
                      → Map   (associative array)
                      → Stack, Queue, etc. (future)
```

