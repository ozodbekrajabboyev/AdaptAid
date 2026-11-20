# Linked lists at a glance

```mermaid
flowchart TD
    N["Node: value + next reference"] --> SL["Singly linked list: head -> ... -> None"]
    SL --> T["Traversal: follow next from the head"]
    T --> AK["Access k-th item or search: O(n)"]
    T --> REV["Reverse in place with prev, cur, nxt: O(n) time, O(1) space"]
    SL --> HD["Insert or delete at the head: O(1)"]
    SL --> AF["Insert after a node you hold: O(1)"]
    SL --> TL["Delete the tail: O(n), needs the previous node"]
    SL --> DL["Doubly linked list: adds a prev reference"]
    DL --> DD["Delete a node you hold: O(1)"]
    DL --> BW["Walk backwards"]
    DL --> MEM["Cost: one more reference per node"]
    HD --> USE["Used to build stacks and queues"]
    SL -.->|compare| AR["Array: O(1) indexing, O(n) insert at the front"]
```

**Takeaways**

- A linked list trades **O(1) indexing** for **O(1) insertion and deletion** wherever you already hold a reference.
- Every operation is a matter of **re-pointing references**; do it in an order that never loses the rest of the list.
- **Singly linked** lists are cheap at the head; **doubly linked** lists can also remove any node they hold in O(1) and walk backwards.
- Finding a position is the expensive part: walking there costs O(n) even if the change itself is O(1).
- Always test the **empty list**, the **head** and the **tail** as separate cases.
