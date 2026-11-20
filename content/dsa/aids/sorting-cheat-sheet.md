# Sorting cheat sheet

## The algorithms

| Algorithm | Best | Average | Worst | Extra space | Stable | In place | Idea |
|---|---|---|---|---|---|---|---|
| Bubble sort (early exit) | O(n) | O(n²) | O(n²) | O(1) | yes | yes | swap neighbours that are out of order |
| Selection sort | O(n²) | O(n²) | O(n²) | O(1) | no | yes | swap the smallest remaining item to the front |
| Insertion sort | O(n) | O(n²) | O(n²) | O(1) | yes | yes | shift each item left into the sorted part |
| Merge sort | O(n log n) | O(n log n) | O(n log n) | O(n) | yes | no | split, sort both halves, merge |
| Quicksort | O(n log n) | O(n log n) | O(n²) | O(log n) stack on average | no | yes | partition around a pivot, recurse on both sides |

Python's `sorted()` and `list.sort()` use **Timsort**: stable, O(n) best case on sorted data, O(n log n) worst case, up to O(n) extra memory. `sorted()` returns a new list; `list.sort()` changes the list and returns `None`.

## When to use what

| Situation | Choose | Why |
|---|---|---|
| Everyday Python code | `sorted()` or `list.sort()` | fast, stable and well tested |
| Small or nearly sorted data | insertion sort | close to O(n), very little overhead |
| Must guarantee O(n log n), or need stability | merge sort | it has no bad inputs |
| Large arrays, little spare memory | quicksort with a random pivot | fast in practice, works in place |
| Writing to memory is expensive | selection sort | at most n − 1 swaps |

## Key facts

- **Quicksort's worst case** comes from pivots that are always the smallest or largest item, such as the last element of a sorted array: about n levels of recursion and n²/2 comparisons.
- **Merge sort** does about log₂ n levels × O(n) merge work per level.
- **Selection sort** makes n(n − 1)/2 comparisons whatever the input.
- **Insertion sort** on sorted input makes n − 1 comparisons and no shifts.
- **Bubble sort** after pass k has the k largest items in their final places.
- No comparison-based sort can beat **O(n log n)** in the worst case.
- **Multi-key sorting trick:** sort by the secondary key first, then stable-sort by the primary key.
