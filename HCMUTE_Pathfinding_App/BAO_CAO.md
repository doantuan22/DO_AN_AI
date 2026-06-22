# Báo cáo: Phân tích các thuật toán tìm đường (Pathfinding) trong hệ thống HCMUTE App

Tài liệu này tổng hợp cấu trúc, mã nguồn cốt lõi và phân tích cách áp dụng 5 thuật toán tìm đường chính được tích hợp trong hệ thống. Tất cả các thuật toán đều được thiết kế dưới dạng Python Generator (`yield`) để hỗ trợ việc hiển thị hiệu ứng trực quan (animation) theo từng bước trên giao diện UI.

---

## 1. Breadth-First Search (BFS) - Tìm kiếm theo chiều rộng
**Sơ bộ:** Thuật toán duyệt qua các đỉnh của đồ thị theo từng cấp bậc (chiều rộng), ưu tiên mở rộng các đỉnh kề gần nhất (xét theo số lượng cạnh) trước khi đi sâu hơn.

**Code cài đặt cốt lõi:**
```python
def bfs(graph: Graph, start: str, goal: str) -> Generator:
    queue = deque()
    queue.append((start, [start]))
    visited = set()
    visited.add(start)
    visited_order = [start]
    
    while queue:
        current, path = queue.popleft()
        
        if current == goal:
            # Yield kết quả thành công và dừng thuật toán
            return
        
        # Mở rộng các node kề chưa visited
        for neighbor, weight in graph.get_neighbors(current):
            if neighbor not in visited:
                visited.add(neighbor)
                visited_order.append(neighbor)
                new_path = path + [neighbor]
                queue.append((neighbor, new_path))
                # Yield trạng thái để vẽ animation...
```

**Mô tả thuật toán:**
*   **Ý tưởng chính:** Sử dụng cấu trúc hàng đợi (Queue - Cơ chế FIFO: Vào trước ra trước). Bắt đầu từ điểm gốc, nó duyệt hết tất cả các điểm hàng xóm cùng cấp độ trước khi di chuyển sang cấp độ xa hơn.
*   **Cách áp dụng vào hệ thống:** Hệ thống sử dụng thư viện `collections.deque` để tối ưu thao tác thêm/rút phần tử ở 2 đầu `queue`. Mỗi phần tử trong hàng đợi lưu trữ dạng tuple `(node_id, đường_đi_đến_node)`. Ở mỗi bước duyệt, hàm sẽ dùng lệnh `yield` để gửi một bản đồ trạng thái (gồm `current, visited, frontier`) về cho giao diện (MapWidget) render và hiển thị mô phỏng loang màu trên bản đồ.
*   **Kết quả trả về:** BFS luôn tìm được đường đi có **số lượng cạnh ít nhất**. Tuy nhiên trên bản đồ HCMUTE, do các cạnh có khoảng cách (trọng số) khác nhau, đường đi ít cạnh nhất chưa chắc đã là đường đi có khoảng cách ngắn nhất.

---

## 2. Depth-First Search (DFS) - Tìm kiếm theo chiều sâu
**Sơ bộ:** Thuật toán duyệt bằng cách ưu tiên đi sâu nhất có thể dọc theo mỗi nhánh của đồ thị cho đến khi đụng ngõ cụt mới tiến hành quay lui (backtrack).

**Code cài đặt cốt lõi:**
```python
def dfs(graph: Graph, start: str, goal: str) -> Generator:
    stack = [(start, [start])]
    visited = set()
    discovered = {start}
    visited_order = []
    
    while stack:
        current, path = stack.pop()
        
        if current in visited:
            continue
        
        visited.add(current)
        visited_order.append(current)
        
        if current == goal:
            # Yield kết quả thành công...
            return
        
        # Đảo thứ tự để duyệt node đầu tiên trước khi pop
        neighbors = graph.get_neighbors(current)
        for neighbor, weight in reversed(neighbors):
            if neighbor not in visited and neighbor not in discovered:
                discovered.add(neighbor)
                stack.append((neighbor, path + [neighbor]))
                # Yield trạng thái để vẽ animation...
```

**Mô tả thuật toán:**
*   **Ý tưởng chính:** Dựa trên cấu trúc ngăn xếp (Stack - Cơ chế LIFO: Vào sau ra trước). Cứ đi tới một node kề, bỏ nó vào Stack, sau đó ngay lập tức bật nó ra để đi tiếp, bỏ qua các node kề cùng cấp khác cho đến khi phải lùi lại.
*   **Cách áp dụng vào hệ thống:** Sử dụng `list` của Python làm Stack. Hệ thống áp dụng một kỹ thuật rất tinh tế là `reversed(neighbors)` khi duyệt lân cận. Do Stack lấy phần tử ở cuối (hàm `pop()`), việc nạp ngược thứ tự các node kề sẽ giúp mô phỏng thuật toán đi đúng thứ tự thuận trên đồ thị. `discovered` set được dùng để tránh đưa trùng lặp node vào ngăn xếp.
*   **Kết quả trả về:** DFS trả về đường đi đầu tiên mà nó tìm thấy chạm đến đích. Đường đi này thường rất dài và đi lòng vòng, **không đảm bảo tối ưu** về bất cứ mặt nào (số cạnh hay khoảng cách).

---

## 3. Uniform Cost Search (UCS) - Tìm kiếm chi phí đồng nhất
**Sơ bộ:** Thuật toán mở rộng đồ thị dựa trên chi phí đường đi thực tế tích lũy $g(n)$ từ điểm đầu đến đỉnh hiện tại, luôn mở rộng nhánh có tổng chi phí nhỏ nhất.

**Code cài đặt cốt lõi:**
```python
def ucs(graph: Graph, start: str, goal: str) -> Generator:
    counter = 0
    pq: list[tuple[float, int, str, list[str]]] = [(0.0, counter, start, [start])]
    best_g: Dict[str, float] = {start: 0.0}
    visited = set()
    visited_order = []
    
    while pq:
        cost, _, current, path = heapq.heappop(pq)
        
        if current in visited or cost > best_g.get(current, float("inf")):
            continue
            
        visited.add(current)
        visited_order.append(current)
        
        if current == goal:
            # Yield kết quả tối ưu...
            return
        
        for neighbor, weight in graph.get_neighbors(current):
            new_cost = cost + weight
            if neighbor not in visited and new_cost < best_g.get(neighbor, float("inf")):
                best_g[neighbor] = new_cost
                counter += 1
                heapq.heappush(pq, (new_cost, counter, neighbor, path + [neighbor]))
                # Yield trạng thái...
```

**Mô tả thuật toán:**
*   **Ý tưởng chính:** Đây là biến thể của thuật toán Dijkstra. Khác với BFS (coi mọi cạnh có trọng số như nhau), UCS xét trọng số thực. Nó luôn chọn node có tổng khoảng cách $g(n)$ nhỏ nhất để mở rộng tiếp.
*   **Cách áp dụng vào hệ thống:** 
  - Hệ thống áp dụng Hàng đợi ưu tiên (Priority Queue) thông qua module `heapq`. 
  - Các phần tử trong Priority Queue có dạng `(cost, counter, current, path)`. Biến `counter` là bộ đếm số thứ tự giúp phân định ưu tiên khi 2 điểm có cùng `cost`.
  - Một dictionary tên `best_g` được dùng làm bộ đệm để ghi nhớ chi phí tốt nhất đi đến mỗi node, qua đó tránh được việc thêm dư thừa các node có đường đi tốn kém hơn vào hàng đợi.
*   **Kết quả trả về:** UCS luôn đảm bảo **tìm ra đường đi có khoảng cách (tổng chi phí cạnh) ngắn nhất**. Giao diện sẽ mô phỏng UCS lan tỏa theo vòng tròn các đường đồng mức từ điểm xuất phát.

---

## 4. Greedy Search - Tìm kiếm tham lam
**Sơ bộ:** Thuật toán mở rộng dựa vào hàm đánh giá $h(n)$ (khoảng cách Heuristic). Luôn chọn node có vẻ "gần đích nhất" theo phán đoán của hàm $h(n)$ để ưu tiên đi trước.

**Code cài đặt cốt lõi:**
```python
def greedy_search(graph: Graph, start: str, goal: str, heuristic_func=None) -> Generator:
    goal_pos = graph.get_node_position(goal)
    counter = 0
    start_pos = graph.get_node_position(start)
    h_start = heuristic_func(start_pos, goal_pos)
    pq: list[tuple[float, int, str, list[str], float]] = [(h_start, counter, start, [start], 0.0)]
    visited = set()
    # ...
    while pq:
        h_val, _, current, path, g_cost = heapq.heappop(pq)
        
        if current in visited: continue
        visited.add(current)
        # ...
        if current == goal: return
        
        for neighbor, weight in graph.get_neighbors(current):
            if neighbor not in visited:
                n_pos = graph.get_node_position(neighbor)
                h_n = heuristic_func(n_pos, goal_pos)
                counter += 1
                new_g = g_cost + weight
                heapq.heappush(pq, (h_n, counter, neighbor, path + [neighbor], new_g))
```

**Mô tả thuật toán:**
*   **Ý tưởng chính:** Bỏ qua chi phí đã di chuyển $g(n)$, Greedy chỉ quan tâm đến $h(n)$ (Khoảng cách đường chim bay / Euclidean hoặc Manhattan từ điểm hiện tại tới đích). Nó hành động một cách "mù quáng" hướng về đích.
*   **Cách áp dụng vào hệ thống:** Vẫn dùng `heapq` làm Priority Queue nhưng yếu tố quyết định ưu tiên bây giờ là `h_val` ($h(n)$). Hàm tính khoảng cách `heuristic_func` được truyền vào dưới dạng một tham số (callback) linh hoạt để người dùng tùy biến qua giao diện. Tọa độ của Node (`graph.get_node_position()`) được trích xuất để làm input cho hàm heuristic.
*   **Kết quả trả về:** **Tốc độ tìm kiếm rất nhanh** do số lượng node phải mở rộng ít, lao thẳng đến đích. Tuy nhiên, đường đi trả về có thể **không phải là ngắn nhất** (bị mắc kẹt hoặc phải đi vòng qua chướng ngại vật khiến tổng $g(n)$ tăng vọt).

---

## 5. A* (A-Star) Search
**Sơ bộ:** Thuật toán thông minh nhất, kết hợp ưu điểm của cả UCS (ưu tiên chi phí thực) và Greedy (hướng về đích). Đánh giá mỗi đỉnh bằng hàm $f(n) = g(n) + h(n)$.

**Code cài đặt cốt lõi:**
```python
def astar(graph: Graph, start: str, goal: str, heuristic_func=None) -> Generator:
    goal_pos = graph.get_node_position(goal)
    counter = 0
    start_pos = graph.get_node_position(start)
    h_start = heuristic_func(start_pos, goal_pos)
    f_start = h_start
    pq: list[tuple[float, int, str, list[str], float]] = [(f_start, counter, start, [start], 0.0)]
    best_g: Dict[str, float] = {start: 0.0}
    visited = set()
    
    while pq:
        f_val, _, current, path, g_cost = heapq.heappop(pq)
        if current in visited: continue
        visited.add(current)
        
        if current == goal: return
        
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
```

**Mô tả thuật toán:**
*   **Ý tưởng chính:** Khắc phục tính "bảo thủ" của UCS và tính "cận thị" của Greedy. `f(n)` cân bằng hoàn hảo giữa chi phí đã phải trả `g(n)` và hy vọng về đích sớm `h(n)`.
*   **Cách áp dụng vào hệ thống:**
  - Hàng đợi ưu tiên xếp loại bằng `f_n` (giá trị $f(n)$).
  - Tối ưu hóa giống UCS bằng cách duy trì `best_g` dictionary để đảm bảo không đưa những con đường dài hơn đến cùng một node kề vào danh sách duyệt.
  - Sử dụng chung hàm `heuristic_func` linh hoạt như Greedy.
*   **Kết quả trả về:** Luôn đảm bảo **tìm được đường đi ngắn nhất** (với điều kiện hàm $h(n)$ hợp lệ - admissible, tức không đánh giá vống khoảng cách). Đồng thời số lượng node phải mở rộng (mô phỏng trên bản đồ) ít hơn UCS rất nhiều. Mức độ lan tỏa của animation thay vì thành vòng tròn đồng tâm như UCS sẽ bị "kéo nghiêng" lấn về phía có điểm đích.
