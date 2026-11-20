# Time and space complexity

**Complexity** describes how the cost of an algorithm grows as its input gets bigger. **Time complexity** counts the basic steps it performs (comparisons, assignments, arithmetic); **space complexity** counts the extra memory it needs. Both are written as a function of the input size *n*.

Why not just time the program? Seconds depend on the computer, the language and the data. Counting steps gives an answer that holds on any machine and predicts what happens as *n* grows.

## Big-O: keep the part that grows fastest

Suppose a function performs `3n² + 5n + 20` steps. At n = 1,000 the `3n²` part is 3,000,000 while the rest is about 5,000, so the leading term decides everything. **Big-O** keeps that term and drops its constant: the function is **O(n²)**.

Formally, f(n) is O(g(n)) if f(n) ≤ c·g(n) for some constant c and every large enough n. Big-O is an upper bound, so always quote the *tightest* one you can.

## Common growth rates, best to worst

| Big-O | Name | Typical example |
|---|---|---|
| O(1) | constant | read `a[i]` |
| O(log n) | logarithmic | halve the search range each step |
| O(n) | linear | one loop over the input |
| O(n log n) | linearithmic | merge sort |
| O(n²) | quadratic | nested loops over all pairs |
| O(2ⁿ) | exponential | try every subset |

## Counting rules

- Steps one after another **add**: two separate loops over n items cost O(n + n) = O(n).
- Nested loops **multiply**: a loop of n inside a loop of n costs O(n²).
- A loop whose variable **halves** (or doubles) each time runs about log₂ n times.
- Drop constants and smaller terms: O(4n + 7) = O(n).

## Best, worst and average case

Inputs of the same size can take different amounts of work. Linear search finds its target on the first comparison in the **best case** (O(1)), checks all n items in the **worst case** (O(n)), and checks about n/2 on **average**, which is still O(n). "The complexity" usually means the worst case, because it is a guarantee.

## Space complexity

Count the *extra* memory the algorithm creates, not the input itself. Summing a list with one running total is O(1) extra space; building a new list of n results is O(n).

## Common mistakes

- **"Two loops means O(n²)."** Only when they are *nested*. Loops in sequence add.
- **Reading Big-O as seconds.** An algorithm doing 50n steps is slower than one doing n² steps until n passes 50. Big-O describes how cost *grows*, not which is faster on small inputs.
