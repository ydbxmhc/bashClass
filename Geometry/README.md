---
title: Geometry
---

# Geometry

2D and 3D bounding boxes.

## Inheritance

```
boop → Geometry.Box → Geometry.Cube
```

## Classes

| Class | Description |
|---|---|
| [Geometry.Box](/docs/Box) | 2D axis-aligned bounding box — area, overlap, contains |
| [Geometry.Cube](/docs/Cube) | 3D box — volume, surface area; extends Box |

## Quick start

```bash
. boop Geometry::Box

into=b Geometry.Box x=0 y=0 w=100 h=50
into=a $b.area           # a="5000"
$b.contains 50 25 && printf "inside\n"
```

→ [Full class reference](/docs/index)
