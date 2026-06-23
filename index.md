[Get started](#quick-start) &nbsp;·&nbsp; [Read the docs](docs/boop.md) &nbsp;·&nbsp; [Source on GitHub](https://github.com/ydbxmhc/bashClass)

The framework file is called `boop` because fun is a feature — but it is not
a toy. boop brings real object-oriented programming to bash 4.3+: real
classes, real objects, single inheritance with mixins, a namespace system,
and a growing standard library. All in pure bash, with no third-party tools
and no subshells in the dispatch path.

---

## Why boop

Bash is a glue language. It excels at wiring programs together, not at
organizing large amounts of logic. Past a few hundred lines, the usual
tools — functions, global variables, naming conventions — start to fight
each other: prefixed globals, parallel arrays, subshells spawned just to
return a value, state leaking everywhere.

boop gives bash the vocabulary it's missing: objects with conventionally
private state, classes with constructors and inherited methods, a return
system that avoids subshells, and a namespace-aware loader that scales from
a single script to a library of dozens of classes.

It is not a toy. The framework is ~2,500 lines of bash; the bundled classes
are well-tested implementations; the suite runs 1,300+ tests across unit,
integration, and property-based cases.

---

## A taste

```bash
. boop Cube

into=c Cube size=5 unit=cm
into=vol $c.volume          # 125

$c.toString pretty
# Cube(_a1b2c3) {
#   size   = 5
#   unit   = cm
#   length = 5
#   width  = 5
#   height = 5
# }
```

Define your own class in a few lines:

```bash
. boop

Greeter.greet() {
  local _Class="${_Class:-Greeter}"
  local _Self="${_Self:-${_Class}}"
  local __Greeter_greet_name="I'm a Boop Class"
  [[ "$_Self" == "$_Class" ]] || into=__Greeter_greet_name $_Self.name
  boop.pass "Hello, ${__Greeter_greet_name:-World}!" ${into:-}
}

boopClass Greeter 'has:name public:greet'

into=g Greeter name="from Boop"
into=msg $g.greet
printf '%s\n' "$msg"          # Hello, from Boop!
```

---

## What you get

- **Real objects and classes** — constructors, properties, single
  inheritance, and mixins for shared behavior.
- **A subshell-free return system** — `into=var $obj.method` writes results
  straight into the caller's variable via namerefs. No `$()` fork, no global
  clobbering.
- **A namespace-aware loader** — `. boop List Map Config` pulls in classes
  and their dependencies; `::` and `/` are interchangeable; short names
  resolve when unambiguous.
- **A standard library** — Collections (List, Map, Set, Stack, Queue,
  Map.Fast), arbitrary-precision Math, Config, Args, Data.JSON, DateTime,
  Text.String, SemVer, and more.
- **CLI tools built on the framework** — `lens` (stream inspection),
  `boson` (jq-style JSON query), `probe` (plaintext HTTP), `collider`
  (single-file bundler).
- **errexit-safe by default** — all framework code survives `set -e`.

---

## Quick start

```bash
git clone https://github.com/ydbxmhc/bashClass boop
PATH+=":$PWD/boop"      # so `. boop` works anywhere
```

No build step. No package manager. Source the framework and start:

```bash
. boop List

into=fruits List
$fruits.push apple banana cherry
into=n $fruits.length         # 3
into=v $fruits.get -1         # cherry
```

**Requirements:** bash 4.3+ (associative arrays and namerefs); 5.0+
recommended. macOS ships bash 3.2 — `brew install bash` fixes that.

> **NUL bytes:** bash variables cannot hold or detect NUL bytes; any value
> containing one is silently truncated at the first. This is a bash
> limitation that applies throughout the framework. See
> [GOTCHAS](docs/GOTCHAS.md).

---

## Documentation

| Document | Contents |
|----------|----------|
| [boop](docs/boop.md) | Full framework reference — return system, dispatch mechanics, naming rules, gotchas |
| [comparison](docs/comparison.md) | boop idioms next to Python, Ruby, and Go equivalents |
| [List](docs/List.md) · [Map](docs/Map.md) · [Container](docs/Container.md) | Collection API references |
| [Math](docs/Math.md) | Arbitrary-precision arithmetic internals |
| [String](docs/String.md) | Text.String API — mutators, `-ed` forms, pipelines |
| [DateTime](docs/DateTime.md) | DateTime API — formatting, arithmetic, DST notes |
| [JSON](docs/JSON.md) | Data.JSON parser/serializer |
| [SemVer](docs/SemVer.md) | Version constraints and the `require:` guard |
| [tools](docs/tools.md) | CLI tools overview — `lens`, `boson`, `probe`, `collider` |
| [TODO](docs/TODO.md) | Roadmap and open design questions |

---

<p align="center"><em>boop — fun is a feature.</em></p>
