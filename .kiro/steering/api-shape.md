---
inclusion: auto
description: API shape rules — primitives inward, wrappers outward
---

# API Shape

## Primitives Inward, Wrappers Outward

When a class exposes the same operation over multiple input forms (a
string, a file path, a stream), the **reduced form is the primitive**.
Other entry points are thin wrappers that produce the reduced form and
delegate.

For text parsing the reduced form is "lines on stdin." `loadFile` reads
the file and pipes into the parser; `fromString` feeds the string in
via `<<<`; `fromStdin` is the parser itself. The parsing logic exists
exactly once.

## The Inverse Is Forbidden

Making the file variant the primitive and routing in-memory data
through `mktemp` → `printf >` → `< "$file"` → `rm` to reuse it is
**forbidden**. It pays for:

- `mktemp` (fork + syscalls)
- `printf >file` (open/write/close)
- `< file` re-read (open/read/close)
- `rm -f file` (fork + unlink)
- A subshell if `$(...)` is involved
- A tmpfile leak window if `_Crash` fires before `rm` (no `trap`)

…all to skip a one-function refactor. A `while read; done < "$file"`
loop and a `while read; done <<< "$str"` loop are the *same loop* —
extract it.

## The Refactor

```bash
# Bad — string variant routes through disk to reuse the file variant
fromString() {
  local tmp; tmp=$(mktemp)
  printf '%s\n' "$1" > "$tmp"
  loadFromFile "$tmp"
  rm -f "$tmp"
}

# Good — extract the loop, share between forms
__parseLines() {
  local line
  while IFS= read -r line; do
    # ...parse $line into state...
  done
}
loadFromFile() { __parseLines < "$1"; }
fromString()   { __parseLines <<< "$1"; }
```

The refactor is cheaper than one invocation of the wrong design.

## Same Shape Elsewhere

- **Serializers**: `toString` is the primitive; `save <file>` writes
  its output. Never `save` to a tmpfile then `cat` it back to stdout.
- **Iteration**: a callback/visitor primitive is the core; `forEach`,
  `map`, `filter` wrap it. Never reimplement the walk.
- **Constructors**: `new` (empty) is the primitive; `fromString`,
  `fromFile`, `fromArray` build empty then populate via public methods.

## Cross-Reference

See [docs/STANDARDS.md](../../docs/STANDARDS.md) "API Shape" and
[docs/bash_style.md](../../docs/bash_style.md) "Don't Round-Trip
Through Disk" for the full text and the exact `Config.fromString`
anti-pattern that motivated this rule.
