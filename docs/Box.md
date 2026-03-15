# Box

A 3D rectangular prism with named dimensions. Demonstrates basic class
definition, method registration, and inheritance in boop.

## Dependencies

```bash
. boop Box
```

## Constructor

```bash
into=b Box length=5 width=3 height=7
into=b Box length=5 width=3 height=7 unit=cm color=red
```

All dimensions are integers. `unit` and `color` are optional metadata
properties stored in the descriptor but not used by any built-in method.

## Properties

| Property | Type    | Description                    |
|----------|---------|--------------------------------|
| length   | integer | Length of the box               |
| width    | integer | Width of the box                |
| height   | integer | Height of the box               |
| unit     | string  | Optional unit label (e.g. "cm") |
| color    | string  | Optional color label            |

## Methods

### Geometry

```bash
into=v $b.volume          # length × width × height
into=a $b.top             # length × width (top face)
into=a $b.bottom          # same as top
into=a $b.side            # height × length
into=a $b.end             # height × width
```

### Utility

```bash
into=a $b.area 4 5        # generic 2D multiply (two args)
into=c $b.calc 2 3 4      # generic N-way multiply
```

`calc` accepts variadic integer arguments and returns their product.
The `required=N` typecast enforces exact argument count:

```bash
required=2 into=a $b.area 4 5    # must be exactly 2 args
```

### Inherited (from bashClass)

```bash
into=v $b.get "length"    # read property
$b.set "color" "blue"     # write property
$b.isa Box && echo yes    # type check (walks inheritance)
into=s $b.toString         # Box(_id){ length=5 width=3 height=7 }
```

## Example

```bash
. boop Box

into=b Box length=10 width=5 height=3
into=v $b.volume
echo "Volume: $v"          # Volume: 150

into=t $b.top
echo "Top area: $t"        # Top area: 50
```

