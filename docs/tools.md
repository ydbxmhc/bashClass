# boop Tools

Standalone command-line tools built on the boop framework. Each is a normal
boop script: it sources the framework, loads a few classes, and exposes a
focused CLI. They run from a boopRoot checkout (the framework on `PATH`), and
each can be packaged into a self-contained single-file bundle with `collider`.

This page is the map. Each tool has its own full reference in POSIX man-page
form (NAME / SYNOPSIS / DESCRIPTION / OPTIONS / EXAMPLES / …) — follow the links.

| Tool | Reach for it when… | Built on | Reference |
|------|--------------------|----------|-----------|
| **lens** | you'd otherwise chain `head`/`tail`/`grep`/`cut`/`wc` | Stream, Args | [lens.md](lens.md) |
| **boson** | you need to pull values out of JSON without `jq` | Data.JSON, Map.Fast, Args | [boson.md](boson.md) |
| **probe** | you need a quick plaintext HTTP request, no curl | Net.Socket, Args | [probe.md](probe.md) |
| **collider** | you want to ship a tool as one portable file | Args | [collider.md](collider.md) |

---

## Pure bash, by design

These tools began as a thought experiment: how far can an object-oriented
standard library written in pure bash be pushed? The answer turned out to be
"surprisingly far" — a stream processor, a JSON query engine, an HTTP client,
and a bundler, none of which shell out to external programs.

They are **not** competitive on speed with the C utilities they echo (`grep`,
`cut`, `jq`, `curl` fork once and run native code; these interpret bash). What
they offer instead is **reach and features**: they run anywhere **bash 4.3+** is
present — stripped containers, minimal images, locked-down hosts where
installing coreutils, jq, or curl is not an option — and they frequently add
capabilities the classic tools lack (multi-character and character-class
delimiters, one-axis composition, sourceable JSON output, `/dev/tcp` fetches).
Reach for them when the "right" tool isn't installed and bash is.

Each per-tool reference repeats this note in its NOTES section, since the docs
are meant to stand alone.

---

## Common conventions

**Layered help.** Every tool answers `--help` with a compact synopsis, plus
`--about` and `--boop`. lens and the query tools add `--examples`; lens also
has `--options` for the full reference. The idea: `--help` fits on a screen,
deeper help is one flag away.

**boopRoot script vs bundle.** The bare-named file (`boson`) is the
development script — it needs the framework reachable on `PATH`. `collider`
turns it into `bundle-boson`, a single file that carries boop core, the
classes it needs, and an installer inline. Bundles run with zero installation
and are rename-safe. See [collider.md](collider.md) for the bundle format and
naming rationale.

**Installer.** Every bundle carries `lib/installer`, so any tool can bootstrap
the full framework on demand (`--boop-install`) or update itself
(`--self-update`). See the "Adoption & Distribution" section of
[TODO.md](../TODO.md) for the delivery model.

---

## Testing

Each tool's test suite lives in `tests/tools/`. These are **not** part of
`tests/test_all` — they're slow unbundled (every invocation re-sources the
whole framework) and `test_probe` needs python for a loopback HTTP server.
Run them individually as needed:

```bash
bash tests/tools/test_lens        # ~2 min unbundled
bash tests/tools/test_boson       # ~2 min unbundled
bash tests/tools/test_probe       # needs python (loopback server)
bash tests/tools/test_collider    # builds a bundle
bash tests/tools/test_installer
```
