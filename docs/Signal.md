# Signal

Managed per-signal callback stacks. Layers a LIFO handler queue on top of
bash's single-slot `trap`, so multiple components in the same script can
register cleanup or error handlers without stomping each other.

## Contents

- [Dependencies](#dependencies)
- [The Problem](#the-problem)
- [Quick Start](#quick-start)
- [Signal Names](#signal-names)
  - [Bash pseudo-signals](#bash-pseudo-signals)
  - [Standard signals](#standard-signals)
  - [Untrappable signals](#untrappable-signals)
  - [Notes on specific signals](#notes-on-specific-signals)
  - [Unrecognized names](#unrecognized-names)
- [Methods](#methods)
  - [`Signal.strict [0|1|on|off]`](#signalstrict-011onoff)
  - [`Signal.on signame callback`](#signalon-signame-callback)
  - [`Signal.push signame callback`](#signalpush-signame-callback)
  - [`Signal.off signame callback`](#signaloff-signame-callback)
  - [`Signal.pop signame` → `into=`](#signalpop-signame--into)
  - [`Signal.shift signame` → `into=`](#signalshift-signame--into)
  - [`Signal.clear signame`](#signalclear-signame)
  - [`Signal.list signame` → `into=`](#signallist-signame--into)
  - [`Signal.dispatch signame [extra_args...]`](#signaldispatch-signame-extra_args)
  - [`Signal.returnTrap [signame] handler` → `into=`](#signalreturntrap-signame-handler--into)
- [LIFO Dispatch Order](#lifo-dispatch-order)
- [Error Resilience](#error-resilience)
- [Callback Contract](#callback-contract)
- [Pre-existing Trap Survey](#pre-existing-trap-survey)
- [Common Patterns](#common-patterns)
  - [Multi-component EXIT cleanup](#multi-component-exit-cleanup)
  - [Terminal raw-mode guard](#terminal-raw-mode-guard)
  - [Temporary suspension of a handler](#temporary-suspension-of-a-handler)
  - [One-shot handler](#one-shot-handler)
  - [Caller-scoped RETURN cleanup](#caller-scoped-return-cleanup)
  - [Layered ERR reporting](#layered-err-reporting)
  - [Manual dispatch for testing](#manual-dispatch-for-testing)
- [ERR Notes](#err-notes)
- [Design Notes](#design-notes)

---

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

`DEBUG` and `RETURN` are also bash pseudo-signals, but Signal **rejects**
them — see [Rejected signals](#untrappable-signals) below.

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

### Rejected signals

Signal outright **rejects** four names with `_Error` and returns non-zero.
No handler is registered. The call fails immediately.

| Signal | Reason rejected |
|--------|----------------|
| `KILL` (9) | Unblockable — the OS delivers it without consulting the process; a trap can never fire |
| `STOP` (19) | Unblockable — same reason |
| `DEBUG` | Fires before *every* simple command; a LIFO callback stack on DEBUG means N callbacks per command — that's a profiler, not a signal handler |
| `RETURN` | Fires after every `return` or sourced-file exit; incompatible with the callback-stack model for the same reason |

```bash
Signal.on KILL my_handler   # _Error: '...' is not supported — returns 1
Signal.on STOP my_handler   # same
Signal.on DEBUG my_handler  # same
```

For KILL/STOP alternatives:

- Trap `TSTP` (keyboard `Ctrl-Z` *request*) instead of `STOP` (kernel enforcement).
- Trap `TERM` (polite shutdown) instead of `KILL`. Well-behaved process managers
  send `TERM` first and only escalate to `KILL` if the process doesn't exit.

```bash
# CORRECT — trap the keyboard Ctrl-Z request:
Signal.on TSTP handle_suspend
```

For `DEBUG`/`RETURN`: the callback-stack model doesn't fit, but
[`Signal.returnTrap`](#signalreturntrap-signame-handler--into) builds a
caller-scoped `trap` command for exactly these (or use `trap ... RETURN`
directly).

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
names not present on the current OS) produce a warning in strict mode and
are silently skipped otherwise. All collection operations (`on`, `off`,
`list`, `pop`, `shift`, `clear`) and `Signal.dispatch` still work even
without a trap installed. Turn strict mode off when using synthetic signal
names in tests (`Signal.strict off`).

---

## Methods

### `Signal.strict [0|1|on|off]`

Set strict mode on (`1`/`on`/`true`, the default) or off (`0`/`off`/`false`).

When **on** (default):
- `Signal.on` warns if the signal name is invalid (trap refused by bash)
- `Signal.on` warns if the callback is not currently a defined function

When **off**: both of the above warnings are suppressed. KILL, STOP, DEBUG,
and RETURN are always rejected with an error regardless of this setting.

```bash
# Turn off for a test file that uses synthetic signal names:
Signal.strict off
Signal.on FAKE_SIG my_handler    # no warning
Signal.strict on

# Or inline for a single call:
Signal.strict off
Signal.on EXIT fn_defined_later
Signal.strict on
```

---

### `Signal.on signame callback`

Push a callback onto the top of the signal's LIFO stack. Installs the
signal's `trap` on the first registration.

```bash
Signal.on EXIT cleanup_tmpdir
Signal.on EXIT restore_terminal    # fires first on exit
Signal.on ERR  log_error
```

**Checks at registration time:**

- If `signame` is `KILL`, `STOP`, `DEBUG`, or `RETURN`, `Signal.on` returns
  non-zero with a descriptive error. No handler is registered. These four names
  are always rejected regardless of strict mode.
- If `signame` is otherwise invalid (bash rejects the trap), warns in strict
  mode. The callback is still registered; `Signal.dispatch` works manually.
- If `callback` is not currently a defined bash function, warns in strict mode.
  The registration proceeds — the function may be defined later before the
  signal fires. If it is not, the callback will silently fail at dispatch time
  (errors are suppressed per the error-resilience contract).

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

### `Signal.returnTrap [signame] handler` → `into=`

Build — but do **not** install — a `trap` command string for the **caller**
to run in its own function scope. Returns the command via `into=` (or stdout).

This is the escape hatch for the per-frame pseudo-signals (`RETURN`, `DEBUG`)
that `Signal.on` rejects, and it works for any signal name. Unlike the
callback-stack API, `returnTrap` excludes nothing — `RETURN` and `DEBUG` are
exactly what it exists for.

**Why a string instead of installing it?** A function cannot install a trap in
its caller's frame — bash's `trap` only ever affects the current execution
context. When you call `Signal.returnTrap`, the "current function" is
`Signal.returnTrap` itself, so a trap it set would fire on *its* return, not
yours. So it hands the command back and you install it where the trap must
actually live.

**Arguments:**

- One argument → treated as the handler; the signal defaults to `RETURN`.
- Two arguments → `signame handler`, for any spec (`RETURN`, `DEBUG`, `INT`,
  `EXIT`, `ERR`, ...).
- `once=1` (environment) → the returned handler clears its own trap after it
  fires.

**Install it in the caller's scope with `eval`:**

```bash
myMethod() {
  eval "$(Signal.returnTrap 'cleanup')"    # RETURN trap, scoped to myMethod
  # ... work ...
}                                           # 'cleanup' runs as myMethod returns
```

Or capture first, then eval (boop's no-subshell return path):

```bash
myMethod() {
  local __t; into=__t Signal.returnTrap DEBUG 'probe'
  eval "$__t"
  # ...
}
```

One-shot, self-clearing:

```bash
eval "$(once=1 Signal.returnTrap INT 'handle_once')"
```

**Always install with `eval`.** The handler is quoted with `printf %q` so it
reconstructs exactly when the shell parser re-reads it — which is what `eval`
does. Do **not** run the returned command through bare, unquoted command
substitution:

```bash
$(Signal.returnTrap 'cleanup')          # DON'T — works only by accident
```

That form *appears* to work for a trivial single-word handler (the `trap`
command does end up running in your frame), but it routes the string through
word-splitting and globbing instead of the parser. Any handler containing a
space, a quote, a glob character, or the `; trap - SIG` that `once=1` appends
is silently mangled. `eval "$(...)"` re-parses it correctly; the bare form does
not. A real `( ... )` subshell is worse — the trap either just prints or dies
with the subshell and never reaches the caller.

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

## Pre-existing Trap Survey

When Signal loads it scans the current trap table with `trap -p` and
internalizes any traps that were already set. Each pre-existing handler is
wrapped in a named function (`__Signal_legacy_SIGNAME`) and pushed onto the
bottom of the LIFO stack for that signal, so newly registered handlers still
fire first.

```bash
. boop           # load framework

# Set traps before Signal arrives:
trap 'rm -rf $tmpdir' EXIT        # bare code
trap my_existing_fn INT           # function name

. boop Signal    # Signal surveys and wraps both

# Add new handlers — these fire BEFORE the legacy ones:
Signal.on EXIT  my_new_cleanup
Signal.on INT   my_new_int_handler
```

On exit, the order is:
1. `my_new_cleanup` (registered last → fires first)
2. `__Signal_legacy_EXIT` wrapper → runs `rm -rf $tmpdir`

**Bare code is handled correctly.** The handler string from `trap -p` is in
bash's reusable quoted format. Signal wraps it with `eval` inside the legacy
function, so `$tmpdir` (or any other variable reference) is evaluated at the
time the handler fires, not at survey time. This matches the behavior the
original trap would have had.

**Ignored signals are not wrapped.** A signal ignored with `trap '' SIGNAME`
(empty handler) is left alone. Signal does not install a handler for it.

**Survey runs once at class load time.** Traps set after `. boop Signal`
are not automatically detected — use `Signal.on` for those.

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

### Caller-scoped RETURN cleanup

Run cleanup when *the current function* returns, without touching global signal
state. `Signal.on` can't do this — `RETURN` is rejected, and it's per-frame
anyway — so use [`Signal.returnTrap`](#signalreturntrap-signame-handler--into)
and install it with `eval`:

```bash
process_file() {
  local fd
  exec {fd}<"$1"
  eval "$(Signal.returnTrap "exec ${fd}<&-")"   # close fd on return, any path
  # ... read from $fd; early returns still trigger the close ...
}
```

The trap is scoped to `process_file` only: it fires on every return path and
does not leak to callers or sibling functions.

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
misspelled `EXITT`), `trap` returns non-zero and Signal warns in strict mode
but still creates the per-signal array. `Signal.dispatch` and all collection
operations work — useful for tests that use synthetic signal names. Disable
the warning with `Signal.strict off`.

**KILL, STOP, DEBUG, and RETURN are always rejected.** `Signal.on` returns
non-zero with a clear error for all four, regardless of strict mode. KILL/STOP
are unblockable OS signals; DEBUG/RETURN fire per-command or per-return and are
incompatible with the callback-stack model. For per-command hooks use
`trap ... DEBUG` directly; for a caller-scoped `RETURN`/`DEBUG` trap use
[`Signal.returnTrap`](#signalreturntrap-signame-handler--into).

**Undefined callback warning.** `Signal.on` checks `declare -f` at
registration time. This catches typos immediately rather than silently
failing at signal delivery time. The check runs only in strict mode (the
default); turn it off if you're registering handlers for functions defined
later in the file, or use `Signal.strict off` for that one call.

**Strict mode is global state.** `Signal.strict` sets a global flag
(`__Signal_strict`). Toggle it around a block that needs looser rules, then
restore it. The common pattern in test files is to call `Signal.strict off`
once at the top and `Signal.strict on` at the end.

**Pre-existing trap survey uses eval.** The `eval` call in
`__Signal.surveyExisting` is intentional and safe: it executes code that was
already registered as a trap handler and would have run regardless. The handler
string comes from bash's own `trap -p` output (trusted shell state, not user
input), and it is evaluated at dispatch time inside a wrapper function rather
than at survey time, so variable references like `$tmpdir` expand correctly
when the handler fires.

**Callback errors suppressed at dispatch time.** `2>/dev/null || true`
wraps each callback invocation. This means even a callback that calls `exit`
or crashes will not abort the dispatch loop. If a callback legitimately needs
to propagate an error, it should write to a shared variable and let the
calling code check it after dispatch.

**Class-level only — no instances.** Signal has no constructor. All methods
are static (`Signal.method args`). There is no reason to create a Signal
object; the handler stacks are process-global by nature.
