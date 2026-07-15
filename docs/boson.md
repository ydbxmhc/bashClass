# boson(1)

## Contents

- [NAME](#name)
- [SYNOPSIS](#synopsis)
- [DESCRIPTION](#description)
  - [Path expressions](#path-expressions)
  - [Pipe expressions](#pipe-expressions)
  - [Predicates](#predicates)
- [OPTIONS](#options)
- [EXAMPLES](#examples)
  - [Reading values](#reading-values)
  - [Iterating arrays](#iterating-arrays)
  - [Non-leaf output](#non-leaf-output)
  - [Type-aware default output](#type-aware-default-output)
  - [Pipe expressions and filtering](#pipe-expressions-and-filtering)
  - [Sourceable output for shell scripts](#sourceable-output-for-shell-scripts)
- [CAVEATS](#caveats)
  - [NUL bytes](#nul-bytes)
  - [`-E` / `--eponymous`: variable name collisions](#e--eponymous-variable-name-collisions)
  - [`$()` strips trailing newlines](#strips-trailing-newlines)
  - [Predicate numeric comparisons](#predicate-numeric-comparisons)
  - [Pipe spaces are required](#pipe-spaces-are-required)
- [EXIT STATUS](#exit-status)
- [NOTES](#notes)
- [SEE ALSO](#see-also)

---

## NAME

**boson** — query JSON with jq-style path expressions and pipelines

## SYNOPSIS

```
boson [-r | -e | --into=VAR | -E] EXPR [FILE]
boson (-h | --help | --examples | --caveats | --about | --boop)
```

EXPR is a path expression, or a pipeline of stages joined by ` | `.
With no FILE, boson reads JSON from standard input.

## DESCRIPTION

**boson** parses a JSON document into a flat key-value store and evaluates
an expression against it, like a small `jq`. It reads standard input or a
single file given as the final argument, and writes the selected value(s) in
one of several output formats.

The name stands for "Bash Oriented Scripting Object Notation."

> **NUL bytes.** Bash variables cannot hold or detect NUL bytes. Any JSON
> string value containing a NUL will be silently truncated at the first one.
> This applies to all output modes. See CAVEATS.

### Path expressions

A path expression selects a value or set of values from the document.

| Expression | Meaning |
|------------|---------|
| `.key` | Top-level key |
| `.key.sub` | Nested key |
| `.arr[0]` | Array element by index |
| `.arr[]` | Iterate all array elements (one per line) |
| `.obj[].name` | Iterate an array, extract `.name` from each element |

Internally a path becomes a compound key — `.users[0].email` →
`users.0.email`. Array iteration (`[]`) enumerates the numeric children
under a prefix, in index order. A key that does not exist yields `null`.
A non-leaf node (an object or array) is re-emitted as JSON.

### Pipe expressions

Stages are joined by ` | ` (spaces required). Each stage receives the
set of contexts produced by the previous one and transforms or filters them:

```bash
boson -r '.users[] | select(.active) | .name' < data.json
```

The two stage types are:

- **Path** — any path expression from the table above; advances every
  context by that path relative to where it currently sits.
- **`select(PRED)`** — filter; keeps only the contexts where PRED is true.

### Predicates

Predicates are used inside `select(...)`. The field reference may be
`.field` (relative to the current context) or `.` (the whole element,
for scalar iteration). String values on the right-hand side may be quoted
(`"value"`) or bare. Numeric comparisons use integer arithmetic.

| Form | Passes when |
|------|-------------|
| `.field` | non-empty, not `null`, not `false` (truthy) |
| `.` | current element is truthy |
| `-n .field` | non-empty string (bash `-n` semantics; `"false"` passes) |
| `-z .field` | empty or missing value |
| `has(.field)` | key is present in document (even if `null`, `false`, or `""`) |
| `.field == VALUE` | **string** equality (byte-for-byte) |
| `.field != VALUE` | **string** inequality |
| `.field -eq N` | **numeric** equality — missing/empty field coerces to 0 |
| `.field -ne N` | **numeric** inequality |
| `.field < N` or `.field -lt N` | numeric less-than |
| `.field > N` or `.field -gt N` | numeric greater-than |
| `.field <= N` or `.field -le N` | numeric less-than-or-equal |
| `.field >= N` or `.field -ge N` | numeric greater-than-or-equal |
| `.field =~ PAT` | ERE regex match — covers startswith (`^pfx`), endswith (`sfx$`), contains |

**`==` vs `-eq`:** `==` compares bytes; `-eq` compares integers. For
well-formed JSON numbers they usually agree, but they differ in two
important cases:

- **Missing or empty field:** `-eq 0` matches a record where the field is
  absent (empty string coerces to 0); `== "0"` does not.
- **Leading zeros / whitespace:** `"007" -eq 7` passes; `"007" == "7"` does not.

Use `==` when the field is a string or when exact byte identity matters.
Use `-eq` / `-ne` when you're comparing JSON numbers and want integer
semantics, particularly when the field might be absent in some records.

The `-n`/`-z` distinction from truthy matters when a field holds the
string `"false"` or `"0"`: truthy rejects both, `-n` passes them (the
string is non-empty).

The `has` / truthy distinction matters when a field exists but holds
`null` or `false`: `has(.field)` passes, `.field` (truthy) does not.

## OPTIONS

The output modes are mutually exclusive; choose at most one. With none,
boson uses type-aware default output.

| Short | Long | Meaning |
|-------|------|---------|
| | (default) | Type-aware: strings quoted, numbers/booleans/null bare |
| `-r` | `--raw` | Raw values, unquoted (one per line when iterating) |
| `-e` | `--emit` | Every leaf under EXPR as sourceable `var=value` lines |
| | `--into=VAR` | The value as `VAR=value`, or an array as `VAR=(...)` |
| `-E` | `--eponymous` | Like `--emit`; errors on variable name collisions — see CAVEATS |

Help:

| Short | Long | Meaning |
|-------|------|---------|
| `-h` | `--help` | Synopsis |
| | `--examples` | Cookbook |
| | `--caveats` | Known gotchas and limitations |
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

### Non-leaf output

When an expression resolves to an object or array rather than a scalar,
boson re-emits it as JSON:

```bash
boson '.database' < config.json       # {"host":"localhost","port":5432,...}
boson '.users[0]' < data.json         # {"name":"Alice","age":30}
boson '.users[]' < data.json          # one JSON object per line
```

### Type-aware default output

```bash
boson '.count'   < d.json   # 42      (number, bare)
boson '.active'  < d.json   # true    (boolean, bare)
boson '.nothing' < d.json   # null
boson '.name'    < d.json   # "boop"  (string, quoted)
```

### Pipe expressions and filtering

Pipe stages filter or transform an iterating result set. The output mode
(`-r`, `--into`, etc.) applies to the final stage.

```bash
# Keep users where active is true, extract name
boson -r '.users[] | select(.active) | .name' < data.json

# Numeric comparison
boson '.orders[] | select(.total > 100) | .id' < data.json

# String equality
boson -r '.items[] | select(.type == "fruit") | .name' < data.json

# Regex — startswith, endswith, or contains
boson -r '.files[] | select(.name =~ "\.sh$") | .name' < data.json
boson -r '.logs[]  | select(.msg  =~ "error|warn") | .msg' < data.json

# Key existence — field present even if null or false
boson -r '.users[] | select(has(.email)) | .email' < data.json

# Non-empty string — field is set and not empty (unlike truthy, "false" passes)
boson -r '.items[] | select(-n .description) | .name' < data.json

# Missing or empty — inverse of the above
boson -r '.items[] | select(-z .description) | .name' < data.json

# Collect filtered results into a shell array
boson --into=active '.users[] | select(.active) | .name' < data.json
# → active=(Alice Carol)

# Non-leaf output through a pipe
boson '.users[] | select(.active)' < data.json   # one JSON object per line
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

## CAVEATS

### NUL bytes

Bash variables cannot hold or detect NUL bytes. Any JSON string value
containing a NUL will be silently truncated at the first one. This applies to
all output modes — there is no warning and no error.

### `-E` / `--eponymous`: variable name collisions

Variable names are derived from the key path **relative to your expression
root**, with dots replaced by underscores. Two source paths that differ only
in a key containing underscores versus nested dots will sanitize to the same
variable name:

```
{ "a_b": 1, "a": { "b": 2 } }

boson -E '.' data.json
  → boson: -E collision: "a_b" and "a.b" both map to variable "a_b"
```

boson detects every collision before emitting anything and exits nonzero,
listing all conflicting pairs. It never produces partial output. Options:

- Use a **deeper expression root** to narrow the field set (`-E '.a'` instead
  of `-E '.'`)
- Assign specific values explicitly with `--into=VAR`
- Use `--emit` instead — same relative-path naming, fully deterministic
- Refactor the JSON to remove the ambiguous key names

### `$()` strips trailing newlines

All variable captures use `$(...)` substitution, which bash unconditionally
strips trailing newlines from. A JSON string value ending in one or more
newlines will lose them when assigned to a shell variable.

### Predicate numeric comparisons

`<`/`-lt`, `>`/`-gt`, `<=`/`-le`, `>=`/`-ge`, `-eq`, `-ne` all use
integer arithmetic (`(( ))`). Floating-point values are truncated;
non-numeric strings are coerced to 0; **missing or empty fields are also
coerced to 0**, which means `select(.count -eq 0)` will match records
where `count` is absent. Use `== "0"` (string equality) if you want to
match the literal value `0` without catching missing fields.

### Pipe spaces are required

The pipe separator is ` | ` — a space, pipe, space. A bare `|` without
surrounding spaces is not recognized and will be treated as part of the
expression, producing unexpected results.

## EXIT STATUS

- **0** — query succeeded; a value (or `null`) was written.
- **non-zero** — malformed JSON, no input (no file and nothing piped), an empty
  expression, conflicting output modes, or a `-E` variable name collision.

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
the same engine is intended to serve YAML and Config sources once those parsers
feed the same backend. For repeated use, bundle boson with `collider`
(`collider boson` → `bundle-boson`) to avoid the per-invocation framework load.

## SEE ALSO

`jq(1)` — the tool boson imitates. [docs/JSON.md](JSON.md) for the parser,
[docs/Map.md](Map.md) for the backing store, [docs/tools.md](tools.md) for the
tool family, and [TODO.md](TODO.md) for the staged roadmap.

---

[↑ Site map](index)
