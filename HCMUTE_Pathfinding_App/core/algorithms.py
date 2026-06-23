# Cài đặt 5 thuật toán tìm kiếm: BFS, DFS, UCS, Greedy, A*
# Mỗi thuật toán là generator yield từng bước để mô phỏng trực quan.
# Mỗi bước yield dict chứa: current, visited, frontier, path, cost, log.

import heapq
import time
from collections import deque
from typing import List, Dict, Tuple, Optional, Generator, Callable, Any

from core.graph import Graph
from core.heuristic import euclidean_distance, manhattan_distance


# Tạo dict mô tả một bước của thuật toán
def _make_step(current: str, visited: list, frontier: list,
               path: list, cost: float, log: str) -> dict:
    return {
        "current": current,
        "visited": list(visited),
        "frontier": list(frontier),
        "path": list(path),
        "cost": cost,
        "log": log,
    }


def _reconstruct_path(parent: Dict[str, str], start: str, goal: str) -> List[str]:
    path = []
    current = goal
    while current is not None:
        path.append(current)
        if current == start:
            break
        current = parent.get(current)
    return path[::-1]




def bfs(graph: Graph, start: str, goal: str) -> Generator:
    if not graph.node_exists(start) or not graph.node_exists(goal):
        yield _make_step(start, [], [], [], 0, "❌ Node không tồn tại trong đồ thị!")
        return
    
    if start == goal:
        yield _make_step(start, [start], [], [start], 0,
                        f"✅ Điểm bắt đầu trùng điểm đích: {graph.get_node_name(start)}")
        return
    
    # Hàng đợi FIFO: node_id
    queue = deque()
    queue.append(start)
    visited = set()
    visited.add(start)
    visited_order = [start]
    parent: Dict[str, str] = {start: None}
    
    yield _make_step(start, visited_order, [start], [], 0,
                    f"🔵 BFS: Khởi tạo - Thêm {graph.get_node_name(start)} vào queue")
    
    while queue:
        current = queue.popleft()
        
        frontier_nodes = list(queue)
        
        yield _make_step(current, visited_order, frontier_nodes, [], 0,
                        f"🔍 Đang xét: {graph.get_node_name(current)}")
        
        if current == goal:
            path = _reconstruct_path(parent, start, goal)
            cost = graph.calculate_path_cost(path)
            route = " → ".join(graph.get_node_name(n) for n in path)
            yield _make_step(current, visited_order, [], path, cost,
                            f"✅ Tìm thấy đường đi!\n   Lộ trình: {route}\n   Tổng: {cost:.1f} m")
            return
        
        # Mở rộng các node kề chưa visited
        for neighbor, weight in graph.get_neighbors(current):
            if neighbor not in visited and neighbor not in queue:
                visited.add(neighbor)
                visited_order.append(neighbor)
                parent[neighbor] = current
                queue.append(neighbor)
                
                yield _make_step(current, visited_order,
                               list(queue),
                               [], 0,
                               f"   ➕ Thêm {graph.get_node_name(neighbor)} vào queue")
    
    yield _make_step("", visited_order, [], [], 0,
                    f"❌ Không tìm thấy đường đi từ {graph.get_node_name(start)} "
                    f"đến {graph.get_node_name(goal)}")




def dfs(graph: Graph, start: str, goal: str) -> Generator:
    if not graph.node_exists(start) or not graph.node_exists(goal):
        yield _make_step(start, [], [], [], 0, "❌ Node không tồn tại trong đồ thị!")
        return
    
    if start == goal:
        yield _make_step(start, [start], [], [start], 0,
                        f"✅ Điểm bắt đầu trùng điểm đích: {graph.get_node_name(start)}")
        return
    
    # Ngăn xếp: node_id
    stack = [start]
    visited = set()
    discovered = {start}
    visited_order: list[str] = []
    parent: Dict[str, str] = {start: None}
    
    yield _make_step(start, visited_order, [start], [], 0,
                    f"🟣 DFS: Khởi tạo - Thêm {graph.get_node_name(start)} vào stack")
    
    while stack:
        current = stack.pop()
        
        if current in visited:
            continue
        
        visited.add(current)
        visited_order.append(current)
        
        frontier_nodes = [n for n in stack if n not in visited]
        
        yield _make_step(current, visited_order, frontier_nodes, [], 0,
                        f"🔍 Đang xét: {graph.get_node_name(current)}")
        
        if current == goal:
            path = _reconstruct_path(parent, start, goal)
            cost = graph.calculate_path_cost(path)
            route = " → ".join(graph.get_node_name(n) for n in path)
            yield _make_step(current, visited_order, [], path, cost,
                            f"✅ Tìm thấy đường đi!\n   Lộ trình: {route}\n   Tổng: {cost:.1f} m")
            return
        
        # Đảo thứ tự để duyệt node đầu tiên trước khi pop
        neighbors = graph.get_neighbors(current)
        for neighbor, weight in reversed(neighbors):
            if neighbor not in visited and neighbor not in discovered:
                discovered.add(neighbor)
                parent[neighbor] = current
                stack.append(neighbor)
                
                yield _make_step(current, visited_order,
                               [n for n in stack if n not in visited],
                               [], 0,
                               f"   ➕ Thêm {graph.get_node_name(neighbor)} vào stack")
    
    yield _make_step("", visited_order, [], [], 0,
                    f"❌ Không tìm thấy đường đi từ {graph.get_node_name(start)} "
                    f"đến {graph.get_node_name(goal)}")




def ucs(graph: Graph, start: str, goal: str) -> Generator:
    if not graph.node_exists(start) or not graph.node_exists(goal):
        yield _make_step(start, [], [], [], 0, "❌ Node không tồn tại trong đồ thị!")
        return
    
    if start == goal:
        yield _make_step(start, [start], [], [start], 0,
                        f"✅ Điểm bắt đầu trùng điểm đích: {graph.get_node_name(start)}")
        return
    
    # Priority queue: cost, counter, node_id
    # counter phá vỡ tie-breaking khi cost bằng nhau
    counter = 0
    pq: list[tuple[float, int, str]] = [(0.0, counter, start)]
    best_g: Dict[str, float] = {start: 0.0}
    visited = set()
    visited_order: list[str] = []
    parent: Dict[str, str] = {start: None}
    
    yield _make_step(start, visited_order, [start], [], 0,
                    f"🟠 UCS: Khởi tạo - g({graph.get_node_name(start)}) = 0")
    
    while pq:
        cost, _, current = heapq.heappop(pq)
        
        if current in visited or cost > best_g.get(current, float("inf")):
            continue
        
        visited.add(current)
        visited_order.append(current)
        
        frontier_nodes = [item[2] for item in pq if item[2] not in visited]
        
        yield _make_step(current, visited_order, frontier_nodes, [], cost,
                        f"🔍 Đang xét: {graph.get_node_name(current)} | g(n) = {cost:.1f}")
        
        if current == goal:
            path = _reconstruct_path(parent, start, goal)
            route = " → ".join(graph.get_node_name(n) for n in path)
            yield _make_step(current, visited_order, [], path, cost,
                            f"✅ Tìm thấy đường đi tối ưu!\n   Lộ trình: {route}\n   "
                            f"Tổng chi phí: {cost:.1f} m")
            return
        
        for neighbor, weight in graph.get_neighbors(current):
            new_cost = cost + weight
            if neighbor not in visited and new_cost < best_g.get(neighbor, float("inf")):
                best_g[neighbor] = new_cost
                parent[neighbor] = current
                counter += 1
                heapq.heappush(pq, (new_cost, counter, neighbor))
                
                yield _make_step(current, visited_order,
                               [item[2] for item in pq if item[2] not in visited],
                               [], cost,
                               f"   ➕ {graph.get_node_name(neighbor)}: "
                               f"g(n) = {cost:.1f} + {weight:.1f} = {new_cost:.1f}")
    
    yield _make_step("", visited_order, [], [], 0,
                    f"❌ Không tìm thấy đường đi từ {graph.get_node_name(start)} "
                    f"đến {graph.get_node_name(goal)}")




def greedy_search(graph: Graph, start: str, goal: str,
                  heuristic_func: Optional[Callable[..., Any]] = None) -> Generator:
    if heuristic_func is None:
        heuristic_func = euclidean_distance
    
    if not graph.node_exists(start) or not graph.node_exists(goal):
        yield _make_step(start, [], [], [], 0, "❌ Node không tồn tại trong đồ thị!")
        return
    
    if start == goal:
        yield _make_step(start, [start], [], [start], 0,
                        f"✅ Điểm bắt đầu trùng điểm đích: {graph.get_node_name(start)}")
        return
    
    goal_pos = graph.get_node_position(goal)
    
    # Priority queue: (h(n), counter, node_id, g_cost)
    counter = 0
    start_pos = graph.get_node_position(start)
    h_start = heuristic_func(start_pos, goal_pos)
    pq: list[tuple[float, int, str, float]] = [(h_start, counter, start, 0.0)]
    visited = set()
    visited_order: list[str] = []
    parent: Dict[str, str] = {start: None}
    
    yield _make_step(start, visited_order, [start], [], 0,
                    f"🟢 Greedy: Khởi tạo - h({graph.get_node_name(start)}) = {h_start:.1f}")
    
    while pq:
        h_val, _, current, g_cost = heapq.heappop(pq)
        
        if current in visited:
            continue
        
        visited.add(current)
        visited_order.append(current)
        
        frontier_nodes = [item[2] for item in pq if item[2] not in visited]
        
        yield _make_step(current, visited_order, frontier_nodes, [], g_cost,
                        f"🔍 Đang xét: {graph.get_node_name(current)} | h(n) = {h_val:.1f}")
        
        if current == goal:
            path = _reconstruct_path(parent, start, goal)
            total_cost = graph.calculate_path_cost(path)
            route = " → ".join(graph.get_node_name(n) for n in path)
            yield _make_step(current, visited_order, [], path, total_cost,
                            f"✅ Tìm thấy đường đi!\n   Lộ trình: {route}\n   "
                            f"Tổng: {total_cost:.1f} m")
            return
        
        for neighbor, weight in graph.get_neighbors(current):
            if neighbor not in visited and neighbor not in parent:
                parent[neighbor] = current
                n_pos = graph.get_node_position(neighbor)
                h_n = heuristic_func(n_pos, goal_pos)
                counter += 1
                new_g = g_cost + weight
                heapq.heappush(pq, (h_n, counter, neighbor, new_g))
                
                yield _make_step(current, visited_order,
                               [item[2] for item in pq if item[2] not in visited],
                               [], g_cost,
                               f"   ➕ {graph.get_node_name(neighbor)}: h(n) = {h_n:.1f}")
    
    yield _make_step("", visited_order, [], [], 0,
                    f"❌ Không tìm thấy đường đi từ {graph.get_node_name(start)} "
                    f"đến {graph.get_node_name(goal)}")




def astar(graph: Graph, start: str, goal: str,
          heuristic_func: Optional[Callable[..., Any]] = None) -> Generator:
    if heuristic_func is None:
        heuristic_func = euclidean_distance
    
    if not graph.node_exists(start) or not graph.node_exists(goal):
        yield _make_step(start, [], [], [], 0, "❌ Node không tồn tại trong đồ thị!")
        return
    
    if start == goal:
        yield _make_step(start, [start], [], [start], 0,
                        f"✅ Điểm bắt đầu trùng điểm đích: {graph.get_node_name(start)}")
        return
    
    goal_pos = graph.get_node_position(goal)
    
    # Priority queue: (f(n), counter, node_id, g_cost)
    counter = 0
    start_pos = graph.get_node_position(start)
    h_start = heuristic_func(start_pos, goal_pos)
    f_start = h_start
    pq: list[tuple[float, int, str, float]] = [(f_start, counter, start, 0.0)]
    
    # Lưu chi phí tốt nhất đến mỗi node (tránh duplicate)
    best_g: Dict[str, float] = {start: 0.0}
    
    visited = set()
    visited_order: list[str] = []
    parent: Dict[str, str] = {start: None}
    
    yield _make_step(start, visited_order, [start], [], 0,
                    f"⭐ A*: Khởi tạo - f({graph.get_node_name(start)}) = "
                    f"g(0) + h({h_start:.1f}) = {f_start:.1f}")
    
    while pq:
        f_val, _, current, g_cost = heapq.heappop(pq)
        
        if current in visited:
            continue
        
        visited.add(current)
        visited_order.append(current)
        
        cur_pos = graph.get_node_position(current)
        h_cur = heuristic_func(cur_pos, goal_pos)
        
        frontier_nodes = [item[2] for item in pq if item[2] not in visited]
        
        yield _make_step(current, visited_order, frontier_nodes, [], g_cost,
                        f"🔍 Đang xét: {graph.get_node_name(current)} | "
                        f"f(n) = g({g_cost:.1f}) + h({h_cur:.1f}) = {f_val:.1f}")
        
        if current == goal:
            path = _reconstruct_path(parent, start, goal)
            route = " → ".join(graph.get_node_name(n) for n in path)
            yield _make_step(current, visited_order, [], path, g_cost,
                            f"✅ Tìm thấy đường đi!\n   Lộ trình: {route}\n   "
                            f"Tổng chi phí: {g_cost:.1f} m")
            return
        
        for neighbor, weight in graph.get_neighbors(current):
            new_g = g_cost + weight
            
            # Chỉ mở rộng nếu tìm được đường tốt hơn đến neighbor
            if neighbor not in visited and (neighbor not in best_g or new_g < best_g[neighbor]):
                best_g[neighbor] = new_g
                parent[neighbor] = current
                n_pos = graph.get_node_position(neighbor)
                h_n = heuristic_func(n_pos, goal_pos)
                f_n = new_g + h_n
                counter += 1
                heapq.heappush(pq, (f_n, counter, neighbor, new_g))
                
                yield _make_step(current, visited_order,
                               [item[2] for item in pq if item[2] not in visited],
                               [], g_cost,
                               f"   ➕ {graph.get_node_name(neighbor)}: "
                               f"f(n) = g({new_g:.1f}) + h({h_n:.1f}) = {f_n:.1f}")
    
    yield _make_step("", visited_order, [], [], 0,
                    f"❌ Không tìm thấy đường đi từ {graph.get_node_name(start)} "
                    f"đến {graph.get_node_name(goal)}")


# Mapping tên thuật toán -> hàm tương ứng
ALGORITHM_MAP = {
    "BFS": bfs,
    "DFS": dfs,
    "UCS": ucs,
    "Greedy": greedy_search,
    "A*": astar,
}

# Các thuật toán cần heuristic
ALGORITHMS_WITH_HEURISTIC = {"Greedy", "A*"}


# Lấy hàm thuật toán theo tên
def get_algorithm(name: str):
    func = ALGORITHM_MAP.get(name)
    if func is None:
        available = ", ".join(ALGORITHM_MAP.keys())
        raise ValueError(f"Thuật toán '{name}' không hợp lệ. Có sẵn: {available}")
    return func


def needs_heuristic(algo_name: str) -> bool:
    return algo_name in ALGORITHMS_WITH_HEURISTIC
