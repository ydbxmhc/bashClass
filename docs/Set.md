# Collection.Set

Unordered collection of unique values. Backed by a bash associative array
(keys are members, values are unused). Membership tests, add, and remove are
O(1). Set operations (`union`, `intersect`, `diffs`, `minus`) return new Set objects.

## Contents

- [Dependencies](#dependencies)
- [Constructor](#constructor)
- [Membership](#membership)
  - [$s.add val [val...]](#s-add-val-val)
  - [$s.has val](#s-has-val)
  - [$s.remove val [val...]](#s-remove-val-val)
- [Size](#size)
- [Iteration](#iteration)
- [Set Operations](#set-operations)
  - [union — all members of A or B](#union-all-members-of-a-or-b)
  - [intersect — members in both A and B](#intersect-members-in-both-a-and-b)
  - [diffs — members in exactly one (symmetric difference)](#diffs-members-in-exactly-one-symmetric-difference)
  - [minus — members of A not in B (A − B)](#minus-members-of-a-not-in-b-a--b)
- [Common Patterns](#common-patterns)
  - [Deduplication](#deduplication)
  - [Tag/label system](#taglabel-system)
  - [Computing changed items](#computing-changed-items)
- [Design Notes](#design-notes)

---

## Dependencies

```bash
. boop Set
```

---

## Constructor

```bash
into=s Collection.Set
```

No arguments. You can seed it immediately:

```bash
into=s Collection.Set
$s.add "alpha" "beta" "gamma"
```

---

## Membership

```bash
$s.add "foo"
$s.add "bar"

$s.has "foo" && echo "yes"    # exits 0
$s.has "baz" && echo "yes"    # exits 1 — silent
```

### `$s.add val [val...]`

Add one or more members. Duplicates are silently ignored.

```bash
$s.add "x"
$s.add "x"         # no-op — already a member
$s.add "a" "b" "c" # add three at once
```

### `$s.has val`

Exit code: 0 if `val` is a member, 1 if not.

```bash
if $s.has "$candidate"; then
  printf "%s is already registered\n" "$candidate"
fi
```

### `$s.remove val [val...]`

Remove one or more members. No-op if any are absent.

```bash
$s.remove "foo"
$s.remove "a" "b" "c"   # remove several at once
$s.remove "missing"     # silent no-op
```

---

## Size

```bash
into=n $s.size      # number of members
$s.isEmpty          # exit 0 if empty
```

---

## Iteration

`toArray` returns all members joined by `_Delimiter` (default: newline).
Iteration order is hash-defined — not insertion order.

```bash
_Delimiter=$'\n' into=members $s.toArray
while IFS= read -r m; do
  printf "member: %s\n" "$m"
done <<< "$members"
```

To get members as a bash array:

```bash
_Delimiter=$'\n' into=raw $s.toArray
mapfile -t arr <<< "$raw"
for m in "${arr[@]}"; do
  printf "%s\n" "$m"
done
```

---

## Set Operations

All operations return a **new** Set object. The originals are unchanged.

```
a = {1, 2, 3}    b = {3, 4, 5}
```

### union — all members of A or B

Symmetric: `a.union(b)` == `b.union(a)`.

```bash
into=a Collection.Set; $a.add 1 2 3
into=b Collection.Set; $b.add 3 4 5

into=u $a.union "$b"
into=n $u.size          # "5"  → {1, 2, 3, 4, 5}
```

### intersect — members in both A and B

Symmetric: `a.intersect(b)` == `b.intersect(a)`.

```bash
into=i $a.intersect "$b"
into=n $i.size          # "1"  → {3}
$i.has "3" && echo "yes"
```

### diffs — members in exactly one (symmetric difference)

Symmetric: `a.diffs(b)` == `b.diffs(a)`.

```bash
into=d $a.diffs "$b"
into=n $d.size          # "4"  → {1, 2, 4, 5}
$d.has "1" && echo "only in a"
$d.has "5" && echo "only in b"
```

### minus — members of A not in B (A − B)

Asymmetric: `a.minus(b)` ≠ `b.minus(a)`.

```bash
into=m $a.minus "$b"
into=n $m.size          # "2"  → {1, 2}

into=m2 $b.minus "$a"
into=n $m2.size         # "2"  → {4, 5}
```

---

## Common Patterns

### Deduplication

```bash
into=seen Collection.Set
for item in "${items[@]}"; do
  if ! $seen.has "$item"; then
    $seen.add "$item"
    process "$item"
  fi
done
```

### Tag/label system

```bash
into=tags Collection.Set
$tags.add "urgent" "backend" "v2"

$tags.has "urgent" && notify_oncall
```

### Computing changed items

```bash
into=old Collection.Set
into=new Collection.Set
# ... populate both ...

into=added   $new.minus    "$old"    # in new but not old
into=removed $old.minus    "$new"    # in old but not new
into=changed $old.diffs    "$new"    # in exactly one (added or removed)
into=kept    $old.intersect "$new"   # in both
```

---

## Design Notes

**O(1) membership.** `has` looks up a key in a bash associative array —
one operation, no iteration.

**Unordered.** Bash associative arrays have hash-defined iteration order.
If you need a set with stable iteration order, use a Map (insert key with
a placeholder value; `$map.keys` gives insertion order).

**Values are strings.** Set members can be any non-empty string, including
object IDs, file paths, or multi-word strings. Empty string is not a valid
member (add ignores it silently).
