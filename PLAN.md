# boop — Project Plan

*Working document. @@ marks incomplete or needs-work items.*

---

## Current Status

### What Exists and Passes Tests

| Component | Tests | Notes |
|-----------|-------|-------|
| `boop` (core framework) | — | Dispatch, registry, encoding, return handler, import system |
| `Box` / `Cube` | 14/14 | Example classes; good interface model |
| `Container` / `List` / `Map` | 88/88 | Full collection layer, nested structures work |
| `Math` | 75/75 | Arbitrary precision; fast path for ≤18 digits; Machin pi verified to 50+ digits |
| `test_stress` | 132/132 | Framework adversarial tests |
| `test_pi_growth` | — | Incremental pi benchmark (runs until >10s/digit) |

### Removed

| Component | Reason |
|-----------|--------|
| `Float` | Fully superseded by Math. Math's native integer fast path covers Float's entire use case (auto-selects `$(( ))` for operands ≤18 digits). No external consumers — clean removal. |

### Recently Completed

- **Chunked arithmetic** (strAdd/strSub/strMul process 9 digits at a time)
- **printf octal bug** fixed in strAdd/strSub (zero-padded strings into `local -i`)
- **Raw triple arithmetic** (rawAdd/rawSub/rawMul/rawDiv bypass object system for hot loops)
- **Math static API** — full-word names, value returns, symbol aliases, Math.DO (infix), Math.RPN (postfix)
- **Fast path** — native `$(( ))` for add/sub/mul/div/mod when operands fit in 64-bit
- **New Math methods** — mod, pow, square, toScale, format; symbol aliases `%`, `^`
- **Regex/printf optimization pass** across entire codebase (Float, Math, boop)
- **`set -u` removed from boop** — framework no longer alters caller's shell options
- **`.gitattributes`** — `* text=auto eol=lf` enforced
- **`__bashClass_static`** declared in boop for cross-class caching
- **Float removed** — deleted class, tests, docs, log file
- **Global rounding removed** — `__Math_round` and `__Math.setRound` eliminated entirely. All operations truncate. Rounding is opt-in via explicit `Math.round` / `$obj.round N` only.
- **strDiv leading-zero bug** fixed — quotient digits past decimal that were zero got included in digit string (e.g., 1/25 → digits `04`), risking octal interpretation
- **Arctan precision padding** — exact divisions like 1/5=0.2 now padded to full working precision so power accumulator carries precision through multiplies
- **Math.round banker's rounding bug** fixed — replaced `printf '%.0f'` (round-to-even) with direct `>= 5` check for true half-up
- **toScale carry fix** — rounding carry (e.g., 999.999→1000) now preserves requested decimal places
- **Box.new comment lie** fixed
- **docs/** created for all classes (Box, Cube, Container, List, Map, Math)

### Known Bugs — None Currently

All previously tracked bugs have been fixed:
- ~~`__bashClass_static` undeclared~~ — added to boop
- ~~`pi(N)` display repeats~~ — was caused by global rounding; removed entirely
- ~~CRLF line endings~~ — `.gitattributes` enforces LF

---

## Phase 1 — Polish Pass ✓ DONE

All classes audited. Comments match behavior. Error messages reviewed.
`Box.new` comment fixed. Doc comments added to all raw arithmetic helpers.

---

## Phase 2 — Collection Primitives

*Roughly in order of effort, all building on existing Container/List foundations.*

### Stack
Classic LIFO. Constrain List: expose `push`, `pop`, `peek`, `isEmpty`.
Hide `shift`, `unshift`, `get`-by-index. One morning's work.

### Queue
Classic FIFO. Expose `enqueue` (push), `dequeue` (shift), `peek`, `isEmpty`.
Possibly `size`. Half a morning's work once Stack is done.

### LinkedList
Each node is itself an object (or a Map entry).
Requires `insertAt`, `removeAt`, `next`/`prev` traversal.
Consider whether doubly-linked is worth the complexity at this stage. @@

### Set
Unique unordered collection. Implement on top of Map keys — values are irrelevant,
keys are the members. Expose `add`, `has`, `remove`, `toArray`, `union`, `intersect`.
Arguably simpler than LinkedList.

### Iterator Protocol
The gap that will hurt most if deferred too long.
A common `each` method on `Container` taking a callback function name would let
any function traverse any container without knowing its type.
Enables writing generic algorithms — sort, filter, map, reduce — once,
for everything.

**Suggested interface:**
```bash
$list.each "my_callback_fn"     # calls my_callback_fn index value
$map.each "my_callback_fn"      # calls my_callback_fn key value
```

---

## Phase 3 — String Class

Heavy string work is happening natively everywhere. A proper wrapper would clean
up a lot of downstream code and give callers a consistent interface.

**Minimum useful interface:**
`trim`, `split`, `join`, `contains`, `startsWith`, `endsWith`, `replace`, `length`,
`toUpper`, `toLower`, `substring`

All implementable in pure bash parameter expansion — no forks, no subshells.
Fits the framework's no-external-dependencies philosophy perfectly.

---

## Phase 4 — Infrastructure

*Do these when the collection layer is solid, before any public-facing push.*

### BOOP_CLASSPATH
Colon-delimited environment variable for class file search paths.
Current resolution order: classPath registry → `__bashClass_dir` → PATH.
Add BOOP_CLASSPATH between classPath registry and `__bashClass_dir`.
Enables separate-repo class libraries without hand-registration.

### Version Declaration
```bash
declare -gr __bashClass_version="0.1.0"
```
No enforcement needed yet. Lets downstream scripts check compatibility.
Semantic versioning from the start — worth the five seconds it takes.

### README Expansion
Current README is good. Needs:
- Explicit bash 5+ requirement *and why* (macOS ships 3.2, GPL3 issue)
- Known performance characteristics (Math/pi digits-per-second ballpark)
- BOOP_CLASSPATH documentation once it exists
- Brief "how to write a class" walkthrough beyond the quick example

---

## Phase 5 — I/O Classes (Deferred)

The idea is interesting. `read` has real limitations for high-record-count streams.
No use-case pressure yet — flag and revisit when something concrete drives the need. @@

---

## Install Story

Current: `git clone` + ensure top-level directory is in PATH.
Only external dependency: `base64` (coreutils), only for binary-safe encode/decode.
Everything else is pure bash 5+.

This is honest and sufficient for now. Do not complicate it until there's a reason.

---

## Promotion Considerations

**Audience that exists and is underserved:**
- Containerized/minimal Linux environments where "install perl" isn't an option
- Embedded systems and tooling with bash available but nothing else
- Anyone who needs non-trivial math in bash without farming to `awk`/`bc`/`perl`

**The macOS problem:**
Apple ships bash 3.2 (GPL2). Associative arrays require bash 4+; `local -I`,
`EPOCHREALTIME`, and several other features require bash 5+.
This cuts a meaningful chunk of potential users. State it clearly and up front.
`brew install bash` solves it, but users need to know they need to solve it.

**The veteran reaction:**
Expected. Probably useful for visibility.
Post it with a straight face and let the thread do the work.

---

## Running Notes / @@ Backlog

- `bdecode` TODO: `output=file` support for binary-safe round-trip
- `__bashClass.return` filesystem mode: `__bashClass.returnPath` from call stack introspection
- `boop` TODO: typecast interface variable naming convention (`_Input` vs `_input` etc.)
- Doubly-linked List: decide before implementing LinkedList @@
- Clean up `REFACTOR_STATUS.md` — largely superseded by this file @@
- Clean up stale log files (`math_out.log`, `pi_growth.log`, `tc_debug.log`) @@
- `test_matrix` — not in the test count table; verify it still runs @@

