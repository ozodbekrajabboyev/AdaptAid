# Hashing

A **hash table** stores keys (or key-value pairs) so that inserting, finding and deleting a key take **O(1) time on average**, however many keys it holds. Python's `dict` and `set` are hash tables.

## How it works

1. A **hash function** turns the key into an integer. It must be deterministic (the same key always gives the same hash) and should spread different keys evenly.
2. The table reduces that integer to an index into an array of `m` **buckets** (slots), for example `index = hash(key) % m`.
3. The key is stored at that index. A lookup hashes the key again and goes straight to that bucket instead of scanning the table.

## Collisions

There are far more possible keys than buckets, so two different keys will sometimes get the same index: a **collision**. Two standard fixes:

- **Separate chaining**: each bucket holds a small list, and colliding keys share it. A lookup scans only that one list.
- **Open addressing with linear probing**: every key lives in the array itself. If slot `i` is taken, try `i + 1`, `i + 2`, ... (wrapping with `% m`) until a free slot appears. A search follows the same path and stops at an empty slot. Deleting therefore needs a "deleted" marker (a tombstone), or later searches would stop too early.

## Load factor and resizing

The **load factor** is α = n / m, the number of keys per bucket. As α grows, chains and probe runs get longer. So tables **resize** when α passes a threshold (0.75 is common with chaining; Python's dict grows at about 2/3): allocate about twice as many buckets and **re-insert every key**, because each index depends on `m`. One resize costs O(n), but doubling makes resizes rare, so insertion stays **O(1) amortised**.

## Costs

| Operation | Average | Worst |
|---|---|---|
| insert, search, delete | O(1) | O(n) |

The worst case comes when many keys land in one place, for example with a poor hash function, so a lookup scans them all.

## In Python

```python
ages = {"ana": 21, "ben": 19}    # dict: key -> value
ages["cy"] = 22                  # insert: O(1) on average
"ben" in ages                    # True: O(1) on average
seen = {3, 1, 4}                 # set: keys only
```

Keys must be **hashable**: immutable values such as numbers, strings and tuples. A list cannot be a key (`TypeError: unhashable type: 'list'`), because changing it would change its hash.

## Common mistake

Treating hash tables as O(1) in every case, or as ordered. They give fast lookups **by key** only; a dict remembers insertion order, not sorted order.
