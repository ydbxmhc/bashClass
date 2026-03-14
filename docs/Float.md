# Float

Virtual decimal arithmetic via scaled integers. Stores values as scaled
integers in the descriptor — `3.14` at scale 2 is stored as integer `314`.
All arithmetic uses bash's native `$(( ))`. No forks, no subshells.

## Dependencies

```bash
. boop Float
```

## Constructor

```bash
into=f Float 3.14
into=f Float -42
into=f Float value=3.14 scale=6    # force scale (pads with zeros)
```

## Precision

Bounded by bash's 64-bit signed integer range (~18 significant digits).
The effective range depends on scale: at scale 2 you get ~16 integer
digits, at scale 10 you get ~8. For arbitrary precision, use Math instead.

## Methods

### Arithmetic

```bash
into=r $f.add 1.5          # f + 1.5
into=r $f.sub $g            # f - g (accepts objects or literals)
into=r $f.mul 2             # f × 2
into=r $f.div 3             # f ÷ 3
into=r $f.mod 2             # f % 2
into=r $f.pow 3             # f³ (non-negative integer exponents only)
```

Arguments can be Float object IDs or literal decimal strings.

### Comparisons

```bash
$f.eq 3.14 && echo "equal"     # exit code 0 = true
$f.lt $g && echo "less"
$f.gt $g && echo "greater"
$f.le $g && echo "less or equal"
$f.ge $g && echo "greater or equal"
```

### Utility

```bash
into=r $f.abs               # absolute value (new Float)
into=r $f.neg               # negated value (new Float)
into=r $f.round 2           # round to 2 decimal places (new Float)
into=i $f.toInt             # truncate to integer string
into=r $f.toScale 4         # new Float with different scale
into=v $f.val               # raw decimal string: "3.14"
into=s $f.format "%010.4f"  # printf-formatted: "00003.1400"
into=s $f.toString           # Float(_id){ 3.14 }
```

## Float vs Math

| Feature          | Float                    | Math                        |
|------------------|--------------------------|-----------------------------|
| Storage          | 64-bit scaled integer    | Arbitrary-length digit string |
| Precision        | ~18 significant digits   | Unlimited (memory-bound)    |
| Speed            | Native `$(( ))`          | String-based, slower        |
| Use case         | Config math, percentages | Pi, arbitrary precision     |
| External deps    | None                     | None                        |

Use Float for everyday decimal math. Use Math when you need more than
18 digits or operations like pi calculation.

## Example

```bash
. boop Float

into=price Float 19.99
into=tax Float 0.08
into=total $price.mul $tax
into=v $total.val
echo "Tax: $v"              # Tax: 1.5992

into=rounded $total.round 2
into=v $rounded.val
echo "Rounded: $v"          # Rounded: 1.60
```
