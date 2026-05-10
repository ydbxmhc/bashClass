# Collection.Queue

FIFO (first-in, first-out) queue. Backed internally by a List; exposes only
the queue surface. Enqueue to the back, dequeue from the front.

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

Remove and return the front value. Crashes if the queue is empty.

```bash
into=v $q.dequeue
```

Note: `dequeue` is O(n) — it uses `List.shift`, which re-indexes the
underlying array. For high-throughput work queues, consider a ring buffer
or two-stack implementation instead.

### `$q.peek`

Return the front value without removing it. Crashes if the queue is empty.

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

**Crash on underflow.** Both `dequeue` and `peek` call `_Crash` on an empty
queue. Check `isEmpty` before calling if underflow is possible.
