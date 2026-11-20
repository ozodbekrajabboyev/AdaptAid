# Searching

Searching means finding where, or whether, a value occurs in a collection. Two algorithms cover most cases.

## Linear search

Check the items one by one from the start until you find the target or run out.

```python
def linear_search(a, x):
    for i in range(len(a)):
        if a[i] == x:
            return i
    return -1          # not found
```

It works on **any** sequence, sorted or not, including linked lists. Best case: 1 comparison (the target is first). Worst case: **O(n)** (the target is last or missing).

## Binary search

If the array is **sorted**, compare the target with the middle item. If they differ, the target can only be in one half, so discard the other half. Each step halves the range, so n items need at most about log₂ n + 1 comparisons: **O(log n)**. A million items take at most 20.

```python
def binary_search(a, x):
    lo, hi = 0, len(a) - 1      # search a[lo..hi], both ends included
    while lo <= hi:             # stop when the range is empty
        mid = (lo + hi) // 2
        if a[mid] == x:
            return mid
        elif a[mid] < x:
            lo = mid + 1        # x can only be right of mid
        else:
            hi = mid - 1        # x can only be left of mid
    return -1
```

**Preconditions:** the data must be sorted, and you must be able to reach any index in O(1), as in an array (not a linked list).

## Getting the boundaries right

Decide what `lo` and `hi` mean and keep everything consistent with that choice:

- With an inclusive `hi = len(a) - 1`, the loop must be `while lo <= hi`. Using `<` skips the last remaining candidate.
- Always move past `mid`: `lo = mid + 1` or `hi = mid - 1`. Writing `lo = mid` can loop forever once `lo` and `hi` are neighbours, because `mid` rounds down to `lo`.

## Lower bound

With duplicates, plain binary search returns *some* matching index, not necessarily the first. The **lower bound** of `x` is the first index `i` with `a[i] >= x`: the first occurrence of `x` if it is present, otherwise the position where `x` would be inserted. Python's `bisect.bisect_left(a, x)` computes it in O(log n).

## Which one to use?

For one search in unsorted data, use linear search: sorting first would cost O(n log n). For many searches, sort once and use binary search, or use a hash set for O(1) average lookups.

## Common mistake

Running binary search on unsorted data. It does not crash; it silently gives wrong answers, because discarding half is only safe when the order proves the target is not there.
