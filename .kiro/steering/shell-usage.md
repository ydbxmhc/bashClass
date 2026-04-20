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
