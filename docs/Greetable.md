# Greetable (mixin)

Demo mixin used to exercise and document the mixin system.
Provides two methods: a greeting and an identification string.

## Dependencies

```bash
. boop Greetable
```

## Mixing In

```bash
boopClass MyClass mixin:Greetable public:new,...
```

---

## Methods

### `$obj.greet`

Returns `"Hello from <ClassName>"` via `into=`.

```bash
into=g $obj.greet
printf "%s\n" "$g"    # "Hello from MyClass"
```

The class name reflects the actual concrete class of the object, not
`Greetable` itself.

### `$obj.identify`

Returns `"Greetable::identify"` — used in tests to verify which mixin's
version of a conflicting method was selected.

```bash
into=s $obj.identify
printf "%s\n" "$s"    # "Greetable::identify"
```

---

## Conflict Resolution Example

When two mixins both provide `identify`, the first one listed wins:

```bash
boopClass MyClass mixin:Greetable mixin:Taggable public:new,...
# $obj.identify → "Greetable::identify" (Greetable listed first)

boopClass MyClass mixin:Taggable mixin:Greetable public:new,...
# $obj.identify → "Taggable::identify" (Taggable listed first)
```

To call a specific mixin's version regardless of resolution order:

```bash
$obj.Greetable::identify    # always Greetable's version
$obj.Taggable::identify     # always Taggable's version
```

---

## Purpose

Greetable exists to exercise and demonstrate the mixin system — it has no
production use case. [Taggable](Taggable) and [Terminal](Terminal) are the production mixins.

---

[↑ Site map](index)
