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

## Running test_all

Always run `test_all` in verbose mode with output teed to a log:

```bash
bash -x test_all 2>&1 | tee test_all.log
```

This ensures:
- Progress is visible in real time (stdout)
- Full output is captured in `test_all.log` for review after timeouts
- `bash -x` shows each command as it executes so you can see what's running
