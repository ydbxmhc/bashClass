# boop — Known Gotchas

Surprising behaviors, silent failures, and things that look like they should
work but don't. Read this before debugging something mysterious.

---

## NUL Bytes — Silent Truncation, No Detection

**Bash variables CANNOT hold or detect NUL bytes.**

This is a fundamental bash limitation, not a boop limitation. A NUL byte
(`\x00`) terminates a C string, and bash's internal variable storage is
C-string-based. The consequences:

- Any value read into a bash variable that contains a NUL is **silently
  truncated at the first NUL**. No error. No warning. No indication that
  data was lost.
- You **cannot detect** after the fact whether truncation occurred — the
  variable simply holds the truncated string with no flag set.
- This applies to **every** mechanism that stores data in a bash variable:
  `read`, `mapfile`, command substitution `$()`, parameter expansion,
  arithmetic, string operations — all of them.

### Where this matters in boop

| Component | Exposure |
|-----------|----------|
| `Data.JSON` | JSON string values parsed into Map.Fast keys/values |
| `Stream` | Record and field values read via `read` |
| `probe` | HTTP response bodies read via `mapfile` |
| `boson` | All output modes write through bash variables |
| `Config` | Config values stored as bash variables |
| Any `Map.Fast` / `Map` store | All keys and values |

### What you can do

- **Avoid NUL in your data.** If your JSON, config, or HTTP payloads can
  contain NUL bytes, boop is not the right tool for that data path.
- **Use an external tool** (`jq`, `python`, `perl`) when you need to handle
  binary or NUL-containing data correctly.
- **Validate at ingestion.** If you control the data source, reject or
  sanitize NUL bytes before they reach boop.

### Why there is no workaround

A bash variable is a null-terminated string at the C level. There is no
way to store a NUL byte in one — not even with `printf`, `read -d ''`, or
any other mechanism. The kernel `read()` syscall may deliver the NUL, but
bash drops it before it reaches the variable. There is no fix short of
rewriting the shell.

---

## `$()` Strips Trailing Newlines

Command substitution unconditionally strips all trailing newlines from its
output before assigning to a variable:

```bash
x=$(printf 'hello\n\n\n')
printf '%q\n' "$x"   # hello  (three newlines gone)
```

This affects any value capture via `$()`. Values ending in one or more
newlines will be silently shortened. Intermediate newlines are preserved.

---

## `read` Discards Partial Last Line Without Trailing Newline

If a file or stream ends without a final newline, `read` returns nonzero
on the last line but still populates the variable. The common idiom:

```bash
while IFS= read -r line; do ...; done < file
```

...silently drops the last line if it has no trailing newline. The safe
form:

```bash
while IFS= read -r line || [[ -n "$line" ]]; do ...; done < file
```

Stream uses the safe form internally. Be aware of it when writing your
own read loops.

---

## `$(</dev/fd/N)` Does Not Work for Socket FDs

Bash's `$(<file)` optimization reads a file directly without forking, but
it only fires for **regular files**. For socket file descriptors (e.g.,
those opened via `/dev/tcp`), bash falls back to `open()` on the path,
which returns `ENXIO` — the socket is not accessible via the filesystem
path interface.

Use `mapfile -u N` or `read -u N` to read from socket/pipe fds directly
by number. Both are bash builtins and work correctly on non-regular fds.

---

## Nameref Loops (`local -n`) and Same-Named Variables

A `local -n ref=target` creates a nameref. If the calling scope has a
variable with the same name as `target`, the nameref resolves to the
caller's variable — which may not be what you intended. This is a bash
nameref scoping quirk, not a boop bug, but it can surface in framework
internals if you use variable names that collide with boop's internal
`__ClassName_methodName_varname` locals.

The triple-prefix naming convention (`__ClassName_methodName_varname`)
exists specifically to avoid this.
