# Complexity cheat sheet

## Growth rates, best to worst

| Big-O | Name | n = 10 | n = 1,000 | n = 1,000,000 | Example |
|---|---|---|---|---|---|
| O(1) | constant | 1 | 1 | 1 | `a[i]`, `len(a)`, dict lookup (average) |
| O(log n) | logarithmic | ≈ 3 | ≈ 10 | ≈ 20 | binary search, halving loop |
| O(n) | linear | 10 | 1,000 | 10⁶ | linear search, one loop |
| O(n log n) | linearithmic | ≈ 33 | ≈ 10,000 | ≈ 2 × 10⁷ | merge sort, `sorted()` |
| O(n²) | quadratic | 100 | 10⁶ | 10¹² | comparing all pairs |
| O(2ⁿ) | exponential | 1,024 | ≈ 10³⁰¹ | hopeless | trying every subset |

## Counting rules

| Code shape | Cost |
|---|---|
| a fixed number of simple statements | O(1) |
| one loop over n items | O(n) |
| two loops one after the other | O(n) + O(n) = O(n) |
| a loop of n inside a loop of n | O(n) × O(n) = O(n²) |
| inner loop `for j in range(i)` | 0 + 1 + … + (n − 1) = n(n − 1)/2 = O(n²) |
| inner loop with a fixed bound (say 10) | 10n = O(n) |
| variable halves or doubles each step | O(log n) |
| loop of n around a halving loop | O(n log n) |

**Simplify:** drop constants (O(3n) = O(n)), keep the biggest term (O(n² + n) = O(n²)). The base of a logarithm does not matter: log₂ n and log₁₀ n differ only by a constant factor.

## Python built-ins

| Operation | Cost |
|---|---|
| `a[i]`, `a[i] = x`, `len(a)` | O(1) |
| `a.append(x)`, `a.pop()` | O(1) (append amortised) |
| `a.insert(0, x)`, `a.pop(0)` | O(n) |
| `x in a` for a list | O(n) |
| `x in s` for a set, `d[k]` for a dict | O(1) on average |
| slice `a[i:j]` | O(j − i) |
| `sorted(a)`, `a.sort()` | O(n log n) |

## Cases and space

| Term | Meaning | Linear search |
|---|---|---|
| best case | least work over all inputs of size n | O(1): target is first |
| worst case | most work over all inputs of size n (the usual guarantee) | O(n): target is missing |
| average case | expected work over typical inputs | O(n): about n/2 checks |
| extra space | memory created beyond the input | O(1) |

## Rough limits

- A few thousand items: O(n²) is usually fine.
- Hundreds of thousands or more: aim for O(n log n) or better.
- O(2ⁿ) is only practical for n up to about 25 to 30.
