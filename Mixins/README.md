---
title: Mixins
---

# Mixins

Composable behaviours that add capability to any boop class without
forcing a particular inheritance chain. A class can include multiple mixins.

## Mixins

| Mixin | Description |
|---|---|
| [Mixins.Greetable](/docs/Greetable) | Adds configurable greeting behaviour |
| [Mixins.Serializable](/docs/Serializable) | Object serialization and deserialization |
| [Mixins.Taggable](/docs/Taggable) | Tag and label management |
| [Mixins.Terminal](/docs/Terminal) | ANSI terminal output — colours, cursor control, screen clear |

## Usage pattern

```bash
. boop Mixins::Taggable

boopClass MyClass isa:Mixins.Taggable public:new,tag,untag,hasTag
```

See the [mixin guide](/docs/mixin) for how to author and apply mixins.

→ [Full class reference](/docs/index)
