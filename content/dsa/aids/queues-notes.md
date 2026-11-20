# Queues

A **queue** hands items back in the order they arrived: **first in, first out (FIFO)**. Think of a line at a ticket counter: people join at the **back** and are served from the **front**.

Queues appear wherever work must be handled in arrival order: print jobs, requests to a web server, messages between programs, keyboard buffers, and the to-visit list of **breadth-first search** (BFS), which explores a graph level by level.

## Operations

| Operation | What it does | Cost |
|---|---|---|
| `enqueue(x)` | add `x` at the back | O(1) |
| `dequeue()` | remove and return the front item | O(1) |
| `peek()` | read the front item without removing it | O(1) |
| `is_empty()`, `size()` | inspect the queue | O(1) |

Looking for an arbitrary value is not a queue operation: it would take O(n).

## Two ways to get O(1) at both ends

**Circular array.** Keep a fixed-size array, the index `head` of the front item and a `count` of items. The next free slot is `(head + count) % capacity`. The `% capacity` wraps an index that runs off the end back to 0, so slots freed by dequeues get reused. When the array is full, allocate a bigger one and copy the items over **in queue order**, starting from `head`.

**Linked list.** Keep pointers to the `head` and the `tail` node. Enqueue links a new node after the tail; dequeue removes the head. Both are O(1). (Removing the tail of a singly linked list would be O(n), because you would have to walk to the node before it.)

## In Python

```python
from collections import deque

q = deque()
q.append("job1")       # enqueue at the right
q.append("job2")
first = q.popleft()    # dequeue from the left: "job1"
```

`collections.deque` is a **double-ended queue**: `append`, `appendleft`, `pop` and `popleft` are all O(1), so one deque can serve as a queue or a stack.

## Common mistake

Using a list and `items.pop(0)` to dequeue. A list stores its items in one contiguous block, so removing index 0 shifts every remaining item one place left: **O(n)** per dequeue, and O(n²) to empty the whole queue. Use `deque.popleft()` instead.
