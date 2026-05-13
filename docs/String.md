# Text.String — String Objects

A string object class for the boop framework. Wraps a string value and
exposes a consistent method surface for transformation, inspection, and
pipeline composition.

**Before you use this class, read the performance section below.** It
exists to explain when Text.String is the right tool and when it is not.
Using it in the wrong place is slower for no benefit; using it in the
right place pays for itself many times over.

---

## Quick Start

```bash
. boop Text::String

into=s Text.String.new "  Hello, World!  "

$s.trim                         # mutates in place
into=v $s.read                  # "Hello, World!"
into=v $s.raw                   # "  Hello, World!  " (original, never changes)

into=s2 $s.downcased            # new object; $s unchanged
into=v $s2.read                 # "hello, world!"

$s.do "trim,downcase,capitalize"     # bare pipeline: mutates $s
into=s3 $s.do "trimmed,downcased"    # -ed pipeline: new object
```

---

## Design Rationale and Performance

### What this class actually is

Text.String is a **convenience and reuse layer**, not a new capability.
Every operation it provides — trimming whitespace, changing case,
padding, finding substrings — is already available in bash through
parameter expansion, built-in operators, and arithmetic. The class adds
no functionality that bash does not already have.

What it adds instead:

- **A consistent interface** — the same calling convention as everything
  else in the framework. `into=v $s.trim` reads the same as `into=v
  $box.volume`.
- **A single tested implementation** — one `trim` that is tested once.
  Ten classes that need to trim a string share that implementation
  rather than each inlining their own parameter expansion.
- **Composable pipelines** — `do` chains multiple operations with type
  checking and a single object allocation, making multi-step string
  transformations readable at the call site.
- **Mixin capability** — any class with a primary string value can mix
  in Text.String and inherit the full manipulation surface without
  reimplementing it.

### The performance cost

Using Text.String is **strictly slower** than inline parameter expansion
for any individual operation. The overhead comes from several layers:

1. **Object creation** (`new`): allocates a descriptor, stores two
   properties (`value` and `raw`), registers with the boop runtime.
2. **Method dispatch**: every `$s.trim` call resolves through the MRO,
   locates `Text.String.trim`, and enters a function frame.
3. **Property access**: every internal `get`/`set` is a descriptor read
   or write — a hash lookup, not a variable access.
4. **The `-ed` forms**: each creates a full new object (via `new`) in
   addition to the dispatch and property overhead of the transform.

For a single `trim` on a one-off string, raw parameter expansion is
faster by an order of magnitude:

```bash
# Fast: direct, zero overhead
v="${v#"${v%%[![:space:]]*}"}"
v="${v%"${v##*[![:space:]]}"}"

# Slow: three function calls, two property writes, one descriptor lookup
into=s Text.String.new "$v"
$s.trim
into=v $s.read
```

### When the cost pays for itself

**Code reuse across many callers.** If you find yourself writing the
same trim-downcase-replace pattern in five constructors, those five
copies will contain bugs independently. One implementation tested once
and called everywhere is worth more than the cycles you save inlining
it. The framework's own classes are the primary beneficiaries of this.

**Multi-step pipelines.** `do` amortizes the dispatch overhead across
all operations in the chain. Five transforms via `$s.do
"trim,downcase,capitalize,replace:foo:bar,rpad:40"` pays one `do` call
plus five bare function calls on a single object — cheaper than five
separate object-mode `-ed` chains, and with type checking enforced.

**Non-hot code paths.** Constructors, initialization, configuration
loading, formatting for output — these run once or a handful of times.
At that frequency, the overhead is immeasurable in practice. The
readability and correctness benefits are real; the performance cost is
not.

**As a mixin.** When a class mixes in Text.String to operate on its own
string-valued property, the overhead is paid in the class's methods
where string manipulation already dominates the cost. The mixin surface
replaces per-class reimplementation with a shared, tested layer.

### When to avoid it

- **Inside tight loops.** If you are processing thousands of strings in
  a loop, inline parameter expansion. The per-call overhead accumulates.
- **Inside the framework's own internals.** The core `boop` runtime,
  `Args.parse`, and other framework-level code avoid framework
  abstractions to keep their own overhead minimal.
- **For a single one-shot transform.** `${v^^}` is one character and
  zero overhead. `$s.upcase` is not worth the ceremony for a value you
  use once and discard.

The rule of thumb: if you would reach for a private helper function to
avoid repeating string logic, reach for Text.String instead.

---

## Method Reference

### Constructor

```bash
into=s Text.String.new "value"
```

Creates a new String object storing `value` as both the current value
and the immutable original. The original is accessible via `raw` for
the lifetime of the object regardless of subsequent mutations.

---

### Getters

#### `read`

```bash
into=v $s.read
```

Returns the current string value. Reflects all mutations made since
construction.

#### `raw`

```bash
into=v $s.raw
```

Returns the original string as passed to `new`. Never changes, even
after mutations. Useful for audit trails, undo implementations, or
anywhere the provenance of a value matters.

```bash
into=s Text.String.new "  Hello  "
$s.trim
$s.upcase
into=v $s.read   # "HELLO"
into=v $s.raw    # "  Hello  "
```

---

### Read-Only Queries

These never modify `$s` and never return a new object. They return a
value or an exit code.

#### `length`

```bash
into=n $s.length
```

Returns the byte length of the current value.

#### `isEmpty`

```bash
$s.isEmpty && printf "nothing here\n"
```

Returns exit code 0 if the current value is the empty string, 1
otherwise. Does not print anything.

#### `contains`

```bash
$s.contains "needle" && printf "found\n"
```

Returns 0 if the current value contains the literal string `needle`,
1 otherwise.

#### `startsWith`

```bash
$s.startsWith "prefix"
```

Returns 0 if the current value begins with `prefix`.

#### `endsWith`

```bash
$s.endsWith "suffix"
```

Returns 0 if the current value ends with `suffix`.

#### `indexOf`

```bash
into=i $s.indexOf "needle"
```

Returns the zero-based byte offset of the first occurrence of `needle`
in the current value, or `-1` if not found.

```bash
into=s Text.String.new "hello world"
into=i $s.indexOf "world"   # 6
into=i $s.indexOf "xyz"     # -1
into=i $s.indexOf "hello"   # 0
```

#### `substr`

```bash
into=v $s.substr offset [length]
```

Returns a substring starting at `offset`. If `length` is given, returns
at most that many bytes. Both values are zero-based.

```bash
into=s Text.String.new "hello world"
into=v $s.substr 6       # "world"
into=v $s.substr 0 5     # "hello"
into=v $s.substr 6 3     # "wor"
```

---

### Bare Mutators

Bare mutators edit the current value **in place** and return an exit
code only. They do not return the new value; use `read` after mutation
if you need it.

| Method | Effect |
|---|---|
| `trim` | Remove leading and trailing whitespace |
| `upcase` | Convert all characters to uppercase |
| `downcase` | Convert all characters to lowercase |
| `capitalize` | Uppercase the first character only |
| `decapitalize` | Lowercase the first character only |
| `reverse` | Reverse the string character by character |
| `append suffix` | Append `suffix` to the end |
| `prepend prefix` | Prepend `prefix` to the beginning |
| `replace from to` | Replace all occurrences of `from` with `to` |
| `lpad width [char]` | Left-pad to `width` with `char` (default: space) |
| `rpad width [char]` | Right-pad to `width` with `char` (default: space) |
| `center width [char]` | Center within `width` with `char` (default: space) |
| `fold width` | Wrap words at `width` columns (default: 80) |

Padding methods are no-ops if the current value is already at or wider
than `width`. They do not truncate.

`fold` wraps on word boundaries, inserting newlines. It does not split
words that are longer than `width`.

```bash
into=s Text.String.new "  HELLO, WORLD.  "
$s.trim
$s.downcase
$s.capitalize
into=v $s.read          # "Hello, world."
into=v $s.raw           # "  HELLO, WORLD.  "
```

---

### `-ed` Forms

Every bare mutator has a corresponding `-ed` form that returns a **new
Text.String object** with the transformation applied. The original
object is not modified.

| Bare | `-ed` form |
|---|---|
| `trim` | `trimmed` |
| `upcase` | `upcased` |
| `downcase` | `downcased` |
| `capitalize` | `capitalized` |
| `decapitalize` | `decapitalized` |
| `reverse` | `reversed` |
| `append` | `appended` |
| `prepend` | `prepended` |
| `replace` | `replaced` |
| `lpad` | `lpadded` |
| `rpad` | `rpadded` |
| `center` | `centered` |
| `fold` | `folded` |

Arguments are forwarded unchanged from the `-ed` form to its bare
counterpart.

```bash
into=s Text.String.new "  hello  "
into=s2 $s.trimmed
into=v $s.read    # "  hello  "  (unchanged)
into=v $s2.read   # "hello"      (new object)

into=s3 $s2.replaced "hello" "world"
into=v $s3.read   # "world"
```

The `-ed` form internally creates one clone of the current value, applies
the corresponding bare mutator to the clone, and returns the clone. No
intermediate objects are created.

---

### `do` — Pipeline Executor

```bash
$s.do "op,op,op:arg"                  # bare pipeline
into=s2 $s.do "opped,opped,opped:arg" # -ed pipeline
```

Executes a comma-separated sequence of operations in a single call.
Operations are separated by `,`. Arguments to an operation are separated
from the name and from each other by `:`.

```bash
$s.do "trim,downcase,capitalize"
$s.do "replace:hello:world,upcase"
$s.do "lpad:20:*,rpad:30"
```

#### Type homogeneity

A pipeline must be **uniformly bare or uniformly `-ed`**. Mixing the two
is a hard error:

```bash
$s.do "trim,downcased"    # CRASH: type mismatch
```

This is enforced because the two families have different return
contracts. A bare pipeline mutates `$s` and returns an exit code; an
`-ed` pipeline returns a new object and leaves `$s` unchanged. Allowing
mixing would make the return type of `do` unpredictable.

#### Performance

`do` is the most efficient way to apply multiple transformations. A bare
`do` pipeline pays one `do` dispatch overhead plus one function call per
operation, and performs all mutations on the same object. An `-ed` `do`
pipeline clones the current value once, applies all bare mutators to the
clone, and returns it — a single object allocation regardless of how
many operations are in the pipeline.

Compare the two approaches for five operations:

```bash
# Five -ed chains: five object allocations, five dispatches
into=s2 $s.trimmed
into=s3 $s2.downcased
into=s4 $s3.capitalized
into=s5 $s4.replaced "foo" "bar"
into=s6 $s5.rpadded 40

# One -ed do: one object allocation, one do dispatch, five bare calls
into=s2 $s.do "trimmed,downcased,capitalized,replaced:foo:bar,rpadded:40"
```

---

## As a Mixin

Text.String can be mixed into any class that has a primary string value,
giving it the full manipulation surface without reimplementation.

```bash
boopClass Slug '
  has:value,raw
  mixin:Text.String
  public:new
'
```

The mixin attaches all Text.String methods to `Slug` instances. A
`Slug` object responds to `trim`, `trimmed`, `do`, `read`, `raw`, and
all other Text.String methods directly, operating on its own `value`
property.

This is the highest-leverage use of the class: a shared, tested string
manipulation layer that any string-valued type can inherit at zero
implementation cost.

---

## Design Notes

### Naming convention: bare vs `-ed`

The two-family naming convention follows the same principle as Python's
`list.sort()` vs `sorted(list)` and Ruby's `sort!` vs `sort`.

- **Bare verbs** signal mutation: "do this to the thing."
- **Past-tense adjectives** signal a new value: "give me the thing as
  it would look if this were done to it."

The convention is grounded in English grammar and carries the semantics
without any framework ceremony. A reader who has never seen Text.String
before can correctly guess what `$s.trimmed` returns.

`decapitalize`/`decapitalized` are longer than the others because they
describe a less common operation. This is intentional: name length
should track usage frequency. Short names for common operations
(`trim`, `read`); longer names for rare ones (`decapitalize`). The
asymmetry is a feature, not an accident.

### `raw` as an audit anchor

Storing the original value costs one extra property write at
construction time and negligible ongoing memory. The benefit is that
any code receiving a Text.String object can always recover the
unmodified input, regardless of what transformations have been applied.
This is useful for logging, error messages, undo, and any context where
"what did this start as?" has meaning.

### Why `do` enforces type homogeneity

The bare and `-ed` families have incompatible return contracts. A bare
`do` returns an exit code; an `-ed` `do` returns an object. If both
types were allowed in the same pipeline, the caller would need to
inspect the pipeline string at runtime to know what to do with the
result — or silently discard one of the two possible outputs. Crashing
on a mixed pipeline catches the mistake at the call site where it is
cheapest to fix.

### `fold` and word splitting

`fold` splits on whitespace using bash word splitting (`for word in
$v`). This means runs of whitespace collapse to single spaces in the
output, which is usually the right behavior for prose text. It does not
split mid-word: a word longer than `width` appears on its own line and
exceeds the width limit. This matches the behavior of the Unix `fold -s`
flag.

### What is not here

**`split`** is absent from the current implementation because it changes
the type of the result from a string to a sequence. The right return
type for `split` is a `Collection.List`, and that dependency has not
been established yet. When it is, `split` will return a List object and
live here alongside the rest of the interface.

**Case-folding for Unicode** is not implemented. `upcase`, `downcase`,
`capitalize`, and `decapitalize` use bash's `^^`, `,,`, `^`, and `,`
operators, which operate on bytes and handle only ASCII case mapping
reliably. Full Unicode case folding requires external tooling and is
beyond scope for a pure-bash implementation.

**Regex operations** (`match`, `grep`, `sed`-style substitution) are
not implemented. Bash's `=~` and `${v/pattern/replacement}` cover the
common cases. A richer regex surface would likely live in a separate
`Text.Regex` class.
