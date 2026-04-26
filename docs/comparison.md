# boop — Language Comparison and Benchmarks

Running document. Benchmarks are collected opportunistically; each entry
notes the platform and date when possible. `@@` marks sections with
missing data or open questions.

All boop timings were collected on the development machine (Linux 6.18,
bash 5.x). Python 3, Ruby 3.x. Times are wall-clock; no CPU pinning.
Treat them as order-of-magnitude guidance, not precise measurements.

---

## Model Overview

| | boop | Python | Ruby | Perl | Node |
|---|---|---|---|---|---|
| **OOP style** | prototype-ish, explicit dispatch | class-based | class-based | blessed refs | prototypal |
| **Precision math** | chunked base-10⁹ in bash | native bignum (C) | native bignum (C) | Math::BigInt | BigInt |
| **Subprocess model** | zero-fork | subprocess / native | subprocess / native | subprocess / native | child_process |
| **Primary use** | bash scripts that need OOP | general purpose | general purpose / scripting | text / system | JS ecosystem |
| **Object overhead** | ~3ms per object | <0.1µs | <0.1µs | ~10µs | <1µs |
| **Method dispatch** | ~4ms per call | ~0.1µs | ~0.1µs | ~1µs | ~0.1µs |

The object overhead is not a bug — it's the cost of `eval`'ing 30+ per-object
wrapper functions at creation time. This is a deliberate trade for zero-dispatch
overhead at call time (one-hop to the class function, no hash lookup). For
scripts that create tens of objects, not thousands, it doesn't matter.

---

## OOP Syntax

### Object Creation

```bash
# boop
into=rect new Box length=5 width=3 height=7
into=deck new Deck

# Python
rect = Box(length=5, width=3, height=7)
deck = Deck()

# Ruby
rect = Box.new(length: 5, width: 3, height: 7)
deck = Deck.new

# Perl (Moose)
my $rect = Box->new(length => 5, width => 3, height => 7);
```

### Method Calls

```bash
# boop
into=vol $rect.volume
$deck.shuffle
into=card $deck.draw

# Python
vol = rect.volume()
deck.shuffle()
card = deck.draw()

# Ruby
vol = rect.volume
deck.shuffle
card = deck.draw
```

### Inheritance

```bash
# boop: extend= on import
. boop Box
# Cube extends Box — declared in Cube's class file:
#   __boop_registry["Cube"]="...|parent=Box|..."

# Python
class Cube(Box):
    pass

# Ruby
class Cube < Box; end
```

### Return Values

This is where boop diverges most sharply. Python and Ruby have a single
return value mechanism. boop has three, matching the three contexts where
bash runs:

```bash
# boop -- caller controls where the value goes
into=vol $rect.volume    # nameref: zero-copy write into 'vol'
$rect.volume             # stdout: captured by $() or redirected
_OutMode=global $rect.volume; echo "$_Out"  # side channel: $_Out

# Python / Ruby -- always a return value; caller chooses what to do with it
vol = rect.volume()      # assignment
print(rect.volume())     # inline
```

The `into=` form is the preferred path. It is zero-fork, zero-copy. No
subshell opens; the value is written directly into the caller's variable
via bash nameref. The `$()` form opens a subshell (fork + exec), which is
fast in Python/Ruby (it's how their C code runs) but costly in bash — every
`$()` is a full process creation.

### isa / isinstance

```bash
# boop
$obj.isa Box          # exit code 0/1
$obj.class            # prints class name

# Python
isinstance(obj, Box)
type(obj).__name__

# Ruby
obj.is_a?(Box)
obj.class
```

---

## Precision Arithmetic

### What Each Language Does

| | ≤18 digits | >18 digits |
|---|---|---|
| **boop** | native `$(( ))` (64-bit, instant) | chunked base-10⁹ in bash |
| **Python** | native C integer | native C bignum (seamless) |
| **Ruby** | native C Fixnum | native C Bignum (seamless) |
| **Perl** | native C (doubles) | Math::BigInt (XS or pure Perl) |
| **bash / bc** | `$(( ))` only | `echo "expr" \| bc` subprocess |

Python and Ruby use native C bignum. There is no threshold — the language
handles all sizes transparently, in compiled code, at native speed. boop
uses bash arithmetic for small numbers and chunked string arithmetic for
large ones. It is not competitive on throughput.

The question boop answers differently: **can you do arbitrary-precision
math in bash without forking an external process?** Yes. Whether you should
depends on what else your script is doing.

### Benchmark: Addition

Measured on development machine.

| Operation | boop | Python | Ruby | bc (per-fork) |
|---|---|---|---|---|
| add 9-digit × 1000 | 4300ms | 0.08ms | 0.04ms | ~2500ms |
| add 20-digit × 100 | 490ms | 0.008ms | <0.01ms | ~310ms |

The boop column is dominated by method dispatch overhead (~4ms/call), not
arithmetic. The arithmetic itself (`$(( ))` for ≤18 digits) runs at 2µs per
operation — about 20ms for 10,000 iterations. The dispatch chain around it
costs 100× more than the arithmetic.

bc is faster per operation than boop (~2.5ms fork vs ~4ms boop call) for
simple arithmetic. boop's advantage is not raw throughput — it's integration:
a Math object persists across operations, carries scale and sign, and
participates in the class system without needing external tools to be present.

### Benchmark: Pi

| Digits | boop | Python (Decimal) | Ruby (BigDecimal) |
|---|---|---|---|
| 50 | 12s | <1ms | 0.3ms |
| 100 | 49s | <1ms | <1ms |

boop pi uses the Machin formula, same as the Python reference implementation
above. The difference is C vs bash string arithmetic. This is expected.

The boop pi implementation is useful for: verifying the Math implementation,
demonstration, and scripts that need a handful of pi digits and cannot or
will not invoke external tools.

---

## Zero-Fork Philosophy

boop's `into=` return system exists specifically to avoid subshells. In bash,
`$()` forks a process. For a single call that's fast. For a loop over
thousands of objects, the cost accumulates.

```bash
# Subshell path (slow) -- forks per call
for obj in "${objects[@]}"; do
    vol=$(${obj}.volume)
    total=$(( total + vol ))
done

# into= path (fast) -- zero-fork
for obj in "${objects[@]}"; do
    into=vol ${obj}.volume
    (( total += vol ))
done
```

Python, Ruby, and Perl don't have this concern. Their method calls return
values natively in the same process. The `into=` design is a bash-specific
optimization for a bash-specific problem.

### When subshell overhead matters

| Call rate | `$()` penalty | Verdict |
|---|---|---|
| < 100 calls/script | negligible | use whichever reads better |
| 100–1000 calls | noticeable | prefer `into=` |
| > 1000 calls | significant | `into=` required for performance |

---

## Object Lifecycle

| | boop | Python | Ruby |
|---|---|---|---|
| **Create** | `into=obj new ClassName` | `obj = ClassName()` | `obj = ClassName.new` |
| **Destroy** | `$obj.destroy` (explicit) | GC (automatic) | GC (automatic) |
| **Identity** | string ID (`_abc123`) | object reference | object reference |
| **Serialization** | bencode descriptor | pickle / json | Marshal / yaml |

boop objects are not garbage collected. `$obj.destroy` removes the registry
entry and undefines all baked wrapper functions. Scripts that create many
short-lived objects should call destroy explicitly. Scripts that create a
handful of long-lived objects can ignore it — process exit cleans up.

---

## Collection Operations

@@  Direct timing comparison with Python list / dict operations. Qualitatively:
- boop List.push / pop: one hash write + array append. Fast relative to dispatch cost.
- boop Map operations: associative array, insertion-ordered via parallel index array.
- Python list: C array operations, orders of magnitude faster.
- The Collection layer is not a performance tool. It is an organizational tool
  for bash scripts that need structured data.

---

## Method Dispatch Cost Breakdown

For a call like `$obj.method arg`:

1. `$obj` expands to the object ID (bash variable expansion, ~1µs)
2. `_ID.method` is a baked function — bash looks it up in the function table
3. The baked function sets `_Self` and `_Class`, calls `ClassName.method`
4. `ClassName.method` runs the real implementation
5. `boop.pass` routes the return value

Total overhead per call: **~4ms** on the benchmark machine, dominated by
bash function call setup and the `boop.pass` nameref write. The baked wrapper
eliminates one hash lookup (method registry is consulted at `registerClass`
time, not at call time), but bash function invocation itself is not free.

Comparison:

| | Cost per call |
|---|---|
| `(( ))` arithmetic | ~2µs |
| bash function call | ~0.1ms |
| boop method dispatch | ~4ms |
| `echo expr \| bc` | ~2500µs |
| Python method call | ~0.1µs |
| Ruby method call | ~0.05µs |

The gap between bare bash function calls (~0.1ms) and boop dispatch (~4ms)
suggests there is room to optimize the dispatch chain. Primary candidates:
the `boop.pass` nameref path, and the `local -I` inheritance overhead. @@

---

## When to Use What

**Use boop when:**
- You are writing a bash script and want OOP structure without leaving bash
- You have multiple object types that share behavior (inheritance helps)
- You need arbitrary-precision math in a bash script with no external deps
- You want a consistent return value API across all your bash functions
- Object count is in the tens, not thousands

**Use Python/Ruby/Perl when:**
- Performance matters (any threshold)
- You need a large ecosystem of libraries
- You're writing anything beyond a few hundred lines of logic
- You need real closures, decorators, generators, comprehensions

**Use bare bash (no boop) when:**
- You have a simple script with a handful of functions
- You don't need OOP structure
- Startup time and minimal footprint matter

**Use bc when:**
- You need precision math in a bash script, have bc available, and don't
  need the Math object model — bc-per-call is faster than boop.Math for
  simple one-shot calculations

---

## Known Limitations vs Other Languages

| Feature | boop | Python | Ruby |
|---|---|---|---|
| **Closures** | No (dynamic scope only) | Yes | Yes |
| **First-class functions** | Partial (function names as strings) | Yes | Yes (Proc/lambda) |
| **GC** | Manual destroy | Automatic | Automatic |
| **Threads** | No (bash is single-threaded) | Yes (GIL-limited) | Yes (GVL-limited) |
| **Error handling** | `_Crash` / exit codes | exceptions | exceptions |
| **Pattern matching** | bash regex ([[ =~ ]]) | re module | Regexp / case/in |
| **Generics / templates** | No | Yes (typing module) | No (duck typing) |

---

## Benchmark Notes

- Timings are from a single run, not averaged. For stable comparisons,
  run multiple times and take the median. @@ automate this.
- boop timings include framework load time when `@@` noted; most times
  measure steady-state (boop already loaded).
- Python and Ruby times use monotonic nanosecond timers; boop uses
  `$EPOCHREALTIME` (microsecond resolution).
- No effort was made to warm CPU caches or isolate from background load.
  These are "real script" numbers, not laboratory numbers.
