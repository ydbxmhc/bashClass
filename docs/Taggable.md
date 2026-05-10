# Taggable (mixin)

Tag, untag, and query arbitrary string labels on any object.
Tags are stored in the host object's descriptor as a comma-separated
internal property (`_tags`). The host class does not need to declare
`_tags` with `has:`.

## Dependencies

```bash
. boop Taggable
```

## Mixing In

```bash
boopClass Article isa:SomeBase mixin:Taggable has:title,body public:new,...
```

---

## Adding Tags

```bash
$obj.addTag "urgent"
$obj.addTag "backend" "v2" "reviewed"    # multiple at once
$obj.addTag "urgent"                     # duplicate — silently ignored
```

Tags are case-sensitive strings. Any non-empty string is a valid tag.

---

## Querying Tags

```bash
$obj.hasTag "urgent" && echo "needs attention"    # exit 0 = has tag
$obj.hasTag "missing" && echo "yes"               # exit 1 — silent

into=all $obj.getTags      # all="urgent,backend,v2,reviewed"
into=n   $obj.tagCount     # n="4"
```

`getTags` returns a comma-separated string, or empty string if untagged.
`tagCount` returns an integer count as a string.

---

## Removing Tags

```bash
$obj.removeTag "reviewed"
$obj.removeTag "nonexistent"    # no-op — does not crash
```

---

## Common Patterns

### Filtering by tag

```bash
# Given a list of object IDs, find those tagged "urgent"
for id in "${objects[@]}"; do
  _Self="$id" Taggable.hasTag "urgent" && urgent_list+=("$id")
done
```

### Tag-based routing

```bash
if $task.hasTag "async"; then
  queue_task "$task"
elif $task.hasTag "immediate"; then
  run_now "$task"
fi
```

### Reporting tag inventory

```bash
into=tags $obj.getTags
IFS=',' read -ra tag_arr <<< "$tags"
printf "Tags (%d):\n" "${#tag_arr[@]}"
for tag in "${tag_arr[@]}"; do
  printf "  - %s\n" "$tag"
done
```

---

## Design Notes

**No `has:` required.** Tags go into the descriptor under the `_tags`
key using `__boop.set`/`__boop.get`. The leading underscore is a naming
convention for internal/private properties that the host class did not
declare. This avoids polluting the host class's declared property list.

**Comma separator.** Tags are stored as `tag1,tag2,tag3`. This means commas
are not valid characters within a tag value. Any other character is fine.

**Conflict resolution.** If another mixin also declares `identify`, the first
mixin listed in `boopClass` wins. Call `$obj.Taggable::identify` to invoke
Taggable's version explicitly regardless of resolution order.
