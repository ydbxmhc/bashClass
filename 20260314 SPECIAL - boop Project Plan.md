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
| `Float` | 49/49 | Fixed-scale decimal arithmetic |
| `Math` | 35/35 | Arbitrary precision; Machin pi to 50+ digits confirmed |

### Known Bugs (Fix Before Moving Forward)

- **`__bashClass_static` undeclared in `boop`.**
  Used by `Math` for result caching. Missing `declare -gA __bashClass_static`
  in `boop`'s globals section. Causes arithmetic syntax error on dotted cache keys.
  Fix: add one line alongside `__bashClass_classPath` declaration.
  *Confirmed by test — one line fixes all Math/pi tests.*

- **`pi(N)` display repeats a digit at some precision steps.**
  `pi(12)` and `pi(13)` display identically due to rounding consuming the last digit.
  Not a math bug — a display behavior. Consider printing unrounded value,
  or adding a note to `test_pi_growth` output. @@

- **`boop` distributed with Windows line endings (CRLF).**
  Upstream source control issue. Confirm `.gitattributes` enforces LF. @@

---

## Phase 1 — Polish Pass (Do This First)

*Class by class, completely, before building anything new.*

**Strategy:** One class per session. Read it cold. Mark every `@@`. 
Check that comments match behavior. Verify error messages help rather than confuse.
Confirm the interface is what you'd want if you'd never seen the internals.

**Order:**
1. `boop` — globals audit (static declaration is the known gap; look for others)
2. `Box` / `Cube` — fix the "adds defaults" comment lie in `Box.new`
3. `Container` / `List` / `Map` — iterator interface question (see Phase 2)
4. `Float` — review relationship to `Math`; are both needed long-term?
5. `Math` — static cache declaration, pi display, rawDiv/rawDivSmall comment parity

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
Slightly more involved — each node is itself an object (or a Map entry).
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

- `Box.new` comment says "adds defaults" — it doesn't. Fix or fulfill.
- `bdecode` TODO: `output=file` support for binary-safe round-trip
- `__bashClass.return` filesystem mode: `__bashClass.returnPath` from call stack introspection
- `boop` TODO: typecast interface variable naming convention (`_Input` vs `_input` etc.)
- Evaluate whether `Float` and `Math` should share a common base or converge
- Doubly-linked List: decide before implementing LinkedList @@
- `pi(N)` display: unrounded output vs. note in test @@
- `.gitattributes` LF enforcement @@
