# Data.JSON -- JSON Parser and Serializer

Pure bash JSON parser and serializer. No external dependencies (no jq,
no python). Parses JSON into a `Collection.Map.Fast` flat store for
O(1) point lookups via compound keys.

## Quick Start

```bash
. boop Data::JSON

# Parse
into=doc Data.JSON.parse '{"name":"Alice","scores":[10,20,30]}'
into=name $doc.get "name"         # "Alice"
into=s1 $doc.get "scores.1"      # "20"

# Stringify
into=json Data.JSON.stringify "$doc"
printf "%s\n" "$json"
# {"name":"Alice","scores":[10,20,30]}
```

## API

### `Data.JSON.parse jsonString`

Parses a JSON string into a `Collection.Map.Fast` object. Returns the
object ID via `boop.pass`.

Compound keys use `.` as separator:
- Object keys: `"user.name"`, `"user.address.city"`
- Array indices: `"items.0"`, `"items.1"`
- Mixed: `"users.0.name"`, `"matrix.1.2"`

All values are stored as strings. Type information is preserved by
convention:
- Numbers: stored as-is (`"42"`, `"-3.14"`)
- Booleans: `"true"` / `"false"`
- Null: empty string `""`

### `Data.JSON.stringify docObject`

Serializes a `Collection.Map.Fast` back to a JSON string. Infers
structure from compound keys:
- All-numeric children = JSON array
- String children = JSON object

Type reconstruction:
- Values matching `^-?[0-9]+\.?[0-9]*$` = unquoted number
- `"true"` / `"false"` = unquoted boolean
- Empty string = `null`
- Everything else = quoted string

### Not Instantiable

`Data.JSON` is a static-only class. `Data.JSON.new` crashes with a
helpful message. Use `Data.JSON.parse` directly.

## Supported JSON Features

- Objects: `{"key": "value"}`
- Arrays: `[1, 2, 3]`
- Strings: with escape sequences (`\n`, `\t`, `\\`, `\"`, `\/`)
- Numbers: integers, floats, negative, scientific notation
- Booleans: `true`, `false`
- Null: `null`
- Nested structures: arbitrary depth
- Whitespace: ignored between tokens

## Limitations

- Unicode escapes (`\uXXXX`) are skipped (position advanced, char dropped)
- Key order in stringify output is hash-iteration order (not insertion order)
- No streaming/incremental parse (whole string in memory)
- Duplicate keys: last value wins (no error)
- No `parseDeep` yet (full Map/List object tree -- planned)

## Performance

- Parser: no subshells, no forks. Pure string indexing via
  `${str:pos:1}`. State shared via globals.
- Stringify: no subshells for normal documents. Builds result via
  string concatenation in a shared variable. Recursive function calls
  with `local` vars for stack isolation. Depth guard at 50 spawns a
  subshell to reset the stack for pathological nesting.

## Error Handling

Parse errors crash with position information:
- `"Data.JSON: unterminated string"`
- `"Data.JSON: expected ':'"` 
- `"Data.JSON: expected ',' or '}'"`
- `"Data.JSON: unexpected character 'X' at position N"`
- `"Data.JSON: unexpected end of input"`
- `"Data.JSON: invalid token"`

## Examples

```bash
# Config file
into=cfg Data.JSON.parse '{"host":"localhost","port":8080,"debug":true}'
into=host $cfg.get "host"
into=port $cfg.get "port"

# API response
into=resp Data.JSON.parse "$api_output"
into=status $resp.get "status"
into=first_item $resp.get "data.items.0.name"

# Build and serialize
into=doc Collection.Map.Fast.new
$doc.set "name" "Bob"
$doc.set "scores.0" "95"
$doc.set "scores.1" "87"
into=json Data.JSON.stringify "$doc"
# {"name":"Bob","scores":[95,87]}
```

