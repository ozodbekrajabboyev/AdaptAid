# Arrays

An **array** stores items in one contiguous block of memory: equal-sized slots, one after another, numbered from 0. An array of length *n* has indices 0 to n − 1.

## Why indexing is O(1)

Because the slots are the same size and sit side by side, the computer *calculates* where item *i* lives instead of searching for it:

address of `a[i]` = start address + i × slot size

That is one multiplication and one addition whatever the length, so reading or writing `a[i]` is **O(1)**. A Python `list` stores references in its slots, so the same formula applies.

## Inserting and deleting means shifting

An array has no gaps. To insert at index *i*, every item from *i* to the end moves one slot right; deleting at *i* moves them one slot left.

```python
a = [10, 20, 30, 40]
a.insert(1, 15)   # 20, 30, 40 shift right -> [10, 15, 20, 30, 40]
a.pop(0)          # every remaining item shifts left -> [15, 20, 30, 40]
```

The cost is O(n − i): O(1) at the end, O(n) at the front. Searching an unsorted array for a value is O(n), because it may have to check every slot.

## Dynamic arrays and amortised append

A plain array has a fixed **capacity**. A **dynamic array** (Python's `list`, Java's `ArrayList`) keeps spare slots. When an append finds it full, it allocates a bigger block, typically twice the size, copies every item across, then appends.

That copy costs O(n), but it is rare. With doubling, appending n items copies fewer than 2n items in total, so append is **O(1) amortised**: cheap on average over the whole sequence, even though an occasional single append is O(n). (CPython grows lists by about 12% rather than doubling; growing by any constant factor gives the same result.)

## 2D arrays

A grid is an array of rows: `grid[r][c]` is row *r*, column *c*. Stored row by row in one block (**row-major** order), cell (r, c) of a grid with C columns is at flat index r × C + c. Visiting every cell of an R × C grid costs O(R × C).

## Two pointers

Many array problems need only one pass with two indices. To reverse in place, swap `a[i]` and `a[j]`, move *i* right and *j* left, and stop when they meet: O(n) time and O(1) extra space.

## Common mistake

`grid = [[0] * 3] * 3` does **not** build three rows. It builds one row and three references to it, so `grid[0][0] = 1` changes every row. Build each row separately: `[[0] * 3 for _ in range(3)]`.
