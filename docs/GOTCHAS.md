# boop Framework -- Gotchas

Things that will shoot you in the foot. Especially the subtle ones
that are hard to debug when you don't know what you're looking at.

---

## Environment Prefix Leakage (`into=`, `_EOL=`, etc.)

**The trap:** Bash's dynamic scoping means environment variable prefixes
on a command are visible to EVERY function that command calls internally.
If you write:

```bash
into=s Stream.new -P "file" -f ':' name age
```

...then `into=s` is visible not just to `Stream.new`, but to every
function `Stream.new` calls: `Args.parse`, `__boop.new`, `Config.set`,
etc. If any of those functions check `into` and change their behavior
based on it (Args does -- it switches to object-return mode), you get
silent, baffling misbehavior.

**The same applies to:** `_EOL=`, `_Delimiter=`, `_LogLevel=`, `_Class=`,
or any other inline prefix. If the function you're calling also calls
other functions that inspect those variables, the prefix leaks downward.

**The guard:** At the top of any method that (a) receives `into=` from
its caller AND (b) calls other framework code internally, save and
clear:

```bash
MyClass.new() {
  local __MyClass_new_into="${into:-}"; into=''
  # ... all internal work, subcalls, Args.parse, etc. ...
  # into is empty here -- nothing downstream sees it
  boop.pass "$_Self" ${__MyClass_new_into:+$__MyClass_new_into}
}
```

Two lines. The method owns its return target. Nothing downstream is
confused by a leaked `into`.

**When you DON'T need this:** If your method doesn't call other
framework code that inspects `into` (most simple methods just do
their work and call `boop.pass` at the end), the prefix works fine
as-is. The leak only matters when there's a function in the middle
that ALSO checks `into` and changes behavior.

**Why we can't fix this at the framework level:** Bash has no lexical
scoping. There's no way to say "this prefix is only for the final
boop.pass." Every solution (stacks, traps, consume-on-use) either
adds unacceptable overhead to the hot path or requires the same
discipline this guard requires. We chose the simplest correct answer.

---

## `read` Drops the Last Record Without a Trailing Delimiter

**The trap:** `while read line; do ... done < file` silently skips the
last line if the file doesn't end with a newline. `read` returns
non-zero on EOF even if it read data, so the loop exits before
processing the final record.

**The classic workaround:**
```bash
while read line || [[ -n "$line" ]]; do ... done < file
```

**With Stream:** `$s.read` handles this internally -- it returns 0 if
data was read, even when `read` returned non-zero. You don't need the
`|| [[ -n ]]` workaround. This is an intentional LSP divergence from
raw `read` in favor of correctness. See `docs/Stream.md` for details.

---

## `${array[*]}` Joins on IFS

**The trap:** `"${array[*]}"` joins array elements using the first
character of `$IFS`. If IFS has been changed (or is empty), your
joined string is wrong. This is especially dangerous in framework
code where IFS might be anything.

**The guard:** Always use `"${array[@]}"` for iteration. If you
genuinely need a joined string, set IFS explicitly inline:

```bash
IFS=',' printf '%s' "${array[*]}"   # explicit join on comma
```

Never assume IFS is at its default value.

---

## Here-String (`<<<`) Appends a Newline

**The trap:** `<<< "$data"` always appends a trailing newline to the
input. If your data doesn't have one, the receiving command sees an
extra byte.

**When it matters:** Byte-exact input processing, checksums, binary-ish
data. For line-oriented text processing it's usually harmless (the
extra newline just means `read` has a clean delimiter to stop on).

**The guard:** Use `printf '%s' "$data" |` or process substitution
`< <(printf '%s' "$data")` when you need exact bytes.

---

## `declare -g` Inside a Function vs `local` in the Caller

**The trap:** `declare -g varname=value` inside a called function
creates a global variable. But if the CALLING function has a `local`
with the same name, the caller can't see the global -- the local
shadows it. This makes `declare -g` unreliable for communicating
values back to a caller.

**When it bites:** Args.parse uses `declare -g` to set option
variables in script-context mode. If the caller already has a `local`
with the same name as an option, the value is invisible.

**The guard:** Use prefixed variable names in schemas (e.g.
`__Stream_new_blockSize` instead of `blockSize`) so they can't
collide with caller variables. Or use `into=` mode to get values
back via a Config object instead of globals.

---

## Fork Bomb Awareness (the `:` joke)

Yes, `:(){ :|:& };:` is one line. No, we don't do that here. But
the broader point: bash makes it trivially easy to create runaway
processes, infinite loops, and resource exhaustion. The framework
can't protect against all of these, but:

- Never use `&` (background) in framework code without a clear
  lifecycle plan for the child process
- Never recurse without a depth guard
- Never `while true` without a break condition that's guaranteed
  to eventually fire

