# Stacks at a glance

```mermaid
flowchart TD
    S["Stack: last in, first out"] --> OPS["push, pop, peek, is_empty: all O(1)"]
    OPS --> ERR["pop or peek on an empty stack: underflow"]
    S --> IMP{"How is it stored?"}
    IMP --> ARR["Python list: top is the end, append and pop()"]
    IMP --> LL["Linked list: top is the head"]
    ARR -.-> AMO["append is O(1) amortised; using the front would be O(n)"]
    LL -.-> MEM["never resizes; one extra reference per item"]
    S --> APP["Applications: the most recent item matters first"]
    APP --> BR["Balanced brackets"]
    APP --> UN["Undo and redo"]
    APP --> CS["Call stack: one frame per active function call"]
    APP --> PF["Evaluating postfix expressions"]
    APP --> RV["Reversing a sequence"]
    CS --> REC["Recursion builds on this"]
```

**Takeaways**

- A stack only gives access to its **top**: push, pop and peek are all **O(1)**.
- **LIFO** means items come out in the reverse of the order they went in.
- Use the **end** of a Python list, or the **head** of a linked list, as the top; the other end costs O(n).
- Reach for a stack whenever the **most recent unfinished thing** must be handled first: matching brackets, undo, function calls.
- Always check for an **empty** stack before popping or peeking.
