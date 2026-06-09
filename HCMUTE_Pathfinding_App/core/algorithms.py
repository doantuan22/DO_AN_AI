"""Các thuật toán tìm đường dạng generator để UI mô phỏng từng bước."""

import heapq
import time
from collections import deque
from typing import List, Dict, Tuple, Optional, Generator, Callable, Any, Deque

from core.graph import Graph
from core.heuristic import euclidean_distance, manhattan_distance


def _make_step(current: str, visited: list, frontier: list,
               path: list, cost: float, log: str) -> dict:
    """Tạo dữ liệu một bước chạy để map/log/stat cập nhật đồng bộ."""
    return {
        "current": current,
        "visited": list(visited),
        "frontier": list(frontier),
        "path": list(path),
        "cost": cost,
        "log": log,
    }


def bfs(graph: Graph, start: str, goal: str) -> Generator:
    """BFS dùng queue FIFO, phù hợp tìm đường ít cạnh nhất."""
    # Kiểm tra đầu vào.
    if not graph.node_exists(start) or not graph.node_exists(goal):
        yield _make_step(start, [], [], [], 0, "❌ Node không tồn tại trong đồ thị!")
        return
    
    if start == goal:
        yield _make_step(start, [start], [], [start], 0,
                        f"✅ Điểm bắt đầu trùng điểm đích: {graph.get_node_name(start)}")
        return
    
    # Queue lưu (node, path) để khôi phục đường đi khi gặp goal.
    queue: Deque[Tuple[str, List[str]]] = deque()
    queue.append((start, [start]))  # (node_id, path_to_node)
    visited: set[str] = set()
    visited.add(start)
    visited_order: List[str] = [start]
    
    yield _make_step(start, visited_order, [start], [start], 0,
                    f"🔵 BFS: Khởi tạo - Thêm {graph.get_node_name(start)} vào queue")
    
    while queue:
        current, path = queue.popleft()
        
        # Frontier là các node còn trong queue để UI tô màu.
        frontier_nodes = [item[0] for item in queue]
        
        yield _make_step(current, visited_order, frontier_nodes, path, 0,
                        f"🔍 Đang xét: {graph.get_node_name(current)}")
        
        # Gặp goal thì trả về path và tổng chi phí.
        if current == goal:
            cost = graph.calculate_path_cost(path)
            route = " → ".join(graph.get_node_name(n) for n in path)
            yield _make_step(current, visited_order, [], path, cost,
                            f"✅ Tìm thấy đường đi!\n   Lộ trình: {route}\n   Tổng: {cost:.1f} m")
            return
        
        # BFS thêm node kề chưa thăm vào cuối queue.
        for neighbor, weight in graph.get_neighbors(current):
            if neighbor not in visited:
                visited.add(neighbor)
                visited_order.append(neighbor)
                new_path = path + [neighbor]
                queue.append((neighbor, new_path))
                
                yield _make_step(current, visited_order,
                               [item[0] for item in queue],
                               path, 0,
                               f"   ➕ Thêm {graph.get_node_name(neighbor)} vào queue")
    
    yield _make_step("", visited_order, [], [], 0,
                    f"❌ Không tìm thấy đường đi từ {graph.get_node_name(start)} "
                    f"đến {graph.get_node_name(goal)}")


def dfs(graph: Graph, start: str, goal: str) -> Generator:
    """DFS dùng stack LIFO, đi sâu trước và không đảm bảo tối ưu."""
    if not graph.node_exists(start) or not graph.node_exists(goal):
        yield _make_step(start, [], [], [], 0, "❌ Node không tồn tại trong đồ thị!")
        return
    
    if start == goal:
        yield _make_step(start, [start], [], [start], 0,
                        f"✅ Điểm bắt đầu trùng điểm đích: {graph.get_node_name(start)}")
        return
    
    # Stack lưu (node, path) để đi sâu và quay lui.
    stack = [(start, [start])]  # (node_id, path_to_node)
    visited = set()
    visited_order: List[str] = []
    
    yield _make_step(start, visited_order, [start], [start], 0,
                    f"🟣 DFS: Khởi tạo - Thêm {graph.get_node_name(start)} vào stack")
    
    while stack:
        current, path = stack.pop()
        
        if current in visited:
            continue
        
        visited.add(current)
        visited_order.append(current)
        
        frontier_nodes = [item[0] for item in stack if item[0] not in visited]
        
        yield _make_step(current, visited_order, frontier_nodes, path, 0,
                        f"🔍 Đang xét: {graph.get_node_name(current)}")
        
        # Gặp goal thì trả về path hiện tại.
        if current == goal:
            cost = graph.calculate_path_cost(path)
            route = " → ".join(graph.get_node_name(n) for n in path)
            yield _make_step(current, visited_order, [], path, cost,
                            f"✅ Tìm thấy đường đi!\n   Lộ trình: {route}\n   Tổng: {cost:.1f} m")
            return
        
        # Đảo thứ tự để node đầu danh sách kề được xét trước.
        neighbors = graph.get_neighbors(current)
        for neighbor, weight in reversed(neighbors):
            if neighbor not in visited:
                stack.append((neighbor, path + [neighbor]))
                
                yield _make_step(current, visited_order,
                               [item[0] for item in stack if item[0] not in visited],
                               path, 0,
                               f"   ➕ Thêm {graph.get_node_name(neighbor)} vào stack")
    
    yield _make_step("", visited_order, [], [], 0,
                    f"❌ Không tìm thấy đường đi từ {graph.get_node_name(start)} "
                    f"đến {graph.get_node_name(goal)}")


def ucs(graph: Graph, start: str, goal: str) -> Generator:
    """UCS dùng min-heap theo g(n), đảm bảo tối ưu theo trọng số."""
    if not graph.node_exists(start) or not graph.node_exists(goal):
        yield _make_step(start, [], [], [], 0, "❌ Node không tồn tại trong đồ thị!")
        return
    
    if start == goal:
        yield _make_step(start, [start], [], [start], 0,
                        f"✅ Điểm bắt đầu trùng điểm đích: {graph.get_node_name(start)}")
        return
    
    # Heap lưu (g, counter, node, path); counter phá hòa khi g bằng nhau.
    counter = 0
    pq: list[tuple[float, int, str, list[str]]] = [(0.0, counter, start, [start])]
    visited = set()
    visited_order: List[str] = []
    
    yield _make_step(start, visited_order, [start], [start], 0,
                    f"🟠 UCS: Khởi tạo - g({graph.get_node_name(start)}) = 0")
    
    while pq:
        cost, _, current, path = heapq.heappop(pq)
        
        if current in visited:
            continue
        
        visited.add(current)
        visited_order.append(current)
        
        frontier_nodes = [item[2] for item in pq if item[2] not in visited]
        
        yield _make_step(current, visited_order, frontier_nodes, path, cost,
                        f"🔍 Đang xét: {graph.get_node_name(current)} | g(n) = {cost:.1f}")
        
        # Node đầu tiên lấy ra là goal thì chi phí đã tối ưu.
        if current == goal:
            route = " → ".join(graph.get_node_name(n) for n in path)
            yield _make_step(current, visited_order, [], path, cost,
                            f"✅ Tìm thấy đường đi tối ưu!\n   Lộ trình: {route}\n   "
                            f"Tổng chi phí: {cost:.1f} m")
            return
        
        # Đẩy láng giềng vào heap với chi phí tích lũy mới.
        for neighbor, weight in graph.get_neighbors(current):
            if neighbor not in visited:
                new_cost = cost + weight
                counter += 1
                heapq.heappush(pq, (new_cost, counter, neighbor, path + [neighbor]))
                
                yield _make_step(current, visited_order,
                               [item[2] for item in pq if item[2] not in visited],
                               path, cost,
                               f"   ➕ {graph.get_node_name(neighbor)}: "
                               f"g(n) = {cost:.1f} + {weight:.1f} = {new_cost:.1f}")
    
    yield _make_step("", visited_order, [], [], 0,
                    f"❌ Không tìm thấy đường đi từ {graph.get_node_name(start)} "
                    f"đến {graph.get_node_name(goal)}")


def greedy_search(graph: Graph, start: str, goal: str,
                  heuristic_func: Optional[Callable[..., Any]] = None) -> Generator:
    """Greedy ưu tiên h(n) nhỏ nhất, nhanh nhưng không đảm bảo tối ưu."""
    if heuristic_func is None:
        heuristic_func = euclidean_distance
    
    if not graph.node_exists(start) or not graph.node_exists(goal):
        yield _make_step(start, [], [], [], 0, "❌ Node không tồn tại trong đồ thị!")
        return
    
    if start == goal:
        yield _make_step(start, [start], [], [start], 0,
                        f"✅ Điểm bắt đầu trùng điểm đích: {graph.get_node_name(start)}")
        return
    
    goal_pos = graph.get_node_position(goal) or (0, 0)
    
    # Heap ưu tiên h(n); vẫn giữ g_cost để hiển thị tổng đã đi.
    counter = 0
    start_pos = graph.get_node_position(start) or (0, 0)
    h_start = heuristic_func(start_pos, goal_pos)
    pq: list[tuple[float, int, str, list[str], float]] = [(h_start, counter, start, [start], 0.0)]
    visited = set()
    visited_order: List[str] = []
    
    yield _make_step(start, visited_order, [start], [start], 0,
                    f"🟢 Greedy: Khởi tạo - h({graph.get_node_name(start)}) = {h_start:.1f}")
    
    while pq:
        h_val, _, current, path, g_cost = heapq.heappop(pq)
        
        if current in visited:
            continue
        
        visited.add(current)
        visited_order.append(current)
        
        frontier_nodes = [item[2] for item in pq if item[2] not in visited]
        
        yield _make_step(current, visited_order, frontier_nodes, path, g_cost,
                        f"🔍 Đang xét: {graph.get_node_name(current)} | h(n) = {h_val:.1f}")
        
        # Greedy dừng khi chạm goal, path có thể không tối ưu.
        if current == goal:
            total_cost = graph.calculate_path_cost(path)
            route = " → ".join(graph.get_node_name(n) for n in path)
            yield _make_step(current, visited_order, [], path, total_cost,
                            f"✅ Tìm thấy đường đi!\n   Lộ trình: {route}\n   "
                            f"Tổng: {total_cost:.1f} m")
            return
        
        # Chỉ xếp h(n) vào heap, không cộng g(n) vào ưu tiên.
        for neighbor, weight in graph.get_neighbors(current):
            if neighbor not in visited:
                n_pos = graph.get_node_position(neighbor) or (0, 0)
                h_n = heuristic_func(n_pos, goal_pos)
                counter += 1
                new_g = g_cost + weight
                heapq.heappush(pq, (h_n, counter, neighbor, path + [neighbor], new_g))
                
                yield _make_step(current, visited_order,
                               [item[2] for item in pq if item[2] not in visited],
                               path, g_cost,
                               f"   ➕ {graph.get_node_name(neighbor)}: h(n) = {h_n:.1f}")
    
    yield _make_step("", visited_order, [], [], 0,
                    f"❌ Không tìm thấy đường đi từ {graph.get_node_name(start)} "
                    f"đến {graph.get_node_name(goal)}")


def astar(graph: Graph, start: str, goal: str,
          heuristic_func: Optional[Callable[..., Any]] = None) -> Generator:
    """A* ưu tiên f(n)=g(n)+h(n), tối ưu khi heuristic không vượt quá thực tế."""
    if heuristic_func is None:
        heuristic_func = euclidean_distance
    
    if not graph.node_exists(start) or not graph.node_exists(goal):
        yield _make_step(start, [], [], [], 0, "❌ Node không tồn tại trong đồ thị!")
        return
    
    if start == goal:
        yield _make_step(start, [start], [], [start], 0,
                        f"✅ Điểm bắt đầu trùng điểm đích: {graph.get_node_name(start)}")
        return
    
    goal_pos = graph.get_node_position(goal) or (0, 0)
    
    # Heap lưu f(n), path và g(n) thật để tái tạo đường đi.
    counter = 0
    start_pos = graph.get_node_position(start) or (0, 0)
    h_start = heuristic_func(start_pos, goal_pos)
    f_start = h_start  # g(start) = 0
    pq: list[tuple[float, int, str, list[str], float]] = [(f_start, counter, start, [start], 0.0)]
    
    # best_g chặn mở rộng lại nếu đường mới không tốt hơn.
    best_g: Dict[str, float] = {start: 0.0}
    
    visited = set()
    visited_order: List[str] = []
    
    yield _make_step(start, visited_order, [start], [start], 0,
                    f"⭐ A*: Khởi tạo - f({graph.get_node_name(start)}) = "
                    f"g(0) + h({h_start:.1f}) = {f_start:.1f}")
    
    while pq:
        f_val, _, current, path, g_cost = heapq.heappop(pq)
        
        if current in visited:
            continue
        
        visited.add(current)
        visited_order.append(current)
        
        cur_pos = graph.get_node_position(current) or (0, 0)
        h_cur = heuristic_func(cur_pos, goal_pos)
        
        frontier_nodes = [item[2] for item in pq if item[2] not in visited]
        
        yield _make_step(current, visited_order, frontier_nodes, path, g_cost,
                        f"🔍 Đang xét: {graph.get_node_name(current)} | "
                        f"f(n) = g({g_cost:.1f}) + h({h_cur:.1f}) = {f_val:.1f}")
        
        # Với heuristic phù hợp, goal đầu tiên lấy ra là tối ưu.
        if current == goal:
            route = " → ".join(graph.get_node_name(n) for n in path)
            yield _make_step(current, visited_order, [], path, g_cost,
                            f"✅ Tìm thấy đường đi tối ưu!\n   Lộ trình: {route}\n   "
                            f"Tổng chi phí: {g_cost:.1f} m")
            return
        
        for neighbor, weight in graph.get_neighbors(current):
            new_g = g_cost + weight
            
            # Chỉ mở rộng nếu tìm được đường tốt hơn đến neighbor.
            if neighbor not in visited and (neighbor not in best_g or new_g < best_g[neighbor]):
                best_g[neighbor] = new_g
                n_pos = graph.get_node_position(neighbor) or (0, 0)
                h_n = heuristic_func(n_pos, goal_pos)
                f_n = new_g + h_n
                counter += 1
                heapq.heappush(pq, (f_n, counter, neighbor, path + [neighbor], new_g))
                
                yield _make_step(current, visited_order,
                               [item[2] for item in pq if item[2] not in visited],
                               path, g_cost,
                               f"   ➕ {graph.get_node_name(neighbor)}: "
                               f"f(n) = g({new_g:.1f}) + h({h_n:.1f}) = {f_n:.1f}")
    
    yield _make_step("", visited_order, [], [], 0,
                    f"❌ Không tìm thấy đường đi từ {graph.get_node_name(start)} "
                    f"đến {graph.get_node_name(goal)}")


ALGORITHM_MAP = {
    "BFS": bfs,
    "DFS": dfs,
    "UCS": ucs,
    "Greedy": greedy_search,
    "A*": astar,
}

ALGORITHMS_WITH_HEURISTIC = {"Greedy", "A*"}


def get_algorithm(name: str):
    """Lấy hàm thuật toán theo tên hiển thị trên UI."""
    func = ALGORITHM_MAP.get(name)
    if func is None:
        available = ", ".join(ALGORITHM_MAP.keys())
        raise ValueError(f"Thuật toán '{name}' không hợp lệ. Có sẵn: {available}")
    return func


def needs_heuristic(algo_name: str) -> bool:
    """Kiểm tra thuật toán có cần heuristic hay không."""
    return algo_name in ALGORITHMS_WITH_HEURISTIC
