# Mixin Support — Design Notes

## Current State

The boop class system uses single inheritance (`isa:Parent`). The closest existing
mechanisms are:

- `boopExtend ClassName custom:method=impl` — adds methods to one class imperatively
- `_Cast Class obj method` — calls a different class's method on an object
- `_Delegate $other.method "$@"` — forwards to another object's method

None of these are declarative mixin composition.

## What Needs to Change

Three blockers, all small:

### 1. Descriptor format — add `mixins=` field

`boopClass` stores class metadata as a pipe-delimited descriptor in `__boop_registry`.
Currently: `|class=Box|trueClass=Box|parent=boop|methods=...|properties=...|`

Add: `|mixins=Serializable,Comparable|` alongside the existing `parent=` field.

### 2. Token parser — recognize `mixin:` in `boopClass`

`__boopClass.parseTokens()` (boop:2282) handles `isa:`, `has:`, `public:`, `custom:`.
Add `mixin:Mixin1,Mixin2` as a new token type, parsed into a `__boopClass_mixins`
variable the same way `isa:` is parsed into `__boopClass_parent`.

### 3. Method resolution — check mixins before climbing to parent

`__boop.methodResolve()` (boop:1044) walks the parent chain linearly. Add one loop
before the parent walk: iterate `mixins=`, check `__boop_methodRegistry["Mixin.method"]`,
inject into the calling class's registry entry if found. Cache hit after first lookup —
same O(1) behaviour as today.

`__boop.backfillMethods()` (boop:1419) generates per-object wrappers by walking the
`methods=` field. Mixin methods just need to appear in that list — inject them at
registration time (step 2 above).

## Design Decision: Conflict Resolution

If a mixin and the parent both define the same method, **mixin wins**. Resolution order:

```
own class → mixins (left to right) → parent chain
```

This matches Ruby/Python mixin semantics and keeps the rule simple.

## Scope

~100 lines across four functions:

| Function | File | Change |
|---|---|---|
| `__boopClass.parseTokens()` | boop:2282 | Parse `mixin:` token |
| `boopClass()` | boop:2333 | Store `mixins=` in descriptor |
| `__boop.methodResolve()` | boop:1044 | Check mixins before parent |
| `__boop.backfillMethods()` | boop:1419 | Include mixin methods in wrapper generation |

Fully backward compatible — classes without `mixin:` are unaffected.

## Example Syntax (proposed)

```bash
boopClass Serializable '
  public:toJSON,fromJSON
'

boopClass Comparable '
  public:eq,lt,gt,between
'

boopClass Product isa:BaseModel mixin:Serializable,Comparable has:name,price '
  public:new,toString
'
```
