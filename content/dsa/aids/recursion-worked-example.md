# Worked example: sum of the digits of a number

**Problem.** Write a recursive function `digit_sum(n)` that returns the sum of the decimal digits of a non-negative integer, so `digit_sum(4096) == 19`.

## Step 1: find the base case

A single-digit number is its own digit sum. The smallest case is `n < 10`:

```python
if n < 10:
    return n
```

## Step 2: shrink the problem

For a larger number, split off the last digit:

- last digit: `n % 10` (for 4096 that is 6)
- the rest: `n // 10` (for 4096 that is 409)

`409` is a smaller instance of the same problem.

## Step 3: trust the smaller call and combine

If `digit_sum(409)` is correct, the answer for 4096 is `6 + digit_sum(409)`.

```python
def digit_sum(n):
    if n < 10:                          # base case
        return n
    return n % 10 + digit_sum(n // 10)  # last digit + sum of the rest
```

## Step 4: check it moves toward the base case

Each call divides `n` by 10, so the number of digits drops by one every time. It must reach `n < 10`.

## Step 5: trace it

| Call | `n % 10` | Recursive call | Returns |
|---|---|---|---|
| `digit_sum(4096)` | 6 | `digit_sum(409)` | 6 + 13 = **19** |
| `digit_sum(409)` | 9 | `digit_sum(40)` | 9 + 4 = 13 |
| `digit_sum(40)` | 0 | `digit_sum(4)` | 0 + 4 = 4 |
| `digit_sum(4)` | (base case) | none | 4 |

The calls go *down* the table; the return values are built on the way back *up*.

## Step 6: cost

There is one call per digit, so a number with *d* digits takes O(*d*) time and O(*d*) stack space. Since *d* ≈ log₁₀ *n*, that is **O(log n)**.

**Try it yourself:** change the function so it counts the digits instead of adding them. Only the combine step changes: `1 + count(n // 10)`.
