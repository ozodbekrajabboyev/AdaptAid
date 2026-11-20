# Sorting

Sorting puts items in order, smallest to largest or by some key. Sorted data is easy to search with binary search, to deduplicate and to merge, so sorting is one of the most common steps in real programs.

## Three simple O(n²) sorts

- **Bubble sort**: sweep left to right, swapping neighbours that are out of order; after pass k the k largest items are in place. With an early exit when a pass makes no swaps, sorted input takes one pass: O(n).
- **Selection sort**: find the smallest remaining item and swap it to the front of the unsorted part. It always makes about n²/2 comparisons, even on sorted input, but at most n − 1 swaps.
- **Insertion sort**: take the next item and shift it left into place within the sorted part, like sorting playing cards in your hand. On sorted or nearly sorted input it is close to O(n).

## Two O(n log n) sorts: divide and conquer

- **Merge sort**: split the array in half, sort each half recursively, then **merge** the two sorted halves in O(n). There are about log₂ n levels of splitting, each with O(n) merge work, so it is **O(n log n) for every input**. The merge writes into a temporary array: **O(n) extra space**.
- **Quicksort**: pick a **pivot**, **partition** the array so smaller items go left and larger ones go right, then sort each side recursively. Pivots that split evenly give **O(n log n) on average**. Pivots that split off one item at a time give the **O(n²) worst case**, for example always taking the last item of an already sorted array. It partitions within the array, using only the recursion stack (O(log n) on average).

## Two properties

- **Stable**: items with equal keys keep their original relative order, which matters when you sort records by one field after another. Bubble, insertion and merge sort are stable; selection sort and the usual quicksort are not.
- **In place**: only O(1) extra memory besides the input (quicksort is usually counted as in place despite its stack). Bubble, selection and insertion sort are in place; standard merge sort is not.

## In Python

`sorted(items)` returns a new sorted list and `items.sort()` sorts the list itself. Both use Timsort, a merge/insertion sort hybrid: stable, O(n log n) in the worst case and O(n) on already sorted data.

## Common mistake

Assuming quicksort is always O(n log n). With a fixed first or last element as the pivot, already sorted input is its worst case. Real implementations choose a random or median-of-three pivot to make that very unlikely.
