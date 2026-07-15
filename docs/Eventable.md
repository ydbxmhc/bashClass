# Eventable (mixin)

Per-object publish/subscribe events. Mix `Eventable` into any class and its
instances gain their own event channels: subscribe callbacks to named events,
then emit those events to fire every subscriber.

It's a thin layer over the core [`_Stack`](boop#stack)
primitive — each event is a stack of handlers scoped to the object — so it
inherits `_Stack`'s two best properties for free: arbitrary event names, and
automatic cleanup when the object is destroyed.

## Contents

- [Dependencies](#dependencies)
- [Mixing In](#mixing-in)
- [Quick Start](#quick-start)
- [Methods](#methods)
  - [`on EVENT CALLBACK`](#on-event-callback)
  - [`emit EVENT [args...]`](#emit-event-args)
  - [`off EVENT CALLBACK`](#off-event-callback)
  - [`count EVENT` → `into=`](#count-event--into)
  - [`clear EVENT`](#clear-event)
- [The Callback Contract](#the-callback-contract)
- [Dispatch Order (LIFO)](#dispatch-order-lifo)
- [Error Handling](#error-handling)
- [Per-Object Isolation](#per-object-isolation)
- [Lifecycle: Free Cleanup on Destroy](#lifecycle-free-cleanup-on-destroy)
- [Class-Level Events](#class-level-events)
- [Common Patterns](#common-patterns)
- [Design Notes](#design-notes)
- [Eventable vs Signal](#eventable-vs-signal)

---

## Dependencies

```bash
. boop Eventable
```

`Eventable` uses the core `_Stack` primitive, which is always available once
boop is loaded — no other classes required.

---

## Mixing In

```bash
boopClass Button isa:SomeBase mixin:Eventable has:label public:new,press
```

Any instance of `Button` now has `on`, `emit`, `off`, `count`, and `clear`.
A class may mix in `Eventable` alongside other mixins; class methods win over
mixin methods, and earlier-listed mixins win over later ones (call
`$obj.Eventable::on` to force Eventable's version if a name collides).

---

## Quick Start

```bash
. boop Eventable
boopClass Button mixin:Eventable public:new,press

into=b Button

# Subscribe a couple of listeners
on_click()  { printf 'clicked at %s,%s\n' "$2" "$3"; }   # $1=event, $2..=args
log_click() { printf 'audit: click\n'; }
$b.on click on_click
$b.on click log_click

# Fire the event, forwarding coordinates
$b.emit click 12 34
# audit: click            <- log_click (subscribed last, fires first)
# clicked at 12,34        <- on_click
```

---

## Methods

### `on EVENT CALLBACK`

Subscribe `CALLBACK` (a function name) to `EVENT` on this object. The newest
subscriber fires first (see [dispatch order](#dispatch-order-lifo)).

```bash
$obj.on ready initialize_widget
$obj.on ready log_ready
```

Both `EVENT` and `CALLBACK` are required; a missing one is an `_Error` and
returns non-zero. `EVENT` can be any string — dots, spaces, anything — because
it's a `_Stack` name, not a bash identifier.

### `emit EVENT [args...]`

Fire every handler registered for `EVENT` on this object, in LIFO order,
forwarding the event name and any extra arguments to each handler.

```bash
$obj.emit ready
$obj.emit data "$payload" "$source"
```

Emitting an event with no subscribers is a harmless no-op. `emit` does not
return a meaningful value — it's a broadcast, not a query.

### `off EVENT CALLBACK`

Remove the first registration of `CALLBACK` from `EVENT`. If the same callback
was subscribed twice, the second registration remains.

```bash
$obj.off ready log_ready
$obj.off ready never_subscribed   # no-op, no error
```

### `count EVENT` → `into=`

Return the number of handlers currently registered for `EVENT`.

```bash
into=n $obj.count ready    # n="2"
into=n $obj.count unknown  # n="0"
```

### `clear EVENT`

Remove all handlers for `EVENT`.

```bash
$obj.clear ready
into=n $obj.count ready    # n="0"
```

---

## The Callback Contract

A handler is invoked as:

```
callback <event> [emit-args...]
```

- **`$1`** — the event name that fired (clean, not an internal channel id).
- **`$2…`** — whatever `emit` forwarded after the event name.

```bash
on_data() {
  local event="$1"           # "data"
  local payload="$2"
  local source="${3:-}"
  process "$payload"
}
$obj.on data on_data
$obj.emit data "$blob" upstream
```

Handlers must be defined functions. Their return value is ignored by the
emitter (this is a notification, not a pipeline) — but see
[Error Handling](#error-handling) for what a non-zero return triggers.

---

## Dispatch Order (LIFO)

Handlers fire in reverse subscription order: last subscribed, first called.
This matches the usual "most recently attached handler gets first crack"
expectation and mirrors [Signal](Signal)'s ordering.

```bash
$obj.on save write_disk       # fires last
$obj.on save validate         # fires first
$obj.emit save                # validate, then write_disk
```

If you need first-subscribed-first ordering, subscribe in the reverse order,
or model it explicitly — the LIFO guarantee is stable and part of the contract.

---

## Error Handling

A handler that returns non-zero **does not** halt dispatch — the remaining
handlers still fire. This is deliberate: subscribers are independent parties,
and one buggy listener shouldn't silently deprive the others of a notification
they registered for.

The failure is **not** swallowed silently, though. Eventable logs a `_Warn`
naming the offending listener:

```
[WARN] __Eventable.invoke: Eventable: listener 'bad_handler' returned nonzero (save)
```

- The warning is visible at the default log level and silenceable via
  `_LogLevel error` if you find it noisy.
- Because `_Warn` returns 0, dispatch stays `set -e`-safe.
- Under the opt-in `_FatalLevel warn` (or `_FatalLevel warn <HostClass>`), that
  warning **escalates to a crash** — the intended strict-mode behaviour for
  CI and the like. In normal operation (`_FatalLevel crash`, the default) a
  failing listener never aborts the run.

A handler's own stderr is never suppressed, so it can complain in its own
voice too.

---

## Per-Object Isolation

Each object's event channels are entirely its own. Subscribing to `click` on
one button has no effect on another.

```bash
into=a Button
into=b Button
$a.on click handle_a
$b.on click handle_b
$a.emit click    # only handle_a runs
$b.emit click    # only handle_b runs
```

This falls out of `_Stack`'s identity scoping: the handler stacks are keyed by
the object's ID.

---

## Lifecycle: Free Cleanup on Destroy

Because subscriptions live in `__boop_static` under the object's `<id>.`
prefix, `$obj.destroy` sweeps them away with everything else the object owns.
There is no `_destroy` hook to write and no leak to worry about:

```bash
into=w Button
$w.on click handler
$w.destroy         # the click subscription is gone with it
```

This is the payoff of building on `_Stack` rather than a bespoke registry:
lifecycle is handled by the core, uniformly, for free.

---

## Class-Level Events

Called on the class rather than an instance, the identity falls back to the
class name, giving you shared/broadcast channels:

```bash
Button.on globalReset reset_all_buttons
Button.emit globalReset
```

Use this sparingly — class-level subscriptions persist for the life of the
process (classes aren't destroyed) and are shared by all callers.

---

## Common Patterns

### Widget lifecycle hooks

```bash
boopClass Widget mixin:Eventable public:new,mount,unmount

Widget.mount()   { local _Self="${_Self:-}"; $_Self.emit mounted; }
Widget.unmount() { local _Self="${_Self:-}"; $_Self.emit unmounted; }

into=w Widget
$w.on mounted   start_animation
$w.on unmounted stop_animation
```

### One-shot listener

```bash
__once() {
  _Self="$obj" $obj.off ready __once   # unsubscribe self
  printf 'ready, once\n'
}
$obj.on ready __once
```

### Fan-out to independent subscribers

```bash
$order.on placed notify_customer
$order.on placed reserve_inventory
$order.on placed emit_metrics
$order.emit placed "$order_id"   # all three fire, independently
```

---

## Design Notes

**Built on `_Stack`.** Each event is a `_Stack` named `evt.<event>`, scoped to
the object. Eventable adds no storage of its own — `on` is `_Stack push`, `off`
is `_Stack remove`, `emit` is `_Stack each` through a small trampoline, `count`
is `_Stack size`, `clear` is `_Stack clear`.

**Clean event names, arbitrary strings.** Because event names are `_Stack`
keys (associative-array keys), not bash variable names, any string works —
including dotted (`user.login`) or spaced names. The earlier hand-rolled
`Emitter` sketch composed the object ID and event into a bash *variable* name
and broke on dots; `_Stack` sidesteps that entirely.

**The listener runs with the caller's IFS.** The internal dispatch trampoline
is careful not to set a `local IFS` before invoking a handler — that would leak
into the handler via bash's dynamic scoping and silently change its
word-splitting. IFS is pinned only around Eventable's own warning message.

---

## Eventable vs Signal

Both layer LIFO handler stacks over `_Stack`, but they serve different needs:

| | Eventable | [Signal](Signal) |
|---|---|---|
| Scope | Per-object (or per-class) channels | Process-global, per OS signal |
| Trigger | Manual `$obj.emit EVENT` | OS signals via `trap`, or `Signal.dispatch` |
| Event names | Any string you choose | Real signal names (INT, TERM, EXIT, ...) |
| Failing handler | Logs a `_Warn`, continues | Silently continues (`|| true`) — trap-safe |
| Cleanup | Automatic on `$obj.destroy` | `Signal.clear` |

Reach for **Eventable** when objects need to announce things to interested
observers; reach for **Signal** when you're handling actual OS signals or need
one shared, process-wide handler stack.

---

[↑ Site map](index)
