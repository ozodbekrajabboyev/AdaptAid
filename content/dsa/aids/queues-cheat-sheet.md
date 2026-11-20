# Queues cheat sheet

## Operations (good implementation)

| Operation | Meaning | Cost |
|---|---|---|
| `enqueue(x)` | add at the back | O(1) |
| `dequeue()` | remove and return the front | O(1) |
| `peek()` | read the front, do not remove | O(1) |
| `is_empty()`, `size()` | inspect | O(1) |
| is `x` anywhere in the queue? | not a queue operation | O(n) |

## Implementations compared

| Implementation | Enqueue | Dequeue | Notes |
|---|---|---|---|
| Python list: `append` + `pop(0)` | O(1) | **O(n)** | every remaining item shifts left; avoid |
| Python list: `insert(0, x)` + `pop()` | **O(n)** | O(1) | every item shifts right; avoid |
| Circular array (`head`, `count`) | O(1), amortised if it resizes | O(1) | fixed block of memory, cache friendly |
| Singly linked list with `head` and `tail` | O(1) at the tail | O(1) at the head | extra pointer per item |
| `collections.deque` | O(1) `append` | O(1) `popleft` | the standard choice in Python |

## Circular-array formulas

| Quantity | Formula |
|---|---|
| front item | `data[head]` |
| next free slot | `(head + count) % capacity` |
| slot of the back item | `(head + count - 1) % capacity` |
| after a dequeue | `head = (head + 1) % capacity`, `count -= 1` |
| empty / full | `count == 0` / `count == capacity` |
| growing | copy in queue order from `head` into slots 0, 1, 2, ..., then `head = 0` |

## Linked-queue edge cases

| Situation | Update |
|---|---|
| enqueue into an empty queue | `head` and `tail` both point to the new node |
| dequeue the only node | `head` and `tail` both become `None` |

## Queue, stack, deque or priority queue?

| Structure | Removes first | Typical uses |
|---|---|---|
| Stack | the newest item (LIFO) | undo, the call stack, depth-first search |
| Queue | the oldest item (FIFO) | scheduling, buffers, breadth-first search |
| Deque | either end, your choice | sliding windows, a queue and a stack in one |
| Priority queue | the most urgent item | Dijkstra's algorithm, event simulation (see heaps) |

## `collections.deque` quick reference

| Call | Effect | Cost |
|---|---|---|
| `q.append(x)` | add at the right (back) | O(1) |
| `q.popleft()` | remove from the left (front) | O(1) |
| `q.appendleft(x)` | add at the left | O(1) |
| `q.pop()` | remove from the right | O(1) |
| `q[0]`, `q[-1]` | peek at the front, the back | O(1) |
| `len(q)`, `if q:` | size, non-empty test | O(1) |
