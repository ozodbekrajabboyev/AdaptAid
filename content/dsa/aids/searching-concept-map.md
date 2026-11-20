# Searching at a glance

```mermaid
flowchart TD
    Q["Find x in a collection"] --> S{"Sorted array with index access?"}
    S -- no --> M{"How many searches?"}
    M -- one --> L["Linear search: check items in order, O(n)"]
    M -- many --> SO["Sort once: O(n log n)"]
    M -- many --> HS["Or build a hash set: O(1) average per lookup"]
    SO --> B
    S -- yes --> B["Binary search: compare x with the middle item"]
    B --> H["Discard half the range each step: O(log n)"]
    B --> E["Exact match: lo ≤ hi, then lo = mid + 1 or hi = mid - 1"]
    B --> LB["Lower bound: first index with a[i] ≥ x"]
    LB --> U["First occurrence, insert position, counting"]
    E -.-> BUG["Off-by-one bugs: lo < hi skips a candidate, lo = mid loops forever"]
```

**Takeaways**

- **Linear search** works on anything and costs O(n); it is the right choice for a single search in unsorted data.
- **Binary search** needs two things: **sorted** data and **O(1) access to any index**. Without both it is either wrong or no faster.
- Halving gives **O(log n)**: doubling the input adds only one more comparison.
- Most binary search bugs are **boundary bugs**. Fix what `lo` and `hi` mean, then make the loop condition and the updates match.
- The **lower bound** (`bisect_left`) turns binary search into a tool for first occurrences, insertion points and "how many are smaller than x?" questions.
