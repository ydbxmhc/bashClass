---
title: Data
---

# Data

Data format classes.

## Classes

| Class | Description |
|---|---|
| [Data.JSON](/docs/JSON) | Pure-bash JSON parser and serializer — no `jq` required |

## Quick start

```bash
. boop Data::JSON

into=doc Data.JSON.parse '{"name":"world","count":3}'
into=name Data.JSON.get "$doc" name   # name="world"
```

→ [Full class reference](/docs/index)
