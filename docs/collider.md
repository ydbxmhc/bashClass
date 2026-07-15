# collider(1)

## Contents

- [NAME](#name)
- [SYNOPSIS](#synopsis)
- [DESCRIPTION](#description)
  - [What it does](#what-it-does)
- [OPTIONS](#options)
- [EXAMPLES](#examples)
  - [A bundle is also an installer](#a-bundle-is-also-an-installer)
- [BUNDLE NAMING](#bundle-naming)
- [WHAT IT DOES NOT DO](#what-it-does-not-do)
- [EXIT STATUS](#exit-status)
- [NOTES](#notes)
- [SEE ALSO](#see-also)

---

## NAME

**collider** — bundle a boop tool and its dependencies into one file

## SYNOPSIS

```
collider TOOL [-o OUTPUT]
collider (-h | --help)
```

## DESCRIPTION

**collider** turns a boop tool into a self-contained single-file executable. It
resolves the tool's class dependencies transitively, orders them correctly,
neutralizes the dynamic `. boop` load lines, and concatenates boop core, the
required classes, the installer library, and the tool's own code into one file
that runs anywhere bash does — no framework checkout, no `PATH` setup.

The result is the framework's standard delivery vehicle: a tool that is useful
standalone *and* able to bootstrap the full framework on demand (see
[TODO.md](TODO.md), "Adoption & Distribution").

### What it does

Given TOOL, collider:

1. **Resolves the dependency graph statically** — scans the tool and each class
   it pulls in for `. boop ClassName` loads and `boopClass … isa:Parent`
   inheritance, recursing until every transitive dependency is collected.
   `require:` version tokens are skipped; they are guards, not class names.
2. **Topologically sorts** (DFS post-order) so parents precede children and
   dependencies precede dependents. The visited set is keyed on absolute path,
   so aliases (`List`, `Collection::List`, `Collection.List`) dedupe to one
   node.
3. **Emits boop core**, trimmed at the `__boop_loaded` guard (the import-args
   block that would consume the tool's own `$@` is dropped), then overrides
   `boop.init`/`boop.initMixin` with idempotency-only versions so the
   direct-execution check does not misfire in a single-file context.
4. **Neutralizes source lines** — every `. boop …` becomes `: # bundled`, while
   the `boop.init … || return 0` load guards stay, so re-sourcing a bundle into
   a shell that already has boop loaded is a safe no-op.
5. **Appends the installer** (`lib/installer`) and finally the tool itself.

## OPTIONS

| Short | Long | Argument | Meaning |
|-------|------|----------|---------|
| `-o` | `--output` | FILE | Output path. `-` writes to stdout. Default: `bundle-<tool>` in the tool's directory. |
| `-h` | `--help` | — | Synopsis |

TOOL (the first positional argument) is required and must be a readable file.

## EXAMPLES

```bash
collider boson                  # → bundle-boson, next to boson
collider lens -o /tmp/lens.out  # explicit output path
collider probe -o -             # write the bundle to stdout

./bundle-boson '.name' < data.json   # the result runs with zero installation
```

### A bundle is also an installer

Every bundle carries `lib/installer` inline, so one dropped-in file can
bootstrap the framework or maintain itself:

```bash
./bundle-boson '.name' < data.json   # use it — no install needed
./bundle-boson --about               # the framework version baked in
./bundle-boson --boop-install        # install full boop to ~/.local/lib/boop
./bundle-boson --boop-install /opt/boop
./bundle-boson --self-update         # fetch the latest of this tool
```

## BUNDLE NAMING

The default output is `bundle-<tool>` — `collider boson` writes `bundle-boson`.
The prefix groups bundles in a listing and distinguishes them from the
bare-named development scripts they were built from. The bare name (`boson`) is
reserved for the dev script and, eventually, the public release.

Bundles are **rename-safe** — nothing inside keys off the filename.
`--self-update` uses `$0` only to learn which file to overwrite; the tool's
identity and update URL are baked-in string literals set in the source. So a
bundle may be renamed freely. (A trailing-dot or trailing-colon marker for dev
scripts was considered and rejected — Windows and git cannot represent either
filename.)

## WHAT IT DOES NOT DO

By deliberate choice, collider does not strip inline comments (telling a real
`#` from one inside a string needs a full parser), does not minify, does not
tree-shake individual functions (too coupled to pay off), and does not compile
(bash has no bytecode). An optional pass to strip comment-only lines (~35%
smaller) is planned but off by default; see [TODO.md](TODO.md).

## EXIT STATUS

- **0** — bundle written successfully.
- **non-zero** — no tool given, an unreadable tool file, or an unresolvable
  dependency.

## NOTES

collider is pure bash, built on the **boop** framework's `Args` class. Like the
tools it packages, it began as part of a thought experiment in how far a bash
OOP standard library can be pushed, and it is not a general-purpose build system
— it does exactly one job (dependency-correct concatenation) for boop tools.
It runs anywhere **bash 4.3+** is present.

Naive `cat` concatenation cannot do collider's job: it would mis-order classes
(a subclass registered before its parent fails) and leave live `. boop` lines
that trigger filesystem resolution absent from a bundle. Static graph
resolution with a topological sort plus source-line neutralization is what makes
the single-file output correct.

For reference, the full standard library is ~461 KB with comments (~299 KB with
comment-only lines stripped); a typical tool bundles a subset — boson pulls in
boop, Args, Data.JSON, Map.Fast, List, and friends.

## SEE ALSO

[docs/tools.md](tools.md) for the tool family, [docs/boop.md](boop.md) for the
framework, and [TODO.md](TODO.md) for the bundle/installer delivery model.
Tested by `tests/tools/test_collider` (24 assertions).

---

[↑ Site map](index)
