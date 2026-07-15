# Mixins

Mixins are method bundles composed into classes at declaration time.
They are not classes — they have no constructor, no state of their own,
and do not appear in the `isa` chain. They give objects additional behavior
without inheritance.

## Contents

- [Declaring a Mixin](#declaring-a-mixin)
- [Composing into a Class](#composing-into-a-class)
- [Resolution Order](#resolution-order)
- [Provenance Dispatch (`::`)](#provenance-dispatch)
- [`mixes` Predicate](#mixes-predicate)
- [Writing a Mixin File](#writing-a-mixin-file)
- [A Class That Is Also a Mixin](#a-class-that-is-also-a-mixin)
- [Available Mixins](#available-mixins)
- [Mixin vs Inheritance](#mixin-vs-inheritance)

---

## Declaring a Mixin

```bash
# Define the functions:
Printable.print() {
  printf '%s\n' "${_Class}: $(boop.pass "$_Self" ${into:-})"
}

Printable.inspect() {
  boop.pass "Printable::inspect on ${_Self}" ${into:-}
}

# Register them as a mixin:
boopMixin Printable 'public:print,inspect'
```

`boopMixin` takes the same `public:` and `custom:` token syntax as `boopClass`.
The mixin's functions must already be defined before calling `boopMixin`.

## Composing into a Class

```bash
boopClass Article isa:Document mixin:Printable mixin:Taggable '
  has:title,body
  public:new,toString
'
```

Multiple `mixin:Name` tokens compose multiple mixins. The first mixin listed
wins when two mixins provide the same method name.

## Resolution Order

For any method call, boop searches in this order:

1. The object's own class
2. Mixins (left to right, as listed in `boopClass`)
3. Parent class
4. Parent's mixins
5. (continues up the chain)

**Own class always wins.** If `Article` defines `print`, its definition is
used — the mixin's `print` is shadowed.

## Provenance Dispatch (`::`)

To call a specific mixin's version of a method regardless of resolution order:

```bash
$article.Printable::print     # always Printable's version
$article.Taggable::identify   # always Taggable's version
```

This works even when the method is shadowed by the class or another mixin.

## `mixes` Predicate

Check whether an object's class composes a given mixin (walks the inheritance chain):

```bash
$article.mixes Printable   && echo "yes"   # 0 = true
$article.mixes Comparable  && echo "yes"   # 1 = false — silent
```

A subclass of a class that composes a mixin also satisfies `mixes`:

```bash
boopClass BlogPost isa:Article public:new,...
# BlogPost inherits Article's mixins

into=post BlogPost.new
$post.mixes Taggable   # 0 — inherited from Article
```

## Writing a Mixin File

```bash
#!/bin/bash
# Comparable mixin — comparison predicates.

. boop
boop.initMixin Comparable || return 0

Comparable.eq() { ... }
Comparable.lt() { ... }
Comparable.gt() { ... }

boopMixin Comparable 'public:eq,lt,gt'
```

`boop.initMixin` is the mixin equivalent of `boop.init` for classes:
- Returns 1 (and the file returns 0 via `|| return 0`) if already loaded
- Detects direct execution and prints a helpful error instead of crashing

## A Class That Is Also a Mixin

A file can declare both `boopClass` and `boopMixin` for the same name.
The class registration covers `new`, `isa`, and object dispatch.
The mixin registration separately lists which methods other classes can
compose (typically the same methods minus `new`):

```bash
boopClass Serializable public:new,toJSON,fromJSON has:...
boopMixin  Serializable 'public:toJSON,fromJSON'
```

This is valid because both registries (`__boop_registry` for classes and
`__boop_mixin_registry` for mixins) are independent.

## Available Mixins

| Mixin | Purpose | Doc |
|-------|---------|-----|
| `Terminal` | ANSI output, raw input, named symbols | [Terminal.md](Terminal.md) |
| `Taggable` | Tag/untag/query labels on any object | [Taggable.md](Taggable.md) |
| `Greetable` | Demo/test mixin for the system | [Greetable.md](Greetable.md) |

## Mixin vs Inheritance

| | Inheritance (`isa:`) | Mixin (`mixin:`) |
|-|---------------------|-----------------|
| State | Inherited | Not shared (host's descriptor) |
| Constructor | Inherited | None |
| `isa` check | Yes | No |
| `mixes` check | N/A | Yes |
| Multiple | No (single parent) | Yes (as many as needed) |
| Method priority | Parent loses to child | First mixin listed wins |

---

[↑ Site map](index)
