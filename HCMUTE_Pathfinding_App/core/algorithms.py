

"""
algorithms.py - Module cài đặt các thuật toán tìm kiếm trên đồ thị
====================================================================
Bao gồm 5 thuật toán:
  1. BFS  (Breadth-First Search)
  2. DFS  (Depth-First Search)
  3. UCS  (Uniform-Cost Search)
  4. Greedy Search
  5. A* Search

Mỗi thuật toán được cài đặt dưới dạng generator (yield từng bước)
để hỗ trợ mô phỏng trực quan trên giao diện.

Mỗi bước yield một dict chứa trạng thái hiện tại của thuật toán.
"""

import heapq
import time
from collections import deque
from typing import List, Dict, Tuple, Optional, Generator, Callable, Any

from core.graph import Graph
from core.heuristic import euclidean_distance, manhattan_distance


# ──────────────────────────────────────────────────────────────
# Kiểu dữ liệu cho mỗi bước mô phỏng
# ──────────────────────────────────────────────────────────────

def _make_step(current: str, visited: list, frontier: list,
               path: list, cost: float, log: str) -> dict:
    """
    Tạo dict mô tả một bước của thuật toán.
    
    Args:
        current: Node đang xét
        visited: Danh sách các node đã duyệt
        frontier: Danh sách các node trong hàng đợi/ngăn xếp
        path: Đường đi hiện tại đến node current
        cost: Chi phí tích lũy đến node current
        log: Thông báo log cho bước này
        
    Returns:
        Dict chứa trạng thái bước hiện tại
    """
    return {
        "current": current,
        "visited": list(visited),
        "frontier": list(frontier),
        "path": list(path),
        "cost": cost,
        "log": log,
    }


# ──────────────────────────────────────────────────────────────
# 1. BFS - Breadth-First Search
# ──────────────────────────────────────────────────────────────

def bfs(graph: Graph, start: str, goal: str) -> Generator:
    """
    Thuật toán BFS - Tìm kiếm theo chiều rộng.
    
    Args:
        graph: Đồ thị HCMUTE
        start: ID node bắt đầu
        goal: ID node đích
        
    Yields:
        Dict trạng thái mỗi bước
    """
    # Kiểm tra đầu vào
    if not graph.node_exists(start) or not graph.node_exists(goal):
        yield _make_step(start, [], [], [], 0, "❌ Node không tồn tại trong đồ thị!")
        return
    
    if start == goal:
        yield _make_step(start, [start], [], [start], 0,
                        f"✅ Điểm bắt đầu trùng điểm đích: {graph.get_node_name(start)}")
        return
    
    # Khởi tạo
    queue = deque()          # Hàng đợi FIFO
    queue.append((start, [start]))  # (node_id, path_to_node)
    visited = set()          # Tập các node đã thăm
    visited.add(start)
    visited_order = [start]  # Thứ tự duyệt
    
    yield _make_step(start, visited_order, [start], [start], 0,
                    f"🔵 BFS: Khởi tạo - Thêm {graph.get_node_name(start)} vào queue")
    
    while queue:
        current, path = queue.popleft()
        
        # Lấy danh sách frontier hiện tại để hiển thị
        frontier_nodes = [item[0] for item in queue]
        
        yield _make_step(current, visited_order, frontier_nodes, path, 0,
                        f"🔍 Đang xét: {graph.get_node_name(current)}")
        
        # Kiểm tra đã đến đích chưa
        if current == goal:
            cost = graph.calculate_path_cost(path)
            route = " → ".join(graph.get_node_name(n) for n in path)
            yield _make_step(current, visited_order, [], path, cost,
                            f"✅ Tìm thấy đường đi!\n   Lộ trình: {route}\n   Tổng: {cost:.1f} m")
            return
        
        # Mở rộng các node kề
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
    
    # Không tìm thấy đường đi
    yield _make_step("", visited_order, [], [], 0,
                    f"❌ Không tìm thấy đường đi từ {graph.get_node_name(start)} "
                    f"đến {graph.get_node_name(goal)}")


# ──────────────────────────────────────────────────────────────
# 2. DFS - Depth-First Search
# ──────────────────────────────────────────────────────────────

def dfs(graph: Graph, start: str, goal: str) -> Generator:
    """
    Thuật toán DFS - Tìm kiếm theo chiều sâu.
    
    Args:
        graph: Đồ thị HCMUTE
        start: ID node bắt đầu
        goal: ID node đích
        
    Yields:
        Dict trạng thái mỗi bước
    """
    if not graph.node_exists(start) or not graph.node_exists(goal):
        yield _make_step(start, [], [], [], 0, "❌ Node không tồn tại trong đồ thị!")
        return
    
    if start == goal:
        yield _make_step(start, [start], [], [start], 0,
                        f"✅ Điểm bắt đầu trùng điểm đích: {graph.get_node_name(start)}")
        return
    
    # Khởi tạo ngăn xếp
    stack = [(start, [start])]  # (node_id, path_to_node)
    visited = set()
    visited_order = []
    
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
        
        # Kiểm tra đích
        if current == goal:
            cost = graph.calculate_path_cost(path)
            route = " → ".join(graph.get_node_name(n) for n in path)
            yield _make_step(current, visited_order, [], path, cost,
                            f"✅ Tìm thấy đường đi!\n   Lộ trình: {route}\n   Tổng: {cost:.1f} m")
            return
        
        # Mở rộng theo chiều sâu (đảo thứ tự để duyệt node đầu tiên trước)
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


# ──────────────────────────────────────────────────────────────
# 3. UCS - Uniform-Cost Search
# ──────────────────────────────────────────────────────────────

def ucs(graph: Graph, start: str, goal: str) -> Generator:
    """
    Thuật toán UCS - Tìm kiếm chi phí đồng nhất.
    Args:
        graph: Đồ thị HCMUTE
        start: ID node bắt đầu
        goal: ID node đích
        
    Yields:
        Dict trạng thái mỗi bước
    """
    if not graph.node_exists(start) or not graph.node_exists(goal):
        yield _make_step(start, [], [], [], 0, "❌ Node không tồn tại trong đồ thị!")
        return
    
    if start == goal:
        yield _make_step(start, [start], [], [start], 0,
                        f"✅ Điểm bắt đầu trùng điểm đích: {graph.get_node_name(start)}")
        return
    
    # Priority queue: (cost, counter, node_id, path)
    # counter dùng để phá vỡ tie-breaking khi cost bằng nhau
    counter = 0
    pq: list[tuple[float, int, str, list[str]]] = [(0.0, counter, start, [start])]
    visited = set()
    visited_order = []
    
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
        
        # Kiểm tra đích
        if current == goal:
            route = " → ".join(graph.get_node_name(n) for n in path)
            yield _make_step(current, visited_order, [], path, cost,
                            f"✅ Tìm thấy đường đi tối ưu!\n   Lộ trình: {route}\n   "
                            f"Tổng chi phí: {cost:.1f} m")
            return
        
        # Mở rộng
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


# ──────────────────────────────────────────────────────────────
# 4. Greedy Search
# ──────────────────────────────────────────────────────────────

def greedy_search(graph: Graph, start: str, goal: str,
                  heuristic_func: Optional[Callable[..., Any]] = None) -> Generator:
    """
    Thuật toán Greedy Best-First Search.
    
    Args:
        graph: Đồ thị HCMUTE
        start: ID node bắt đầu
        goal: ID node đích
        heuristic_func: Hàm heuristic (mặc định: Euclidean)
        
    Yields:
        Dict trạng thái mỗi bước
    """
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
    
    # Priority queue: (h(n), counter, node_id, path, g_cost)
    counter = 0
    start_pos = graph.get_node_position(start)
    h_start = heuristic_func(start_pos, goal_pos)
    pq: list[tuple[float, int, str, list[str], float]] = [(h_start, counter, start, [start], 0.0)]
    visited = set()
    visited_order = []
    
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
        
        # Kiểm tra đích
        if current == goal:
            total_cost = graph.calculate_path_cost(path)
            route = " → ".join(graph.get_node_name(n) for n in path)
            yield _make_step(current, visited_order, [], path, total_cost,
                            f"✅ Tìm thấy đường đi!\n   Lộ trình: {route}\n   "
                            f"Tổng: {total_cost:.1f} m")
            return
        
        # Mở rộng
        for neighbor, weight in graph.get_neighbors(current):
            if neighbor not in visited:
                n_pos = graph.get_node_position(neighbor)
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


# ──────────────────────────────────────────────────────────────
# 5. A* Search
# ──────────────────────────────────────────────────────────────

def astar(graph: Graph, start: str, goal: str,
          heuristic_func: Optional[Callable[..., Any]] = None) -> Generator:
    """
    Thuật toán A* Search.

    Args:
        graph: Đồ thị HCMUTE
        start: ID node bắt đầu
        goal: ID node đích
        heuristic_func: Hàm heuristic (mặc định: Euclidean)
        
    Yields:
        Dict trạng thái mỗi bước
    """
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
    
    # Priority queue: (f(n), counter, node_id, path, g_cost)
    counter = 0
    start_pos = graph.get_node_position(start)
    h_start = heuristic_func(start_pos, goal_pos)
    f_start = h_start  # g(start) = 0
    pq: list[tuple[float, int, str, list[str], float]] = [(f_start, counter, start, [start], 0.0)]
    
    # Lưu chi phí tốt nhất đến mỗi node
    best_g: Dict[str, float] = {start: 0.0}
    
    visited = set()
    visited_order = []
    
    yield _make_step(start, visited_order, [start], [start], 0,
                    f"⭐ A*: Khởi tạo - f({graph.get_node_name(start)}) = "
                    f"g(0) + h({h_start:.1f}) = {f_start:.1f}")
    
    while pq:
        f_val, _, current, path, g_cost = heapq.heappop(pq)
        
        if current in visited:
            continue
        
        visited.add(current)
        visited_order.append(current)
        
        cur_pos = graph.get_node_position(current)
        h_cur = heuristic_func(cur_pos, goal_pos)
        
        frontier_nodes = [item[2] for item in pq if item[2] not in visited]
        
        yield _make_step(current, visited_order, frontier_nodes, path, g_cost,
                        f"🔍 Đang xét: {graph.get_node_name(current)} | "
                        f"f(n) = g({g_cost:.1f}) + h({h_cur:.1f}) = {f_val:.1f}")
        
        # Kiểm tra đích
        if current == goal:
            route = " → ".join(graph.get_node_name(n) for n in path)
            yield _make_step(current, visited_order, [], path, g_cost,
                            f"✅ Tìm thấy đường đi tối ưu!\n   Lộ trình: {route}\n   "
                            f"Tổng chi phí: {g_cost:.1f} m")
            return
        
        # Mở rộng
        for neighbor, weight in graph.get_neighbors(current):
            new_g = g_cost + weight
            
            # Chỉ mở rộng nếu tìm được đường tốt hơn đến neighbor
            if neighbor not in visited and (neighbor not in best_g or new_g < best_g[neighbor]):
                best_g[neighbor] = new_g
                n_pos = graph.get_node_position(neighbor)
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


# ──────────────────────────────────────────────────────────────
# Mapping tên thuật toán -> hàm tương ứng
# ──────────────────────────────────────────────────────────────

ALGORITHM_MAP = {
    "BFS": bfs,
    "DFS": dfs,
    "UCS": ucs,
    "Greedy": greedy_search,
    "A*": astar,
}

# Các thuật toán cần heuristic
ALGORITHMS_WITH_HEURISTIC = {"Greedy", "A*"}


def get_algorithm(name: str):
    """
    Lấy hàm thuật toán theo tên.
    
    Args:
        name: Tên thuật toán ("BFS", "DFS", "UCS", "Greedy", "A*")
        
    Returns:
        Hàm thuật toán tương ứng
    """
    func = ALGORITHM_MAP.get(name)
    if func is None:
        available = ", ".join(ALGORITHM_MAP.keys())
        raise ValueError(f"Thuật toán '{name}' không hợp lệ. Có sẵn: {available}")
    return func


def needs_heuristic(algo_name: str) -> bool:
    """Kiểm tra thuật toán có cần heuristic hay không."""
    return algo_name in ALGORITHMS_WITH_HEURISTIC
