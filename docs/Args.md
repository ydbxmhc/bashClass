# Args -- CLI Argument Parser

A complete command-line argument parser for bash scripts. Two entry
points: a lightweight `getopts` wrapper for simple scripts, and a
full GNU-style long-option + subcommand parser for complex CLIs.

Both operate in the caller's scope by default (setting variables
directly), or return a Config object when used with `into=`.

## Contents

- [Quick Start](#quick-start)
- [Args.getOpts](#argsgetopts)
  - [Signature](#signature)
  - [Behavior](#behavior)
  - [Example](#example)
- [Args.parse](#argsparse)
  - [Signature](#signature-1)
  - [Schema Format](#schema-format)
    - [Sections](#sections)
    - [Option Line Syntax](#option-line-syntax)
    - [Subcommand Line Syntax](#subcommand-line-syntax)
  - [Examples](#examples)
  - [Option Processing Rules](#option-processing-rules)
  - [After Parsing (Scope-Write Mode)](#after-parsing-scope-write-mode)
  - [After Parsing (Object Mode)](#after-parsing-object-mode)
  - [Args.given -- was an option supplied?](#argsgiven---was-an-option-supplied)
  - [Error Handling](#error-handling)
- [Help Generation (Planned)](#help-generation-planned)
- [Subcommand Option Isolation (Planned)](#subcommand-option-isolation-planned)
- [Design Notes](#design-notes)
  - [Why Not Just Use getopts?](#why-not-just-use-getopts)
  - [Why Schema-as-String?](#why-schema-as-string)
  - [Scope-Write vs Object Mode](#scope-write-vs-object-mode)
  - [Variable Naming](#variable-naming)

---

## Quick Start

```bash
. boop Args

# Simple: POSIX short options
Args.getOpts ":vf:o:" "$@"
shift $((OPTIND-1))
# $v = "1" if -v was passed
# $f = value of -f
# $o = value of -o
# $@ = remaining positionals

# Full: GNU long options + subcommands
Args.parse '
[Use]
  myapp [options] COMMAND [args...]

[Options]
  verbose | v                    # boolean flag
  output  | o = /tmp/out.txt    # value with default
  : token | t =                 # required, value-taking

[Subcommands]
  deploy  | d                   # subcommand with alias
  status  | s

[deploy]
  workers | w = 4               # deploy-specific option
' "$@"

# After parsing:
printf "verbose=%s token=%s output=%s\n" "$verbose" "$token" "$output"
printf "action=%s\n" "$_Action"
set -- "${_ArgsRemaining[@]}"   # restore positionals
```

---

## Args.getOpts

Thin wrapper around bash's built-in `getopts`. Parses POSIX short
options and sets a variable per recognized option.

### Signature

```bash
Args.getOpts optstring "$@"
```

### Behavior

- Follows standard `getopts` optstring conventions
- Leading `:` in optstring enables silent error mode
- A letter followed by `:` means that option takes a value
- Boolean options (no `:`) get the value `"1"` when present
- Value-taking options get the argument value
- Unknown option or missing required value: `_Crash`
- Sets `$__Args_orig` to the original argument array
- Caller MUST run `shift $((OPTIND-1))` after to consume processed args

### Example

```bash
Args.getOpts ":vf:o:" "$@"
shift $((OPTIND-1))

[[ "$v" == "1" ]] && printf "verbose mode\n"
printf "file: %s\n" "$f"
printf "remaining: %s\n" "$*"
```

---

## Args.parse

Full GNU-style argument parser with long options, short options,
option clustering, subcommands, required options, defaults, and
`--` termination.

### Signature

```bash
Args.parse 'schema' "$@"           # scope-write mode
into=obj Args.parse 'schema' "$@"  # object mode
```

### Schema Format

The schema is an INI-style string. Sections are marked with `[Name]`.
Everything to the right of `#` on a line is a comment (ignored by the
parser, useful as inline documentation).

#### Sections

| Section | Purpose |
|---------|---------|
| `[Use]` | Synopsis/usage text. Documentation only, not parsed. |
| `[Options]` | Global options available regardless of subcommand. |
| `[Subcommands]` | Valid subcommand names and their aliases. |
| `[SubcmdName]` | Options specific to a named subcommand. |

#### Option Line Syntax

```
[: ] varName [| alias ...] [= [default]]
```

| Element | Meaning |
|---------|---------|
| Leading `:` | Option is required. Parse crashes if not provided. |
| `varName` | The bash variable name to set. Must be a valid identifier (no hyphens). |
| `\| alias` | Additional CLI names. Single char = `-x`. Multi char = `--name`. Hyphens allowed in aliases. |
| `= default` | Option takes a value. If not provided on CLI, uses `default`. |
| `=` (no default) | Option takes a value. If not provided, variable is empty string. |
| (no `=`) | Boolean flag. Absent = `""`, present = `"1"`. |

#### Subcommand Line Syntax

```
canonicalName [| alias ...]   # description
```

First entry is the canonical name (stored in `$_Action`). Additional
entries are CLI aliases that resolve to the same canonical name.

### Examples

```bash
# Boolean flag
verbose | v                    # -v or --verbose -> $verbose="1"

# Value with default
output | o = /tmp/out.txt      # --output file or -o file -> $output

# Required value (no default)
: token | t =                  # --token X or -t X -> $token (crashes if missing)

# Required value with explicit default (unusual but valid)
: config | c = ./config.yml    # still required on CLI despite default shown

# Multiple aliases
log_level | log-level | l =    # --log-level X or --log_level X or -l X
```

### Option Processing Rules

1. `--name value` or `--name=value` -- long option with value
2. `--flag` -- long boolean (no `=`, no following value consumed)
3. `-x value` -- short option with value
4. `-xVALUE` -- short option with value attached (no space)
5. `-abc` -- short option clustering: `-a -b -c` (all boolean)
6. `-abcVALUE` -- cluster where last option takes a value
7. `--` -- terminates option processing; everything after is positional
8. First non-option positional matching a subcommand name becomes `$_Action`
9. All other positionals go into `$_ArgsRemaining`

### After Parsing (Scope-Write Mode)

| Variable | Contents |
|----------|----------|
| `$varName` | Value for each declared option (value, default, or `""`) |
| `$_Action` | Canonical subcommand name, or `""` if none matched |
| `$_ArgsRemaining` | Array of unconsumed positional arguments |
| `$__Args_orig` | Array of the original arguments before parsing |

To restore `$@` after parsing:
```bash
set -- "${_ArgsRemaining[@]}"
```

### After Parsing (Object Mode)

When called with `into=`, returns a Config object instead of setting
scope variables. Requires Config class to be available.

```bash
into=opts Args.parse "$schema" "$@"
into=v $opts.get verbose
into=a $opts.get _action
into=r $opts.get _remaining
```

Scope variables are NOT set in object mode. The Config object owns
all the parsed state.

### Args.given -- was an option supplied?

After a scope-write parse, an omitted scalar and one given an empty value both
leave `$varName` empty, so the value alone cannot tell them apart. `Args.given`
answers the "was it actually supplied?" question:

```bash
Args.parse '
[Options]
ofs =
' "$@"

if Args.given ofs; then
  printf 'output separator explicitly set to [%s]\n' "$ofs"
else
  printf 'using the default separator\n'
fi
```

The argument is the option's **variable name** (the first name in its schema
line), not a CLI alias. It returns exit 0 if the option was supplied on the
command line — with any value, including empty — and exit 1 otherwise. It works
for every option type (scalar, boolean, array, map).

**Persistence and the intended model.** The seen-record persists across parses
for the life of the process. This is deliberate: the intended use is a single
script-argv parse, and constructors (e.g. `Stream.new`) often run their *own*
`Args.parse` internally — a fresh-each-time table would let those nested parses
erase the script's record before you could query it. Persistence means
`Args.given` still answers correctly after you have built such objects.

The trade-off is that `Args.given` is **cumulative**: an option supplied to any
earlier parse keeps reporting as given. For the intended one-parse-per-process
model this is a non-issue. Repeated independent parsing belongs to object mode
(where each object owns its own state), not to repeated top-level `Args.parse`.

(Duplicate-option detection is *not* affected by this persistence — it uses a
separate per-parse table, so giving the same option in two separate parses is
not a "duplicate" error.)

### Error Handling

All errors crash with a descriptive message:

- `"Args.parse: unknown option: --badname"` -- unrecognized option
- `"Args.parse: --token requires a value"` -- value-taking option with no value
- `"Args.parse: --flag is a boolean flag, does not take a value"` -- `--flag=x` on a boolean
- `"Args.parse: required options not provided: token, config"` -- missing required options

---

## Help Generation (Planned)

Auto-generated `--help` output from the schema. The `[Use]` section
provides the synopsis, option descriptions come from `#` comments,
and the formatter aligns columns automatically.

```
Usage: myapp [options] COMMAND [args...]

Options:
  -v, --verbose              enable verbose output
  -o, --output FILE          output file (default: /tmp/out.txt)
  -t, --token TOKEN          auth token (required)

Commands:
  deploy, d                  deploy the application
  status, s                  check deployment status

deploy options:
  -w, --workers N            number of workers (default: 4)
```

Implementation: parse the schema, extract `#` comments as descriptions,
format with column alignment, print to stdout, exit 0.

---

## Subcommand Option Isolation (Planned)

Currently all option sections (`[Options]`, `[deploy]`, `[status]`)
share a single alias pool. A `--workers` option defined under `[deploy]`
is recognized even when the subcommand is `status`.

Future: options defined under a subcommand section are only recognized
after that subcommand is matched. Global `[Options]` are always available.

---

## Design Notes

### Why Not Just Use getopts?

`getopts` handles short options only. No `--long-options`, no
subcommands, no defaults, no required validation, no clustering
with attached values. For anything beyond a trivial script, you
end up writing the same boilerplate every time.

### Why Schema-as-String?

The schema string serves double duty: it's both the parser
configuration AND the documentation. You write it once, and both
humans and the parser read the same source. No drift between
what the code accepts and what the help text says.

### Scope-Write vs Object Mode

Scope-write is the natural bash idiom -- after parsing, your
variables are just there. No object ceremony, no `.get` calls.
It's what script authors expect.

Object mode exists for library code that needs to parse arguments
without polluting the caller's namespace, or for cases where you
want to pass parsed options around as a data structure.

### Variable Naming

The first entry in each option line is the variable name. It must
be a valid bash identifier (letters, digits, underscores; no leading
digit). Hyphens are NOT allowed in the variable name but ARE allowed
in aliases:

```bash
log_level | log-level | l =    # variable is $log_level
                               # CLI accepts --log-level or -l
```

This means the variable name and the CLI flag can differ. The
variable name is what your code uses; the aliases are what the
user types.

