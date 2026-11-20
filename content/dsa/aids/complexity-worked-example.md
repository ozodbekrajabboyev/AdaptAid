# Worked example: does a list contain a duplicate?

**Problem.** A sign-up system must reject a batch of usernames if any name appears twice. Write `has_duplicate(names)` and work out how its running time and memory grow with the number of names *n*.

## Step 1: write the obvious solution

Compare every pair of names once:

```python
def has_duplicate(names):
    n = len(names)
    for i in range(n):
        for j in range(i + 1, n):    # only pairs with j > i
            if names[i] == names[j]:
                return True
    return False
```

## Step 2: count the basic operation

The comparison `names[i] == names[j]` is the step that repeats. In the worst case (no duplicates, so the function never returns early) the inner loop runs:

| `i` | values of `j` | comparisons |
|---|---|---|
| 0 | 1 … n−1 | n − 1 |
| 1 | 2 … n−1 | n − 2 |
| … | … | … |
| n−2 | n−1 | 1 |
| n−1 | none | 0 |

Total = (n − 1) + (n − 2) + … + 1 + 0 = **n(n − 1)/2**.

## Step 3: check the formula with real numbers

| n | comparisons n(n − 1)/2 |
|---|---|
| 10 | 45 |
| 100 | 4,950 |
| 1,000 | 499,500 |
| 10,000 | 49,995,000 |

Each time *n* grows 10×, the work grows about 100×. That is the signature of quadratic growth.

## Step 4: simplify to Big-O

n(n − 1)/2 = ½n² − ½n. Keep the leading term and drop its constant: **O(n²) time**. The function only stores `i`, `j` and `n`, so its extra space is **O(1)**.

## Step 5: best case versus worst case

If the first two names are equal, the function returns after **1** comparison: the best case is O(1). The worst case, a batch with no duplicates at all, is the O(n²) counted above. We quote the worst case because it is what the system must be able to handle.

## Step 6: trade memory for time

A set answers "have I seen this name before?" in O(1) on average, so a single pass is enough:

```python
def has_duplicate_fast(names):
    seen = set()
    for name in names:          # n iterations
        if name in seen:        # O(1) on average
            return True
        seen.add(name)          # O(1) on average
    return False
```

Trace for `["ana", "bo", "cy", "bo"]`:

| name | `name in seen`? | `seen` afterwards |
|---|---|---|
| "ana" | no | {"ana"} |
| "bo" | no | {"ana", "bo"} |
| "cy" | no | {"ana", "bo", "cy"} |
| "bo" | **yes**, return `True` | (unchanged) |

## Result

| Version | Time (worst case) | Extra space |
|---|---|---|
| nested loops | O(n²) | O(1) |
| set | O(n) on average | O(n) |

For 10,000 names the first version makes almost 50 million comparisons; the second makes about 10,000 set lookups. Spending extra memory to save time is one of the most common trade-offs in algorithm design.
