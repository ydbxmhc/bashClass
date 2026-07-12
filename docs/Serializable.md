# Serializable

A mixin that adds JSON-backed save/load to any class.
Mix it in and your objects gain `toJSON`, `fromJSON`, `save`, and `load` — no inheritance needed.

## Loading

```bash
. boop Serializable
```

---

## Quick Start

```bash
. boop Serializable

# Declare a class with the mixin
Config.new() {
  local _Class="${_Class:-Config}"
  local __Config_new_self
  into=__Config_new_self __boop.new "$@"
  boop.pass "$__Config_new_self" ${into:-}
}
boopClass Config mixin:Serializable has:host,port,debug 'public:new'

# Create an object
into=c Config.new host="db.example.com" port="5432" debug="false"

# Serialize to JSON
into=json $c.toJSON
printf '%s\n' "$json"
# → {"_class":"Config","host":"db.example.com","port":"5432","debug":"false"}

# Save to file
$c.save /tmp/config.json

# Load into a fresh object
into=c2 Config.new
$c2.load /tmp/config.json

into=h $c2.get host
printf '%s\n' "$h"   # → db.example.com
```

---

## Methods

### `$obj.toJSON`

Serializes the object's declared properties (`has:` in `boopClass`) to a JSON string.

- Internal properties (names starting with `_`) are excluded.
- Includes a `"_class"` key with the class name — useful for self-describing files.
- Pure bash, no external tools.

```bash
into=json $c.toJSON
# → {"_class":"Config","host":"localhost","port":"5432","debug":"false"}
```

**Returns** (via `into=` or stdout): a JSON object string.

---

### `$obj.fromJSON json_string`

Restores properties from a JSON object string.

- Skips the `"_class"` key (it is metadata, not a property).
- Lazy-loads `Data.JSON` on first call — no cost if you only use `toJSON`.
- Only sets properties that appear in the JSON; existing properties not in the JSON are unchanged.

```bash
$c.fromJSON '{"host":"prod.example.com","port":"5433","debug":"true"}'
into=h $c.get host   # → prod.example.com
```

**Parameter**: JSON object string (required; returns non-zero with an error if empty).

---

### `$obj.save [file]`

Writes `toJSON` output to a file.

- If `file` is given, saves to that path and remembers it as `_savefile`.
- If `file` is omitted, reuses the last path stored in `_savefile`.
- Returns non-zero with an error if no file has ever been specified.

```bash
$c.save /tmp/config.json    # save and remember the path
$c.set host "newhost"
$c.save                     # no arg — reuses /tmp/config.json
```

---

### `$obj.load [file]`

Reads a JSON file and restores properties via `fromJSON`.

- Same path memory as `save` — first call stores the path, subsequent calls can omit it.
- Returns non-zero with an error if the file doesn't exist.

```bash
into=c2 Config.new
$c2.load /tmp/config.json
```

---

## Round-Trip Example

```bash
into=p Player.new name="Alice" score="99" level="7"

# Serialize
into=json $p.toJSON

# Restore into a new object
into=p2 Player.new
$p2.fromJSON "$json"

into=n $p2.get name    # → Alice
into=s $p2.get score   # → 99
```

---

## Special Characters

`toJSON` JSON-escapes backslashes, double quotes, newlines, carriage returns, and tabs.
`fromJSON` unescapes them via the Data.JSON parser. The full round-trip is lossless.

```bash
into=p Player.new name='say "hello"'
into=json $p.toJSON

into=p2 Player.new
$p2.fromJSON "$json"
into=n $p2.get name    # → say "hello"
```

---

## What Gets Serialized

Only properties declared in `has:` are serialized. Internal properties (any name starting with `_`, including `_savefile`) are always excluded.

```bash
boopClass Player mixin:Serializable has:name,score,level 'public:new'
# Serialized: name, score, level
# Excluded:   _savefile (internal), any other _* properties
```

---

## Composing with Other Mixins

```bash
boopClass Hero mixin:Serializable,Taggable has:name,level 'public:new'

into=h Hero.new name="Thor" level="50"
$h.addTag "legendary" "divine"
$h.save /tmp/hero.json    # saves name and level; tags are internal (_tags)
```

---

## Design Notes

- **`_savefile` is internal**: it is stored in the object but never serialized — it won't appear in the JSON and won't collide with any user property named `_savefile`.
- **Lazy parsing**: `Data.JSON` is only loaded when `fromJSON` is first called. If your code only uses `toJSON`/`save`, no JSON parser is loaded.
- **Class name leaking**: `toJSON` always writes `"_class"`. `fromJSON` ignores it on load. This makes saved files self-describing but does not enforce class compatibility — you can load any JSON into any object.
- **No nested objects**: properties are serialized as flat strings. If a property holds an object ID, that ID is saved literally (a meaningless string in another session).
