# Stream

A record-oriented reader/writer wrapping a file descriptor. Handles
delimited and fixed-width formats with multi-character delimiter support.
Parsing is configured once at construction; each `Read` call executes
the pre-built contract with zero per-iteration overhead.

## Loading

```bash
. boop Stream
```

---

## Quick Start

```bash
# Simple: read lines, split on colon, assign fields
into=s Stream.open "/etc/passwd" -d ':' user _ uid gid desc home shell
while $s.Read; do
  printf "%s lives at %s\n" "$user" "$home"
done
$s.close

# Array mode: CSV into an array each iteration
into=s Stream.open "data.csv" -d ',' -a row
while $s.Read; do
  printf "first col: %s\n" "${row[0]}"
done
$s.close

# Whole-line (no field splitting)
into=s Stream.open "log.txt" line
while $s.Read; do
  printf "%s\n" "$line"
done
```

---

## Construction

Two forms: inline arguments (simple) or schema string (complex).

### Inline (simple formats)

```bash
into=s Stream.open PATH [options] [field names...]
into=s Stream.new fd=N [options] [field names...]
into=s Stream.fromString "$data" [options] [field names...]
```

Options:
- `-d CHAR` -- field delimiter (default: `${_Delimiter}`, fallback `=`)
- `--eol STR` -- record delimiter (default: `${_EOL}`, fallback `\n`)
- `-a NAME` -- array mode: all fields into `$NAME` indexed array
- `-n N` -- read exactly N characters (fixed-width record, no EOL scan)
- `-t N` -- timeout in seconds (0 = non-blocking poll)

Positional args after options are field variable names. Last variable
gets "the rest" (same as bash `read`). `_` discards a field.

### Schema string (complex formats)

```bash
into=s Stream.open "batch.dat" '
  [Parser]
  eol       = \n
  delimiter = |
  mode      = delimited

  [Fields]
  name age city country
'
```

The schema is a single-quoted multi-line string parsed the same way
Args parses its schema -- line by line, section headers in brackets,
comments with `#`. Sections:

#### `[Parser]`

| Key | Default | Meaning |
|-----|---------|---------|
| `eol` | `\n` | Record delimiter. Multi-char OK. |
| `delimiter` | (context) | Field delimiter. |
| `mode` | `delimited` | `delimited` or `fixed` |
| `switch` | (none) | Field name used as format discriminator |
| `trim` | `false` | Trim trailing whitespace from fields |

#### `[Fields]` (delimited mode)

Space-separated field names on one line. `_` discards. Last field
gets the remainder.

```
user _ uid gid desc home shell
```

#### `[Format NAME]` (fixed-width mode)

Each token is `WIDTH:FIELDNAME`. Fields are extracted by position.
Multiple `[Format]` sections define a union-of-structs layout; the
`switch` key in `[Parser]` names the discriminator field.

```
[Parser]
mode   = fixed
switch = type

[Format 00]
2:type  20:account  30:desc

[Format 01]
2:type  20:dept

[Format 09]
2:type  20:user  10:role
```

---

## Methods

### `$s.Read`

Read one record and assign fields per the construction contract.

**No arguments (hot path):** executes the pre-built parsing logic.
One `(( $# ))` check -- if no args, straight into the fast path.

**With arguments (override):** temporarily overrides field names or
options for this one read. Useful when a stream has mixed record
types that can't be fully described by a static schema.

Returns exit code 0 on success, 1 on EOF.

```bash
while $s.Read; do
  # fields are populated
done
```

### `$s.write STR`

Write a string to the stream's FD. No delimiter appended.

### `$s.writeLine STR`

Write a string followed by `_EOL` to the stream's FD.

### `$s.eof`

Exit 0 if the FD is exhausted and the internal buffer is empty.

### `$s.close`

Close the FD if the stream owns it (opened via `Stream.open`).
No-op if the FD was passed in (caller owns it).

### `$s.readAll`

Drain the FD and return everything as a single string. Ignores
record/field delimiters -- pure slurp.

---

## Internal: The Read Algorithm

### Fast path (single-char EOL)

When `_EOL` is one character, `Read` uses bash's `read -d` builtin
directly. Zero buffering overhead. This is the common case.

```bash
IFS="$delimiter" read -r -d "$eol" -u "$fd" field1 field2 ...
```

### Slow path (multi-char EOL)

When `_EOL` is longer than one character, `Read` maintains an internal
buffer string and scans for the delimiter using parameter expansion:

1. `tail = buffer contents not yet consumed`
2. `match = ${tail%%"$eol"*}` -- everything before first occurrence
3. If `match` is shorter than `tail`: found. Extract record, trim buffer.
4. If equal: not found. Append more from FD (`read -N 8192`), retry.
5. FD exhausted + buffer non-empty: return remainder (final record).
6. FD exhausted + buffer empty: EOF.

### Fixed-width path

No delimiter scanning. Each `Read` pulls exactly `record_length` bytes
(`read -N $len`), then slices into fields by offset:

```bash
field="${record:offset:width}"
```

Pure parameter expansion. O(1) per field.

### Format-switching

After extracting the record, peek at the discriminator field (always
at a known offset in fixed-width mode). Hash-lookup the format spec.
Apply that format's offset/width table to assign fields.

---

## Ownership and Lifecycle

- `Stream.open PATH` -- Stream opens the FD, owns it, closes on `$s.close`
  or object destruction.
- `Stream.new fd=N` -- caller owns the FD. Stream reads/writes it but
  never closes it.
- `Stream.fromString "$data"` -- Stream creates a here-string FD
  internally, owns it.

---

## Relationship to _EOL and _Delimiter

The stream reads `_EOL` and `_Delimiter` at construction time and
stores them as properties. Subsequent changes to the global variables
do not affect an already-opened stream -- the contract is locked in
at open time. This is intentional: a stream's parsing behavior should
not change mid-read because someone set a global elsewhere.

Per-read overrides (via arguments to `Read`) are the escape hatch for
streams that need to change behavior mid-flight.

---

## Performance Notes

- **Hot path:** `Read` with no arguments, single-char EOL, delimited
  mode. One `read` builtin call per record. As fast as a bare
  `while read` loop with the same IFS/delimiter settings.
- **Multi-char EOL:** adds one string scan per record (parameter
  expansion, no fork). Cost is proportional to buffer size, not
  record count.
- **Fixed-width:** one `read -N` per record, then N parameter
  expansions for N fields. No scanning, no delimiter search.
- **Object overhead:** one boop method dispatch per `Read` call.
  For bulk processing (millions of records), consider the raw
  `read` builtin with the same IFS settings. Stream is for
  convenience and correctness, not for beating raw bash.

