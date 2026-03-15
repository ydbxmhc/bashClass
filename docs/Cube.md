# Cube

A cube — all faces equal. Inherits from Box, overrides face and volume
methods to use the single `size` dimension.

## Dependencies

```bash
. boop Cube    # automatically loads Box
```

## Constructor

```bash
into=c Cube size=4
```

The constructor sets `length`, `width`, and `height` equal to `size`
in the underlying Box descriptor. Defaults to `size=1` if omitted.

## Properties

| Property | Type    | Description                     |
|----------|---------|----------------------------------|
| size     | integer | Edge length (all faces equal)    |
| length   | integer | Inherited from Box (set = size)  |
| width    | integer | Inherited from Box (set = size)  |
| height   | integer | Inherited from Box (set = size)  |
| unit     | string  | Optional unit label              |

## Methods

All geometry methods are overridden to use `size` directly:

```bash
into=v $c.volume           # size³
into=a $c.side             # size²
into=a $c.top              # size² (delegates to side)
into=a $c.end              # size² (delegates to side)
into=a $c.bottom           # size² (delegates to side)
```

### Typecasting

Cube inherits from Box, so you can call Box methods via typecast:

```bash
class=Box $c.volume        # dispatches to Box.volume
```

## Example

```bash
. boop Cube

into=c Cube size=5
into=v $c.volume
echo "Volume: $v"          # Volume: 125

$c.isa Box && echo "yes"   # yes — Cube inherits from Box
```

