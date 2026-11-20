# Trees at a glance

```mermaid
flowchart TD
    T["Tree: nodes joined by edges, one root, no cycles"] --> V["Vocabulary"]
    V --> V1["Root, parent, child, leaf"]
    V --> V2["Depth: edges down from the root"]
    V --> V3["Height: edges up from the deepest leaf"]
    T --> BT["Binary tree: at most a left and a right child"]
    BT --> TR{"Visit every node once: O(n)"}
    TR --> DFS["Depth-first: recursion, which uses the call stack"]
    TR --> BFS["Breadth-first: a queue"]
    DFS --> PRE["Preorder: node, left, right"]
    DFS --> IN["Inorder: left, node, right"]
    DFS --> POST["Postorder: left, right, node"]
    BFS --> LVL["Level-order: one level at a time"]
    BT --> REC["Recursive pattern: None is the base case, combine left and right answers"]
    REC --> SZ["size = 1 + size(L) + size(R)"]
    REC --> HT["height = 1 + max(height(L), height(R))"]
    POST -.-> SZ
```

**Takeaways**

- A tree is a **hierarchy**: one root, every other node has exactly one parent, and there are no cycles.
- **Depth** is measured from the root down; **height** from the deepest leaf up. With edge counting, a single node has height 0 and an empty tree height -1.
- The three **depth-first** orders differ only in *when* the node is visited relative to its two subtrees.
- **Level-order** swaps recursion for a **queue**, which processes nodes in order of depth.
- Almost every tree function is recursive: handle `None`, solve both subtrees, combine. That costs **O(n)** time and **O(h)** stack space.
