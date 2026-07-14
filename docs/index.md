---
title: boop — Class & Tool Reference
---

# boop — Class & Tool Reference

Complete catalog of every class and tool in the boop framework,
grouped by namespace.

**Jump to:** [Collection](#collection) · [Data](#data) · [Games](#games) · [Geometry](#geometry) · [Mixins](#mixins) · [Net](#net) · [Text](#text) · [Testing](#testing) · [System](#system) · [Tools](#tools)

---

## Collection

Containers, sequences, maps, and sets. All share the iterator protocol
from `Container`.

| Class | Description |
|---|---|
| [Collection.Container](Container) | Abstract base; provides the iterator protocol and `forEach` |
| [Collection.List](List) | Indexed array — push/pop, shift/unshift, slice, filter/map/reduce |
| [Collection.Map](Map) | Insertion-ordered key-value store |
| [Collection.Map.Fast](Map.Fast) | Hash-table map — O(1) lookup, no insertion-order guarantee |
| [Collection.Queue](Queue) | FIFO queue |
| [Collection.Queue.Fast](Queue) | Ring-buffer FIFO — O(1) all operations |
| [Collection.Set](Set) | Unordered unique-value collection — union, intersect, diffs, minus |
| [Collection.Stack](Stack) | LIFO stack |
| [Collection.Stack.Fast](Stack) | Array-backed LIFO with minimal overhead |

---

## Data

| Class | Description |
|---|---|
| [Data.JSON](JSON) | Pure-bash JSON parser and serializer — no `jq` required |
| [DateTime](DateTime) | Date/time parsing, formatting, and arithmetic |
| [Math](Math) | Arbitrary-precision arithmetic beyond bash builtins |
| [SemVer](SemVer) | Semantic version parsing and comparison |

---

## Games

| Class | Description |
|---|---|
| [Games.Card](Card) | Generic card base — property bag, no game logic |
| [Games.Deck](Deck) | Shuffleable, drawable List (Fisher-Yates shuffle, pop-based draw) |
| [Games.PlayingCard](PlayingCard) | Standard playing card — suit, rank, ANSI render, `newDeck` factory |

See also the [combined Games reference](Card) for a narrative walkthrough of all three together.

---

## Geometry

| Class | Description |
|---|---|
| [Geometry.Box](Box) | 2D axis-aligned bounding box — area, overlap, contains |
| [Geometry.Cube](Cube) | 3D box — volume, surface area; extends Box |

---

## Mixins

Composable behaviours that add capability to any boop class without
forcing a particular inheritance chain. A class can include multiple mixins.

| Mixin | Description |
|---|---|
| [Mixins.Eventable](Eventable) | Per-object publish/subscribe events — on/emit/off, LIFO dispatch |
| [Mixins.Greetable](Greetable) | Adds configurable greeting behaviour |
| [Mixins.Serializable](Serializable) | Object serialization and deserialization |
| [Mixins.Taggable](Taggable) | Tag and label management |
| [Mixins.Terminal](Terminal) | ANSI terminal output — colours, cursor control, clear |

See the [mixin guide](mixin) for how to author and apply mixins.

---

## Net

| Class | Description |
|---|---|
| [Net.Socket](Socket) | Plaintext TCP connection via bash `/dev/tcp` — no TLS |

---

## Text

| Class | Description |
|---|---|
| [Text.String](String) | String objects — transform, inspect, compose in pipelines |

---

## Testing

| Class | Description |
|---|---|
| [Testing.TestSuite](TestSuite) | Test runner — section grouping, assertion helpers, summary report |

---

## System

| Class | Description |
|---|---|
| [Args](Args) | Command-line argument parser |
| [Config](Config) | Structured config reader/writer — flat `key=value` and INI |
| [Signal](Signal) | LIFO signal handler stacks layered over bash `trap` |
| [Stream](Stream) | Record-oriented file-descriptor reader |

---

## Tools

Standalone command-line tools distributed as single-file scripts from
[boopshell.com/dist](https://boopshell.com/dist/).

| Tool | Description |
|---|---|
| [boop](boop) | Core OOP framework — object model, dispatch, lifecycle |
| [lens](lens) | Interactive class inspector REPL |
| [probe](probe) | Diagnostic tool — inspect live objects and framework state |
| [boson](boson) | JSON processor CLI |
| [collider](collider) | Single-file bundle builder — topological dependency resolver |

---

## Guides & References

| Document | Description |
|---|---|
| [API reference](API) | Complete boop API reference |
| [Tutorial](tutorial) | Step-by-step introduction to boop |
| [Mixin guide](mixin) | How to author and apply mixins |
| [Iterator guide](Iterator) | Deep dive into the iterator protocol |
| [GOTCHAS](GOTCHAS) | Common pitfalls and their fixes |
| [STANDARDS](STANDARDS) | Coding standards for boop classes |
| [Bash style guide](bash_style) | Shell conventions used throughout the codebase |
