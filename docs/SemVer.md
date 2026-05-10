# SemVer

Semantic version parsing, comparison, and constraint checking.
Pure bash — no `sort -V`, no `awk`. Static-only API: no constructor needed.

## Dependencies

```bash
. boop SemVer
```

## Version Strings

SemVer parses versions in `major.minor.patch` format. Missing components
default to zero:

| Input | Interpreted as |
|-------|---------------|
| `1` | `1.0.0` |
| `1.2` | `1.2.0` |
| `1.2.3` | `1.2.3` |
| `1.2.3-beta` | `1.2.3` (pre-release tag stored but ignored) |

---

## SemVer.compare

Compare two version strings. Returns `-1`, `0`, or `1` via `into=`.

```bash
into=r SemVer.compare "1.2.0" "1.3.0"    # r="-1"  (A < B)
into=r SemVer.compare "2.0.0" "2.0.0"    # r="0"   (equal)
into=r SemVer.compare "3.1.0" "2.9.9"    # r="1"   (A > B)

# Compare as an exit code
[[ "$(into=r SemVer.compare "$a" "$b"; echo $r)" == "1" ]] && echo "a is newer"
```

---

## SemVer.satisfies

Test whether a version string satisfies a constraint. Returns exit code 0
(satisfied) or 1 (not satisfied).

```bash
SemVer.satisfies "1.3.0"  "1.2+"    && echo "ok"   # >= 1.2.0 — passes
SemVer.satisfies "1.1.9"  "1.2+"    && echo "ok"   # >= 1.2.0 — fails (silence)
SemVer.satisfies "1.2.3"  ">=1.2.0" && echo "ok"   # explicit >= — passes
SemVer.satisfies "2.0.0"  "<2.0"    && echo "ok"   # < 2.0.0  — fails
SemVer.satisfies "1.2.3"  "1.2.3"   && echo "ok"   # exact    — passes
```

### Constraint syntax

| Syntax | Meaning | Example |
|--------|---------|---------|
| `N.M+` | >= N.M.0 | `1.2+` means >= 1.2.0 |
| `>=N.M.P` | >= N.M.P | `>=1.2.3` |
| `>N.M` | > N.M.0 | `>1.2` means > 1.2.0 |
| `<=N.M` | <= N.M.0 | `<=2.0` means <= 2.0.0 |
| `<N.M.P` | < N.M.P | `<2.0.0` |
| `N.M.P` | exact match | `1.2.3` |

---

## boop Version Guard

The most common use of version constraints is guarding framework
compatibility at load time:

```bash
. boop require:1.2+       # crashes if boop version < 1.2.0
. boop require:>=1.1.0    # same, explicit form
```

This check runs before any classes load (boop evaluates `require:` args in
its entry point using inlined comparison logic, not the SemVer class itself).

---

## In Scripts

```bash
. boop SemVer

# Gate a feature on a minimum tool version
tool_ver="$(mytool --version 2>&1 | grep -o '[0-9]*\.[0-9]*\.[0-9]*' | head -1)"
SemVer.satisfies "$tool_ver" "2.4+" || {
  printf "mytool >= 2.4.0 required (have %s)\n" "$tool_ver" >&2
  exit 1
}

# Sort versions (manual — SemVer has no batch sort)
into=order SemVer.compare "1.10.0" "1.9.0"   # order="1" (1.10 > 1.9)
```

---

## Design Notes

**Comparison engine lives in boop core.** `SemVer.satisfies` and
`SemVer.compare` delegate to `__boop.versionSatisfies` and
`__boop.versionCompare` — the same functions used by the `. boop require:`
guard. The logic exists exactly once; SemVer exposes it as a clean public API.

**Pre-release tags are ignored.** `1.2.3-beta` compares identically to
`1.2.3`. If you need to distinguish pre-releases, compare the tag suffix
yourself after calling `SemVer.compare`.

**No leading zeros in components.** `01.02.03` is treated as `1.2.3`.
