---
inclusion: auto
description: Shell execution rules for this workspace
---

# Shell Execution Rules

## CRITICAL — READ THIS FIRST

The user's terminal IS Git Bash. It is the native shell. All commands
execute directly as plain bash commands.

**NEVER** use any of these patterns:
- `& "C:\Program Files\Git\bin\bash.exe" -c "..."`
- PowerShell syntax of any kind
- Full paths to bash.exe
- Wrapping commands in PowerShell calls

**ALWAYS** just run commands directly:
```bash
git add -A
git commit -m "message"
bash test_all
grep -r "pattern" .
```

This is not negotiable. The shell is bash. Use it as bash.

## Timing

Run `date` before and after each command execution. This provides:
- A reference for how long tasks take
- Awareness of actual passage of time during the session

## Running test_all

Always run `test_all` in verbose mode with output teed to a log:

```bash
bash -x test_all 2>&1 | tee test_all.log
```

This ensures:
- Progress is visible in real time (stdout)
- Full output is captured in `test_all.log` for review after timeouts
- `bash -x` shows each command as it executes so you can see what's running

## Prefer Positive Assertions in Conditionals

Test for what things ARE, not what they aren't. Negative conditions
(`!= "none"`, `!= "char"`, `! -z`) are harder to reason about and
often mask the actual logic.

```bash
# BAD: testing what it's NOT
if [[ "$mode" != "none" && "$mode" != "char" ]]; then

# GOOD: testing what it IS
if [[ "$mode" == "string" || "$mode" == "class" || "$mode" == "collapse" ]]; then
```

Exception: a single `[[ -z "$var" ]]` or `[[ -n "$var" ]]` is fine
for presence/absence checks. The rule targets multi-branch logic where
negation obscures intent.


## No Continuation Backslashes (Unless Genuinely Needed)

Operators like `||`, `&&`, and `|` already signal continuation to
bash. A trailing backslash after them is noise and a trailing-
whitespace bug waiting to happen.

```bash
# BAD: unnecessary backslash
[[ -f "$file" ]] || \
  _Crash "not found"

# GOOD: operator signals continuation
[[ -f "$file" ]] ||
  _Crash "not found"
```

Backslashes ARE needed when splitting a single command's argument
list across lines (no operator to signal continuation). But prefer
keeping argument lists on one line unless they're truly unwieldy.

## No eval -- Prefer Namerefs

Use `local -n` namerefs for dynamic variable assignment. `eval` is
a last resort for cases namerefs genuinely can't handle.

```bash
# BAD
eval "$varname=\"\$value\""

# GOOD
local -n __ref="$varname"
__ref="$value"
```

## Avoid Unnecessary Subshells and Complexity

Never use a subshell when a reasonable alternative exists. "Reasonable"
means: if you can name and explain why the simpler form doesn't work,
use the complex one. If you can't, use the simple one.

Parameter expansion handles most cases that cargo-culted `$(...)` reaches for:

```bash
# BAD: two subshells, cd, pwd, dirname — all to get a directory path
__root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# GOOD: one string operation, no forks
__root="${BASH_SOURCE[0]%/*}/.."
```

The resolved-absolute-path form is only justified when the path itself
will be used in a context that can't handle `..` (e.g. passed to a tool
that resolves relative to cwd, or used as a base for further `cd`).
Sourcing a file by path is not such a context.

More generally: every `$(...)` forks a subshell. In a loop or hot path
that cost compounds. But even once is worth avoiding when parameter
expansion, `printf -v`, builtins, namerefs, or `into=` patterns do
the same job without forking.

The rule is not "avoid subshells in hot paths." It is: **avoid subshells
you cannot justify.** If you reach for `$(...)`, ask first whether
parameter expansion handles it. Usually it does.

## Real Arrays Over Joined Strings

When data is naturally a list, store it as a bash indexed array.
Don't join into a string and split later -- that introduces delimiter
fragility. Accept proprietary-named globals (`__boop_data_${_Self}_fields`)
when a real array is needed across function boundaries.

## IFS Discipline

- Always use `"${array[@]}"` (not `"${array[*]}"`) unless you have a
  specific reason AND have explicitly set IFS for the join.
- Never assume IFS is at its default value in framework code.
- When you must use `[*]`, prefix with `IFS=' '` or whatever the
  intended join character is.

