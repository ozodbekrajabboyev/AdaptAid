# Binary search trees at a glance

```mermaid
flowchart TD
    P["BST property: left subtree smaller, right subtree larger, at every node"] --> IN["Inorder traversal gives the keys in sorted order"]
    P --> OPS["Each operation follows one path from the root"]
    OPS --> S["Search: go left or right until found or None"]
    OPS --> I["Insert: search, then attach a new leaf where it fell off"]
    OPS --> D{"Delete: how many children?"}
    D -- "0" --> D0["Remove the leaf"]
    D -- "1" --> D1["Replace the node by its child"]
    D -- "2" --> D2["Copy in the inorder successor, then delete the successor"]
    OPS --> H["Cost O(h), h = height"]
    H --> BAL["Balanced: h about log2 n, so O(log n)"]
    H --> DEG["Degenerate chain from sorted inserts: h = n - 1, so O(n)"]
    DEG --> FIX["AVL and red-black trees rotate to stay balanced: O(log n) worst case"]
```

**Takeaways**

- The BST property holds for **whole subtrees**, not just a node and its two children.
- **Search, insert and delete** all walk a single root-to-leaf path, so they cost **O(h)**.
- **Height decides everything**: about log₂ n when balanced, n − 1 when keys arrive in sorted order.
- Deleting a node with **two children** borrows its **inorder successor**, the leftmost node of its right subtree.
- **Inorder traversal** of a BST is sorted, which is also a quick way to check that a tree really is a BST.
