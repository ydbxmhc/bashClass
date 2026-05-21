# Stream

A record-oriented reader wrapping a file descriptor. Parsing is
configured once at construction; each `Read` call executes the
pre-built contract. Supports single-char delimiters (via bash `read`
directly), multi-char exact-string delimiters, and char-class
delimiters with run-collapsing.

## Loading

```bash
. boop Stream
```

---

## Quick Start

```bash
# Direct mode: read lines, IFS splits on colon
into=s Stream.new -P "/etc/passwd"
while IFS=':' $s.read user _ uid gid desc home shell; do
  printf "%s lives at %s\n" "$user" "$home"
done
$s.close

# Buffered mode: -f for char-class field splitting
into=s Stream.new -P "data.csv" -f ',' name age city
while $s.Read; do
  printf "%s is %s\n" "$name" "$age"
done
$s.close

# Buffered mode: CRLF records with colon-separated fields
into=s Stream.new -P "windows.log" -D $'\r\n' -f ':' ts level msg
while $s.Read; do
  printf "[%s] %s\n" "$level" "$msg"
done
$s.close
```

---

## Construction

```bash
into=s Stream.new [options] [field names...]
```

The constructor determines the **parse mode** based on the options
given and locks it for the object's lifetime. Three modes exist:

| Mode | When chosen | How it reads |
|------|-------------|--------------|
| **direct** | Single-char EOL, no `-f`/`-F` | `read -d` from FD directly |
| **regex** | Char-class EOL (`-E`) or char-class field delim (`-f`) | Buffered, regex match |
| **pe** | Multi-char exact-string EOL (`-D`) or exact-string field delim (`-F`) | Buffered, parameter expansion |

### Source options (mutually exclusive with fallback)

| Option | Meaning |
|--------|---------|
| `-P PATH` / `--path=PATH` | Open file for reading |
| `-u FD` / `--fd=FD` | Use an already-open FD |
| *(neither)* | Dup stdin |

### Record delimiter options (mutually exclusive)

| Option | Meaning | Mode |
|--------|---------|------|
| `-d CHAR` | Single-char EOL, exact | direct |
| `-D STRING` | Multi-char EOL, exact string, non-stacking | pe |
| `-E CHARS` | EOL char class -- any char in set, runs collapse | regex |
| *(default)* | `${_EOL:-\n}`. Length determines mode. | auto |

### Field delimiter options (mutually exclusive)

| Option | Meaning | Mode |
|--------|---------|------|
| `-f CHARS` | Any single char in set, non-stacking (empties preserved) | regex |
| `-F STRING` | Exact multi-char string, non-stacking | pe |
| `-W CHARS` | Char class, stacking (runs of delimiters collapse into one boundary) | regex |
| *(default, direct mode)* | IFS splitting -- user controls IFS | direct |
| *(default, buffered mode)* | Defaults to record delimiter (one field per record) | buffered |

`-W` is the buffered-mode equivalent of IFS whitespace behavior. Use
`-W "$IFS"` to get collapsing-whitespace field splitting in buffered mode.
Unlike IFS, `-W` treats ALL chars in the set identically (no special
whitespace vs non-whitespace distinction).

**Note:** Stream does NOT read the `_Delimiter` framework global. Use
`-f`, `-F`, or `-W` explicitly. If you want `_Delimiter`'s value, pass
it: `-f "$_Delimiter"`.

### Other options

| Option | Meaning |
|--------|---------|
| `-a NAME` | Array mode: all fields into named array |
| `-x` | Expose: generate `$o.fieldname` accessors, store field values on the object |
| `-n N` / `-N N` | Fixed-width: read exactly N chars per record |
| `-t N` | Timeout in seconds (direct mode: passed to `read`) |
| `-b N` / `--blockSize=N` | Buffer fill size (default: 1024). Buffered modes only. |

### Positional arguments

Everything after the options that isn't recognized as an option is a
**field name**. Field names must be valid bash identifiers. The last
field gets "the rest" (same as bash `read`). Use `_` to discard a field.

```bash
into=s Stream.new -P "data.csv" -f ',' name age _ city
#                                       ^^^^ ^^^ ^ ^^^^
#                                       f1   f2  discard  f3 (gets remainder)
```

---

## Methods

### `$s.read` (direct mode)

Thin wrapper around bash's `read` builtin. Available only on direct-mode
objects (no `-D`, `-E`, `-f`, `-F`, `-W`, `-n`). IFS does field splitting.

Returns 0 on success, 1 on EOF.

**LSP divergence from raw `read`:** When the final record has no trailing
delimiter (common with files that lack a trailing newline), raw `read`
returns non-zero even though it read data -- causing `while read; do`
loops to skip the last record. Stream handles this: if `read` returns
non-zero but data was read, `$s.read` returns 0 (so your loop body
runs) and sets EOF internally (so the next call returns 1). This means
`while $s.read; do` always processes every record, including unterminated
final records. You do NOT need the `|| [[ -n "$line" ]]` workaround.

```bash
while $s.read; do
  # fields populated via IFS splitting
  # EVERY record is processed, including the last one without trailing newline
done

# With custom IFS:
while IFS=':' $s.read; do ...
```

### `$s.Read` (buffered mode)

Buffered framework reader. Available only on buffered-mode objects
(constructed with `-D`, `-E`, `-f`, `-F`, `-W`, or `-n`). Field
splitting uses the configured delimiter, NOT IFS.

Returns 0 on success, 1 on EOF.

```bash
while $s.Read; do
  # fields are populated
done
```

**Only one of `$s.read` or `$s.Read` is available per object.** Calling
the wrong one returns an error. The constructor logs which is live.

### `$s.next`

Convenience method: calls `$s.read` or `$s.Read` depending on the
object's mode. Use when you don't care about mode and don't need
maximum speed (adds one branch per call).

```bash
while $s.next; do ...
```

### `$s.field INDEX_OR_NAME`

Return a field value by numeric index or field name. Works with both
array mode (`-a`) and named fields with `-x` (expose).

```bash
into=v $s.field 0       # first field by index
into=v $s.field name    # field by name (requires -x or named fields)
```

### `$s.fieldCount`

Return the number of fields from the last read. Use to iterate safely
without running off the end.

```bash
into=n $s.fieldCount
for (( i=0; i < n; i++ )); do
  into=v $s.field $i
  ...
done
```

### `$s.buffered`

Returns exit code 0 if this stream uses the buffered engine (pe or
regex mode). Exit code 1 if direct mode.

### `$s.eof`

Returns exit code 0 if the stream is exhausted. Use after a Read
returns non-zero to distinguish EOF from error.

### `$s.close`

Close the stream's FD. Always closes -- there is no ownership tracking.
If you passed in an FD you still need, don't call close.

### `$s.write STR`

Write a string to the stream's FD. No delimiter appended.

### `$s.writeLine STR`

Write a string followed by the record EOL to the stream's FD.

---

## The CRLF Contract

**This is important.** When the record delimiter is set to an exact
multi-char string (e.g. `\r\n` via `-D`), the delimiter must match
IN FULL to trigger a record boundary. A bare `\n` inside the record
is just data -- it does NOT split the record.

This means:
- `-D $'\r\n'` with data `"line1\nstill line1\r\nline2\r\n"` produces
  two records: `"line1\nstill line1"` and `"line2"`.
- The embedded `\n` is preserved in the first record.

If you want ANY newline-like character to split records (bare LF, bare
CR, CRLF all treated as boundaries), use `-E $'\r\n'` instead. That's
char-class mode with run-collapsing -- any sequence of CR and/or LF
characters constitutes one record boundary.

---

## Parse Modes in Detail

### Direct Mode

The constructor pre-builds a complete `read` argument array:
```
(-r -d "$eol" -u "$fd" field1 field2 field3)
```

Each `$s.Read` call is literally:
```bash
read "${args[@]}"
```

One builtin call. No buffering, no string manipulation, no overhead
beyond method dispatch. IFS splitting works exactly as it does with
bare `read` -- the user controls IFS, we don't touch it.

**When to use:** simple line-oriented parsing where `read` does
everything you need. This is the default for newline-delimited data
with no multi-char delimiter options.

### Regex Mode (buffered)

Used when `-E` (char-class EOL) or `-f` (char-class field delimiter)
is specified. The constructor builds anchored regexes:

- Record regex: `^([^CHARS]*)[CHARS]+` (captures record, consumes delimiter run)
- Field regex: `^([^CHARS]*)[CHARS]` (captures one field, consumes one delimiter char)

Each Read:
1. Apply record regex to buffer
2. No match? Fill buffer from FD, retry
3. Match? Extract record from `BASH_REMATCH[1]`, advance buffer
4. Split record into fields using field regex + nameref assignment

### PE Mode (buffered)

Used when `-D` (exact-string EOL) or `-F` (exact-string field delimiter)
is specified. Uses parameter expansion:

- Record extraction: `${buf%%"$eol"*}` (everything before first EOL)
- Buffer advance: `${buf#*"$eol"}` (everything after first EOL)
- Field extraction: same pattern with field delimiter

Handles arbitrary multi-char delimiters that can't be expressed as
regex character classes (e.g. `<>`, `::`, `\r\n`).

---

## Field Assignment

Fields are assigned via **nameref** -- no `eval`, no `read <<<`, no
IFS manipulation in buffered modes. The field names array is stored
as a real bash indexed array (not a joined string).

```bash
# Internal assignment loop (simplified):
for vname in "${fields[@]}"; do
  [[ "$vname" == "_" ]] && continue
  local -n ref="$vname"
  ref="$value"
done
```

In direct mode, `read` handles field assignment natively (field names
are passed directly as arguments to `read`).

---

## Performance

### Overhead

Stream adds per-record overhead from method dispatch and data access.
Benchmarks on 1000 records:

| Mode | Time | vs raw `read` |
|------|------|---------------|
| Direct (whole line) | ~1.4s | ~10x |
| Direct (IFS split, 5 fields) | ~1.4s | ~7x |
| Buffered PE (whole line) | ~2.3s | ~16x |
| Buffered PE (5 fields, -f) | ~3.2s | ~17x |
| Buffered regex (-E) | ~1.7s | ~12x |

The overhead is dominated by method dispatch and hash lookups, not by
the parsing algorithm. For bulk processing (millions of records), use
raw `read`. Stream is for convenience and correctness on structured
data -- hundreds to low thousands of records.

### Block Size

Benchmarking shows block size has negligible impact in the 256-2048
range. Default is 1024. Override with `--blockSize=N` if you have a
specific reason (e.g. very long records where a larger buffer avoids
multiple refills).

### Optimization: `__Stream_data`

Stream stores per-object configuration in a single global associative
array (`__Stream_data`) with compound keys (`"${objId}.property"`).
This eliminates the `__boop.get` function call overhead that would
otherwise dominate the hot path. The property system is still used
for introspection but not in the read loop.

---

## Null Bytes

Bash variables cannot hold `\0`. Stream operates on text only.
Binary data with embedded nulls is out of scope.

---

## Examples

### CSV with header

```bash
into=s Stream.new -P "data.csv" -f ','
$s.Read header_line  # first record into a single variable
# Now read data rows with known fields:
while $s.Read name age city; do
  printf "%s (%s) from %s\n" "$name" "$age" "$city"
done
$s.close
```

### Paragraph mode (double-newline separated)

```bash
into=s Stream.new -P "document.txt" -D $'\n\n' paragraph
while $s.Read; do
  printf "=== PARAGRAPH ===\n%s\n\n" "$paragraph"
done
$s.close
```

### Mixed line endings (any CR/LF combination)

```bash
into=s Stream.new -P "messy.log" -E $'\r\n' line
while $s.Read; do
  process_line "$line"
done
$s.close
```

### Fixed-width records

```bash
into=s Stream.new -P "mainframe.dat" -n 80 record
while $s.Read; do
  # Slice fields by position
  type="${record:0:2}"
  account="${record:2:20}"
  amount="${record:22:10}"
done
$s.close
```

### Array mode

```bash
into=s Stream.new -P "data.tsv" -f $'\t' -a row
while $s.Read; do
  printf "columns: %d, first: %s\n" "${#row[@]}" "${row[0]}"
done
$s.close
```

### Writing

```bash
exec {fd}> "output.txt"
into=s Stream.new --fd="$fd"
$s.writeLine "header line"
$s.writeLine "data line 1"
$s.write "no newline after this"
$s.close
```

