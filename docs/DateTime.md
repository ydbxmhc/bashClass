# DateTime — Date and Time Objects

A date/time class for the boop framework. Stores time as a UTC epoch integer
and exposes construction, formatting, arithmetic, and comparison methods.
Every method after construction is subshell-free.

## Contents

- [Quick Start](#quick-start)
- [Performance](#performance)
  - [The subshell problem](#the-subshell-problem)
  - [How DateTime avoids it](#how-datetime-avoids-it)
  - [Construction cost](#construction-cost)
- [Constructors](#constructors)
  - [`now`](#now)
  - [`fromEpoch`](#fromepoch)
  - [`utc`](#utc)
  - [`parse`](#parse)
    - [Timezone handling in `parse`](#timezone-handling-in-parse)
- [Getters](#getters)
  - [`epoch`](#epoch)
  - [`format`](#format)
  - [Component getters](#component-getters)
  - [`iso`, `isoDate`, `isoTime`](#iso-isodate-isotime)
- [Arithmetic](#arithmetic)
- [Difference](#difference)
- [Comparison](#comparison)
- [Design Notes](#design-notes)
  - [Why epoch as the single stored value](#why-epoch-as-the-single-stored-value)
  - [`printf '%(format)T'` as a bash builtin](#printf-formatt-as-a-bash-builtin)
  - [The pure-bash epoch computation](#the-pure-bash-epoch-computation)
  - [DST and local time](#dst-and-local-time)
  - [What is not here](#what-is-not-here)

---

## Quick Start

```bash
. boop DateTime

# Current time — no subshell
into=now DateTime.now
into=v $now.iso          # "2024-01-15T10:30:45"
into=v $now.isoDate      # "2024-01-15"

# From a known date — no subshell
into=d DateTime.utc "2024-01-15"
into=v $d.year           # "2024"
into=v $d.weekday        # "1"  (1=Monday, ISO 8601)

# Arithmetic — no subshell
into=d2 $d.addDays 7
into=v $d2.isoDate       # "2024-01-22"

# Comparison — no subshell
$d.before "$d2" && printf "earlier\n"
into=n $d2.diffDays "$d"   # "7"
```

---

## Performance

### The subshell problem

The `date` command is the standard tool for date handling in shell scripts.
Using it in a loop is expensive:

```bash
# Each iteration forks a process and execs /usr/bin/date
for log_line in "${logs[@]}"; do
  ts=$(echo "$log_line" | cut -d' ' -f1)
  epoch=$(date -d "$ts" +%s)         # fork + exec every iteration
  # ...
done
```

At scale this dominates runtime. A tight loop over thousands of log lines
calling `date -d` will spend most of its time in process creation.

### How DateTime avoids it

DateTime stores time as a single integer — UTC epoch seconds. Once an object
is constructed, every operation works on that integer directly:

- **Formatting** uses `printf '%(format)T' epoch` — bash's built-in strftime.
  `printf` is a shell builtin; it calls strftime(3) without forking.
- **Arithmetic** (`addDays`, `addHours`, etc.) is integer math: `(( epoch + n * 86400 ))`.
- **Comparison** (`before`, `after`, `diffDays`) is integer comparison: `(( a < b ))`.
- **Component access** (`year`, `month`, `day`, etc.) uses the same `printf`
  builtin trick — no fork.

### Construction cost

The only place a subshell may appear is at object construction:

| Constructor | Cost | When |
|---|---|---|
| `DateTime.now` | zero | `printf -v ep '%(%s)T' -1` — bash 4.2+ builtin |
| `DateTime.fromEpoch n` | zero | direct property write |
| `DateTime.utc "YYYY-MM-DD"` | zero | pure bash regex + arithmetic |
| `DateTime.parse "ISO 8601"` | zero | same pure bash path |
| `DateTime.parse "Jan 15 2024"` | **one subshell** | `date -d` for non-ISO formats |

The key pattern for hot loops: construct once (or use `fromEpoch` if you
already have epoch values), then operate freely:

```bash
# Construct outside the loop — pay construction cost once
into=base DateTime.utc "2024-01-01"

# Inside the loop: pure integer arithmetic, no forks
for (( i = 0; i < 10000; i++ )); do
  into=d $base.addDays "$i"
  into=v $d.isoDate
  # ... process v
done
```

If your input strings are ISO 8601, `DateTime.parse` is also zero-cost inside
a loop. If they are not, extract epochs outside the loop with a single
`date -d` call and use `DateTime.fromEpoch` inside.

---

## Constructors

### `now`

```bash
into=d DateTime.now
```

Returns a DateTime for the current UTC time. Uses `printf -v '%(%s)T' -1`
(bash 4.2+ builtin) — no subshell, no fork.

### `fromEpoch`

```bash
into=d DateTime.fromEpoch 1705276800
```

Constructs from a known UTC epoch integer. Zero cost — a single property
write. This is the fastest constructor and the right choice when you already
have epoch values (from a database, a log parser, arithmetic on another
DateTime's `epoch`).

### `utc`

```bash
into=d DateTime.utc "2024-01-15"
into=d DateTime.utc "2024-01-15T10:30:45"
into=d DateTime.utc "2024-01-15 10:30:45"
```

Parses an ISO 8601 date or datetime as UTC. Pure bash — no subshell. Accepts
the `T` or space separator between date and time. The time part is optional;
omitting it gives midnight UTC.

Crashes if the input is not a recognized ISO 8601 form. Use `parse` for
arbitrary formats.

### `parse`

```bash
into=d DateTime.parse "2024-01-15"                  # ISO — zero cost
into=d DateTime.parse "2024-01-15T10:30:45Z"        # ISO UTC — zero cost
into=d DateTime.parse "2024-01-15T10:30:45+05:30"   # ISO with offset — zero cost
into=d DateTime.parse "January 15, 2024"            # arbitrary — one subshell
into=d DateTime.parse "15 Jan 2024 UTC"             # arbitrary — one subshell
```

The fast path: if the input matches ISO 8601 (date only, or datetime with
optional `Z` or `±HH:MM` offset), `parse` handles it in pure bash with no
subshell. This covers the common server/log formats.

The slow path: anything else is passed to `date -d`, which forks once. That
cost is paid at construction only — all subsequent operations on the object
are free.

Crashes if neither path can parse the input.

#### Timezone handling in `parse`

| Input form | How it is handled |
|---|---|
| `2024-01-15T10:30:00Z` | UTC — exact |
| `2024-01-15T10:30:00+05:30` | Explicit offset — exact |
| `2024-01-15T10:30:00` | Local time — current UTC offset applied (DST-approximate) |
| `2024-01-15` | Local midnight — current UTC offset applied |
| arbitrary string | `date -d` handles timezone via the system's zoneinfo |

The "DST-approximate" caveat applies only to the pure-bash path when no
timezone is specified: the parser reads the current UTC offset via
`printf '%(%z)T' -1` and applies it. This is correct for dates near the
present but may be off by one hour across DST transitions for historical
dates. For exact DST-correct local-time parsing, include an explicit offset
(`+01:00`, `-07:00`) or let `parse` fall back to `date -d`.

---

## Getters

### `epoch`

```bash
into=n $d.epoch
```

Returns the stored UTC epoch integer. Useful for passing to `fromEpoch`,
storing in a file, or doing arithmetic outside the class.

### `format`

```bash
into=v $d.format "%Y/%m/%d"     # "2024/01/15"
into=v $d.format "%A, %B %-d"  # "Monday, January 15"
into=v $d.format "%s"           # epoch as string
```

Accepts any strftime(3) format string. Implemented via `printf '%(fmt)T' epoch`
— bash builtin, no subshell. Output reflects the local timezone (controlled by
`$TZ`). Set `TZ=UTC` to get UTC output regardless of system timezone.

### Component getters

```bash
into=v $d.year     # "2024"
into=v $d.month    # "01"   (zero-padded)
into=v $d.day      # "15"   (zero-padded)
into=v $d.hour     # "10"
into=v $d.minute   # "30"
into=v $d.second   # "45"
into=v $d.weekday  # "1"    (ISO 8601: 1=Monday … 7=Sunday)
```

All are zero-fork `printf '%(...)T' epoch` calls. `month`, `day`, `hour`,
`minute`, and `second` return zero-padded strings matching strftime output.

### `iso`, `isoDate`, `isoTime`

```bash
into=v $d.iso       # "2024-01-15T10:30:45"
into=v $d.isoDate   # "2024-01-15"
into=v $d.isoTime   # "10:30:45"
```

Convenience shortcuts for the most common formatting needs. All zero-fork.

```bash
into=d DateTime.utc "2024-01-15T10:30:45"
into=v $d.iso       # "2024-01-15T10:30:45"
into=v $d.isoDate   # "2024-01-15"
into=v $d.isoTime   # "10:30:45"
```

---

## Arithmetic

All arithmetic methods return a **new DateTime object**. The original is
not modified. Negative values subtract: `addDays -7` goes back one week.

```bash
into=d2 $d.addSeconds n
into=d2 $d.addMinutes n
into=d2 $d.addHours   n
into=d2 $d.addDays    n
```

All are pure integer arithmetic on the epoch — `(( epoch + n * unit ))`.
No subshells, no forks.

```bash
into=d DateTime.utc "2024-01-15"

into=tomorrow  $d.addDays  1
into=lastweek  $d.addDays  -7
into=plusthree $d.addHours 72

into=v $tomorrow.isoDate   # "2024-01-16"
into=v $lastweek.isoDate   # "2024-01-08"
```

There is no `subtractDays` or similar. Pass negative values to `addDays`,
`addHours`, etc.

---

## Difference

```bash
into=n $a.diffSeconds "$b"   # (a.epoch - b.epoch)
into=n $a.diffDays    "$b"   # (a.epoch - b.epoch) / 86400, truncated toward zero
```

Both return a **signed integer** — positive if `$a` is later than `$b`,
negative if earlier, zero if equal.

`diffDays` truncates toward zero, so a gap of 23 hours returns `0`, not `1`.
For ceiling or rounding behavior, use `diffSeconds` and divide yourself.

```bash
into=a DateTime.utc "2024-01-22"
into=b DateTime.utc "2024-01-15"

into=n $a.diffDays    "$b"   # "7"
into=n $b.diffDays    "$a"   # "-7"
into=n $a.diffSeconds "$b"   # "604800"
```

---

## Comparison

Exit-code-only methods. No output, no `into=` required.

```bash
$a.before "$b"    # exits 0 if a.epoch < b.epoch
$a.after  "$b"    # exits 0 if a.epoch > b.epoch
$a.equals "$b"    # exits 0 if a.epoch == b.epoch
```

All are `(( ))` integer comparisons — no subshells.

```bash
into=a DateTime.utc "2024-01-15"
into=b DateTime.utc "2024-01-22"

$a.before "$b" && printf "a is earlier\n"    # prints
$b.after  "$a" && printf "b is later\n"      # prints
$a.equals "$a" && printf "same\n"            # prints

if $deadline.before "$(DateTime.now)"; then
  printf "overdue\n"
fi
```

---

## Design Notes

### Why epoch as the single stored value

Storing one integer is the minimal representation. Every other value —
year, month, day, hour, formatted string — is derived from it on demand via
`printf '%(...)T'`. This means:

- **Arithmetic is trivial.** Adding a day is `(( epoch + 86400 ))`. No
  month-length table, no carry propagation, no year boundary detection.
- **No synchronization.** If the object stored year/month/day/hour separately,
  every mutation would need to update all fields. One field, one write.
- **Formatting is free.** The C library's strftime handles all the calendar
  math — leap years, month lengths, weekday calculation — and bash exposes
  it as a builtin.

The tradeoff: decomposing a date (year/month/day) from an epoch is slightly
more work than reading stored fields. In practice this is immeasurable because
`printf '%(...)T'` calls strftime(3) directly without forking.

### `printf '%(format)T'` as a bash builtin

Bash 4.2 added `printf '%(datefmt)T' timestamp` as a builtin that calls
strftime(3) with the given epoch. This is how all DateTime formatting works:

```bash
printf -v year  '%(%Y)T' "$epoch"    # calls strftime, no fork
printf -v iso   '%(%Y-%m-%dT%H:%M:%S)T' "$epoch"
```

The `-v varname` form writes directly to a variable without any output,
making it equivalent to a variable assignment with calendar-aware formatting.
This is available from bash 4.2 onward — the minimum for DateTime.

### The pure-bash epoch computation

`DateTime.utc` and the ISO 8601 fast path in `DateTime.parse` compute epoch
seconds from year/month/day/hour/minute/second using the proleptic Gregorian
calendar formula in pure bash arithmetic:

1. Count full years from 1970 to Y-1, multiplied by 365.
2. Add the number of leap years in that range using the standard formula
   (`Y/4 - Y/100 + Y/400`), anchored to 1969 (477 leap days before 1970).
3. Sum the days in each month for the current year, accounting for leap year
   in February.
4. Add the day-of-month (zero-based) and convert to seconds.

Leap year rule: divisible by 4, except centuries, except 400-year centuries.
This is correct for all dates from 1970 onward; the proleptic calendar
applies the same rule retroactively.

The formula has been verified against `date -d` for epoch 0 (1970-01-01),
leap day 2000-02-29 (951782400), and year 2100 (4102444800, confirming
2100 is not a leap year).

### DST and local time

Daylight Saving Time is not tracked by DateTime. The class works in UTC
internally. `format`, `iso`, and the component getters output local time
by respecting `$TZ` through strftime — this is handled by the C library
without any special treatment.

When `DateTime.parse` receives an ISO 8601 string without an explicit
timezone, it applies the current UTC offset (read via `printf '%(%z)T' -1`)
to the parsed components. This gives the right answer for current dates but
may be off by one hour for historical dates across DST transitions, because
the current offset may differ from the offset that was in effect on the
parsed date. For DST-correct parsing of historical local times, include an
explicit offset in the string, or let `parse` fall back to `date -d` by
using a non-ISO format that includes timezone information.

### What is not here

**Sub-second precision.** DateTime stores whole seconds. `EPOCHREALTIME`
(bash 5.0+) provides microsecond resolution; `EPOCHSECONDS` provides whole
seconds. For timing and profiling (rather than calendar work), use those
variables directly. A `DateTime.Precise` class built on `EPOCHREALTIME` is
a possible future addition.

**Timezone-aware objects.** The class has no concept of a timezone beyond
what `$TZ` provides to strftime. There is no `DateTime.inTimezone` or
offset-stored object. For timezone conversion, set `TZ` before reading
components or calling `format`.

**Duration objects.** There is no `Duration` class. Differences are integers
(seconds or days). If you need to represent "3 hours and 45 minutes" as a
first-class value, compute the seconds and pass the integer around.

**Parsing natural language.** "next Monday", "two weeks ago", "yesterday" are
not handled by the pure-bash path. They fall through to `date -d`, which
handles them on systems with GNU date. This is intentional: natural-language
parsing is complex and locale-sensitive; delegating it to `date` is correct.
