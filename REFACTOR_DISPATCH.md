# Dispatch Refactor — boop Framework

Reference document for the dispatch/stub/wrapper simplification.
Delete this file when the refactor is complete.

---

## Summary

Replace the current two-phase stub→dispatch→bake system with direct
wrapper creation at class registration and object creation time.
Dispatch becomes a pure MRO resolver that returns a class name. The
three-tier typecast/leakage system goes away — methods handle their
own `_Class` hygiene.

---

## Current Architecture (what we're replacing)

1. `registerClass` walks inheritance, creates class-level shims:
   `Box.toString() { _Class='Box' __boop.dispatch toString "$@"; }`

2. `stubAll` (called from `__boop.new`) writes lazy stubs on objects:
   `$obj.volume() { __init=true _Self='$id' __boop_originClass='Box' __boop.dispatch volume "$@"; }`

3. On first call, dispatch resolves the method via MRO, then evals a
   baked wrapper with the three-tier typecast/leakage check. The baked
   wrapper replaces the stub. Subsequent calls go through the wrapper.

4. The baked wrapper has three tiers:
   - Tier 1: exact class match → fast path, direct call
   - Tier 2: family member (isa) → re-dispatch for typecast
   - Tier 3: unrelated class → warn, use fast path anyway

---

## New Architecture

### Principle

Wrappers are written once, at creation time. No lazy stubs, no
dispatch on first call, no tier system. Dispatch is a utility for
MRO resolution only — it finds the right class and returns it.

### registerClass — class-level wrappers

Walk inheritance chain. For each inherited method where
`ClassName.method` does NOT already exist as a function:

```bash
# Resolve the impl via MRO (walk methodRegistry)
# e.g., Box doesn't define toString, boop does → impl = __boop.toString
eval "Box.toString() { _Self=\$_Self _Class=Box __boop.toString \"\$@\"; }"
```

- `_Self=$_Self` — runtime expansion, passes through whatever the
  caller set (for class-level static calls, `_Self` is the class name)
- `_Class=Box` — hardcoded to the class being registered
- Direct call to the resolved impl — no dispatch

If the class author already defined `Box.volume`, skip it. Author
definitions take priority (unchanged from current behavior).

Constructor shorthand is unchanged:
`Box() { _Class=Box __boop.dispatch new "$@"; }`
(Constructor still uses dispatch because `new` creates an object and
needs the full machinery. This is the one place dispatch runs.)

### stubAll → backfillMethods (rename)

Called from `__boop.new` at object creation time. Walk inheritance
chain, for each method:

```bash
eval "$obj.volume() { _Self='$id' Box.volume \"\$@\"; }"
```

- `_Self='$id'` — hardcoded to the object ID
- No `_Class` — methods default their own
- Delegates to the class-level function (which is either the author's
  impl or the wrapper registerClass created)
- One hop: `$obj.volume` → `Box.volume` → done

Property stubs stay the same pattern but also become direct:

```bash
eval "$obj.length() {
  if ((\$#)); then _Self='$id' _Class='Box' __boop.dispatch set 'length' \"\$1\"
  else _Self='$id' _Class='Box' __boop.dispatch get 'length'; fi
}"
```

(Properties still use dispatch for get/set because those are boop
base methods and the routing is simple. Could be made direct later
but not worth the complexity now.)

### dispatch — MRO resolver only

Strip out:
- The `__init` / baking logic (entire eval block)
- The three-tier wrapper generation
- The final `"$_Self.$__boop_dispatch_method" "$@"` call at the end

What remains:
- Receive method name
- Check `__boop_methodRegistry` cache
- On miss, walk inheritance chain, cache result
- Call the resolved impl directly: `$__boop_dispatch_impl "$@"`

Dispatch is still called by:
- Constructor shorthand (`Box()` calls `dispatch new`)
- Property accessors (get/set routing)
- `__boop.super` (parent method resolution)
- Any future explicit MRO lookups

It is NOT called by normal method invocations anymore.

### super

Currently: `_Self="$_Self" _Class="$__boop_super_parent" __boop.dispatch "$@"`

This still works. Dispatch resolves the parent's method and calls it.
No change needed — super is inherently a dispatch operation.

### _Delegate

Unchanged: `_Delegate() { _Class='' "$@"; }`

Still needed as documentation/convenience for cross-object calls.
Without the tier system, there's no leakage warning to suppress,
but clearing `_Class` is still correct hygiene.

### refresh

Currently re-stubs everything. Will now re-wrapper everything.
Same logic, just calls the new backfillMethods with force flag.

---

## Changes by Function

### `__boop.dispatch` (~lines 586–690)

- Remove `local -l __init; : "${__init:=false}"`
- Remove entire `if [[ "$__init" == "true" ]]; then ... fi` block
  (the eval that generates the three-tier baked wrapper)
- Remove `"$_Self.$__boop_dispatch_method" "$@"` at the end
- Add: `_Self="$_Self" _Class="${_Class:-$__boop_originClass}" $__boop_dispatch_impl "$@"`
- Update header comment to reflect new role

### `__boop.stubAll` → `__boop.backfillMethods` (~lines 930–975)

- Rename function
- Method stubs become direct wrappers:
  OLD: `eval "$self.$method() { __init=true _Self='$self' __boop_originClass='$class' __boop.dispatch $method \"\$@\"; }"`
  NEW: resolve impl via methodRegistry walk, then:
  `eval "$self.$method() { _Self='$self' $class.$method \"\$@\"; }"`
- Property stubs: unchanged (still route through dispatch for get/set)
- Update all references: `__boop.new` calls backfillMethods instead of stubAll

### `__boop.registerClass` (~lines 990–1030)

- Walk inheritance chain as before
- For each method where `ClassName.method` doesn't exist:
  resolve impl from methodRegistry, then eval a direct wrapper:
  `eval "$class.$method() { _Self=\$_Self _Class='$class' $impl \"\$@\"; }"`
- Constructor shorthand: unchanged (still uses dispatch for `new`)

### `__boop.refresh` (~line 980)

- Update to call `__boop.backfillMethods` instead of `__boop.stubAll`

### `__boop.new` (~lines 870–910)

- Change `__boop.stubAll` call to `__boop.backfillMethods`

### `boopClass` (~lines 1100–1190)

- No structural changes — it calls registerMethod + registerClass,
  which handle the new behavior internally

### `__boop.super` (~line 920)

- No change needed — still dispatches to parent

---

## What Gets Deleted

- `__init` variable and all references to it
- The entire three-tier baked wrapper eval in dispatch
- The `__boop_originClass` parameter in stubs (no longer needed —
  the wrapper knows its class at creation time)
- Tier 3 leakage warning (`_Warn "class leakage..."`)
- The `"$_Self.$__boop_dispatch_method" "$@"` trampoline at end of
  dispatch

---

## Test Impact

- `test_stress_ts` Section 12 ("lazy stubs"): tests that check for
  `__init=true` in stub definitions will need updating — stubs no
  longer exist, wrappers are final from creation
- `test_stress_ts` Section 14 ("_Delegate and leakage"): the Tier 3
  leakage warning test needs to change — warning no longer fires.
  `_Delegate` tests for correct value return still apply.
- `test_stress_ts` Section 13 ("typecasting"): `_Class=Sphere` on a
  Cube no longer triggers a warning path — it just gets ignored by
  the method (no tier system). Value should still be correct.
- `test_stress_ts` Section 19 ("refresh"): update to check for
  direct wrapper instead of `__init=true` stub

---

## Migration Order

1. Revert any partial changes in `boop` to the last known good state
   (git tag `CheckPoint` or current passing state)
2. Modify `__boop.registerClass` — class-level wrappers become direct
3. Rename `__boop.stubAll` → `__boop.backfillMethods`, write direct wrappers
4. Simplify `__boop.dispatch` — remove baking, become call-through
5. Update `__boop.new` and `__boop.refresh` references
6. Update tests in `test_stress_ts` (sections 12, 13, 14, 19)
7. Run full test suite
8. Commit
