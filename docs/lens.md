# lens(1)

## Contents

- [NAME](#name)
- [SYNOPSIS](#synopsis)
- [DESCRIPTION](#description)
  - [The one-axis rule](#the-one-axis-rule)
- [OPTIONS](#options)
  - [Input](#input)
  - [Byte-seek (bulk skip for large inputs)](#byte-seek-bulk-skip-for-large-inputs)
  - [Position (mutually exclusive with the other axes)](#position-mutually-exclusive-with-the-other-axes)
  - [Match (mutually exclusive with the other axes)](#match-mutually-exclusive-with-the-other-axes)
  - [Fields (mutually exclusive with the other axes)](#fields-mutually-exclusive-with-the-other-axes)
    - [Literals in the spec](#literals-in-the-spec)
    - [Changing the spec separator: `--spec-sep CHAR`](#changing-the-spec-separator---spec-sep-char)
  - [Chars (mutually exclusive with the other axes)](#chars-mutually-exclusive-with-the-other-axes)
  - [Output delimiters](#output-delimiters)
  - [Inversion](#inversion)
  - [Record delimiter (choose at most one; default is newline)](#record-delimiter-choose-at-most-one-default-is-newline)
  - [Formatting](#formatting)
  - [Help](#help)
- [EXAMPLES](#examples)
  - [Replacing head / tail / wc](#replacing-head--tail--wc)
  - [Slicing by line range](#slicing-by-line-range)
  - [Combining two position options](#combining-two-position-options)
  - [Replacing grep](#replacing-grep)
  - [Replacing cut / awk field selection](#replacing-cut--awk-field-selection)
  - [Reordering fields](#reordering-fields)
  - [Inserting literals and converting formats](#inserting-literals-and-converting-formats)
  - [Custom output record separator (--ors / --rec-sep)](#custom-output-record-separator---ors---rec-sep)
  - [Scanning the tail of a large file (byte-seek)](#scanning-the-tail-of-a-large-file-byte-seek)
  - [Fixed-width columns](#fixed-width-columns)
  - [Non-line records](#non-line-records)
  - [Multiple files](#multiple-files)
  - [Composing axes with pipes](#composing-axes-with-pipes)
- [EXIT STATUS](#exit-status)
- [NOTES](#notes)
  - [Streaming](#streaming)
- [SEE ALSO](#see-also)

---

## NAME

**lens** — inspect, filter, and slice text streams

## SYNOPSIS

```
lens [--first N] [--last N] [--from N] [--to N] [--not] [FORMAT] [DELIM] [SEEK] [FILE...]
lens (--match PAT | --no-match PAT)... [--and | --or] [--not] [FORMAT] [DELIM] [FILE...]
lens --fields SPEC [-f|-F|-W DELIM] [--ofs STR] [--ors STR] [--spec-sep C] [--not] [FORMAT] [DELIM] [FILE...]
lens --chars SPEC [--ors STR] [--spec-sep C] [--not] [FORMAT] [DELIM] [FILE...]
lens (-h | --help | --options | --examples | --about | --boop)
```

Where:
- **FORMAT** is any of `-n`/`--number`, `-c`/`--count`, `-H`/`--prefix`
- **DELIM** sets the record delimiter: `-d CHAR`, `-D STRING`, or `-E CHARS`
- **SEEK** is `--rec-after-byte N` or `--start-at-byte N` (bulk skip)
- **FILE...** are input files; with none, lens reads standard input

## DESCRIPTION

**lens** reads a text stream — standard input or one or more files — selects
records along a single axis, and writes the survivors. One tool covers work
usually split across `head`, `tail`, `grep`, `cut`, and `wc`, with a consistent
syntax and support for multi-character and character-class record/field
delimiters that those tools lack.

A *record* is a line by default; the **DELIM** options redefine it (paragraph
mode, CRLF, arbitrary strings, character classes).

### The one-axis rule

lens filters along exactly **one axis per invocation**. The four axes are:

| Axis | Options |
|------|---------|
| Position | `--first`, `--last`, `--from`, `--to` |
| Match | `--match`, `--no-match` (with `--and`/`--or`) |
| Fields | `--fields` |
| Chars | `--chars` |

Axes are mutually exclusive — you cannot mix position with match, or fields
with chars, in one call. Combine axes by piping lens into lens; each stage does
one thing, and the result is easier to reason about than one call with many
interacting flags. Violating the rule is a hard error from the argument parser.

```bash
lens --last 100 app.log | lens --match error    # errors in the last 100 lines
lens --match error app.log | lens --fields 1,4  # fields 1,4 of matching lines
```

## OPTIONS

Every option has a short and/or long form. Short options may take their value
attached (`-d:`) or separated (`-d :`).

### Input

| Short | Long | Argument | Meaning |
|-------|------|----------|---------|
| `-P` | `--file` | PATH | Read from PATH instead of stdin |
| `-u` | `--fd` | N | Read from already-open file descriptor N |

Bare file arguments work too: `lens --first 5 a.log` reads `a.log`. With
multiple files, each is processed independently (see EXAMPLES).

### Byte-seek (bulk skip for large inputs)

Two long-only options cheaply skip past a byte offset before reading begins —
useful for scanning the tail of a large file without parsing everything before
it. Both work on **pipes as well as files** (the skip consumes a raw byte blast
off the stream; it does not require a seekable file). They are mutually
exclusive with each other, and not valid with multiple files.

| Long | Argument | Meaning |
|------|----------|---------|
| `--rec-after-byte` | N | Skip N bytes, then discard the partial record landed in, resuming on a clean record boundary |
| `--start-at-byte` | N | Skip N-1 bytes and resume at byte N exactly (the first record may be torn) |

A raw byte offset almost never lands on a record boundary. `--rec-after-byte`
handles that by letting the stream discard the straddled record (using the
active record delimiter, so CRLF / paragraph / char-class all resync
correctly); `--start-at-byte` does not — it resumes at the exact byte, by
design, for when you want byte-precise positioning.

Because the skipped region is never parsed, record *numbers* after a seek are
relative to the seek point, not the true start of input. When `--number` is
combined with either seek, the counter is **tilde-prefixed** (`~1`, `~2`, …) to
flag that the numbering is seek-relative.

### Position (mutually exclusive with the other axes)

| Long | Argument | Meaning |
|------|----------|---------|
| `--first` | N | Keep the first N records of the current window |
| `--last` | N | Keep the last N records of the current window |
| `--from` | N | Start at record N (1-indexed, inclusive) |
| `--to` | N | End at record N (inclusive) |

Any **two** of these four may be combined; combining three or more is rejected,
because every such combination is reducible to a plain `--from/--to` range and
only invites confusion:

```
$ lens --first 2 --last 1 --from 1 file
lens: combine at most two of --first/--last/--from/--to        (exit 1)
```

Values must be positive integers (records are 1-indexed); `--first 0` or a
non-numeric value is rejected. A `--from` greater than `--to` is rejected as an
empty range. When `--first` and `--last` are combined, the **larger value is
the outer window** — command-line order does not matter (see EXAMPLES).

### Match (mutually exclusive with the other axes)

| Short | Long | Argument | Meaning |
|-------|------|----------|---------|
| `-m` | `--match` | PATTERN | Keep records matching PATTERN (repeatable) |
| `-v` | `--no-match` | PATTERN | Keep records NOT matching PATTERN (repeatable) |
| `-A` | `--and` | — | All predicates must pass (default) |
| `-O` | `--or` | — | Any one predicate passing is enough |

PATTERN is a bash extended regular expression. `--and`/`--or` require at least
one `--match` or `--no-match`.

### Fields (mutually exclusive with the other axes)

| Long | Argument | Meaning |
|------|----------|---------|
| `--fields` | SPEC | Emit the named fields of each record |

SPEC is a comma list of 1-based indices and ranges: `1`, `1,3`, `1,3-5`,
`2-4,7`. Fields are emitted in the order listed, so a comma list can **reorder**
columns (`--fields 3,1` emits field 3 then field 1). Ranges are ascending only;
a descending range (`3-1`) is rejected as an error (a transposed typo), so
reverse or reorder with an explicit list (`5,4,3`).

Field delimiter (choose at most one; defaults to whitespace-collapse):

| Short | Argument | Meaning |
|-------|----------|---------|
| `-f` | CHARS | Character set, non-stacking — empties preserved (cut-style) |
| `-F` | STRING | Exact multi-character delimiter |
| `-W` | CHARS | Character class, runs collapse (awk-style) |

#### Literals in the spec

Any spec token that is **not** a valid column reference (not a positive integer
or ascending range) is emitted **verbatim as a literal**, in its position among
the columns. This makes labels and separators trivial to interleave:

```bash
lens --fields '1,=>,3' -f : data        # field1, the text "=>", field3
lens --chars '1-3,. ,5-7' file          # chars 1-3, the text ". ", chars 5-7
```

An empty input field is preserved as an empty value; an empty spec token
(`1,,3`) is likewise a literal empty.

To force a token that *looks* like a column spec to be a literal, or to embed
the spec separator inside a literal, use a backslash escape (single-quote it at
the shell so one backslash reaches lens):

```bash
lens --fields '1,\4,3' -f , --ofs ''    # literal "4", not column 4  → a4c
lens --fields '1,x\,y,3' -f , --ofs ''  # literal "x,y" (escaped comma)
```

`\<sep>` is a literal separator character and `\\` a literal backslash; any
token containing an escape is treated as a literal regardless of its shape.

#### Changing the spec separator: `--spec-sep CHAR`

The spec token separator defaults to comma. `--spec-sep CHAR` changes it, so
commas inside literals need no escaping:

```bash
lens --fields '1;2,5;3' -f , --spec-sep ';'   # col1, literal "2,5", col3
```

CHAR must be a single character and cannot be `-` (the range operator), `\`
(the escape), or a digit (which would shadow a column number).

### Chars (mutually exclusive with the other axes)

| Long | Argument | Meaning |
|------|----------|---------|
| `--chars` | SPEC | Emit the named character positions of each record |

Same SPEC grammar as `--fields`, addressing characters within each record.
Useful for fixed-width data. Literals and `--spec-sep` work the same way (chars
mode concatenates with no separator between elements, so a literal sits
directly between the character groups).

### Output delimiters

By default the **output field separator matches the input field delimiter**, so
fields are reproduced as they came in. Override it to convert formats. The
output is built by joining every emitted element — columns *and* literals
alike — with the OFS.

| Long | Argument | Meaning |
|------|----------|---------|
| `--ofs` / `--field-sep` | STR | Output field separator (default: the input field delimiter) |
| `--ors` / `--rec-sep` | STR | Output record terminator (default: newline) |

Both accept an explicit empty string (`--ofs ''`) — distinguished from being
omitted — to abut elements with no separator, which is how you hand-build output
with literals. When the input is split by a character *class* or
*collapse* delimiter (`-f` with multiple chars, or `-W`), there is no single
delimiter to echo back, so lens **requires an explicit `--ofs`** rather than
silently guessing; omitting it is an error.

### Inversion

| Short | Long | Meaning |
|-------|------|---------|
| `-X` | `--not` | Invert the final selection, in any mode |

In fields/chars mode, `--not` emits the complement (every field/char *except*
those named).

### Record delimiter (choose at most one; default is newline)

| Short | Argument | Meaning |
|-------|----------|---------|
| `-d` | CHAR | Single-character record delimiter |
| `-D` | STRING | Multi-character record delimiter (exact match) |
| `-E` | CHARS | Character-class delimiter (any char in the set ends a record) |

### Formatting

| Short | Long | Meaning |
|-------|------|---------|
| `-n` | `--number` | Prepend the 1-based record number (tab-separated) |
| `-c` | `--count` | Emit a count of selected records instead of their content |
| `-H` | `--prefix` | Prefix each output line with its filename (grep-style) |

`-c` and `-n` are mutually exclusive (a count has nothing to number).

### Help

| Short | Long | Meaning |
|-------|------|---------|
| `-h` | `--help` | Compact synopsis |
| | `--options` | Full options reference |
| | `--examples` | Cookbook |
| | `--about` | About lens |
| | `--boop` | About the boop framework |

## EXAMPLES

### Replacing head / tail / wc

```bash
lens --first 20 file.txt              # head -20
lens --last 20 file.txt               # tail -20
lens -c file.txt                      # wc -l (count all records)
lens --not --first 1 file.txt         # everything but the header line
```

### Slicing by line range

```bash
lens --from 5 --to 15 file.txt        # lines 5-15 (sed -n '5,15p')
lens --from 8 file.txt                # line 8 to end (tail -n +8)
lens --to 3 file.txt                  # first 3 lines
lens --not --from 20 --to 50 file.txt # everything outside lines 20-50
```

### Combining two position options

Each position option is a separate constraint on the same window:

- `--from X` — ignore records before X
- `--to Y` — ignore records after Y
- `--first A` — keep the first A of the records still in view
- `--last B` — keep the last B of the records still in view

```bash
lens --from 2 --first 2 file.txt      # 2 records starting at 2  → lines 2-3
lens --to 4 --last 2 file.txt         # last 2 of lines 1-4      → lines 3-4
lens --from 10 --to 50 file.txt       # lines 10-50
```

The unintuitive pair is `--first A --last B` together. Read it as two steps,
**outer window first, then inner**: the *larger* value defines the outer window,
and the smaller selects from within it. Command-line order does not matter.

```bash
lens --first 20 --last 5 file.txt     # step 1: first 20 (lines 1-20)
                                       # step 2: last 5 of those → lines 16-20
lens --last 20 --first 5 file.txt     # step 1: last 20 (e.g. lines 81-100)
                                       # step 2: first 5 of those → lines 81-85
```

So `--first 20 --last 5` and `--last 5 --first 20` are identical: 20 is the
outer window either way. If you find yourself reaching for a third position
option, you want a plain `--from/--to` range instead (and lens will tell you so).

### Replacing grep

PATTERN is a full POSIX extended regular expression (bash `[[ =~ ]]`), not just
a fixed string — anchors, wildcards, alternation, grouping, and character
classes all work:

```bash
lens --match ERROR log.txt                    # grep ERROR  (substring)
lens -m ERROR log.txt                         # same, short form
lens -m '^ERROR' log.txt                       # anchored at line start
lens -m 'WARN|ERROR' log.txt                   # alternation
lens -m '[0-9]{3}-[0-9]{4}' log.txt            # a phone-number-ish pattern
lens -m 'user_(id|name)' log.txt               # grouping
lens --no-match DEBUG log.txt                 # grep -v DEBUG
lens -v DEBUG log.txt                          # same, short form
lens --count --match ERROR log.txt            # grep -c ERROR
lens --not --match ERROR log.txt              # everything that isn't ERROR
lens --and -m foo -v bar log.txt              # has foo, lacks bar
lens --or  -m error -m warn log.txt           # error OR warn
```

### Replacing cut / awk field selection

```bash
lens --fields 1,3-5 -f : /etc/passwd  # cut -d: -f1,3-5
lens --fields 1,3 -W ' ' log.txt      # awk '{print $1, $3}' (whitespace collapse)
lens --fields 2 -F '||' data.txt      # split on a literal "||" with one flag
lens --not --fields 2 -f , data.csv   # every column except column 2
```

`-F` splits on a multi-character literal directly from a flag. awk can do this
too, but only by setting `FS` to a string or regex in a program (`awk -F'\\|\\|'
'{print $2}'`); lens makes it a single option.

### Reordering fields

Field order follows the SPEC, so a comma list can reorder columns — list the
indices in the order you want them emitted:

```bash
lens --fields 3,1 -f : data.txt       # field 3, then field 1
lens --fields 3,1,2 -f : data.txt     # rotate: 3, 1, 2
```

Ranges (`3-5`) are ascending only; a descending range like `3-1` is **rejected
as an error** (almost always a transposed typo). To reverse or reorder, use an
explicit comma list (`5,4,3`). To use `N-M` as literal *text*, escape any part
of it (`3\-1`) so it is treated as a literal rather than a range.

### Inserting literals and converting formats

```bash
# Insert a literal label/separator between columns
lens --fields '1,: ,2' -f , data.csv         # "field1: field2"

# Convert delimiter: read colon-separated, write CSV
lens --fields '1,2,3' -f : --ofs , /etc/passwd

# Read paragraph-mode records, emit one CSV line each
lens --fields '1,2' -D '' --ofs , notes.txt

# Hand-build output with --ofs '' and literals (escape the comma)
lens --fields '1,\,,2,\,,3' -f : --ofs '' data    # "f1,f2,f3"

# Avoid escaping by changing the spec separator
lens --fields '1; , ;2' -f : --spec-sep ';' --ofs '' data   # "f1 , f2"
```

### Custom output record separator (--ors / --rec-sep)

`--ors` (alias `--rec-sep`) overrides the newline that normally terminates each
output record. Combine it with `--fields` to reformat output for pipelines that
expect a different delimiter:

```bash
# Emit usernames tab-separated on one line
lens --fields 1 -f : --ors $'\t' /etc/passwd

# --rec-sep is identical; choose whichever reads more clearly
lens --fields 1 -f : --rec-sep $'\t' /etc/passwd

# NUL-delimited output for xargs -0 (safe with filenames containing spaces)
lens --match '\.log$' filelist.txt --ors $'\0' | xargs -0 gzip
```

### Scanning the tail of a large file (byte-seek)

```bash
# Skip ~8MB of an 8MB log, then read the last records cleanly
lens --rec-after-byte 8000000 --last 50 huge.log

# Same idea on a pipe (no seekable file needed)
producer | lens --rec-after-byte 100000 --match ERROR

# Count records in the tail section (no tilde prefix with --count)
lens --rec-after-byte 8000000 --count huge.log

# Byte-exact positioning (first record may be torn)
lens --start-at-byte 4096 --first 3 data.bin

# Numbering after a seek is tilde-flagged as seek-relative
lens --rec-after-byte 1000 --first 3 --number log     # ~1, ~2, ~3
```

### Fixed-width columns

```bash
lens --chars 1-10,20-30 data.txt      # characters 1-10 and 20-30 of each line
lens --chars 1,5,10 fixed.txt         # individual character positions
```

### Non-line records

```bash
lens -D '' --match ERROR app.log      # paragraph mode (blank-line separated)
lens -D $'\r\n' --first 5 win.log     # CRLF records
lens -E $'\r\n' -c file.txt           # count records ending in CR or LF
```

### Multiple files

Files are processed independently (like head/tail/grep), not concatenated:

```bash
lens --first 5 a.log b.log            # first 5 of each, with ==> name <== headers
lens --match ERROR -H a.log b.log     # grep-style filename:line output
lens --count --match ERROR *.log      # per-file counts plus a grand total
```

### Composing axes with pipes

```bash
lens --last 100 app.log | lens -m error      # errors among the last 100 lines
lens -m error app.log | lens --fields 1,4    # fields 1 and 4 of matching lines
```

## EXIT STATUS

- **0** — completed; matching records (or a count) were written.
- **1** — invalid usage: conflicting axes, an out-of-range option combination,
  a non-positive position value, a `--from` past `--to`, or an unreadable file.

Errors print a single diagnostic line beginning with `lens:`.

## NOTES

lens is pure bash, built on the **boop** framework's `Stream` and `Args`
classes. It began as a thought experiment — how far can an OOP standard library
in bash be pushed? — and it will never be competitive on speed with the C tools
it imitates (`grep`, `cut`, and friends fork once and run native code). What it
offers instead is reach and features: it runs anywhere **bash 4.3+** is present
— stripped containers, minimal images, locked-down hosts where installing GNU
coreutils is not an option — and it folds multi-character delimiters, paragraph
mode, character-class splitting, and one-axis composition into a single
consistent interface.

For repeated use, bundle lens with `collider` (`collider lens` → `bundle-lens`):
a bundle loads the framework from one file in a single pass, avoiding the
per-invocation source cost of the development script.

### Streaming

Position and match modes stream record by record. `--last N` with no `--to`
bound uses a fixed-size circular buffer holding only the trailing N records, so
memory stays bounded on inputs of any size.

## SEE ALSO

`head(1)`, `tail(1)`, `grep(1)`, `cut(1)`, `wc(1)`, `awk(1)` — the tools lens
consolidates. [docs/Stream.md](Stream.md) for the delimiter engine,
[docs/tools.md](tools.md) for the tool family, and `lens --examples` for the
built-in cookbook.

---

[↑ Site map](index)
