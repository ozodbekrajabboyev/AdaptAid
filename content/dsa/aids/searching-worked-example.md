# Worked example: first occurrence and counting with binary search

**Problem.** A sorted list holds the exam scores of 7 students:

```python
scores = [12, 25, 25, 25, 38, 41, 57]
```

1. Find the index of the **first** score of 25.
2. Count how many students scored **below the pass mark of 40**.

## Step 1: try plain binary search

With `lo = 0` and `hi = 6`, the first `mid` is 3, and `scores[3]` is 25, so plain binary search returns **3**. That is a 25, but not the first one: indices 1 and 2 also hold 25. Plain binary search stops at any match, so it cannot answer question 1.

## Step 2: ask a different question

Instead of "where is 25?", ask "what is the first index `i` with `scores[i] >= 25`?". This is the **lower bound**. If `a[mid] >= x`, the answer is `mid` or something to its left, so `mid` must stay in the range. If `a[mid] < x`, the answer is to the right of `mid`.

```python
def lower_bound(a, x):
    lo, hi = 0, len(a)          # the answer is somewhere in lo..hi (hi = len(a) means "after the end")
    while lo < hi:
        mid = (lo + hi) // 2
        if a[mid] < x:
            lo = mid + 1        # mid and everything left of it are too small
        else:
            hi = mid            # mid might be the answer: keep it
    return lo
```

The boundaries differ from plain binary search: `hi` starts at `len(a)`, the loop runs while `lo < hi`, and the update is `hi = mid`, not `mid - 1`. It still always makes progress, because `mid < hi` whenever `lo < hi`.

## Step 3: trace question 1 (x = 25)

| `lo` | `hi` | `mid` | `a[mid]` | Decision |
|---|---|---|---|---|
| 0 | 7 | 3 | 25 | 25 ≥ 25, so `hi = 3` |
| 0 | 3 | 1 | 25 | 25 ≥ 25, so `hi = 1` |
| 0 | 1 | 0 | 12 | 12 < 25, so `lo = 1` |
| 1 | 1 | | | `lo == hi`: stop |

Result: **1**, the first 25. Notice that the search kept going left after finding a 25 at index 3, because an earlier 25 might exist.

## Step 4: trace question 2 (x = 40)

The lower bound of 40 is the position of the first score that is 40 or more. Every index before it holds a score below 40, so the lower bound **is** the count.

| `lo` | `hi` | `mid` | `a[mid]` | Decision |
|---|---|---|---|---|
| 0 | 7 | 3 | 25 | 25 < 40, so `lo = 4` |
| 4 | 7 | 5 | 41 | 41 ≥ 40, so `hi = 5` |
| 4 | 5 | 4 | 38 | 38 < 40, so `lo = 5` |
| 5 | 5 | | | `lo == hi`: stop |

Result: **5** students scored below 40 (12, 25, 25, 25 and 38). The value 40 is not in the list at all, yet the function still gives a useful answer: the index where 40 would be inserted to keep the list sorted.

## Step 5: check with the standard library

```python
from bisect import bisect_left

bisect_left(scores, 25)   # 1
bisect_left(scores, 40)   # 5
```

## Step 6: cost

Each iteration halves `hi - lo`, so each question takes **O(log n)** time and O(1) extra space. A linear scan would also work, but it costs O(n).

**Try it yourself:** how many students scored exactly 25? Compute `lower_bound(scores, 26) - lower_bound(scores, 25)`, which is 4 − 1 = 3.
