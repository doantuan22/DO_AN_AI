import sys
sys.path.insert(0, '.')
from core.graph import Graph
from core.algorithms import bfs, dfs, ucs, greedy_search, astar
from core.heuristic import euclidean_distance

g = Graph()
g.load_from_json('data/hcmute_graph_nodes_edges.json')

for name, func in [("BFS", bfs), ("DFS", dfs), ("UCS", ucs)]:
    steps = list(func(g, 'N91', 'N04'))
    cost = steps[-1]["cost"]
    print(f"{name} OK: {len(steps)} steps, cost={cost:.1f}")

for name, func in [("Greedy", greedy_search), ("A*", astar)]:
    steps = list(func(g, 'N91', 'N04', euclidean_distance))
    cost = steps[-1]["cost"]
    print(f"{name} OK: {len(steps)} steps, cost={cost:.1f}")

print("All algorithms pass!")
