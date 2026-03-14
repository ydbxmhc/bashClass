# Math

Arbitrary precision arithmetic via string-based digit math. Numbers are
stored as strings of digits with a tracked sign and decimal position.
All arithmetic is done digit-by-digit using bash's native `$(( ))` on
small chunks. No forks, no subshells, no external tools. Precision is
bounded only by available memory.

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

## Global Configuration

```bash
__Math.setPrecision 50      # significant digits for inexact ops (default: 20)
__Math.setRound 0           # 0 = truncate, 1 = round half-up (default: 1)
```

Precision affects division, pi, and other operations that can produce
infinite results. Exact operations (add, sub, mul) are not affected.

## Methods

### Arithmetic

```bash
into=r $m.add $n            # m + n
into=r $m.sub $n            # m - n
into=r $m.mul $n            # m × n
into=r $m.square            # m²
into=r precision=30 $m.div $n   # m ÷ n (with precision override)
```

Arguments can be Math object IDs or literal decimal strings.

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
into=r $m.round 10           # round to 10 significant digits
into=i $m.toInt              # truncate to integer string
into=v $m.val                # decimal string: "3.14159"
into=s $m.toString           # Math(_id){ 3.14159 }
$m.isZero && echo "zero"     # boolean check
```

### Pi

```bash
into=pi Math.pi              # pi to default precision (20 digits)
into=pi Math.pi 100          # pi to 100 significant digits
into=pi Math.pi 1000         # go big
```

Uses Machin's formula: π = 16·arctan(1/5) - 4·arctan(1/239). Results
are cached in `__bashClass_static` so repeated calls at the same
precision are instant.

## Performance

The inner loops of series expansions (arctan, pi) use raw digit/scale/neg
triples instead of Math objects, eliminating all object overhead from the
hot path. Basic arithmetic on Math objects is already minimal — one
resolve, one string op, one object create.

Chunked arithmetic processes 9 digits at a time (base 10^9) for add,
sub, and multiply. Division remains digit-at-a-time (inherently sequential).

Approximate timings (varies by hardware):

| Operation  | Time       |
|------------|------------|
| pi(10)     | ~3 sec     |
| pi(20)     | ~6 sec     |
| pi(50)     | ~25 sec    |

## Internal Representation

Numbers are stored in the descriptor as three fields:

| Field  | Description                                    |
|--------|------------------------------------------------|
| digits | String of digits, no leading zeros (except "0") |
| scale  | Number of digits after the decimal point        |
| neg    | 0 (positive/zero) or 1 (negative)               |

Example: `3.14` → digits="314", scale=2, neg=0

## Example

```bash
. boop Math

into=a Math 1
into=b Math 3
into=r precision=50 $a.div $b
into=v $r.val
echo "$v"
# 0.33333333333333333333333333333333333333333333333333

into=pi Math.pi 30
into=v $pi.val
echo "pi = $v"
# pi = 3.14159265358979323846264338328

for x in 1 2 3 4 5; do
  into=m Math $x
  into=sq $m.square
  into=v $sq.val
  echo "$x² = $v"
done
# 1² = 1
# 2² = 4
# 3² = 9
# 4² = 16
# 5² = 25
```
