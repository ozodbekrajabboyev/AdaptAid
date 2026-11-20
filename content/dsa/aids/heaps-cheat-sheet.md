# Heaps cheat sheet

## Shape and storage

| Fact | Value |
|---|---|
| Shape | complete binary tree: all levels full except the last, filled left to right |
| Min-heap property | every parent ≤ its children, so the minimum is at index 0 |
| Max-heap property | every parent ≥ its children, so the maximum is at index 0 |
| Children of `i` (0-based) | `2*i + 1` and `2*i + 2` |
| Parent of `i` (0-based) | `(i - 1) // 2` |
| Children of `i` (1-based, many textbooks) | `2*i` and `2*i + 1`, parent `i // 2` |
| Leaves (0-based, *n* items) | indexes `n // 2` to `n - 1` |
| Height | ⌊log₂ n⌋ |

## Operations

| Operation | How | Cost |
|---|---|---|
| Peek min | read `a[0]` | O(1) |
| Insert | append, then sift up | O(log n) |
| Extract min | move last to root, then sift down (swap with the smaller child) | O(log n) |
| Build heap | sift down indexes `n//2 - 1` down to 0 | O(n) |
| Insert *n* items one by one | *n* pushes | O(n log n) |
| Search for an arbitrary key | scan the array | O(n) |
| Heapsort | build max-heap, then *n* times: swap root with last, shrink, sift down | O(n log n) time, O(1) extra space, not stable |

## Python `heapq` (a min-heap on a plain list)

| Call | Does | Cost |
|---|---|---|
| `heapq.heapify(a)` | rearranges `a` into a heap in place | O(n) |
| `heapq.heappush(h, x)` | inserts `x` | O(log n) |
| `heapq.heappop(h)` | removes and returns the smallest | O(log n) |
| `h[0]` | the smallest, without removing it | O(1) |
| `heapq.heappushpop(h, x)` | push `x`, then pop the smallest | O(log n) |
| `heapq.nsmallest(k, a)` / `nlargest(k, a)` | the *k* smallest / largest items | about O(n log k) |

- **Max-heap**: push `-x`, and negate the value you pop.
- **Priorities with data**: push tuples `(priority, count, item)`; the unique `count` breaks ties so Python never has to compare two items.

## Which structure for a priority queue?

| Structure | Insert | Extract min | Good when |
|---|---|---|---|
| Unsorted list | O(1) | O(n) | very few extracts |
| Sorted list (largest first, pop from the end) | O(n) | O(1) | very few inserts |
| Binary heap | O(log n) | O(log n) | mixed inserts and extracts (the usual choice) |
| Balanced BST | O(log n) | O(log n) | you also need search, delete-any or sorted iteration |
