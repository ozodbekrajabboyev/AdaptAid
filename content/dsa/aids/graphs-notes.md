# Graphs, BFS and DFS

A **graph** is a set of **vertices** (nodes) joined by **edges**. It models connections: road maps, friendships, web links, course prerequisites. A tree is a special graph with no cycles; a general graph can have **cycles**, several separate pieces, and no root.

## Kinds of graph

- **Undirected**: an edge {u, v} works both ways (a two-way road, a friendship).
- **Directed**: an edge u → v is one-way (a link from one web page to another, "follows").
- **Weighted**: every edge carries a number such as a distance, time or cost.

## Representing a graph

For *V* vertices and *E* edges:

| | Adjacency matrix | Adjacency list |
|---|---|---|
| Idea | V × V table, `m[u][v] = 1` if there is an edge | each vertex keeps a list of its neighbours |
| Space | O(V²) | O(V + E) |
| Is there an edge u–v? | O(1) | O(deg(u)) |
| Visit all neighbours of u | O(V) | O(deg(u)) |

Most real graphs are **sparse** (E is far below V²), so the adjacency list is the usual choice. In Python, a dict of lists works well:

```python
graph = {"A": ["B", "C"], "B": ["A", "D"], "C": ["A", "D"], "D": ["B", "C"]}
```

## Breadth-first search (BFS)

BFS explores in **rings**: first the start, then all vertices one edge away, then two edges away, and so on. It uses a **queue**. Because vertices come out in order of distance, BFS finds **shortest paths by number of edges** in an unweighted graph.

```python
from collections import deque

def bfs(graph, start):
    dist = {start: 0}             # also serves as the visited set
    queue = deque([start])
    while queue:
        v = queue.popleft()
        for w in graph[v]:
            if w not in dist:     # mark when enqueued, not when dequeued
                dist[w] = dist[v] + 1
                queue.append(w)
    return dist
```

## Depth-first search (DFS)

DFS follows one path as far as it can, then **backtracks** to the most recent vertex with an unexplored neighbour. It uses a **stack**, usually the call stack through recursion. DFS is used to detect cycles, find connected components and solve mazes, but it does **not** find shortest paths.

```python
def dfs(graph, v, visited):
    visited.add(v)
    for w in graph[v]:
        if w not in visited:
            dfs(graph, w, visited)
```

## Cost

With adjacency lists, each vertex is visited once and each list is scanned once, so both BFS and DFS run in **O(V + E)** time and use O(V) extra space. With a matrix, scanning a row costs O(V), so they take O(V²).

## Common mistakes

- **No visited set.** Cycles (and every undirected edge, which leads straight back) make the search loop forever.
- **Using BFS on a weighted graph** and expecting the cheapest route: BFS minimises the number of edges, not their total weight. Use Dijkstra's algorithm there.
