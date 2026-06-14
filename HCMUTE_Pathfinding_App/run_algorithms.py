import sys
import os
import time

# Add current directory to path so we can import core
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.graph import Graph
from core.algorithms import ALGORITHM_MAP

def run():
    graph = Graph()
    graph.load_from_json("data/hcmute_graph_nodes_edges.json")
    
    start_node = "N91"
    goal_node = "N04"
    
    print(f"Running algorithms from {start_node} to {goal_node}\n")
    
    results = []
    
    for name, func in ALGORITHM_MAP.items():
        print(f"--- Running {name} ---")
        
        # We need to measure how long it takes to process all steps
        # Using time.perf_counter for higher precision
        start_time = time.perf_counter()
        
        generator = func(graph, start_node, goal_node)
        steps = list(generator)
        
        end_time = time.perf_counter()
        
        duration_ms = (end_time - start_time) * 1000
        
        # The last step has the final result
        last_step = steps[-1]
        
        if "✅" in last_step["log"]:
            path = last_step["path"]
            cost = last_step["cost"]
            visited_count = len(last_step["visited"])
            print(f"Found path: {' -> '.join(path)}")
            print(f"Cost: {cost:.2f}")
            print(f"Visited nodes: {visited_count}")
        else:
            path = []
            cost = 0
            visited_count = len(last_step.get("visited", []))
            print("Path not found!")
            
        print(f"Time taken: {duration_ms:.4f} ms\n")
        
        results.append({
            "name": name,
            "duration_ms": duration_ms,
            "cost": cost,
            "visited": visited_count,
            "path_length": len(path)
        })

if __name__ == "__main__":
    run()
