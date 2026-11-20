# Worked example: a hash table with linear probing

**Problem.** A small library system stores book IDs in a table of 7 slots, using the hash function `h(k) = k % 7` and linear probing. Insert the IDs 10, 22, 31, 4 and 15, then look up 15 (present) and 17 (missing).

## Step 1: compute each home slot

| Key | Working | Home slot |
|---|---|---|
| 10 | 10 = 1 × 7 + **3** | 3 |
| 22 | 22 = 3 × 7 + **1** | 1 |
| 31 | 31 = 4 × 7 + **3** | 3 |
| 4 | 4 = 0 × 7 + **4** | 4 |
| 15 | 15 = 2 × 7 + **1** | 1 |

Collisions are coming: 10 and 31 share home slot 3, and 22 and 15 share home slot 1.

## Step 2: the code

```python
def insert(table, key):
    m = len(table)
    i = key % m                      # home slot
    while table[i] is not None:      # occupied: try the next slot
        i = (i + 1) % m              # wrap around at the end
    table[i] = key

def search(table, key):
    m = len(table)
    i = key % m
    while table[i] is not None:      # an empty slot ends the search
        if table[i] == key:
            return i
        i = (i + 1) % m
    return -1                        # reached an empty slot: not present
```

Both functions assume the table always has at least one empty slot, which resizing guarantees.

## Step 3: trace the inserts

`_` marks an empty slot; the table is shown as slots 0 to 6.

| Insert | Home | Slots tried | Placed at | Table after |
|---|---|---|---|---|
| 10 | 3 | 3 | 3 | `[_, _, _, 10, _, _, _]` |
| 22 | 1 | 1 | 1 | `[_, 22, _, 10, _, _, _]` |
| 31 | 3 | 3 (taken), 4 | 4 | `[_, 22, _, 10, 31, _, _]` |
| 4 | 4 | 4 (taken), 5 | 5 | `[_, 22, _, 10, 31, 4, _]` |
| 15 | 1 | 1 (taken), 2 | 2 | `[_, 22, 15, 10, 31, 4, _]` |

Look at key 4: no other key has its hash, yet it was pushed out of its home slot by 31, which had itself been displaced. Occupied slots join into runs (**clusters**), and every key that lands in a cluster makes it longer. This **primary clustering** is the main weakness of linear probing.

## Step 4: trace the searches

- **Search 15:** 15 % 7 = 1. Slot 1 holds 22, so move on; slot 2 holds 15. Found after **2 probes**.
- **Search 17:** 17 % 7 = 3. Slot 3 holds 10, slot 4 holds 31, slot 5 holds 4, and slot 6 is empty. Stop: 17 is **not present**, after **4 probes**. The search could not stop at slot 3, because 17 might have been pushed along the cluster exactly as 31 was.

## Step 5: compare with separate chaining

With chaining, the same keys would sit in short lists:

| Bucket | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|---|
| Keys | | 22, 15 | | 10, 31 | 4 | | |

Searching for 17 would scan only bucket 3: 2 comparisons. Key 4 stays in its own bucket, because chains never spill into neighbouring buckets.

## Step 6: load factor and cost

The table now holds 5 keys in 7 slots: α = 5 / 7 ≈ 0.71. An open-addressing table would typically resize around this point (Python's dict grows when it is about 2/3 full): allocate roughly twice as many slots and re-insert all five keys with `k % m` for the new `m`, since every home slot changes.

- With a good hash function and a low load factor, each operation probes only a few slots on average: **O(1)**.
- In the worst case, all keys sit in one cluster and a search walks the whole of it: **O(n)**.

**Try it yourself:** insert 24 into the final table. 24 % 7 = 3, and slots 3, 4 and 5 are taken, so it lands in slot 6.
