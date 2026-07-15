# Bash Version Floor Audit

**Date:** 2026-06-04
**Scope:** Every framework file, class, mixin, and tool — which bash features
each uses, and the minimum bash version each feature requires.
**Method:** Exhaustive grep sweep for version-gated constructs, attributed
per component. Evidence (file:line) recorded for each finding.

---

## Verdict

**The framework's hard floor is bash 4.3.** Nothing in framework code,
library classes, mixins, or the CLI tools requires anything newer. The single
4.3-defining feature — namerefs (`local -n` / `declare -n`) — is used pervasively,
including in boop core itself, so 4.3 is a genuine floor, not an incidental one.

bash 5.0 is **recommended but not required**: only `EPOCHREALTIME`/`EPOCHSECONDS`
want it, and every use is either guarded with a fallback (TestSuite) or lives in
benchmarks/tests outside the shipped framework.

There is **one stray hard-5.0 dependency**, and it is in a *test*, not the
framework: `tests/unit/test_logging_ts` uses `local -I`. Flagged below for
evaluation.

| Question | Answer |
|----------|--------|
| Absolute minimum to run the framework | **bash 4.3** |
| Minimum for full library (all classes/mixins/tools) | **bash 4.3** |
| Recommended | bash 5.0+ (microsecond timing in TestSuite) |
| Anything forcing >4.3 in shipped code? | **No** |
| Anything forcing >4.3 anywhere? | Yes — `local -I` in one test file (not shipped) |

This means the current README claim ("bash 4.3+") is **correct** and the
boop.md claim ("bash 5+") is **too strict**. See "Doc Reconciliation" below.

---

## Feature → Version Reference

The milestones that matter for this codebase:

| Feature | Min version | Notes |
|---------|-------------|-------|
| Associative arrays (`declare -A`) | 4.0 | Core to the whole object model |
| Case modification (`${v^^}`, `${v,,}`) | 4.0 | |
| `mapfile` / `readarray` | 4.0 | |
| `&>>`, `\|&` | 4.0 | |
| globstar (`**`), `coproc` | 4.0 | |
| `declare -g` | 4.2 | Global declaration from within functions |
| `printf '%(fmt)T'` (builtin strftime) | 4.2 | Zero-fork date formatting |
| `[[ -v var ]]` (and `[[ -v arr[i] ]]`) | 4.2 | Variable-set test |
| **Namerefs (`local -n`, `declare -n`)** | **4.3** | **The floor-setter** |
| Negative array subscript read (`${arr[-1]}`, `unset 'arr[-1]'`) | 4.3 | |
| Parameter transforms (`${v@Q}`, `${v@A}`, …) | 4.4 | **Not used anywhere** |
| `EPOCHSECONDS` / `EPOCHREALTIME` | 5.0 | Recommended-only; guarded |
| `local -I` (inherit from calling scope) | 5.0 | **One test only — flagged** |
| `${v@U}` / `@u` / `@L`, `SRANDOM` | 5.1 | **Not used anywhere** |

The highest feature present in **shipped** code is 4.3 (namerefs + negative
subscripts). 4.4 transforms, 5.1 features: confirmed absent by grep.

---

## Per-Component Findings

Legend: **Floor** is the highest-version feature that component uses.

### Framework core

| Component | Floor | Features used | Evidence |
|-----------|-------|---------------|----------|
| `boop` | **4.3** | Namerefs (`boop.pass`, `methodResolve`, `classResolve`, `parseConfig`, `methodList`); assoc arrays; `declare -g`; `${,,}`; `printf %(...)T` (log timestamps); globstar in classpath rebuild | namerefs at boop:766, 1046, 1782, 2012, 2805; `%(...)T` at boop:353; globstar at boop:2348; `${,,}` at boop:394,428 |

boop core alone requires 4.3. Everything else is at or below that.

### Collections

| Component | Floor | Features used | Evidence |
|-----------|-------|---------------|----------|
| `Collection/Container` | 4.0 | Assoc arrays, `declare -g` object stores | Container:276 |
| `Collection/List` | **4.3** | Negative subscript `arr[-1]` + `unset 'arr[-1]'` | List:228-229 |
| `Collection/Map` | 4.0 | Assoc arrays, insertion-order companion arrays | Map:304 |
| `Collection/Map/Fast` | 4.0 | Flat compound-key assoc array | Fast:183 |
| `Collection/Set` | 4.0 | `declare -gA` backing store | Set:27 |
| `Collection/Stack` + `Stack/Fast` | **4.3** | Negative subscript `arr[-1]` (Fast peek) | Stack/Fast/Fast:40 |
| `Collection/Queue` + `Queue/Fast` | 4.0 | `declare -g` delegate handle | Queue:23 |

### Data / Text / Time

| Component | Floor | Features used | Evidence |
|-----------|-------|---------------|----------|
| `Data/JSON` | 4.2 | `[[ -v ]]` for ordered-key index; `declare -g`; assoc arrays | JSON:376 |
| `Text/String` | 4.0 | `${v^^}`/`${v,,}`; `declare -gA` operator tables | String:175,183,39 |
| `DateTime` | 4.3 | Namerefs (`epochFromUTC`, `parseISO`); `printf %(...)T` (4.2); assoc arrays | DateTime:39,89; `%(...)T` at 146,159,237 |

### Math / Args / Config / SemVer

| Component | Floor | Features used | Evidence |
|-----------|-------|---------------|----------|
| `Math` | **4.3** | Namerefs throughout (raw ops, resolve, tokenizer); `declare -gi` | Math:67,427,1020; `declare -gi` at 41,60 |
| `Args` | 4.0 | `${,,}` section matching; assoc arrays; `read -ra` | Args:253 |
| `Config` | 4.0 | `declare -gA`/`-ga` config stores; assoc `seen` sets | Config:34-35 |
| `SemVer` | 4.0 | Pure string/arith; delegates to boop core (which is 4.3) | SemVer:73 |

### Mixins

| Component | Floor | Features used | Evidence |
|-----------|-------|---------------|----------|
| `Mixins/Serializable` | 4.0 | `read -ra` into array; assoc property walk | Serializable:38-40 |
| `Mixins/Terminal` | 4.0 | `declare -gA` char/color tables | Terminal:15,44,51 |
| `Mixins/Greetable` | <4.0 | Plain functions; no version-gated features | — |
| `Mixins/Taggable` | 4.0 | Comma-separated property storage (assoc) | — |

### I/O and Net

| Component | Floor | Features used | Evidence |
|-----------|-------|---------------|----------|
| `Stream` | **4.3** | Namerefs everywhere (field arrays, read args, nameref field assignment); `declare -ga` | Stream:176,300,488 |
| `Net/Socket` | 4.0 | `/dev/tcp` (not version-gated — a compile-time bash option); assoc-backed object | Socket:99 |

Note on Socket: `/dev/tcp` is not a *version* requirement — it is a bash
compile-time feature (`--enable-net-redirections`, on by default). Present on
Linux/macOS/Git Bash. Worth stating in probe's docs (already noted there).

### Testing

| Component | Floor | Features used | Evidence |
|-----------|-------|---------------|----------|
| `Testing/TestSuite` | 4.2 (5.0 optional) | `printf %(...)T` fallback (4.2); **`EPOCHREALTIME` used only when present**, guarded | TestSuite:36-45 |

TestSuite is the model for how to do progressive enhancement: it defines
`__TS_now` using `printf '%(%s.000000)T'` (4.2, whole-second), then *overrides*
it with `EPOCHREALTIME` (5.0, microsecond) only if that variable exists. Runs
correctly on 4.2+, better on 5.0+.

### CLI Tools

| Component | Floor | Features used | Evidence |
|-----------|-------|---------------|----------|
| `lens` | **4.3** | Inherits Stream (4.3); assoc exclusion sets; `declare -g*` globals | lens:410,441 |
| `boson` | 4.2 | `[[ -v ]]` ordered-key check; inherits Data.JSON/Map.Fast | boson:239 |
| `probe` | 4.0 | `${^^}`/`${,,}` header/method casing; `/dev/tcp` via Socket | probe:140,207 |
| `collider` | 4.0 | Assoc arrays for dep graph; `read -ra` | collider:47,149 |
| `lib/installer` | 4.0 | `${,,}` platform/confirm casing | installer:57,84 |

### Examples / Demos

| Component | Floor | Features used | Evidence |
|-----------|-------|---------------|----------|
| `blackjack` | 4.0 | `readarray` (card render); `${,,}` menu | blackjack:247,502 |
| `Greeter`, `sayHi`, `Geometry/*`, `Games/*` | 4.0–4.3 | Inherit collections/core; no features above their parents | — |

---

## Flagged for Evaluation

### F1 · `local -I` in `tests/unit/test_logging_ts` — bash 5.0 in a test

**File:** `tests/unit/test_logging_ts:114`

```bash
Box.test_log() {
  local -I _Self; local _Class="${_Class:-Geometry.Box}"
  ...
}
```

`local -I` (capital I — "inherit the value from the calling scope") is a
**bash 5.0** feature. This is the *only* hard 5.0 dependency found anywhere,
and it is in a test helper, not shipped framework code. On bash 4.3/4.4 this
test would fail or misbehave.

The framework deliberately abandoned `local -I` (see TODO "Documentation Sync
Pass" — several docs still reference it; the framework no longer uses it). This
test is a leftover that contradicts that decision.

**Options:**
1. Rewrite without `local -I` — set `_Self` explicitly like the rest of the
   codebase does (`local _Self="${_Self:-}"`). Keeps the test runnable on 4.3.
2. Leave it, and accept that the *test suite* needs 5.0 even though the
   framework does not. (Asymmetric and surprising — not recommended.)

Recommendation: option 1. It aligns the test with the framework's own decision
and removes the only thing standing between the test suite and a 4.3 floor.

### F2 · `EPOCHREALTIME` in benchmarks/tests — 5.0, ungated

**Files:** `tests/integration/test_pi_growth`, `test_matrix`,
`test_adversarial_ts`, `tests/bench/bench_*`

These use `EPOCHREALTIME` directly with no fallback. They are benchmarks and
integration tests, not shipped code, and timing is inherent to their purpose —
so a 5.0 requirement is arguably fine *for them*. But if the goal is "the whole
repo runs on 4.3," they would need the same guard TestSuite uses.

Recommendation: low priority. Document that benchmarks assume 5.0, or apply the
TestSuite guard pattern if 4.3 benchmark runs are wanted. No impact on the
shipped framework's floor.

### F3 · `test_datetime_ts` references `EPOCHSECONDS` — 5.0, in an assertion

**File:** `tests/unit/test_datetime_ts:35-37`

A unit test compares the object's epoch against `EPOCHSECONDS` inside a
`bash -c`. This makes that one assertion 5.0-only. Minor; could use `date +%s`
(a fork, but version-agnostic) if 4.3 unit-test runs matter.

---

## Doc Reconciliation

Two shipped docs disagree on the floor. With this audit, the correct statement is:

- **README.md** — "bash 4.3+ (associative arrays + namerefs); 5.0+ recommended"
  → **correct as written.** Keep it.
- **docs/boop.md** — "bash 5.0+ … associative arrays, namerefs" → **wrong on two
  counts.** Namerefs are 4.3 (not 5.0), and associative arrays are 4.0. Should
  be corrected to 4.3 to match reality and the README.

Suggested boop.md wording:

> Requirements: bash 4.3+ (associative arrays since 4.0, namerefs since 4.3).
> bash 5.0+ is recommended — TestSuite uses `EPOCHREALTIME` for microsecond
> timing when available, and falls back to whole-second `printf` strftime on
> 4.2–4.4.

(macOS note stays as-is — Apple's bash 3.2 is below the floor regardless.)

---

## What Was Searched (for reproducibility)

Grep sweeps run across all non-doc files:

- `@[QEAaPULuKk]}` — 4.4/5.1 parameter transforms → **none found**
- `EPOCHREALTIME|EPOCHSECONDS` — 5.0 epoch vars → tests/bench + guarded TestSuite
- `local -n|declare -n` — 4.3 namerefs → boop core + DateTime, Math, Stream, Signal
- `local -I` — 5.0 scope inheritance → **one test only** (F1)
- `[[ -v ` — 4.2 → Signal, Data.JSON, boson
- `%(...)T` — 4.2 strftime → boop, DateTime, TestSuite, benches
- `declare -g*` — 4.2 → widespread (all object stores)
- `declare -A|local -A` — 4.0 → widespread
- `mapfile|readarray` — 4.0 → blackjack only
- `${^^}|${,,}` — 4.0 → String, probe, Args, boop, installer, blackjack
- `globstar|coproc|shopt -s` — 4.0 → boop classpath rebuild (globstar)
- `\[-[0-9]+\]|\[-1\]` — 4.3 negative subscripts → List, Stack.Fast
- `SRANDOM` — 5.1 → **none** (only `RANDOM`, which is ancient)
- `wait -n` / funsub `${ ;}` — 4.4/5.3 → **none found**

---

[↑ Site map](index)
