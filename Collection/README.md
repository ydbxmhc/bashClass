---
title: Collection
---

# Collection

Containers, sequences, maps, and sets.

All collection classes share the iterator protocol defined in `Container`.
`List`, `Map`, `Queue`, `Stack`, and `Set` extend or compose with it.

## Inheritance

```
Collection.Container
├── Collection.List
│   └── Games.Deck
├── Collection.Map
├── Collection.Map.Fast
├── Collection.Queue
├── Collection.Queue.Fast
├── Collection.Stack
└── Collection.Stack.Fast
```

`Collection.Set` uses the same iterator shape but is backed by an associative
array (keys are members, values unused).

## Classes

| Class | Load alias | Description |
|---|---|---|
| [Container](/docs/Container) | `Collection::Container` | Abstract base — iterator protocol, `forEach` |
| [List](/docs/List) | `Collection::List` | Indexed array — push/pop, shift/unshift, slice, filter/map/reduce |
| [Map](/docs/Map) | `Collection::Map` | Insertion-ordered key-value store |
| [Map.Fast](/docs/Map.Fast) | `Collection::Map::Fast` | Hash-table map — O(1) lookup, no insertion-order guarantee |
| [Queue](/docs/Queue) | `Collection::Queue` | FIFO queue |
| [Queue.Fast](/docs/Queue) | `Collection::Queue::Fast` | Ring-buffer FIFO — O(1) all operations |
| [Set](/docs/Set) | `Collection::Set` | Unordered unique values — union, intersect, diffs, minus |
| [Stack](/docs/Stack) | `Collection::Stack` | LIFO stack |
| [Stack.Fast](/docs/Stack) | `Collection::Stack::Fast` | Array-backed LIFO — minimal overhead |

## Quick start

```bash
. boop Collection::List

into=l Collection.List
$l.push "alpha" "beta" "gamma"
into=v $l.get 0    # v="alpha"
into=n $l.length   # n=3
```

→ [Full class reference](/docs/index)
