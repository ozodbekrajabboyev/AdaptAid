# Recursion

A **recursive** function solves a problem by calling itself on a smaller version of the same problem. It keeps shrinking the problem until it reaches a case small enough to answer directly.

Every correct recursive function has two parts:

1. **Base case**: the smallest input, answered without another call. It stops the recursion.
2. **Recursive case**: reduce the problem, call the function on the smaller input, then combine the result.

```python
def factorial(n):
    if n == 0:                       # base case
        return 1
    return n * factorial(n - 1)     # recursive case: smaller problem, then combine
```

## What actually happens: the call stack

Each call gets its own **stack frame** holding its parameters and local variables. `factorial(3)` does not finish until `factorial(2)` returns, which waits for `factorial(1)`, which waits for `factorial(0)`. The frames pile up, then *unwind* in reverse order as each call returns:

| Call | Waits for | Returns |
|---|---|---|
| `factorial(3)` | `factorial(2)` | 3 × 2 = 6 |
| `factorial(2)` | `factorial(1)` | 2 × 1 = 2 |
| `factorial(1)` | `factorial(0)` | 1 × 1 = 1 |
| `factorial(0)` | nothing (base case) | 1 |

Because the frames stay on the stack until they return, recursion depth costs memory: `factorial(n)` uses **O(n) extra space**.

## How to write one

1. Decide what the function returns for the smallest input. That is your base case.
2. Assume the function already works for a smaller input (the "leap of faith").
3. Use that smaller answer to build the answer for the current input.
4. Check that every call moves *toward* the base case.

## Cost

Time is roughly (number of calls) × (work per call). One recursive call per level, as in factorial, gives O(n). Two calls per level that overlap heavily, as in the naive Fibonacci below, gives O(2ⁿ), because the same values are recomputed again and again. Storing results you have already computed (**memoization**) brings Fibonacci down to O(n).

```python
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)  # two overlapping calls: exponential time
```

## Common mistakes

- **No base case, or one that is never reached** (for example stepping by 2 from an odd number toward 0). The calls never stop and Python raises `RecursionError` when the stack is full.
- **Forgetting to `return`** the recursive result, so the function returns `None`.
- **Using recursion for very deep inputs.** Python's default limit is about 1000 frames; a loop is safer there.
