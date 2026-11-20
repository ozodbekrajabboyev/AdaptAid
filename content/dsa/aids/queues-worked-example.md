# Worked example: a circular-array print queue

**Problem.** An office printer can hold at most 4 waiting jobs. Implement its job queue with a fixed array so that adding and removing a job are both O(1). Then trace a busy morning: jobs A, B and C arrive, two are printed, jobs D, E and F arrive, a seventh job G is attempted, and two more are printed.

## Step 1: choose the state

Store three things:

- `data`: an array with 4 slots
- `head`: the index of the front job (the next one to print)
- `count`: how many jobs are waiting

The back of the queue is not stored; it is computed. The next free slot is `(head + count) % 4`.

## Step 2: write enqueue and dequeue

```python
class CircularQueue:
    def __init__(self, capacity):
        self.data = [None] * capacity
        self.head = 0      # index of the front item
        self.count = 0     # number of items stored

    def is_empty(self):
        return self.count == 0

    def is_full(self):
        return self.count == len(self.data)

    def enqueue(self, item):
        if self.is_full():
            raise OverflowError("queue is full")
        tail = (self.head + self.count) % len(self.data)
        self.data[tail] = item
        self.count += 1

    def dequeue(self):
        if self.is_empty():
            raise IndexError("dequeue from empty queue")
        item = self.data[self.head]
        self.data[self.head] = None              # drop the reference
        self.head = (self.head + 1) % len(self.data)
        self.count -= 1
        return item
```

Neither method contains a loop, so each one does a fixed amount of work.

## Step 3: trace the morning

`_` marks an empty slot.

| # | Operation | Slot used | `data` after | `head` | `count` |
|---|---|---|---|---|---|
| 0 | start | none | `[_, _, _, _]` | 0 | 0 |
| 1 | enqueue A | (0 + 0) % 4 = 0 | `[A, _, _, _]` | 0 | 1 |
| 2 | enqueue B | (0 + 1) % 4 = 1 | `[A, B, _, _]` | 0 | 2 |
| 3 | enqueue C | (0 + 2) % 4 = 2 | `[A, B, C, _]` | 0 | 3 |
| 4 | dequeue, returns A | slot 0 | `[_, B, C, _]` | 1 | 2 |
| 5 | dequeue, returns B | slot 1 | `[_, _, C, _]` | 2 | 1 |
| 6 | enqueue D | (2 + 1) % 4 = 3 | `[_, _, C, D]` | 2 | 2 |
| 7 | enqueue E | (2 + 2) % 4 = **0** (wraps) | `[E, _, C, D]` | 2 | 3 |
| 8 | enqueue F | (2 + 3) % 4 = 1 | `[E, F, C, D]` | 2 | 4 |
| 9 | enqueue G | full: `OverflowError` | `[E, F, C, D]` | 2 | 4 |
| 10 | dequeue, returns C | slot 2 | `[E, F, _, D]` | 3 | 3 |
| 11 | dequeue, returns D | slot 3 | `[E, F, _, _]` | **0** (wraps) | 2 |

## Step 4: read the result

After step 8 the array reads `E, F, C, D`, but the **queue** is read from `head` onwards, wrapping at the end: C, D, E, F. The jobs were printed in exactly the order they arrived: A, B, C, D, with E and F still waiting. Without the wrap-around in step 7, job E would have been refused even though slots 0 and 1 were free.

## Step 5: cost

- `enqueue` and `dequeue`: **O(1)**, a few arithmetic steps each, however many jobs are waiting.
- Space: **O(capacity)**.

To accept any number of jobs, replace the `OverflowError` with a resize: allocate an array twice as big, copy the items **in queue order** (from `head`, wrapping) into slots 0, 1, 2, ... of the new array, and set `head = 0`. That copy costs O(n), but doubling makes it rare, so enqueue stays O(1) on average (amortised).

**Try it yourself:** add a `peek()` method. After checking that the queue is not empty, it is a single line: `return self.data[self.head]`.
