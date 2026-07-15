# Collection.Queue

FIFO (first-in, first-out) queue. Backed internally by a [List](List); exposes
only the queue surface. Enqueue to the back, dequeue from the front.

## Contents

- [Dependencies](#dependencies)
- [Constructor](#constructor)
- [Basic Usage](#basic-usage)
- [Methods](#methods)
  - [$q.enqueue val [val...]](#q-enqueue-val-val)
  - [$q.dequeue](#q-dequeue)
  - [$q.peek](#q-peek)
  - [$q.size](#q-size)
  - [$q.isEmpty](#q-isempty)
- [Common Patterns](#common-patterns)
  - [Work queue](#work-queue)
  - [BFS traversal](#bfs-traversal)
  - [Rate-limited dispatch](#rate-limited-dispatch)
- [Design Notes](#design-notes)
- [Collection.Queue.Fast](#collectionqueuefast)
  - [When to Use Fast](#when-to-use-fast)
  - [When to Use the Composition Version](#when-to-use-the-composition-version)
  - [Usage](#usage)
  - [Blocked Methods](#blocked-methods)
  - [Performance Note](#performance-note)

---

## Dependencies

```bash
. boop Queue    # also loads List and Container
```

---

## Constructor

```bash
into=q Collection.Queue
```

No arguments. The internal List is created automatically.

---

## Basic Usage

```bash
into=q Collection.Queue

$q.enqueue "job-1"
$q.enqueue "job-2"
$q.enqueue "job-3"

into=front $q.peek       # front="job-1" — does not remove
into=front $q.dequeue    # front="job-1" — removes it
into=front $q.dequeue    # front="job-2"
into=n     $q.size       # n="1"
$q.isEmpty || echo "still has items"
```

---

## Methods

### `$q.enqueue val [val...]`

Add one or more values to the back of the queue.

```bash
$q.enqueue "task-a"
$q.enqueue "task-b" "task-c"   # two in one call; task-b is ahead of task-c
```

### `$q.dequeue`

Remove and return the front value. Returns non-zero with an error if the queue is empty.

```bash
into=v $q.dequeue
```

Note: `dequeue` is O(n) — it uses `List.shift`, which re-indexes the
underlying array. For high-throughput work queues, consider a ring buffer
or two-stack implementation instead.

### `$q.peek`

Return the front value without removing it. Returns non-zero with an error if the queue is empty.

```bash
into=v $q.peek
```

### `$q.size`

Number of elements.

```bash
into=n $q.size
```

### `$q.isEmpty`

Exit code: 0 if empty, 1 if not.

```bash
$q.isEmpty && echo "all done"
while ! $q.isEmpty; do
  into=job $q.dequeue
  process "$job"
done
```

---

## Common Patterns

### Work queue

```bash
into=q Collection.Queue

# Producer: add work
for f in *.log; do
  $q.enqueue "$f"
done

# Consumer: process in order
while ! $q.isEmpty; do
  into=f $q.dequeue
  gzip "$f"
done
```

### BFS traversal

```bash
into=frontier Collection.Queue
$frontier.enqueue "$start_node"

while ! $frontier.isEmpty; do
  into=node $frontier.dequeue
  process "$node"
  for child in $(children "$node"); do
    $frontier.enqueue "$child"
  done
done
```

### Rate-limited dispatch

```bash
into=pending Collection.Queue

# Fill queue
for item in "${items[@]}"; do $pending.enqueue "$item"; done

# Process one at a time with delay
while ! $pending.isEmpty; do
  into=item $pending.dequeue
  dispatch "$item"
  sleep 0.5
done
```

---

## Design Notes

**Composition over inheritance.** Queue holds a List internally and exposes
only the queue surface. The full List API (random access, `each`, `slice`)
is not available from outside the object.

**O(n) dequeue.** `dequeue` calls `List.shift`, which re-indexes the whole
array. For bash script use cases this is rarely a problem. If you need true
O(1) dequeue at scale, a two-stack queue (two Collection.Stacks) gives
amortized O(1) at the cost of complexity.

**Error on underflow.** Both `dequeue` and `peek` call `_Error` on an empty
queue and return non-zero. Check `isEmpty` before calling if underflow is possible.

---

## Collection.Queue.Fast

Inheritance-based alternative. Extends List directly instead of wrapping
one via composition. Faster (one object, no delegation), but the full
List API is accessible if a caller ignores the queue contract.

### When to Use Fast

- Performance matters (tight loops, many queue objects)
- You trust callers to respect the queue interface
- You want `each`, `toArray`, `toString`, `clear` available on the queue
- Destroy is simpler (no cascading — it's just one object)

### When to Use the Composition Version

- You need strict encapsulation (internal List is unreachable)
- You want to guarantee no one calls `pop` or `getAt` by accident
- API surface discipline matters more than speed

### Usage

```bash
. boop Collection::Queue::Fast

into=q Collection.Queue.Fast
$q.enqueue "job-1" "job-2" "job-3"
into=v $q.peek              # "job-1"
into=v $q.dequeue           # "job-1"
into=n $q.size              # 2

# Inherited from List — available on Fast, hidden on composition Queue:
$q.each my_callback
into=all $q.toArray

# Blocked — errors with a clear message:
$q.pop                      # ERROR: not a valid queue operation
$q.unshift "x"             # ERROR: not a valid queue operation
```

### Blocked Methods

| Method | Why |
|--------|-----|
| `pop` | Removes from the back — violates FIFO |
| `unshift` | Inserts at the front — violates FIFO |
| `getAt` | Random access — violates FIFO |
| `setAt` | Random access — violates FIFO |
| `delete` | Random access — violates FIFO |
| `slice` | Random access — violates FIFO |

All return exit code 1 and emit `_Error` with guidance on the correct
method to use.

### Performance Note

`dequeue` is still O(n) — it re-indexes the array after removing the
front element. This is inherent to bash indexed arrays. The Fast variant
saves overhead on object creation, method dispatch, and destroy — not on
the dequeue operation itself.

---

[↑ Site map](index)
