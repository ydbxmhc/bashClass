# Config

Structured config file reader/writer. Parses two formats — flat `key=value`
and sectioned INI — behind a single interface. Pure bash, zero forks.

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
into=cfg Config.new          # then call load or fromString to populate
```

The constructor creates an empty Config. You populate it separately via
`load`, `fromString`, or by calling `set`.

---

## Loading

### From a file

```bash
into=cfg Config.new
$cfg.load settings.ini      # auto-detects flat vs INI by scanning for [ headers
$cfg.loadINI settings.ini   # force INI parsing regardless of content
```

`load` reads the file, detects the format, and stores keys. The `file` and
`format` properties are set automatically so `save` can write back.

### From a string

```bash
# Useful for config embedded in a script or received from another process
into=cfg Config.new
$cfg.fromString "$(cat <<'EOF'
host=localhost
port=9000
EOF
)"
```

`fromString` parses flat format only (no `[sections]`).

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
# Walk keys manually and filter by prefix
_Delimiter=$'\n' into=all $cfg.keys
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
$cfg.save                    # writes to the file loaded from (crashes if no file)
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

# Read
into=cfg Config.new
$cfg.load /etc/myapp/config.ini

into=host  $cfg.get "database.host"
into=port  $cfg.get "database.port"
printf "Connecting to %s:%s\n" "$host" "$port"

# Modify and save
$cfg.set "database.port" "5433"
$cfg.save

# Check sections
_Delimiter=" " into=secs $cfg.sections
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

**Format auto-detection.** `load` scans the file for a `[` character at the
start of any line. If found, it uses INI parsing; otherwise flat. Override
with `loadINI`.
