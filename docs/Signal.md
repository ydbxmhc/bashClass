# Signal

Managed per-signal callback stacks. Layers a LIFO handler queue on top of
bash's single-slot `trap`, so multiple components in the same script can
register cleanup or error handlers without stomping each other.

## Dependencies

```bash
. boop Signal
```

---

## The Problem

Bash's `trap` command gives each signal exactly one handler slot. Registering
a second handler silently replaces the first:

```bash
trap "rm -rf $tmpdir" EXIT          # your cleanup
trap "stty echo" EXIT               # also your cleanup — but now $tmpdir leaks
```

Signal solves this by owning the `trap` slot for each signal it manages and
dispatching to a stack of registered callbacks in LIFO order (last registered,
first called). Any number of components can add handlers; none can clobber
another's.

---

## Quick Start

```bash
. boop Signal

# Register two EXIT handlers from different parts of the script:
Signal.on EXIT my_temp_cleanup
Signal.on EXIT my_terminal_restore

# On exit, my_terminal_restore fires first, then my_temp_cleanup.
```

Callbacks receive the signal name as their first argument:

```bash
my_temp_cleanup() {
  local sig="$1"   # "EXIT"
  rm -rf "$tmpdir"
}
```

---

## Signal Names

Signal works with any name that bash's `trap` accepts.

### Bash pseudo-signals

These are not OS signals — bash generates them internally:

| Name | Fires when... |
|------|--------------|
| `EXIT` | The shell exits for any reason |
| `ERR` | A command returns non-zero (see [ERR notes](#err-notes)) |
| `DEBUG` | Before every simple command (use sparingly — fires constantly) |
| `RETURN` | After every `return` or sourced-file exit |

### Standard signals

| Name | Number | Fires when... | Default action |
|------|--------|--------------|----------------|
| `HUP` | 1 | Terminal disconnected or controlling process exited | Terminate |
| `INT` | 2 | `Ctrl-C` | Terminate |
| `QUIT` | 3 | `Ctrl-\` | Terminate + core dump |
| `ILL` | 4 | Illegal instruction executed | Terminate + core dump |
| `ABRT` | 6 | `abort()` called (assertion failure) | Terminate + core dump |
| `FPE` | 8 | Floating-point or integer divide-by-zero | Terminate + core dump |
| `SEGV` | 11 | Invalid memory access | Terminate + core dump |
| `PIPE` | 13 | Write to a closed pipe (`set -o pipefail` or explicit) | Terminate |
| `ALRM` | 14 | Timer set by `alarm()` expired | Terminate |
| `TERM` | 15 | Polite termination request (`kill`, system shutdown) | Terminate |
| `CHLD` | 17 | A child process changed state (exited, stopped, continued) | Ignore |
| `CONT` | 18 | Process resumed after being stopped | Continue |
| `TSTP` | 20 | `Ctrl-Z` keyboard stop request | Stop |
| `TTIN` | 21 | Background process tried to read from terminal | Stop |
| `TTOU` | 22 | Background process tried to write to terminal (if `stty tostop`) | Stop |
| `WINCH` | 28 | Terminal window resized | Ignore |
| `USR1` | 10 | Application-defined | Terminate |
| `USR2` | 12 | Application-defined | Terminate |

### Untrappable signals

`KILL` (9) and `STOP` (19) **cannot** be caught, blocked, or ignored —
the OS enforces this. Bash does not error when you call
`Signal.on KILL …` or `Signal.on STOP …`, but the handler will **never
fire**. The process is simply killed or stopped by the kernel with no
opportunity for cleanup.

If you want to handle the keyboard stop gesture (`Ctrl-Z`), trap `TSTP`,
not `STOP`. `TSTP` is the *request* to stop; the process can intercept it.
`STOP` is the kernel *enforcing* the stop with no escape.

```bash
# CORRECT — trap the keyboard Ctrl-Z request:
Signal.on TSTP handle_suspend

# USELESS — SIGSTOP cannot be caught:
Signal.on STOP handle_suspend   # handler registers but never fires
```

Similarly, trap `TERM` (polite shutdown) and `HUP` (disconnect) rather
than relying on `KILL` cleanup. Well-behaved process managers send `TERM`
first and only escalate to `KILL` if the process doesn't exit within a
timeout.

### Notes on specific signals

**QUIT** — `Ctrl-\` in the terminal. Default action is terminate + core
dump. Trapping it is useful for "dump diagnostics and exit cleanly" rather
than leaving a core file behind. Less commonly sent than `INT` but worth
handling in long-running scripts.

**SEGV** — Invalid memory access. Pure bash scripts don't allocate memory
directly, but bash itself can segfault (rare). Trapping `SEGV` gives you
a last-chance handler to log context before the process dies, but you
cannot continue execution after a SEGV — the handler runs and then the
process exits.

**PIPE** — Fires when you write to a pipe whose reader has closed (e.g.
`printf '%s' "$data" | head -1` — `head` closes the pipe after one line).
Trapping `PIPE` suppresses the default termination and lets the script
handle broken pipes explicitly, though `set -o pipefail` is usually the
more direct tool.

**CONT** — Fires when a stopped process is resumed (e.g. after `Ctrl-Z`
followed by `fg`). Useful for re-initializing terminal state after
suspension.

```bash
Signal.on TSTP save_terminal_state
Signal.on CONT restore_terminal_state
```

**CHLD** — Fires whenever a child process changes state: exits, is stopped
by a signal, or is resumed. Useful for async job tracking without blocking
`wait` calls. The handler cannot easily distinguish which child changed
state (bash doesn't pass that information); use `wait -n` or iterate
`wait $pid` for specifics.

**WINCH** — Terminal window resized. Essential for full-screen terminal UIs
that need to reflow their layout when the user resizes the window.

```bash
Signal.on WINCH redraw_screen
redraw_screen() {
  read -r LINES COLUMNS < <(stty size)
  draw_table
}
```

### Unrecognized names

Signal names that bash itself rejects (misspellings, platform-specific
names not present on the current OS) do not cause errors. Signal silently
skips trap installation; all collection operations (`on`, `off`, `list`,
`pop`, `shift`, `clear`) and `Signal.dispatch` still work. This makes
synthetic signal names safe to use in tests.

---

## Methods

### `Signal.on signame callback`

Push a callback onto the top of the signal's LIFO stack. Installs the
signal's `trap` on the first registration.

```bash
Signal.on EXIT cleanup_tmpdir
Signal.on EXIT restore_terminal    # fires first on exit
Signal.on ERR  log_error
```

`Signal.push` is an exact alias for `Signal.on`.

---

### `Signal.push signame callback`

Alias for `Signal.on`. Prefer whichever reads more naturally in context:
`on` for handler registration, `push` when you're thinking about the stack.

```bash
Signal.push EXIT my_handler
```

---

### `Signal.off signame callback`

Remove the **first occurrence** of a callback from the stack. If the same
function was registered twice, the second occurrence remains.

```bash
Signal.on EXIT cleanup_db
Signal.on EXIT cleanup_cache
Signal.on EXIT cleanup_db    # registered twice

Signal.off EXIT cleanup_db   # removes the first one; second stays
```

`Signal.off` on a signal that has no handlers, or on a callback that is not
registered, is a no-op — no error, no warning.

---

### `Signal.pop signame` → `into=`

Remove and return the **last-pushed** callback (the one that would fire
first). Returns empty string if the stack is empty.

```bash
Signal.on EXIT cleanup_a
Signal.on EXIT cleanup_b
Signal.on EXIT cleanup_c

into=top Signal.pop EXIT    # top="cleanup_c"; still has a, b
```

Use `pop` when you need to temporarily suspend the most recent handler,
modify state, and optionally re-register it.

---

### `Signal.shift signame` → `into=`

Remove and return the **first-pushed** callback (the one that would fire
last). Returns empty string if the stack is empty.

```bash
Signal.on EXIT cleanup_a
Signal.on EXIT cleanup_b
Signal.on EXIT cleanup_c

into=bottom Signal.shift EXIT   # bottom="cleanup_a"; still has b, c
```

---

### `Signal.clear signame`

Remove all callbacks for a signal and uninstall its `trap`. After `clear`,
the signal reverts to bash's default behavior.

```bash
Signal.clear EXIT    # removes all EXIT handlers, resets trap
Signal.clear ERR
```

Calling `clear` on a signal with no handlers is harmless.

---

### `Signal.list signame` → `into=`

Return the registered callbacks as a newline-joined string. The first line
is the first-pushed callback (fires last during dispatch); the last line is
the most recently pushed (fires first).

Returns empty string if no callbacks are registered.

```bash
Signal.on EXIT cleanup_a
Signal.on EXIT cleanup_b
Signal.on EXIT cleanup_c

into=handlers Signal.list EXIT
printf '%s\n' "$handlers"
# cleanup_a
# cleanup_b
# cleanup_c
```

```bash
# Check whether a specific handler is registered:
into=handlers Signal.list EXIT
if printf '%s\n' "$handlers" | grep -qx "my_handler"; then
  printf "already registered\n"
fi
```

---

### `Signal.dispatch signame [extra_args...]`

Manually fire all callbacks for a signal in LIFO order. Extra arguments
beyond the signal name are forwarded to each callback as `$2`, `$3`, etc.

This is how `Signal.on` actually fires during a real signal — the installed
`trap` calls the internal `__Signal.dispatch 'SIGNAME'` automatically.
`Signal.dispatch` is the public version for manual or test use.

```bash
Signal.on CUSTOM my_handler

# Fire manually, passing extra context:
Signal.dispatch CUSTOM "phase=cleanup" "reason=shutdown"
# my_handler receives: $1="CUSTOM"  $2="phase=cleanup"  $3="reason=shutdown"
```

Dispatching on a signal with no registered callbacks is a no-op.

---

## LIFO Dispatch Order

Handlers fire in reverse registration order — last registered, first called.
This matches the natural cleanup expectation: resources should be released in
the reverse order they were acquired.

```bash
acquire_database_connection
Signal.on EXIT release_database_connection

acquire_temp_directory
Signal.on EXIT cleanup_temp_directory      # fires first on exit

acquire_terminal_raw_mode
Signal.on EXIT restore_terminal_mode       # fires first — restores terminal
                                            # before any other cleanup output
```

On exit, the order is:
1. `restore_terminal_mode`
2. `cleanup_temp_directory`
3. `release_database_connection`

---

## Error Resilience

Callback failures are suppressed. If one handler crashes or returns non-zero,
the remaining handlers still fire. This is intentional — a broken cleanup
handler should not abort the rest of the cleanup chain.

```bash
bad_handler()  { return 1; }   # always fails
good_handler() { printf "cleaned\n"; }

Signal.on EXIT good_handler
Signal.on EXIT bad_handler     # fires first; fails
Signal.on EXIT good_handler    # fires last; still runs

# "cleaned" appears once
```

If you need to know whether a handler failed, have it write to a shared
variable or a log file.

---

## Callback Contract

Every callback registered with Signal must be a bash function. It is called:

```
callback signame [extra_args...]
```

- **`$1`** — always the signal name that fired (`EXIT`, `ERR`, `INT`, etc.)
- **`$2…`** — optional extra args forwarded by `Signal.dispatch`; not present
  when the callback fires from a real trap

Callbacks should be self-contained. They cannot safely call boop methods
that use `into=` on globals your script is currently mid-write on, because
`EXIT` and `ERR` can fire at arbitrary command boundaries.

---

## Common Patterns

### Multi-component EXIT cleanup

Different modules register their own cleanups independently. No coordination
needed.

```bash
# In your database module:
db_open() {
  __db_conn_handle="$(db_connect "$@")"
  Signal.on EXIT __db_close
}
__db_close() { db_disconnect "$__db_conn_handle"; }

# In your temp-file module:
tmpfile_create() {
  __tmpfile="$(mktemp)"
  Signal.on EXIT __tmpfile_cleanup
}
__tmpfile_cleanup() { rm -f "$__tmpfile"; }

# Main script — modules clean up in reverse of acquisition order:
db_open localhost mydb
tmpfile_create
# ...
exit 0  # __tmpfile_cleanup fires, then __db_close
```

---

### Terminal raw-mode guard

```bash
enter_raw_mode() {
  stty -echo -icanon min 1 time 0
  Signal.on EXIT __restore_terminal
  Signal.on INT  __restore_terminal
  Signal.on TERM __restore_terminal
}

__restore_terminal() { stty echo icanon; }
```

---

### Temporary suspension of a handler

Pop, do something that shouldn't trigger the cleanup, then re-register.

```bash
Signal.on EXIT delete_lockfile

into=handler Signal.pop EXIT     # suspend
move_lockfile_atomically
Signal.on EXIT delete_lockfile   # re-register (pointing at new location)
```

---

### One-shot handler

Register a handler that removes itself the first time it fires.

```bash
__once_handler() {
  Signal.off EXIT __once_handler
  printf "fired once\n"
}
Signal.on EXIT __once_handler
```

---

### Layered ERR reporting

```bash
. boop Signal

outer_err()  { printf "[outer] error at line %s\n" "$LINENO" >&2; }
inner_err()  { printf "[inner] error at line %s\n" "$LINENO" >&2; }

Signal.on ERR outer_err

# Inner scope adds its handler:
Signal.on ERR inner_err    # fires first
# ...
Signal.off ERR inner_err   # remove when inner scope exits
```

---

### Manual dispatch for testing

```bash
# In production, EXIT fires naturally.
# In tests, fire it manually and verify cleanup happened.
Signal.on EXIT cleanup_fn

Signal.dispatch EXIT
# cleanup_fn ran; verify side effects here
Signal.clear EXIT            # reset for next test
```

---

## ERR Notes

`trap ERR` fires when a command returns a non-zero exit code. Its behavior
depends on shell options:

- Without `set -e`: ERR fires on a failed command, but the script continues.
- With `set -e`: ERR fires, then EXIT fires (the shell exits on error).
- Inside functions, ERR inherits only if `set -E` (`errtrace`) is set.
- ERR does **not** fire inside `if` conditions, `&&`/`||` chains, or negated
  commands (`! cmd`).

For robust error trapping, combine `set -euo pipefail` with `set -E`:

```bash
set -euo pipefail -E   # ERR propagates into functions

Signal.on ERR report_error
Signal.on EXIT cleanup_on_error

report_error() {
  local code=$?
  printf "error (exit %d)\n" "$code" >&2
}
```

---

## Design Notes

**Plain arrays, not boop objects.** Signal uses one raw bash indexed array
per signal (`__Signal_handlers_SIGNAME`) rather than boop List or Stack
objects. This keeps the internal `__Signal.dispatch` function — which runs
inside a `trap` handler — free of boop's global return-value machinery. Trap
handlers fire asynchronously relative to your script's command flow; reading
or writing `into=` globals from within them could corrupt a boop call in
progress. Raw arrays sidestep the problem entirely.

**Trap installed on first `on`.** Signal doesn't install a `trap` until at
least one callback is registered for a signal. Calling `Signal.dispatch`
directly without any prior `Signal.on` is a no-op; the trap slot is never
touched.

**`Signal.clear` resets to default behavior.** After `Signal.clear EXIT`,
bash reverts EXIT to its default (just exit). It does not restore any
previous `trap` that may have been set before Signal took over the slot.
Signal assumes it owns the trap slot for signals it manages.

**Unrecognized signal names.** If bash rejects a signal name (e.g. a
misspelled `EXITT`), `trap` returns non-zero and Signal silently skips
trap installation. The per-signal array is still created, so `Signal.dispatch`
and all collection operations work — useful for tests that use synthetic
signal names.

**Callback errors suppressed at dispatch time.** `2>/dev/null || true`
wraps each callback invocation. This means even a callback that calls `exit`
or crashes will not abort the dispatch loop. If a callback legitimately needs
to propagate an error, it should write to a shared variable and let the
calling code check it after dispatch.

**Class-level only — no instances.** Signal has no constructor. All methods
are static (`Signal.method args`). There is no reason to create a Signal
object; the handler stacks are process-global by nature.
