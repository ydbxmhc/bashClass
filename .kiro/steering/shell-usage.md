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

## No Subshells in Hot Paths

Avoid `$(...)` in loops or frequently-called functions. Use `printf -v`,
builtins, and parameter expansion instead.

```bash
# BAD: forks a subshell every iteration
result=$(some_function)

# GOOD: write to a variable directly
printf -v result '%s' "$value"
# or use into= / boop.pass / nameref patterns
```

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

