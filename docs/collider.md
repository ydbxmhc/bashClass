# collider — Single-File Bundler

collider turns a boop tool into a self-contained single-file executable: boop
core, every class the tool needs (resolved transitively and ordered correctly),
the installer library, and the tool's own code, all concatenated into one file
that runs anywhere bash does — no framework checkout, no `PATH` setup.

Built on `Args`.

---

## Quick Start

```bash
collider boson                  # → bundle-boson (next to boson)
collider lens -o /tmp/lens.out  # explicit output path
collider probe -o -             # write the bundle to stdout
```

```bash
./bundle-boson '.name' < data.json   # runs with zero installation
```

---

## What It Does

Given a tool file, collider:

1. **Resolves the dependency graph statically.** It scans the tool (and each
   class it pulls in) for `. boop ClassName` load lines and `boopClass …
   isa:Parent` inheritance, treating those as edges, and recurses until every
   transitive dependency is collected. `require:` version tokens are skipped —
   they are guards, not class names.

2. **Topologically sorts.** Parents land before children, dependencies before
   dependents (DFS post-order). A class declaring `isa:Box` appears after Box;
   a class doing `. boop Config` appears after Config. The visited set is keyed
   on absolute path, so aliases (`List`, `Collection::List`, `Collection.List`)
   all dedupe to one node.

3. **Emits boop core**, trimmed to the `__boop_loaded` guard — the import-args
   block that would otherwise consume the tool's own `$@` is dropped. It then
   overrides `boop.init` / `boop.initMixin` with idempotency-only versions,
   because in a single-file context the direct-execution check would otherwise
   always fire.

4. **Neutralizes source lines.** Every `. boop …` line in a bundled file is
   replaced with `: # bundled`. The load guards (`boop.init … || return 0`)
   stay, so re-sourcing a bundle into a shell that already has boop loaded is a
   safe no-op.

5. **Appends the installer** (`lib/installer`) and finally the tool itself.

---

## Options

| Option | Meaning |
|--------|---------|
| `-o, --output FILE` | Output path. Default: `bundle-<tool>` in the tool's directory. Use `-` for stdout. |

The tool file is the first positional argument and must be readable.

---

## Bundle Naming

The default output is `bundle-<tool>` — `collider boson` writes `bundle-boson`.
The prefix groups bundles together in a listing and keeps them visually
distinct from the bare-named dev scripts they were built from. The bare name
(`boson`) is reserved for the boopRoot-dependent dev script and, eventually,
the public release.

**Bundles are rename-safe.** Nothing inside a bundle keys off its own filename:

- `--self-update` uses `$0` only to know *which file to overwrite* — correct
  regardless of the name.
- The tool's identity and update URL are baked-in string literals, set in the
  tool source before dispatch, not derived from the filename.

So you can rename `bundle-boson` to anything and it behaves identically. (A
trailing-dot or trailing-colon marker for dev scripts was considered and
rejected — Windows and git cannot represent either filename.)

---

## The Bundle Is Also an Installer

Every bundle carries `lib/installer` inline, so a single dropped-in file can
bootstrap the full framework or maintain itself:

```bash
./bundle-boson '.name' < data.json   # use it — no install
./bundle-boson --about               # bundled framework version
./bundle-boson --boop-install        # install full boop to ~/.local/lib/boop
./bundle-boson --boop-install /opt/boop
./bundle-boson --self-update         # fetch the latest of this tool
```

This is the framework's standard delivery vehicle: a tool is useful standalone
*and* a gateway to the whole ecosystem. See the "Adoption & Distribution"
section of [TODO.md](../TODO.md) for the full model.

---

## What It Does Not Do

By deliberate choice, collider does **not**:

- Strip inline comments (distinguishing a real `#` from one inside a string or
  expansion needs a full parser — not worth the fragility).
- Minify (variable shortening, whitespace collapse).
- Tree-shake individual functions (too coupled to pay off).
- Compile (bash has no bytecode).

An optional pass to strip comment-only lines (~35% size reduction) is planned
but off by default. See TODO.

---

## Design Notes

### Why a real tool, not a cat pipeline

Naive concatenation breaks on two things: dependency order and source lines. A
class that inherits from another must appear after it, or the `boopClass`
registration fails; and a live `. boop X` line inside a bundled class would
trigger filesystem resolution that doesn't exist in a bundle. collider solves
both — static graph resolution with a topological sort, and source-line
neutralization — which a pipeline cannot.

### Why load guards survive

The `boop.init ClassName || return 0` guards are the idempotency mechanism. If
a bundle is sourced into a shell that already has boop and some classes loaded,
the guards make each duplicate registration a clean no-op. collider keeps them
precisely so a bundle works whether boop is pre-loaded or not.

### Size

For reference, the full stdlib with comments is ~461 KB / ~10,294 lines;
comment-only lines stripped, ~299 KB / ~6,106 lines. A typical tool bundles a
subset — boson pulls boop + Args + Data.JSON + Map.Fast + List and friends.
Tested by `tests/tools/test_collider` (24 assertions), which builds a bundle
and verifies structure, ordering, and execution.
