# Arrays cheat sheet

## Operation costs (n = number of items)

| Operation | Python | Cost | Why |
|---|---|---|---|
| read / write by index | `a[i]`, `a[i] = x` | O(1) | address = start + i × slot size |
| length | `len(a)` | O(1) | stored with the list |
| append at the end | `a.append(x)` | O(1) amortised | occasional O(n) resize |
| remove from the end | `a.pop()` | O(1) | nothing to shift |
| insert at index i | `a.insert(i, x)` | O(n − i) | items from i onwards shift right |
| remove at index i | `a.pop(i)`, `del a[i]` | O(n − i) | items after i shift left |
| insert / remove at the front | `a.insert(0, x)`, `a.pop(0)` | O(n) | every item shifts |
| search by value | `x in a`, `a.index(x)` | O(n) | may check every item |
| remove by value | `a.remove(x)` | O(n) | search, then shift |
| slice | `a[i:j]` | O(j − i) | copies j − i items |
| sort | `a.sort()` | O(n log n) | |
| visit every cell of an R × C grid | nested loops | O(R × C) | |

## Static versus dynamic arrays

| | Static array | Dynamic array (Python `list`) |
|---|---|---|
| size | fixed when created | grows and shrinks |
| append when full | not possible (overflow) | allocate a bigger block and copy: O(n), but rarely |
| append cost | not available | O(1) amortised |
| unused memory | none | some spare capacity |

**Doubling from capacity 1:** capacities go 1, 2, 4, 8, 16, …; appending n items copies fewer than 2n items in total. Growing by +1 instead would copy 0 + 1 + … + (n − 1) = O(n²) items.

## 2D arrays

- `grid[r][c]` is row r, column c.
- Row-major flat index: `r * cols + c`.
- Build safely with `[[0] * cols for _ in range(rows)]`, never `[[0] * cols] * rows` (every row would be the same list).

## Two-pointer patterns

| Pattern | Pointers | Examples | Cost |
|---|---|---|---|
| opposite ends, moving inwards | `i = 0`, `j = n - 1` | reverse in place, pair sum in a sorted array, palindrome check | O(n) time, O(1) space |
| same direction, slow and fast | `write`, `read` | remove duplicates from a sorted array in place | O(n) time, O(1) space |

## When to use an array

- **Good fit:** access by position, adding and removing mostly at the end, lots of iteration (contiguous memory is cache-friendly).
- **Poor fit:** frequent inserts or deletes at the front or in the middle; consider a linked list or `collections.deque`.
