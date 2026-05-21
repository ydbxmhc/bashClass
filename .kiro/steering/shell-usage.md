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

