# lens — Text Stream Inspection

One tool for the work usually split across `head`, `tail`, `grep`, `cut`, and
`wc`. lens reads a stream (stdin or files), selects records along a single
axis, and formats what survives. It speaks the same multi-character and
character-class delimiters as the Stream class it is built on, so paragraph
mode, CRLF records, and awk-style field splitting are all in reach.

Built on `Stream` and `Args`. Pure bash — no external tools.

---

## Quick Start

```bash
lens --first 20 file.txt              # head -20
lens --last 20 file.txt               # tail -20
lens --match ERROR log.txt            # grep ERROR
lens --no-match DEBUG log.txt         # grep -v DEBUG
lens --fields 1,3-5 -f : /etc/passwd  # cut -d: -f1,3-5
lens --count --match ERROR log.txt    # grep -c ERROR
```

Help is layered: `lens --help` for the synopsis, `lens --options` for the full
reference, `lens --examples` for a cookbook, `lens --about` / `lens --boop` for
background.

---

## The One-Axis Rule

lens filters along exactly **one axis per invocation**. The axes are mutually
exclusive — you cannot mix position with match, or fields with chars, in a
single call. To combine them, use a pipe: each stage does one thing.

```bash
lens --last 100 app.log | lens --match error    # errors in the last 100 lines
lens --match error app.log | lens --fields 1,4  # fields 1,4 of matching lines
```

This keeps each invocation's behavior unambiguous and composes cleanly. The
exclusivity is enforced by the Args schema; violating it is a hard error.

| Axis | Options | Notes |
|------|---------|-------|
| Position (relative) | `--first N`, `--last N` | Combinable with each other |
| Position (absolute) | `--from N`, `--to N` | Combinable with each other |
| Match | `--match PAT`, `--no-match PAT` | Repeatable; `--and`/`--or` |
| Fields | `--fields SPEC` | With a field delimiter |
| Chars | `--chars SPEC` | Character positions |

Relative and absolute position are also mutually exclusive with each other.

---

## Position (relative): `--first`, `--last`

`--first N` keeps the first N records; `--last N` keeps the last N. They are
combinable, and **argument order is pipeline order** — the left one is applied
first, then the right one selects from that result.

```bash
lens --first 20 file.txt              # first 20
lens --last 5 file.txt                # last 5
lens --first 20 --last 5 file.txt     # last 5 OF the first 20 → lines 16-20
lens --last 20 --first 5 file.txt     # first 5 OF the last 20
```

`--last` with no upper bound streams through a fixed-size circular buffer, so
it does not hold the whole input in memory — only the trailing N records.

---

## Position (absolute): `--from`, `--to`

`--from N` starts at record N (1-indexed, inclusive); `--to N` ends at record N
(inclusive). Either may be omitted.

```bash
lens --from 5 --to 15 file.txt        # lines 5-15
lens --from 8 file.txt                # line 8 to end
lens --to 3 file.txt                  # first 3 lines
```

---

## Match: `--match`, `--no-match`

Content filtering with bash regular expressions. Both flags are repeatable.

- `--match PAT` keeps records matching PAT.
- `--no-match PAT` keeps records NOT matching PAT.
- `--and` (default) requires all predicates to pass.
- `--or` passes a record if any predicate passes.

```bash
lens --match ERROR log.txt                    # grep
lens --no-match DEBUG log.txt                 # grep -v
lens --and --match foo --no-match bar log.txt # foo present AND bar absent
lens --or --match error --match warn log.txt  # error OR warn
```

`--and`/`--or` require at least one `--match` or `--no-match` (enforced by the
schema's `[Requires]` rule).

---

## Fields: `--fields SPEC`

Column extraction by field number. SPEC is a comma list of 1-based indices and
ranges: `1`, `1,3`, `1,3-5`, `2-4,7`.

```bash
lens --fields 1,3-5 -f : /etc/passwd  # cut -d: -f1,3-5
lens --fields 1,3 -W ' ' log.txt      # awk-style whitespace collapse
lens --fields 2 -F '||' data.txt      # multi-char field delimiter
```

The output field separator is derived from the input delimiter (the exact
string for `-F`, the first character for `-f`/`-W`, otherwise a space).

### Field delimiters

| Flag | Meaning |
|------|---------|
| `-f CHARS` | Char set, non-stacking (empties preserved, cut-style) |
| `-F STRING` | Exact multi-character string |
| `-W CHARS` | Char class, runs collapse (awk-style) |

If none is given in fields mode, lens defaults to whitespace collapse (`-W ' '`).

---

## Chars: `--chars SPEC`

Character-position extraction, same SPEC grammar as `--fields` but addressing
characters within each record. Useful for fixed-width data.

```bash
lens --chars 1-10,20-30 data.txt      # columns 1-10 and 20-30
lens --chars 1,5,10 fixed.txt         # individual character positions
```

---

## Inversion: `--not`

`--not` inverts the final selection in **any** mode — position, match, fields,
or chars. In fields/chars mode it emits the complement (every field/char
*except* those named).

```bash
lens --not --first 1 file.txt          # skip the header line
lens --not --from 20 --to 50 file.txt  # everything outside lines 20-50
lens --not --match ERROR log.txt       # everything that isn't an ERROR line
lens --not --fields 2 -f , data.csv    # all fields except field 2
```

---

## Record delimiters

By default a record is a line. Override with one of:

| Flag | Meaning |
|------|---------|
| `-d CHAR` | Single-character record delimiter |
| `-D STRING` | Multi-character record delimiter (exact match) |
| `-E CHARS` | Char-class delimiter (any char in the set ends a record) |

```bash
lens -D '' --match ERROR app.log      # paragraph mode (blank-line separated)
lens -D $'\r\n' --first 5 win.log     # CRLF records
lens -E $'\r\n' --count file.txt      # CR or LF ends a record
```

---

## Formatting

| Flag | Effect |
|------|--------|
| `-n`, `--number` | Prepend the record number (tab-separated) |
| `-c`, `--count` | Emit a count of selected records instead of their content |
| `-H`, `--prefix` | Prefix each output line with its filename (grep-style) |

```bash
lens --first 3 --number file.txt      # 1<TAB>line1 …
lens --count --match ERROR log.txt    # just the number
```

---

## Input sources

lens reads stdin by default. Provide files as positional arguments, or name
one explicitly with `-P FILE`. `-u FD` reads from an open file descriptor.

```bash
lens --match ERROR log.txt            # file argument
lens -P log.txt --match ERROR         # explicit -P
cat log.txt | lens --match ERROR      # stdin
```

### Multiple files

Multiple files are processed **independently** — like `head`/`tail`/`grep`,
not concatenated. `--first 5 a b` gives the first 5 of each.

```bash
lens --first 5 a.log b.log            # first 5 of each, with ==> name <== headers
lens --match ERROR -H a.log b.log     # grep-style filename:line output
lens --count --match ERROR *.log      # per-file counts plus a grand total
```

---

## Options Reference

```
Input:
  -P, --file PATH         Input file (default: stdin)
  -u, --fd N              Read from an open file descriptor

Position (relative):
      --first N           First N records
      --last N            Last N records

Position (absolute):
      --from N            Start at record N (1-indexed, inclusive)
      --to N              End at record N (inclusive)

Match:
  -m, --match PATTERN     Keep records matching PATTERN (repeatable)
  -v, --no-match PATTERN  Keep records NOT matching PATTERN (repeatable)
  -A, --and               All predicates must pass (default)
  -O, --or                Any predicate passing is enough

Inversion:
  -X, --not               Invert the final selection

Column extraction:
      --fields SPEC       Field numbers/ranges: 1,3-5
      --chars SPEC        Character positions/ranges: 1-10,20-30

Record delimiter (mutually exclusive; default: newline):
  -d CHAR                 Single-char record delimiter
  -D STRING               Multi-char record delimiter (exact)
  -E CHARS                Char-class record delimiter

Field delimiter (for --fields):
  -f CHARS                Char set, non-stacking (empties preserved)
  -F STRING               Exact multi-char string
  -W CHARS                Char class, runs collapse (awk-style)

Formatting:
  -n, --number            Prepend record numbers
  -c, --count             Emit total count instead of content
  -H, --prefix            Prefix output lines with the filename

Help:
  -h, --help              Compact synopsis
      --options           Full options reference
      --examples          Cookbook
      --about             About lens
      --boop              About the boop framework
```

---

## Design Notes

### Why one axis at a time

Tools that try to be head *and* grep *and* cut in a single pass accumulate flag
interactions that nobody can predict. lens sidesteps that: each invocation has
exactly one selection model, so its behavior is always obvious. Pipes compose
the axes, and a pipe of two lens calls is still cheaper to reason about than a
single call with six interacting flags.

### Streaming, not slurping

Position and match modes stream record-by-record. `--last N` (with no absolute
bound) uses a fixed-size circular buffer sized to N, so memory stays bounded
even on huge inputs — it never holds more than the trailing N records plus the
current one. The `--not` variant of "first K of last N" emits records as they
are evicted from the buffer, so it streams too.

### Delimiters come from Stream

lens does not reimplement record/field splitting — it passes the delimiter
flags straight through to a `Stream` object and lets the class do the work.
That is why paragraph mode, CRLF, char-class, and multi-char delimiters all
work consistently: they are Stream features, surfaced on the command line.

### Performance

Run from a boopRoot checkout, each `lens` invocation re-sources the whole
framework, which dominates startup cost. For repeated use, bundle it with
`collider` (`collider lens` → `bundle-lens`) — a bundle loads everything from
one file in a single pass. The test suite (`tests/tools/test_lens`, 38
assertions) takes about two minutes unbundled for exactly this reason.
