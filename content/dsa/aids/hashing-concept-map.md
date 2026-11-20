# Hashing at a glance

```mermaid
flowchart TD
    K["Key, such as 'ana' or 42"] --> HF["Hash function: same key, same hash"]
    HF --> IDX["Index = hash % m"]
    IDX --> B["Bucket in an array of m buckets"]
    B --> C{"Another key already there?"}
    C -- no --> O1["Store or find it directly: O(1)"]
    C -- yes --> COL["Collision"]
    COL --> CH["Separate chaining: a list per bucket"]
    COL --> OA["Open addressing: probe i + 1, i + 2, ..."]
    CH --> LF["Load factor α = n / m"]
    OA --> LF
    LF --> RS{"α above the threshold?"}
    RS -- yes --> RH["Resize about 2x and rehash every key: O(n) but rare, so O(1) amortised"]
    RS -- no --> AVG["Average O(1); worst O(n) when keys pile up"]
    O1 --> PY["Python dict and set: keys must be hashable"]
```

**Takeaways**

- A hash table is an **array plus a hash function**: the function turns a key into an index, so a lookup jumps straight to one bucket.
- **Collisions are normal**, not errors. Chaining keeps colliding keys in a list; open addressing moves them to another free slot and needs tombstones for deletion.
- The **load factor** n / m controls speed. Keep it low by **resizing and rehashing** every key, since each index depends on m.
- **O(1) is an average**, resting on a hash function that spreads keys out. If all keys collide, every operation degrades to **O(n)**.
- Python's `dict` and `set` are hash tables; their keys must be **immutable** (hashable), and they are not kept in sorted order.
