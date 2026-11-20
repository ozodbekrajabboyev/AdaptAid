# Worked example: reversing a linked list in place

**Problem.** A music app stores a playlist as a singly linked list `10 → 20 → 30 → 40`. Write `reverse(head)` that reverses the list *in place* (no new nodes) and returns the new head, giving `40 → 30 → 20 → 10`.

```python
class Node:
    def __init__(self, val, next=None):
        self.val = val
        self.next = next
```

## Step 1: what has to change

Every arrow must point the other way: 20 must point to 10, 30 to 20, 40 to 30. The old head, 10, becomes the tail, so its `next` must become `None`.

## Step 2: choose the pointers

Walk the list once with three references:

- `prev`: the head of the part already reversed (starts as `None`)
- `cur`: the node being processed (starts at `head`)
- `nxt`: the rest of the list, saved *before* `cur.next` is overwritten

## Step 3: write the loop

For each node: save the rest, flip the arrow, then move both pointers one step forward.

```python
def reverse(head):
    prev = None
    cur = head
    while cur is not None:
        nxt = cur.next      # 1. save the rest of the list
        cur.next = prev     # 2. flip this node's arrow
        prev = cur          # 3. the reversed part now starts at cur
        cur = nxt           # 4. move on to the rest
    return prev             # prev is the new head
```

## Step 4: trace it

The state after each iteration. "Reversed part" is the list starting at `prev`; "still to do" starts at `cur`.

| After iteration | `prev` | `cur` | reversed part | still to do |
|---|---|---|---|---|
| (start) | None | 10 | (empty) | 10 → 20 → 30 → 40 |
| 1 | 10 | 20 | 10 | 20 → 30 → 40 |
| 2 | 20 | 30 | 20 → 10 | 30 → 40 |
| 3 | 30 | 40 | 30 → 20 → 10 | 40 |
| 4 | 40 | None | 40 → 30 → 20 → 10 | (empty) |

Now `cur` is `None`, the loop stops, and the function returns `prev`: the node holding 40.

## Step 5: check the edge cases

- **Empty list** (`head is None`): the loop never runs and the function returns `None`. Correct.
- **One node:** one iteration sets its `next` to `None` (it already was) and returns it. Correct.

## Step 6: see why `nxt` is needed

Suppose you skip `nxt` and write `cur.next = prev`, `prev = cur`, `cur = cur.next`. After the first line, `cur.next` already points backwards, so `cur` jumps to `None`. The loop ends after one node and returns a list containing only 10: nodes 20, 30 and 40 are lost.

## Result

Each node is visited once with O(1) work: **O(n) time**. Only three extra references are used: **O(1) extra space**. Copying the values into a Python list and rebuilding the links would also work, but it needs O(n) extra space.
