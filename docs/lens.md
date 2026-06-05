# lens(1)

## NAME

**lens** — inspect, filter, and slice text streams

## SYNOPSIS

```
lens [--first N] [--last N] [--from N] [--to N] [--not] [FORMAT] [DELIM] [FILE...]
lens (--match PAT | --no-match PAT)... [--and | --or] [--not] [FORMAT] [DELIM] [FILE...]
lens --fields SPEC [-f|-F|-W DELIM] [--not] [FORMAT] [DELIM] [FILE...]
lens --chars SPEC [--not] [FORMAT] [DELIM] [FILE...]
lens (-h | --help | --options | --examples | --about | --boop)
```

Where:
- **FORMAT** is any of `-n`/`--number`, `-c`/`--count`, `-H`/`--prefix`
- **DELIM** sets the record delimiter: `-d CHAR`, `-D STRING`, or `-E CHARS`
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
columns (`--fields 3,1` emits field 3 then field 1). Ranges are ascending only
(`3-1` selects nothing); reverse or reorder with an explicit list. The output
separator is derived from the input field delimiter (the exact string for `-F`,
the first character for `-f`/`-W`, otherwise a space).

Field delimiter (choose at most one; defaults to whitespace-collapse):

| Short | Argument | Meaning |
|-------|----------|---------|
| `-f` | CHARS | Character set, non-stacking — empties preserved (cut-style) |
| `-F` | STRING | Exact multi-character delimiter |
| `-W` | CHARS | Character class, runs collapse (awk-style) |

### Chars (mutually exclusive with the other axes)

| Long | Argument | Meaning |
|------|----------|---------|
| `--chars` | SPEC | Emit the named character positions of each record |

Same SPEC grammar as `--fields`, addressing characters within each record.
Useful for fixed-width data.

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

Ranges (`3-5`) are ascending only; a "descending range" like `3-1` selects
nothing. To reverse or reorder, use an explicit comma list (`5,4,3`), not a
range.

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
