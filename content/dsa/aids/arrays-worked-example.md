# Worked example: two prices that use up a gift card

**Problem.** A shop keeps its prices in a sorted list. A customer has a gift card worth exactly 25 and wants two *different* items that use it up exactly. Write `pair_with_sum(prices, target)` that returns the two prices, or `None` if there is no such pair.

```python
prices = [3, 5, 8, 11, 14, 19, 23, 27]
target = 25
```

## Step 1: the brute-force idea

Try every pair `(i, j)` with `i < j`. For 8 prices that is 8 × 7 / 2 = 28 pairs; in general n(n − 1)/2 pairs, so **O(n²)** time. It works, but it ignores the fact that the list is sorted.

## Step 2: use the sorted order

Put one pointer `i` on the smallest price and one pointer `j` on the largest, and look at their sum:

- **Sum too big:** `prices[j]` is already paired with the smallest price available, so it is too big to pair with anything. Discard it: `j -= 1`.
- **Sum too small:** `prices[i]` is already paired with the largest price available, so it is too small to pair with anything. Discard it: `i += 1`.
- **Sum equal:** found it.

Every step throws away one price that cannot be part of an answer, so no valid pair is ever skipped.

## Step 3: the code

```python
def pair_with_sum(prices, target):
    i, j = 0, len(prices) - 1
    while i < j:
        s = prices[i] + prices[j]
        if s == target:
            return prices[i], prices[j]
        elif s < target:
            i += 1          # need a bigger sum
        else:
            j -= 1          # need a smaller sum
    return None
```

## Step 4: trace it

| Step | `i` | `j` | `prices[i]` | `prices[j]` | sum | action |
|---|---|---|---|---|---|---|
| 1 | 0 | 7 | 3 | 27 | 30 | too big, `j -= 1` |
| 2 | 0 | 6 | 3 | 23 | 26 | too big, `j -= 1` |
| 3 | 0 | 5 | 3 | 19 | 22 | too small, `i += 1` |
| 4 | 1 | 5 | 5 | 19 | 24 | too small, `i += 1` |
| 5 | 2 | 5 | 8 | 19 | 27 | too big, `j -= 1` |
| 6 | 2 | 4 | 8 | 14 | 22 | too small, `i += 1` |
| 7 | 3 | 4 | 11 | 14 | 25 | **found** |

The function returns `(11, 14)`.

## Step 5: the "no pair" case

With `target = 12` the pointers close in (3 + 27, 3 + 23, … , 5 + 8) until `i == j`, the loop stops, and the function returns `None`. No pair of different items sums to 12.

## Step 6: cost

Each step moves one pointer one place closer to the other, so there are at most n − 1 steps: **O(n) time**. Here it needed 7 steps instead of up to 28 pair checks. The only extra memory is `i`, `j` and `s`: **O(1) extra space**.

**Takeaway.** On a sorted array, two pointers moving inwards can replace a pair of nested loops, turning O(n²) into O(n).
