# Config

Structured config file reader/writer. Parses two formats — flat `key=value`
and sectioned INI — behind a single interface. Pure bash, zero forks.

## Contents

- [Dependencies](#dependencies)
- [Formats](#formats)
  - [Flat](#flat)
  - [INI](#ini)
- [Constructor](#constructor)
- [Loading](#loading)
  - [From a file](#from-a-file)
  - [From a string](#from-a-string)
- [Reading Keys](#reading-keys)
  - [Listing keys](#listing-keys)
  - [Listing sections (INI)](#listing-sections-ini)
- [Writing Keys](#writing-keys)
- [Saving](#saving)
  - [Serializing to string](#serializing-to-string)
- [Full Example](#full-example)
- [Design Notes](#design-notes)

---

## Dependencies

```bash
. boop Config
```

## Formats

### Flat

```ini
# My app config
host=localhost
port=5432
debug=false
```

Keys are top-level. The `=` is the only required character per line.
`#` comments and blank lines are ignored.

### INI

```ini
# My app config

[server]
host=localhost
port=8080

[database]
host=db.internal
port=5432
name=myapp
```

Keys under a `[section]` header are stored as `section.key`. Keys before
any header (top-level keys) have no prefix.

```bash
into=port  $cfg.get "server.port"     # "8080"
into=dbh   $cfg.get "database.host"   # "db.internal"
into=top   $cfg.get "topLevelKey"     # no prefix
```

---

## Constructor

```bash
into=cfg Config.new          # empty config, no backing file
```

`Config.new` creates an empty Config. You can then call `$cfg.set` to add
keys, or use one of the static loading constructors below instead.

---

## Loading

All loaders are **static constructors** — they return a new Config object.
There is no instance-method form of `load`.

### From a file

```bash
into=cfg Config.load    settings.cfg   # flat key=value file
into=cfg Config.loadINI settings.ini   # INI file with [section] headers
```

`Config.load` parses flat key=value format only. For INI files, use
`Config.loadINI`. The `file` and `format` properties are recorded
automatically so `$cfg.save` can write back to the same file.

### From a string

```bash
# Flat key=value string:
into=cfg Config.fromFlatString "host=localhost
port=9000"

# INI-format string:
into=cfg Config.fromString "[server]
host=localhost
port=8080"
```

`fromFlatString` parses flat format. `fromString` parses INI format
(with `[section]` headers). Neither requires a backing file.

---

## Reading Keys

```bash
into=host  $cfg.get "server.host"     # returns value or ""
into=port  $cfg.get "server.port"
into=debug $cfg.get "debug"

$cfg.has "server.host" && echo "configured"   # 0=exists, 1=absent
```

`get` returns an empty string for unknown keys — it does not crash.
Use `has` to distinguish "not set" from "set to empty string".

### Listing keys

```bash
into=all  $cfg.keys               # all keys, newline-joined, insertion order
```

For INI configs, to get all keys in a section:

```bash
# Get all keys in a section using the section argument:
into=db_keys $cfg.keys database     # keys in [database], without the prefix

# Or filter the full key list manually:
into=all $cfg.keys
while IFS= read -r k; do
  [[ "$k" == database.* ]] && printf "%s\n" "$k"
done <<< "$all"
```

### Listing sections (INI)

```bash
into=secs $cfg.sections    # unique section names, newline-joined
# e.g. "server\ndatabase"
```

---

## Writing Keys

```bash
$cfg.set "server.port" "9090"       # creates or overwrites
$cfg.set "feature.enabled" "true"
```

Set does not validate key format. Any string is a valid key.

---

## Saving

```bash
$cfg.save                    # writes to the file loaded from (errors if no file was loaded)
$cfg.save /path/to/new.ini   # saves to a different file; does not update $file
```

The format used is whatever `$cfg.get format` says — either `flat` or `ini`.

### Serializing to string

```bash
into=s $cfg.toFlat   # "host=localhost\nport=5432\n..."
into=s $cfg.toINI    # "[server]\nhost=localhost\n..."
```

---

## Full Example

```bash
. boop Config

# Load an INI file
into=cfg Config.loadINI /etc/myapp/config.ini

into=host  $cfg.get "database.host"
into=port  $cfg.get "database.port"
printf "Connecting to %s:%s\n" "$host" "$port"

# Modify and save back to the same file
$cfg.set "database.port" "5433"
$cfg.save

# Check sections
_EOL=" " into=secs $cfg.sections
printf "Sections: %s\n" "$secs"
```

---

## Design Notes

**No eval, no source.** The parser is a `while IFS= read -r` loop that
splits on the first `=` per line. Config files cannot execute code.

**Insertion order preserved.** Keys are stored in two arrays: an associative
array for O(1) lookup, and an indexed array for ordered iteration. `keys`
always returns keys in the order they were first seen.

**Re-setting a key updates its value but not its position.** The key stays
where it was inserted in the order.

**Two separate loaders, not auto-detection.** `Config.load` always parses flat
key=value format. `Config.loadINI` always parses INI with `[section]` headers.
Choose the right loader for your file — there is no auto-detection.

---

[↑ Site map](index)
