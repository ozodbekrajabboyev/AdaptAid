# Graphs cheat sheet

## Vocabulary

| Term | Meaning |
|---|---|
| Vertex, edge | a node, and a connection between two nodes |
| Undirected / directed | edges work both ways / edges u → v are one-way |
| Weighted | each edge has a number (distance, time, cost) |
| Degree of v | number of edges at v (in a directed graph: in-degree and out-degree) |
| Path, cycle | a sequence of edges; a path that returns to its start |
| Connected component | a maximal group of vertices that can all reach each other |
| Sparse / dense | E much smaller than V² / E close to V² |

## Representations (V vertices, E edges)

| Operation | Adjacency matrix | Adjacency list |
|---|---|---|
| Space | O(V²) | O(V + E) |
| Edge u–v exists? | O(1) | O(deg(u)) |
| All neighbours of u | O(V) | O(deg(u)) |
| Add an edge | O(1) | O(1) |
| Best for | dense graphs, frequent edge checks | sparse graphs, traversals (most real graphs) |

In an undirected graph each edge appears in **two** lists, so the lists hold 2E entries in total.

## BFS vs DFS

| | BFS | DFS |
|---|---|---|
| Frontier | queue (`collections.deque`, `popleft`) | stack (`list.pop`) or recursion |
| Order | ring by ring, nearest first | deep along one path, then backtrack |
| Shortest path (fewest edges, unweighted) | yes | no |
| Typical uses | fewest hops, levels, nearest target | cycles, components, topological sort, mazes |
| Time (adjacency list) | O(V + E) | O(V + E) |
| Time (adjacency matrix) | O(V²) | O(V²) |
| Extra space | O(V) | O(V) (recursion depth can reach V) |

**Weighted shortest paths** need Dijkstra's algorithm (non-negative weights), not BFS.

## Templates

```python
from collections import deque

def bfs(graph, s):
    dist, queue = {s: 0}, deque([s])
    while queue:
        v = queue.popleft()
        for w in graph[v]:
            if w not in dist:
                dist[w] = dist[v] + 1
                queue.append(w)
    return dist

def dfs(graph, v, seen):
    seen.add(v)
    for w in graph[v]:
        if w not in seen:
            dfs(graph, w, seen)
```

**Always keep a visited set** (`dist` or `seen` above); without it, any cycle makes the search run forever.
