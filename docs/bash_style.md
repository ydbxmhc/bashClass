# Bash Style Guide

Compiled from [Google's Shell Style Guide](https://google.github.io/styleguide/shellguide.html)
and [Dave Eddy's YSAP Bash Style Guide](https://style.ysap.sh/), with
project-specific preferences noted. Content was rephrased for compliance
with licensing restrictions.

---

## Shebang

Every executable script starts with a shebang line.

```bash
#!/bin/bash
```

Use `#!/usr/bin/env bash` if portability across systems where bash
may not be at `/bin/bash` matters. For controlled environments where
you know the path, `#!/bin/bash` is fine and avoids `env` lookup.

### boop perspective

Most files in the boop system are meant to be sourced. 
Attempting to execute them should have useful output such as help
screens when possible.

---

## Shell Options

<!-- REVIEW: YSAP argues against set -e entirely (see "The Problem
     with Bash strict mode"). Google says use set -e but check errors.
     boop itself does NOT set shell options (framework must not alter
     caller's environment). For standalone scripts, pick your poison. -->

For standalone scripts, consider:

```bash
set -euo pipefail
```

- `set -e` — exit on error. Controversial: can mask failures in
  conditionals and compound commands. Know the edge cases.
- `set -u` — treat unset variables as errors.
- `set -o pipefail` — pipeline fails if any command in the pipe fails.

For library/framework code that others source: never set shell options.
Save and restore if you must change one temporarily.

### boop perspective

All of boop is effectively a library/framework intended to be sourced.
It should virtually never set shell options unless explicitly requested 
by the user; if some options become important, they mush be PROMINANTLY
listed in the documentation. This applies to anything that in ANY way
significantly affects the user's environment, including `set`, `shopt`,
any edits to system variables such as `PATH`, etc.

---

## Formatting

### Indentation

Two spaces. No tabs. Stay consistent with existing files.  
Exception: `<<-` heredocs require tabs for indentation of the body.

### Pipelines

If a pipeline fits on one line, keep it on one line. Otherwise,
end each line with `|` and indent the continuation. The parser
knows a trailing pipe means more is coming — no `\` needed.

If you line up the trailing pipes they catch the eye to make a 
continuous vertical line through the pipeline, establishing
logical integration, and it isn't fragile about any trailing
whitespace - it even allows comments.

```bash
# Short — one line
command1 | command2

# Long — pipe at end of line, indent continuation
command1   |
  command2 |
  command3

# Bonus: you can comment each stage
date          | # current date string
  grep -o Mar | # extract month
  cat           # (or whatever)
```

Never use `\` continuation for pipelines. A single trailing space
after `\` silently breaks the continuation, and the failure is
invisible. Trailing `|` is self-continuing and robust.

The same applies to `&&` and `||` — end the line with the operator
so the parser knows more is coming.

---

## Quoting

- Always quote strings containing variables, command substitutions,
  spaces, or shell metacharacters unless there is an explicit reason
  not to do so - if so, comment it.
- Use single quotes for literal strings with no expansion.
- Use double quotes when variable expansion or command substitution
  is needed.
- `"$@"` almost always, `$*` almost never - almost.

```bash
foo='literal string, no expansion'
bar="Hello, ${USER}"
myFunc "$arg1" ${maybe:-} # unquoted empty vanishes from the call, 
                          # but value vulnerable to word splitting
```

Inside `[[ ... ]]`, variables don't undergo word splitting, so
unquoted is technically safe — but quoting is still preferred for
consistency and readability.

Braces (`${var}`) are not a substitute for quotes. `${f}` without
quotes still word-splits. Use `"${f}"` or `"$f"`.

---

## Variable Naming

### Local Variables

Lowercase with underscores: `target_file`, `line_count`.

All variables inside functions should be declared `local`, or
*explicitly* as a global with `declare -g` to leave no doubt.

Globals should only be used for good reason, and care must be
taken to prevent accidentally destroying any previous data when/if
initializing. 

```bash
my_func() {
  local name="$1"
  local result
  result="$(some_command)"
  printf '%s\n' "$result"
}
```

Separate declaration from assignment when the value comes from a
command substitution — `local` swallows the exit code:

```bash
# Bad — $? is always 0 (exit code of local, not some_command)
local val="$(some_command)"

# Good — preserves exit code
local val
val="$(some_command)"
```

### Constants and Exported Variables

UPPER_CASE with underscores. Declare at the top of the file.
Use `readonly` or `declare -r` to prevent modification.

```bash
readonly CONFIG_DIR='/etc/myapp'
declare -xr APP_ENV='production'
```

### Loop Variables

Name them meaningfully — match what you're iterating over.

```bash
for zone in "${zones[@]}"; do deploy_to "$zone"; done
```

---

## Functions

### Declaration

Use the `name() { }` form. The `function` keyword is optional and
adds nothing when parentheses are present.

Exception: `function name { }` (without parentheses) is required
when the function name contains operator characters like `+`, `-`,
`*`, `/`, etc. The `name() {}` parser rejects those because it
tries to interpret the special characters. The `function` keyword
form is more permissive about what constitutes a valid name. This
comes up with `eval`'d symbol aliases:

```bash
# name() {} form — parser chokes on the *
eval 'Math.*() { Math.multiply "$@"; }'   # FAILS

# function keyword form — works
eval 'function Math.* { Math.multiply "$@"; }'  # OK
```

Opening brace on the same line as the function name.

### Naming

Lowercase with underscores for standalone functions: `process_file`,
`check_status`.

### Location

Group all functions together near the top of the file, after
constants and sourced dependencies. Don't scatter executable code
between function definitions.

### `main` Function

For scripts with multiple functions, wrap the entry point in a
`main()` function called at the bottom of the file:

```bash
main() {
  parse_args "$@"
  do_work
}

main "$@"
```

Short linear scripts don't need this.

---

## Output

### `printf` Over `echo`

`echo` behavior varies across platforms (backslash interpretation,
`-n` flag handling). `printf` is predictable everywhere.

```bash
# Bad
echo "$value"
echo -n "no newline"

# Good
printf '%s\n' "$value"
printf '%s' "no newline"
```

### STDOUT vs STDERR

Normal output goes to stdout. Error and diagnostic messages go to
stderr.

```bash
printf 'Processing %s\n' "$file"           # stdout — normal output
printf 'Error: file not found\n' >&2       # stderr — error message
```

---

## Command Substitution

Use `$(command)` — never backticks. Backticks don't nest cleanly
and are harder to read.

```bash
# Good
result="$(command "$(inner_command)")"

# Bad
result="`command \`inner_command\``"
```

---

## Conditionals and Tests

### `[[ ]]` Over `[ ]`

Always use `[[ ... ]]`. It doesn't word-split or glob-expand, supports
`=~` for regex, and `==` for pattern matching.

```bash
# Good
if [[ -d "$dir" ]]; then ...
if [[ "$name" =~ ^[a-z]+$ ]]; then ...

# Bad
if [ -d "$dir" ]; then ...
```

### String Testing

Use `-z` (empty) and `-n` (non-empty) explicitly. Don't rely on
implicit truthiness.

```bash
# Good
if [[ -z "$var" ]]; then ...
if [[ -n "$var" ]]; then ...

# Avoid
if [[ "$var" ]]; then ...
```

Use `==` for equality (not `=`, which looks like assignment).

### Numeric Comparison

Use `(( ))` for arithmetic comparisons, not `[[ ]]` with `-gt`/`-lt`
(which work but are less readable), and definitely not `<`/`>` inside
`[[ ]]` (those do lexicographic comparison).

```bash
# Good
if (( count > 10 )); then ...

# Acceptable
if [[ "$count" -gt 10 ]]; then ...

# Wrong — lexicographic, not numeric
if [[ "$count" > 10 ]]; then ...
```

---

## Arithmetic

Use `(( ))` and `$(( ))`. Never `let`, `expr`, or `$[ ]`.

Inside `$(( ))`, variables don't need `$` or `${}`:

```bash
(( total = width * height ))
printf '%s\n' "$(( a + b ))"
```

Beware: `(( ))` as a standalone statement returns exit code 1 when
the expression evaluates to 0. Under `set -e`, `(( i++ ))` starting
from 0 will kill your script.

---

## Arrays

Use arrays for lists. Never pack multiple items into a space-delimited
string.

```bash
# Good
files=(foo.txt bar.txt baz.txt)
for f in "${files[@]}"; do
  process "$f"
done

# Bad
files='foo.txt bar.txt baz.txt'
for f in $files; do
  process "$f"
done
```

Use `"${array[@]}"` (quoted, `@`) to expand safely.

---

## Parameter Expansion

Prefer bash builtins over forking external commands for string
manipulation.

```bash
# Good — builtins, no fork
prog="${0##*/}"                    # basename
dir="${path%/*}"                   # dirname
clean="${name//[0-9]/}"            # strip digits
upper="${val^^}"                   # uppercase (bash 4+)

# Bad — forks external processes
prog="$(basename "$0")"
dir="$(dirname "$path")"
clean="$(echo "$name" | sed 's/[0-9]//g')"
```

---

## Loops and Input

### Don't Parse `ls`

```bash
# Wrong
for f in $(ls); do ...

# Right
for f in *; do ...
```

### Pipe to While — Beware Subshells

Piping to `while` creates a subshell. Variables set inside won't
propagate to the parent.

```bash
# Bug — last_line is always empty in the parent
your_command | while read -r line; do
  last_line="$line"
done
printf '%s\n' "$last_line"  # empty!

# Fix — process substitution
while read -r line; do
  last_line="$line"
done < <(your_command)
printf '%s\n' "$last_line"  # correct
```

Or use `readarray` (bash 4+):

```bash
readarray -t lines < <(your_command)
for line in "${lines[@]}"; do ...
```

### Use `read` Builtin for Parsing

```bash
IFS=: read -r user _ <<< "$line"
IFS=. read -r host domain tld <<< "$fqdn"
```

---

## Useless Use of Cat (UUoC)

If a command can read a file directly, don't pipe `cat` into it.

```bash
# Wrong
cat file | grep pattern

# Right
grep pattern file
grep pattern < file
```

For reading file contents into a variable, use `$(<file)` — it's a
bash builtin, no fork:

```bash
contents="$(<config.txt)"
```

---

## Error Handling

### Check Return Values

Always check return values. Use `if` directly or `||` for inline
handling.

```bash
# Direct check
if ! mv "${files[@]}" "$dest/"; then
  printf 'Failed to move files to %s\n' "$dest" >&2
  exit 1
fi

# Inline
cd /some/path || exit 1
```

### `PIPESTATUS`

Check individual pipeline stages when it matters:

```bash
tar -cf - ./* | gzip > archive.tar.gz
if (( PIPESTATUS[0] != 0 )); then
  printf 'tar failed\n' >&2
fi
```

Capture `PIPESTATUS` immediately — any subsequent command overwrites it.

---

## `eval`

Avoid `eval`. It enables code injection and defeats static analysis.
Almost every use case has a safer alternative: arrays, indirect
expansion (`${!var}`), or `declare`/`printf -v`.

<!-- NOTE: boop uses eval for stub baking and dispatch — this is
     controlled, validated input only. General scripts should not. -->

---

## Wildcard Expansion

Use explicit paths with wildcards to avoid problems with filenames
starting with `-`:

```bash
# Dangerous — "-f" looks like a flag to rm
rm -v *

# Safe
rm -v ./*
```

---

## Aliases

Don't use aliases in scripts. They evaluate at definition time, not
at call time, and are fragile with quoting. Use functions instead.

```bash
# Bad
alias ll='ls -lh'

# Good
ll() { ls -lh "$@"; }
```

---

## File Reading

Prefer `$(<file)` over `cat file` or `$(cat file)` for reading
file contents into a variable. It's a bash builtin — no fork, no
external process.

```bash
# Good
data="$(<input.txt)"

# Bad
data="$(cat input.txt)"
```

---

## Builtins Over External Commands

When a bash builtin can do the job, prefer it over forking an
external process. This matters in loops and hot paths.

```bash
# Good — printf builtin for timestamps
printf '%(%Y-%m-%d %H:%M:%S)T\n' -1

# Bad — forks date(1)
date '+%Y-%m-%d %H:%M:%S'
```

```bash
# Good — parameter expansion
if [[ "$string" == *pattern* ]]; then ...

# Bad — forks grep
if echo "$string" | grep -q pattern; then ...
```

---

## Heredocs and Herestrings

TODO: Document heredoc patterns (`<<EOF`, `<<'EOF'` for no expansion,
`<<-EOF` for tab-stripped indentation). Herestring (`<<<`) usage and
gotchas (trailing newline added automatically). When to use each vs
`printf` or variable assignment.

---

## Trap Handling

TODO: Document `trap` for `EXIT`, `ERR`, `INT`, `TERM`. Stacking
handlers (bash only allows one per signal — layering requires manual
management). Interaction with `set -e`. Cleanup patterns. See also
boop's planned Signal Handler Class in TODO.md.

---

## Namerefs (`local -n`)

TODO: Document nameref declaration, the name-collision problem (a
nameref can't reference a variable with the same name as itself or
any variable in the calling scope with the same name — bash resolves
by name, not by scope). The `__ClassName_method_var` prefix convention
exists specifically to prevent this. Gotchas with namerefs inside
loops. Interaction with `local -I`.

---

## `local` Type Modifiers

TODO: Document `local -i` (integer), `local -l` (lowercase value),
`local -u` (uppercase value), `local -n` (nameref), `local -I`
(inherited). Note: `-l` lowercases the *value*, not the variable
name. `-i` enables arithmetic context on assignment. These compose:
`local -li` gives you a lowercase integer (though that's rarely
useful).

---

## Process Substitution

TODO: Document `<(command)` and `>(command)` beyond the pipe-to-while
case. Using `<(...)` for diff-ing command outputs, feeding multiple
streams to a command, etc. Note that process substitution creates a
subshell and a `/dev/fd/N` file descriptor — not available in all
shells (bash and zsh, not POSIX sh).

---

## `printf -v`

TODO: Document `printf -v varname` for assigning formatted output
directly to a variable without a subshell. Comparison with
`var="$(printf ...)"` (which forks). Useful for building strings
in loops without accumulating subshell overhead.

---

## `mapfile` / `readarray`

TODO: Expand coverage. `readarray -t lines < <(command)` for reading
output into an array. `-t` strips trailing newlines. `-d` for custom
delimiters (bash 4.4+). Comparison with `while read` loops — when
each is appropriate. Memory considerations for large inputs.

---

## `PIPESTATUS` (Advanced)

TODO: Deeper treatment for error handling classes. Capturing
`PIPESTATUS` into a local array immediately after a pipeline.
Checking individual stage exit codes. Interaction with `set -o
pipefail`. Patterns for retry/recovery based on which stage failed.

---

## Sources

- [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html) (CC-BY 3.0)
- [YSAP Bash Style Guide](https://style.ysap.sh/) by Dave Eddy (MIT)
- [Wooledge BashGuide](https://mywiki.wooledge.org/BashGuide)
- [BashPitfalls](https://mywiki.wooledge.org/BashPitfalls)
