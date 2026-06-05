# boson(1)

## NAME

**boson** — query JSON with jq-style path expressions

## SYNOPSIS

```
boson [-r | -e | --into=VAR | -E] EXPR [FILE]
boson (-h | --help | --examples | --about | --boop)
```

EXPR is a path expression. With no FILE, boson reads JSON from standard input.

## DESCRIPTION

**boson** parses a JSON document into a flat key-value store and resolves a
path expression against it, like a small `jq`. It reads standard input or a
single file given as the final argument, and writes the selected value(s) in
one of several output formats.

The name stands for "Bash Oriented Scripting Object Notation."

> **Status.** Path expressions, array iteration, and the output modes below are
> implemented and tested. The richer jq surface — `select(...)`, pipe chaining,
> object construction, `map`/`reduce`/`sort_by`, recursive descent (`..`) — is
> on the roadmap; see [TODO.md](../TODO.md). In the default mode a non-leaf node
> currently prints a `{...} (N keys)` placeholder rather than re-emitting JSON.

### Path syntax

| Expression | Meaning |
|------------|---------|
| `.key` | Top-level key |
| `.key.sub` | Nested key |
| `.arr[0]` | Array element by index |
| `.arr[]` | Iterate all array elements (one per line) |
| `.obj[].name` | Iterate an array, extract `.name` from each element |

Internally a path becomes a compound key — `.users[0].email` → `users.0.email`.
Array iteration (`[]`) enumerates the numeric children under a prefix, in index
order. A key that does not exist yields `null`.

## OPTIONS

The output modes are mutually exclusive; choose at most one. With none, boson
uses type-aware default output.

| Short | Long | Meaning |
|-------|------|---------|
| | (default) | Type-aware: strings quoted, numbers/booleans/null bare |
| `-r` | `--raw` | Raw values, unquoted (one per line when iterating) |
| `-e` | `--emit` | Every leaf under EXPR as sourceable `var=value` lines |
| | `--into=VAR` | The value as `VAR=value`, or an array as `VAR=(...)` |
| `-E` | `--eponymous` | Like `--emit`, but variables are named by the leaf key |

Help:

| Short | Long | Meaning |
|-------|------|---------|
| `-h` | `--help` | Synopsis |
| | `--examples` | Cookbook |
| | `--about` | About boson |
| | `--boop` | About the boop framework |

`--emit` and `--eponymous` preserve the **original document key order**: they
walk the parser's companion ordered-key index, not the raw hash, so assignments
emerge in source order — the same mechanism `Data.JSON.stringify` uses.

## EXAMPLES

### Reading values

```bash
boson '.name' < data.json             # "boop"      (default: strings quoted)
boson -r '.name' < data.json          # boop        (raw, unquoted)
boson '.database.host' < config.json  # nested key
boson '.scores[0]' < data.json        # first array element
boson '.version' package.json         # FILE as the final argument
```

### Iterating arrays

```bash
boson '.tags[]' < data.json           # each element, one per line
boson -r '.users[].email' < data.json # one unquoted email per line
boson '.users[].age' < data.json      # a field extracted from each element
```

### Type-aware default output

```bash
boson '.count'   < d.json   # 42      (number, bare)
boson '.active'  < d.json   # true    (boolean, bare)
boson '.nothing' < d.json   # null
boson '.name'    < d.json   # "boop"  (string, quoted)
```

### Sourceable output for shell scripts

Pull configuration straight into shell variables instead of shelling out per
value:

```bash
# Whole subtree as var=value lines, in document order
boson --emit '.database' < config.json
#   host=localhost
#   port=5432
#   ssl=false

# Load an entire document into the current shell
. <(boson --emit '.' < config.json)

# A single named value
boson --into=host '.database.host' < config.json    # host=localhost
. <(boson --into=port '.server.port' < config.json)

# An iterated field as an array
boson --into=names '.users[].name' < data.json       # names=(Alice Bob)

# Eponymous: variable named by the leaf key
boson -E '.database.host' < config.json              # host=localhost
boson -E '.database' < config.json                   # host=…  port=…  ssl=…
```

## EXIT STATUS

- **0** — query succeeded; a value (or `null`) was written.
- **non-zero** — malformed JSON, no input (no file and nothing piped), an empty
  expression, or conflicting output modes (rejected by the argument parser).

Diagnostics print to standard error beginning with `boson:`.

## NOTES

boson is pure bash, built on the **boop** framework's `Data.JSON`, `Map.Fast`,
and `Args` classes. It began as a thought experiment — how much of `jq` can a
bash OOP standard library express? — and it will never match a C-based JSON
processor on speed. Its value is reach: it runs anywhere **bash 4.3+** is
present, with no `jq`, no Python, and no external dependencies, which makes it a
dependable fallback on stripped containers and minimal hosts where those are
absent.

The query engine operates on the flat key-value store, not on JSON syntax, so
the same engine is intended to serve YAML and INK/Config sources once those
parsers feed the same backend. For repeated use, bundle boson with `collider`
(`collider boson` → `bundle-boson`) to avoid the per-invocation framework load.

## SEE ALSO

`jq(1)` — the tool boson imitates. [docs/JSON.md](JSON.md) for the parser,
[docs/Map.md](Map.md) for the backing store, [docs/tools.md](tools.md) for the
tool family, and [TODO.md](../TODO.md) for the staged roadmap.
