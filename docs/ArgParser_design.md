# Argument Parsing — Design Summary

## Two Tools, One Engine

### `ArgParser` — boop class
Standard boop object. Proper `into=` returns, query via `$args.get`.
Used in constructors and methods. Never touches the caller's scope directly.

```bash
into=args ArgParser '
  o|option:$option
  r|required:$_required
  a|array:@array
' "$@"
$args.get option
$args.get required
```

### `CLI::Args` — sourceable script convenience
The "naughty" version. Sources directly into the calling script's scope,
declares variables, rewrites `"$@"`. Designed for script authors, not library authors.

```bash
. CLI::Args '
  o|option:$option
  r|required:$_required
  a|array:@array
' '
  use: ${0##*/} {-r someVal} [-o value] [-a item]...

  Detailed usage instructions here.
' "$@"
```

Both tools share the same parsing engine. `CLI::Args` sources `boop` internally
if not already loaded — works standalone, uses existing framework if present.

---

## The `CLI::` Namespace

A "batteries included" layer for script writers. Opinionated, convenient,
always prints to stdout, may call `exit` on bad input — things a well-behaved
library would never do unilaterally.

```
boop/
  boop              — framework
  ArgParser         — proper boop class
  Math              — arbitrary precision class
  ...
  CLI/
    CLI::Args       — declares vars, rewrites $@, generates --help
    CLI::Math       — always printfs, wraps Math.DO
    CLI::Table      — formatted tables from arrays/maps (future)
    ...
```

`CLI::` tools are bonuses for installing boop, not framework primitives.

---

## Declaration Syntax

```
synonyms:$varName
```

- Synonyms are `|`-delimited
- Single character → short option (`-o`)
- Multiple characters → long option (`--option`)
- Multiple synonyms are all equivalent: `o|O|option|OPTION:$name`
- No `:$varName` → use first synonym as variable name

---

## Type Sigils

| Sigil | Type | Behavior |
|-------|------|----------|
| `$name` | scalar | Flag (bool) if no value given; string if value given; error if repeated |
| `$_name` | required scalar | Same, but missing at end of parse → error + help |
| `@name` | array | Stacks every occurrence |
| `@_name` | required array | Same, but at least one occurrence required |
| `%name` | map | Each occurrence is bool key or `k=v`; error on repeated keys |
| `%_name` | required map | Same, but at least one entry required |

---

## File Loading — The `<` Prefix

`<` before the sigil means the argument value is a filename to load from.

| Declaration | Delimiter | CLI usage | Behavior |
|-------------|-----------|-----------|----------|
| `<$name` | n/a | `-x file` | Slurp entire file into scalar |
| `<@name` | n/a | `-x file` | Load rows into array (newline-split) |
| `<%name` | `=` (default) | `-x file` | Load rows into map, split on `=` |
| `<%name:` | `:` | `-x file` | Load rows into map, split on `:` |
| `<%name:foo` | `:` | (none) | Always load from `foo`, split on `:` |
| `<%name=foo` | `=` | (none) | Always load from `foo`, split on `=` |

**Delimiter rule:** any non-identifier character after the sigil+name is the
delimiter. If followed by a non-empty string, that string is a hardcoded filename
and no CLI argument is accepted for this option.

**Required + file (`<$_name`):** the CLI argument must be given, the file must
exist, and must be non-empty.

**Lazy loading:** TBD — possible sigil `<+` for deferred/optional file loads.

---

## Map Runtime Assignment

At runtime (non-file), maps accept `k=v` pairs:

```bash
-m a=1      # loads value 1 into key a of map
-m a        # loads boolean true into key a of map
```

The delimiter in the declaration applies to file loading only; runtime
assignment always uses `=` unless overridden. Repeated keys are an error.

---

## Positional Arguments

Undeclared arguments are not errors — they are collected as positionals.

- `__args_original` — the untouched original `"$@"` as received
- `"$@"` is rewritten after parsing to contain only unconsumed (positional) arguments

No special declaration needed for positionals — they're whatever's left
after all declared options are consumed.

---

## Help Screen

If a usage string is provided as the second argument, it is used verbatim
for `--help` output. If not provided, a usage screen is auto-generated from
the declarations.

If both are provided and they disagree (e.g., a required arg appears optional
in the usage string), the whole thing bails at startup — the declaration is
always authoritative.

`CLI::Args` handles `--help` / `-h` automatically, printing the help screen
and calling `exit 0`.

---

## Example

```bash
. CLI::Args '
  v|verbose:$verbose
  o|output:$_output
  f|file:<@_files
  t|tag:%tags
  n|dry-run:$dryRun
' '
  use: ${0##*/} {-o outfile} {-f file}... [-v] [-t k=v]... [-n] [args...]

  -o, --output    Output file (required)
  -f, --file      Input files (required, may repeat)
  -v, --verbose   Enable verbose output
  -t, --tag       Key=value tags (may repeat)
  -n, --dry-run   Dry run, no changes made
' "$@"

# After sourcing:
# $verbose    — "1" or "" (flag)
# $output     — required string value
# ${files[@]} — array of input files (loaded from paths given)
# ${tags[k]}  — associative array of tags
# $dryRun     — "1" or ""
# $@          — remaining positional arguments
# $__args_original — original unmodified argument list
```

---

## Status

Design phase. `@@` Not yet implemented.
Prerequisite: `ArgParser` boop class design finalized first.
`CLI::Args` shares the same parsing engine — implement engine once,
wrap differently for each consumer.
