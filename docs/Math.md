# Math

Arbitrary precision arithmetic via string-based digit math. Numbers are
stored as strings of digits with a tracked sign and decimal position.
All arithmetic is done digit-by-digit using bash's native `$(( ))` on
small chunks. No forks, no subshells, no external tools. Precision is
bounded only by available memory and your patience.

## Dependencies

```bash
. boop Math
```

## Constructor

```bash
into=m Math 3.14159
into=m Math -42
into=m Math 0.001
```

Accepts any decimal string. Leading/trailing zeros are normalized.
Negative zero becomes zero.

## Global Configuration

```bash
__Math.setPrecision 50      # significant digits for inexact ops (default: 20)
```

Precision affects division, pi, and other operations that can produce
infinite results. Exact operations (add, subtract, multiply) are not
affected — they always produce the full result.

All operations truncate by default. Rounding is never applied
automatically. Use `Math.round` or `$obj.round N` to round a result
explicitly when you want it.

## Fast Path

When both operands fit in a 64-bit integer (up to 18 significant digits),
Math automatically uses bash's native `$(( ))` arithmetic instead of the
string-based digit engine. This is transparent — same API, same results,
just faster. The fast path covers add, subtract, multiply, divide, and mod.

## Static API — Class-Level Functions

The most common use case: do some math, get a value string back. No
objects created, no cleanup needed.

```bash
into=v Math.add 1.5 2.3          # v="3.8"
into=v Math.subtract 10 3.5      # v="6.5"
into=v Math.multiply 2.5 4       # v="10"
into=v Math.divide 10 3          # v="3.333333333..."
into=v Math.mod 17 5             # v="2"
into=v Math.pow 2 10             # v="1024"
into=v Math.square 7             # v="49"
into=v Math.abs -42.5            # v="42.5"
into=v Math.neg 3.14             # v="-3.14"
```

### Symbol Aliases

For when you want your bash to look like a calculator:

```bash
into=v Math.+ 1.5 2.3            # add
into=v Math.- 10 3.5             # subtract
into=v Math.x 2.5 4              # multiply
into=v Math.'*' 2.5 4            # multiply (quoted asterisk)
into=v Math./ 10 4               # divide
```

### Math.DO — Infix Expression Evaluator

Shunting-yard algorithm converts infix to RPN tokens, then delegates
to `Math.RPN` for evaluation. One evaluation engine under the hood —
`Math.DO` is purely a precedence and parenthesis reordering pass.

Every token must be whitespace-separated, or packed together (the
tokenizer handles both):

```bash
into=v Math.DO 1.5 + 2.3                    # 3.8
into=v Math.DO 2 + 3 x 4                    # 14 (precedence: x before +)
into=v Math.DO '(' 2 + 3 ')' x 4            # 20 (parens override)
into=v Math.DO "( 1.5 + 2.5 ) / 2"          # 2 (string mode)
into=v Math.DO "(2+3)x4"                    # 20 (packed — no spaces needed)
into=v Math.DO -5 + 8                        # 3 (negative numbers work)
into=v Math.DO "(-3)x4"                     # -12
```

Operators: `+`, `-`, `x` (or quoted `*`), `/`
Precedence: `x` and `/` bind tighter than `+` and `-`.
Left-to-right associativity for equal precedence.

### Math.RPN — Reverse Polish Notation Evaluator

The shared evaluation engine. Operands first, then operators. No
precedence rules — order is explicit in the token sequence. `Math.DO`
feeds into this after its shunting-yard pass; calling `Math.RPN`
directly skips the precedence reordering.

```bash
into=v Math.RPN 1.5 2.3 +                   # 3.8
into=v Math.RPN 3 4 + 2 x                   # 14
into=v Math.RPN "10 3 /"                     # 3.333...
into=v Math.RPN 5 3 - 2 x 1 +              # 5
```

Unlike `Math.DO`, `Math.RPN` does not support packed expressions
(no spaces). `"3 4+2x"` won't parse correctly — use `3 4 + 2 x`.
This is intentional: RPN has no precedence rules, so there's no
structural context to distinguish unary minus from subtraction in
a packed string like `3-2`. With whitespace, `-2` is a negative
number and `- 2` is the subtraction operator followed by `2`.

Both evaluators use internal bash arrays as stacks — no dependency on
the Stack or Container class.

## Instance Methods

Create an object, call methods on it. Instance methods return Math
objects (chainable).

### Arithmetic

Full-word names are the primary API. Short aliases (`sub`, `mul`, `div`)
are kept for backward compatibility.

```bash
into=r $m.add $n            # m + n
into=r $m.subtract $n       # m - n       (also: $m.sub)
into=r $m.multiply $n       # m × n       (also: $m.mul)
into=r $m.divide $n         # m ÷ n       (also: $m.div)
into=r $m.mod $n            # m mod n     (fast path only)
into=r $m.pow $n            # m ^ n       (integer exponent)
into=r $m.square            # m²
into=r precision=30 $m.divide $n   # with precision override
```

Arguments can be Math object IDs or literal decimal strings.

`mod` uses the fast path (native `$(( ))`), so both operands must fit
in 64-bit. For arbitrary-precision modular arithmetic, you'd need a
`strMod` implementation (not yet built).

`pow` uses repeated squaring. Small bases stay on the fast path; large
bases gracefully fall back to the string engine per iteration.

### Comparisons

```bash
$m.eq $n && echo "equal"        # exit code 0 = true
$m.lt $n && echo "less"
$m.gt $n && echo "greater"
$m.le $n && echo "less or equal"
$m.ge $n && echo "greater or equal"
into=rc $m.cmp $n               # 0=equal, 1=greater, 2=less
```

### Utility

```bash
into=r $m.abs                # absolute value
into=r $m.neg                # negated value
into=r $m.round 10           # round to 10 significant digits (half-up)
into=r $m.toScale 4          # force exactly 4 decimal places
into=i $m.toInt              # truncate to integer string
into=v $m.val                # decimal string: "3.14159"
into=s $m.toString           # Math(_id){ 3.14159 }
into=s $m.format "%.4f"      # printf-style formatting: "3.1416"
$m.isZero && echo "zero"     # boolean check
```

`round` uses round-half-up (not banker's rounding). If the digit past
the cut point is >= 5, it rounds up. Always.

`toScale` forces a specific number of decimal places — padding with
trailing zeros if needed, truncating (with rounding carry) if the
number has more decimals than requested.

`format` applies a printf format string to the value. Useful for
fixed-width output, zero-padding, or controlling decimal display.

### Pi

```bash
into=pi Math.pi              # pi to default precision (20 digits)
into=pi Math.pi 100          # pi to 100 significant digits
into=pi Math.pi 1000         # go big (bring coffee)
```

Uses Machin's formula: π = 16·arctan(1/5) − 4·arctan(1/239). The
arctan series expansion runs with raw digit/scale/neg triples (no
object overhead) at extra working precision, then truncates to the
requested digits.

Results are cached in `__bashClass_static` so repeated calls at the
same or lower precision are instant.

## Performance

The inner loops of series expansions (arctan, pi) use raw digit/scale/neg
triples instead of Math objects, eliminating all object overhead from the
hot path. Basic arithmetic on Math objects is already minimal — one
resolve, one string op, one object create.

Chunked arithmetic processes 9 digits at a time (base 10^9) for add,
subtract, and multiply. Division remains digit-at-a-time (inherently
sequential — each step depends on the previous remainder).

The 64-bit fast path (`toInt64`/`fromInt64`) auto-selects native
`$(( ))` for operands with ≤18 significant digits. This covers the
vast majority of everyday arithmetic without touching the string engine.

Approximate timings (varies by hardware):

| Operation  | Time       |
|------------|------------|
| pi(10)     | ~2-4 sec   |
| pi(20)     | ~8-15 sec  |
| pi(50)     | ~40-60 sec |

## Internal Representation

Numbers are stored in the descriptor as three fields:

| Field  | Description                                    |
|--------|------------------------------------------------|
| digits | String of digits, no leading zeros (except "0") |
| scale  | Number of digits after the decimal point        |
| neg    | 0 (positive/zero) or 1 (negative)               |

Example: `3.14` → digits="314", scale=2, neg=0

The raw arithmetic helpers (`rawAdd`, `rawSub`, `rawMul`, `rawDiv`,
`rawMulSmall`, `rawDivSmall`) operate directly on these triples via
namerefs, bypassing the object system entirely. They're used internally
by pi and arctan for performance.

## Examples

```bash
. boop Math

# Static API — quick math, plain value strings
into=v Math.add 1.5 2.3
echo "$v"                    # 3.8

into=v Math.DO "( 10 + 5 ) / 3"
echo "$v"                    # 5

into=v Math.RPN 3 4 + 2 x
echo "$v"                    # 14

# Powers
into=v Math.pow 2 32
echo "$v"                    # 4294967296

# Static square loop
for x in 1 2 3 4 5; do
  into=v Math.square $x
  echo "$x² = $v"
done
# 1² = 1  ...  5² = 25

# Object API — when you need state or chaining
into=a Math 1
into=b Math 3
into=r precision=50 $a.divide $b
into=v $r.val
echo "$v"
# 0.33333333333333333333333333333333333333333333333333

# Rounding is always explicit
into=rounded $r.round 10
into=v $rounded.val
echo "$v"                    # 0.3333333333

# Pi
into=pi Math.pi 30
into=v $pi.val
echo "pi = $v"
# pi = 3.14159265358979323846264338328

# Format for display
into=m Math 3.14159
into=s $m.format "%010.4f"
echo "$s"                    # 00003.1416
```
