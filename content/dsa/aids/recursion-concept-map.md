# Recursion at a glance

```mermaid
flowchart TD
    P["Problem of size n"] --> B{"Small enough to answer directly?"}
    B -- yes --> BC["Base case: return the answer"]
    B -- no --> R["Recursive case: make a smaller problem"]
    R --> C["Call the same function on it"]
    C --> S["Call stack grows: one frame per call"]
    S --> P
    BC --> U["Stack unwinds: each frame combines its result"]
    U --> A["Final answer"]
    R -.-> M{"Same subproblem solved twice?"}
    M -- yes --> MEMO["Memoize: store results, O(2^n) becomes O(n)"]
    M -- no --> OK["Time = number of calls x work per call"]
```

**Takeaways**

- Every recursive function needs a **base case** and a **recursive case that moves toward it**.
- The **call stack** holds one frame per active call, so depth costs memory: O(depth) space.
- **Calls go down, answers come back up**: the combine step runs while the stack unwinds.
- **Overlapping subproblems** (naive Fibonacci) make recursion exponential; **memoization** fixes that.
- Anything recursive can be written with a loop and an explicit stack. Prefer the loop when inputs can be very deep.
