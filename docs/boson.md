# boson — Structured Data Query

A jq-style query tool for JSON, in pure bash. boson parses input into a
`Map.Fast` store and resolves path expressions against it. No `jq`, no external
dependencies — just the boop framework.

The name is "Bash Oriented Scripting Object Notation." It is built on
`Data.JSON`, `Map.Fast`, and `Args`.

> **Status.** Stage 1 (path expressions, array iteration, raw output) and the
> sourceable output modes (`--emit`, `--into`, `--eponymous`) are implemented
> and tested (`tests/tools/test_boson`, 26 assertions). The jq-style query
> features — `select(...)`, pipe chaining, object construction,
> `map`/`reduce`/`sort_by`, recursive descent — are on the roadmap. See
> [TODO.md](../TODO.md).

---

## Quick Start

```bash
boson '.name' < data.json                 # "boop"   (strings quoted)
boson -r '.name' < data.json              # boop     (raw, no quotes)
boson '.database.host' < config.json      # nested key
boson '.scores[0]' < data.json            # array index
boson '.users[]' < data.json              # iterate (one element per line)
boson '.users[].email' < data.json        # iterate + extract a field
boson '.version' package.json             # file as the last argument
```

Reads stdin, or a file given as the final positional argument. Layered help:
`--examples`, `--about`, `--boop`.

---

## Path Syntax

| Expression | Meaning |
|------------|---------|
| `.key` | Top-level key |
| `.key.sub` | Nested key |
| `.arr[0]` | Array element by index |
| `.arr[]` | Iterate all array elements (one per line) |
| `.obj[].name` | Iterate an array, extract `.name` from each element |

Internally a path is rewritten to a Map.Fast compound key: `.users[0].email`
becomes the key `users.0.email`. Array iteration (`[]`) enumerates the numeric
children under a prefix, in index order.

```bash
boson '.address.city' < data.json     # nested
boson '.scores[2]' < data.json        # third element
boson '.tags[]' < data.json           # each tag
boson '.users[].age' < data.json      # each user's age
```

A key that does not exist yields `null`.

---

## Output Modes

The output modes are mutually exclusive. Default mode is type-aware; the others
produce raw or sourceable text.

### Default — type-aware

Strings are quoted; numbers, booleans, and `null` are bare.

```bash
boson '.name'   < d.json   # "boop"
boson '.count'  < d.json   # 42
boson '.active' < d.json   # true
boson '.nothing' < d.json  # null
```

A non-leaf node (an object or array) currently prints a `{...} (N keys)`
placeholder rather than re-emitting JSON. Re-emission is a roadmap item.

### `-r`, `--raw` — unquoted values

```bash
boson -r '.name' < d.json              # boop
boson -r '.users[].email' < d.json     # one unquoted email per line
```

### `--emit` — sourceable assignments

Every leaf under the expression as `var=value` lines, safely quoted for
sourcing. Key paths become variable names (dots and dashes → underscores).

```bash
boson --emit '.database' < config.json
# host=localhost
# port=5432
# ssl=false

. <(boson --emit '.' < config.json)    # load the whole document into the shell
```

### `--into=VAR` — named assignment

A single value as `VAR=value`, or an array as `VAR=(...)`.

```bash
boson --into=host '.database.host' < c.json    # host=localhost
boson --into=names '.users[].name' < d.json    # names=(Alice Bob)
. <(boson --into=port '.server.port' < c.json)
```

### `-E`, `--eponymous` — leaf-name variables

Like `--emit`, but uses the leaf key name as the variable name.

```bash
boson -E '.database.host' < c.json     # host=localhost
boson -E '.database' < c.json          # host=…\nport=…\nssl=…
```

### Output ordering

`--emit` and `--eponymous` preserve **original document key order**. They walk
the JSON parser's companion ordered-key index (`__boop_keys_${doc}`), not the
raw associative array, so emitted assignments come out in the same order the
keys appeared in the source — the same mechanism `Data.JSON.stringify` uses.

---

## Exit Status and Errors

- A successful query exits 0.
- Malformed JSON: a parse error on stderr, non-zero exit.
- No input (no file, nothing piped): error on stderr, non-zero exit.
- An empty expression: error on stderr, non-zero exit.
- Conflicting output modes (e.g. `-r --emit`): rejected by the Args schema.

---

## Design Notes

### Format-agnostic at heart

boson queries a `Map.Fast`. JSON is just the parser that populates it today.
Because the query operates on the flat compound-key store rather than on JSON
syntax, the same engine will serve YAML and Config once those parsers feed the
same backend — which is why the roadmap envisions a reusable `Data.Boson`
*class* with the CLI as a thin wrapper. For now the query logic lives in the
`boson` script.

### Why sourceable output

The `--emit` / `--into` / `--eponymous` modes exist because the most common
thing a shell script wants from a config file is *variables*. Rather than
shelling out per value, you source one boson call and have the whole subtree as
bash variables — in document order, safely quoted.

### Roadmap

Stage 2+ adds the jq-style query surface: `select(.age > 30)` predicates (built
on Math comparison), pipe chaining between stages, string interpolation and
object construction, `map`/`reduce`/`group_by`/`sort_by` (built on List's
functional ops), and recursive descent (`..`). See [TODO.md](../TODO.md) for
the staged plan and what each stage builds on.
