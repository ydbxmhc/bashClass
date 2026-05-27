# boop Framework -- Gotchas

Things that will shoot you in the foot. Especially the subtle ones
that are hard to debug when you don't know what you're looking at.

See also [STANDARDS.md](STANDARDS.md) — particularly the Shell Options
section, which covers the same errexit/IFS/nounset patterns from the
"how to write it correctly" angle rather than the "what goes wrong" angle.

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

## `declare -g` Can't Punch Through a `local`

**The trap:** You have a global variable. A function declares a `local`
with the same name. That function calls another function which uses
`declare -g` to set the global. The global IS updated — but the calling
function can't see the change because its `local` shadows the global
for the entire duration of its scope.

```bash
declare -g name="original"

caller() {
  local name="mine"       # shadows the global within this function
  helper                   # helper sets the global via declare -g
  printf "%s\n" "$name"   # prints "mine" — the local wins here
}

helper() {
  declare -g name="from_helper"   # this DOES set the global...
}

caller
printf "%s\n" "$name"     # prints "from_helper" — the global WAS updated
```

The global changed. It's not lost. But the calling function never sees
it because `local name` takes priority within `caller`'s scope. After
`caller` returns, the global reflects the new value.

**Think of it like this:** `local` creates a sticky note over the
global. `declare -g` from a deeper function writes on the wall behind
the sticky note. The writing is there — you just can't see it until
the sticky note is removed (the function returns).

**When it bites:** `Args.parse` in script-context mode uses `declare -g`
to set option variables. If the caller happens to have a `local` with
the same name as one of the schema's option variables, the caller reads
its own (unchanged) local instead of the value Args just set.

**The guard:** Use prefixed variable names in schemas so they can't
collide with caller locals. Or use `into=` mode to get values back
from Args via a Config object — that sidesteps the whole issue because
the object ID is returned through `boop.pass`, not through a named global.

---

## `set -e` Kills on Innocent Patterns

**The trap:** Under `set -e` (errexit), any command that returns
non-zero terminates the shell — unless it's in a conditional context.
Several common bash patterns are silent killers:

### `[[ test ]] && action`

When the test is false, the `&&` short-circuits and the whole line's
exit code is 1. Under errexit, dead.

```bash
# KILLS under set -e when digits is NOT all zeros:
[[ "${digits//0/}" == "" ]] && neg=0

# SAFE — the || true makes the overall expression always succeed:
[[ "${digits//0/}" == "" ]] && neg=0 || true

# ALWAYS SAFE — if/fi is a conditional context, errexit never fires:
if [[ "${digits//0/}" == "" ]]; then neg=0; fi
```

This only matters at the top level of a function body. Inside an `if`
condition, a `while` condition, or the left side of `||`, errexit is
suppressed by bash's rules.

### `x && y || z` is not a ternary

This looks like if/then/else but it's two independent short-circuit
operators. If `y` fails, `z` runs — even though `x` succeeded.

```bash
# LOOKS like: if grep found it, print "yes", else print "no"
grep -q "pattern" file && printf "yes\n" || printf "no\n"

# ACTUALLY: if grep fails OR printf fails, print "no".
# If stdout is closed, printf fails → "no" prints even though grep matched.
```

*Even assignments* can fail!  
For real conditional logic, use `if/fi`. It's always safe, always clear,
and errexit never fires inside a conditional context:

```bash
# ALWAYS CORRECT regardless of set -e, y's exit code, or anything else:
if grep -q "pattern" file; then
  printf "yes\n"
else
  printf "no\n"
fi
```

### `(( arithmetic ))` as a standalone statement

Arithmetic expressions return their truth value as an exit code.
`(( 0 ))` returns 1. The classic gotcha:

```bash
# KILLS on first iteration when count is 0:
(( count++ ))    # evaluates to 0 (old value) → exit 1

# SAFE — pre-increment evaluates to 1:
(( ++count ))

# SAFE — addition always evaluates to the new value:
(( count += 1 ))
```

But post-increment is fine in contexts where the exit code doesn't
matter:

```bash
arr[n++]=$x      # assignment succeeds; arithmetic is internal
```

**The meta-lesson:** Under `set -e`, every statement's exit code
matters. If a statement can legitimately return non-zero in normal
operation, it needs protection. `if/fi` is always the safest choice —
it creates a conditional context where errexit is suppressed by
bash's own rules. `|| true` is the lightweight alternative when you
just need to neutralize a false-branch exit code.

---

## IFS Isn't Always What You Think

**The trap:** The user may have set IFS to anything before sourcing
boop. Colon (for PATH parsing), empty (to prevent splitting), equals
sign, pipe — all are real-world values. Any code that does word
splitting (`$*`, unquoted `$var`, `for x in $string`) or array
joining (`"${arr[*]}"`) without explicitly setting IFS will break.

```bash
# User has IFS=':' — this joins args with colon, splits on colon:
local input="$*"
for token in $input; do ...    # tokens split on ':' not space

# SAFE — local IFS scopes it to this function, restores on return:
local IFS=$' \t\n'
local input="$*"
for token in $input; do ...    # always splits on whitespace
```

`local IFS=...` is the correct pattern. It scopes IFS to the function
without touching the caller's value. No save/restore needed — bash
handles it automatically on function return.

**Where this bit us:** `boopClass` token parsing. With `IFS=':'`, the
multi-argument class declaration was joined and split on colons instead
of spaces, producing garbage tokens. Fixed by `local IFS=$' \t\n'` at
the top of `__boopClass.parseTokens`.

---

## `unset` Inside Nested Functions May Not Reach Globals

**The trap:** `unset varname` inside a function removes the variable
from the *current scope*. If there's a local with that name in any
enclosing function on the call stack, `unset` peels off that layer
instead of reaching the global. Multiple `unset` calls peel multiple
layers — but you can't reliably predict how many layers deep you are.

**When it bites:** Object destruction. A `_destroy` hook tries to
`unset` a companion array that was `declare -ga`'d at global scope.
If the destroy is called from deep in a call chain, the unset might
not reach the global.

**The guard:** Destroy companion arrays from the same scope depth
that created them (the object's own `_destroy` hook), or use
`_Delegate $obj.destroy` which goes through the public interface
and keeps the call chain shallow.


---

## Fork Bomb Awareness (the `:` joke)

Yes, `:(){ :|:& };:` is one line. No, we don't do that here.

The broader point: bash makes it trivially easy to create runaway
processes, infinite loops, and resource exhaustion. The framework
can't protect against all of these, but:

- Never use `&` (background) in framework code without a clear
  lifecycle plan for the child process
- Never recurse without a depth guard
- Never `while true` without a break condition that's guaranteed
  to eventually fire
