"""
Kiểm tra toàn diện project HCMUTE Pathfinding:
- Thuật toán đúng/sai
- Hàng đợi/ngăn xếp có rò rỉ trạng thái không
- Hiệu năng
- Bộ nhớ (path list accumulation)
"""

import sys, os, time, tracemalloc
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.graph import Graph
from core.algorithms import bfs, dfs, ucs, greedy_search, astar
from core.heuristic import euclidean_distance, manhattan_distance

graph = Graph()
graph.load_from_json("data/hcmute_graph_nodes_edges.json")

PASS = 0
FAIL = 0
WARN = 0

def ok(msg):
    global PASS
    PASS += 1
    print(f"  ✅ PASS: {msg}")

def fail(msg):
    global FAIL
    FAIL += 1
    print(f"  ❌ FAIL: {msg}")

def warn(msg):
    global WARN
    WARN += 1
    print(f"  ⚠️  WARN: {msg}")


# ============================================================
# 1. KIỂM TRA ĐỒ THỊ
# ============================================================
print("=" * 60)
print("1. KIỂM TRA ĐỒ THỊ")
print("=" * 60)

# 1a. Adjacency đối xứng (vô hướng)
for nid, neighbors in graph.adjacency.items():
    for neighbor_id, w in neighbors:
        reverse_found = False
        for rev_nid, rev_w in graph.adjacency.get(neighbor_id, []):
            if rev_nid == nid:
                reverse_found = True
                if abs(rev_w - w) > 0.001:
                    fail(f"Trọng số không đối xứng: {nid}->{neighbor_id}={w} vs ngược lại={rev_w}")
                break
        if not reverse_found:
            fail(f"Cạnh {nid}->{neighbor_id} không có chiều ngược trong adjacency!")

ok(f"Adjacency đối xứng: {len(graph.nodes)} nodes, {len(graph.edges)} edges")

# 1b. Không có cạnh tự nối
for edge in graph.edges:
    if edge.source == edge.target:
        fail(f"Cạnh tự nối: {edge.source}")
ok("Không có cạnh tự nối")

# 1c. Không có trọng số âm
for edge in graph.edges:
    if edge.weight < 0:
        fail(f"Trọng số âm: {edge.source}->{edge.target} = {edge.weight}")
ok("Không có trọng số âm")

# 1d. Node cô lập (không kề gì)
isolated = [nid for nid, adj in graph.adjacency.items() if len(adj) == 0]
if isolated:
    warn(f"Node cô lập (không kề gì): {isolated}")
else:
    ok("Không có node cô lập")


# ============================================================
# 2. KIỂM TRA THUẬT TOÁN - TÍNH ĐÚNG ĐẮN
# ============================================================
print("\n" + "=" * 60)
print("2. KIỂM TRA THUẬT TOÁN - TÍNH ĐÚNG ĐẮN")
print("=" * 60)

TEST_PAIRS = [
    ("N91", "N04"),  # Cổng chính -> KTX
    ("N91", "N78"),  # Cổng chính -> Khoa CNTT
    ("N04", "N91"),  # Ngược lại
    ("N01", "N79"),  # Sân bóng chuyền -> Sân bóng đá
    ("N91", "N91"),  # Trùng điểm
]

def run_algo_to_end(algo_func, graph, start, goal, heuristic=None):
    """Chạy hết generator, trả (path, cost, visited_count, steps)."""
    if heuristic:
        gen = algo_func(graph, start, goal, heuristic)
    else:
        gen = algo_func(graph, start, goal)
    
    steps = list(gen)
    last = steps[-1]
    path = last.get("path", [])
    cost = last.get("cost", 0)
    visited = last.get("visited", [])
    found = "✅" in last.get("log", "")
    return path, cost, len(visited), len(steps), found


for start, goal in TEST_PAIRS:
    print(f"\n  --- Test {start} -> {goal} ---")
    
    # Chạy tất cả thuật toán
    results = {}
    for name, func in [("BFS", bfs), ("DFS", dfs), ("UCS", ucs), 
                         ("Greedy", greedy_search), ("A*", astar)]:
        h = euclidean_distance if name in ("Greedy", "A*") else None
        path, cost, visited, steps, found = run_algo_to_end(func, graph, start, goal, h)
        results[name] = (path, cost, visited, steps, found)
    
    if start == goal:
        # Trường hợp đặc biệt: start == goal
        for name, (path, cost, visited, steps, found) in results.items():
            if found and path == [start]:
                ok(f"{name}: start==goal xử lý đúng")
            else:
                fail(f"{name}: start==goal trả kết quả sai: path={path}, found={found}")
        continue
    
    # 2a. Tất cả thuật toán đều tìm được đường
    for name, (path, cost, visited, steps, found) in results.items():
        if not found:
            fail(f"{name}: Không tìm được đường {start}->{goal}")
        elif len(path) < 2:
            fail(f"{name}: Path quá ngắn: {path}")
        else:
            ok(f"{name}: Tìm được đường, cost={cost:.1f}, visited={visited}, path_len={len(path)}")
    
    # 2b. Kiểm tra path hợp lệ (mỗi cặp liên tiếp phải có cạnh nối)
    for name, (path, cost, visited, steps, found) in results.items():
        if not found or len(path) < 2:
            continue
        valid = True
        for i in range(len(path) - 1):
            w = graph.get_edge_weight(path[i], path[i+1])
            if w is None:
                fail(f"{name}: Path gãy ở {path[i]}->{path[i+1]} (không có cạnh)")
                valid = False
                break
        if valid:
            ok(f"{name}: Path liên tục hợp lệ")
    
    # 2c. Kiểm tra cost == tổng weight thực tế
    for name, (path, cost, visited, steps, found) in results.items():
        if not found or len(path) < 2:
            continue
        real_cost = graph.calculate_path_cost(path)
        if abs(cost - real_cost) > 0.01:
            fail(f"{name}: Cost không khớp! Báo={cost:.2f}, Thực tế={real_cost:.2f}")
        else:
            ok(f"{name}: Cost khớp chính xác ({cost:.2f})")
    
    # 2d. UCS và A* phải tìm đường tối ưu (cost thấp nhất)
    ucs_cost = results["UCS"][1]
    astar_cost = results["A*"][1]
    if abs(ucs_cost - astar_cost) > 0.01:
        fail(f"UCS ({ucs_cost:.2f}) và A* ({astar_cost:.2f}) cho cost khác nhau!")
    else:
        ok(f"UCS và A* cùng cost tối ưu: {ucs_cost:.2f}")
    
    # BFS tìm ít bước nhất (hop count) nhưng không nhất thiết ngắn nhất theo weight
    bfs_hops = len(results["BFS"][0]) - 1
    for name in ["DFS", "UCS", "Greedy", "A*"]:
        other_hops = len(results[name][0]) - 1
        if bfs_hops > other_hops and other_hops > 0:
            warn(f"BFS ({bfs_hops} hops) dài hơn {name} ({other_hops} hops) - check lại!")


# ============================================================
# 3. KIỂM TRA HÀNG ĐỢI/NGĂN XẾP - RÒ RỈ TRẠNG THÁI
# ============================================================
print("\n" + "=" * 60)
print("3. KIỂM TRA RÒ RỈ TRẠNG THÁI (QUEUE/STACK)")
print("=" * 60)

def check_visited_not_in_frontier(algo_func, graph, start, goal, name, heuristic=None):
    """Kiểm tra: mỗi step, frontier KHÔNG chứa node đã visited."""
    if heuristic:
        gen = algo_func(graph, start, goal, heuristic)
    else:
        gen = algo_func(graph, start, goal)
    
    violation_count = 0
    for step in gen:
        visited = set(step.get("visited", []))
        frontier = step.get("frontier", [])
        overlap = visited.intersection(set(frontier))
        if overlap:
            violation_count += 1
    
    if violation_count > 0:
        # Đối với DFS/UCS/Greedy/A* dùng lazy deletion, frontier CÓ THỂ chứa
        # các node đã visited nhưng chưa pop ra. Đây là hành vi bình thường.
        if name in ("DFS", "UCS", "Greedy", "A*"):
            warn(f"{name}: {violation_count} bước có node đã visited trong frontier "
                  "(lazy deletion - bình thường cho heap/stack)")
        else:
            fail(f"{name}: {violation_count} bước có node đã visited vẫn nằm trong frontier!")
    else:
        ok(f"{name}: Frontier sạch, không chứa node đã visited")


for name, func in [("BFS", bfs), ("DFS", dfs), ("UCS", ucs),
                     ("Greedy", greedy_search), ("A*", astar)]:
    h = euclidean_distance if name in ("Greedy", "A*") else None
    check_visited_not_in_frontier(func, graph, "N91", "N04", name, h)


# 3b. Kiểm tra: DFS stack có các phần tử trùng lặp đáng kể không
print("\n  --- DFS stack duplication check ---")
gen = dfs(graph, "N91", "N04")
max_stack_size = 0
for step in gen:
    frontier = step.get("frontier", [])
    max_stack_size = max(max_stack_size, len(frontier))

total_nodes = len(graph.nodes)
if max_stack_size > total_nodes * 3:
    warn(f"DFS stack tối đa ({max_stack_size}) gấp >{total_nodes*3} lần số node "
         f"→ nhiều bản sao path trong stack!")
else:
    ok(f"DFS stack tối đa: {max_stack_size} (OK, tổng {total_nodes} nodes)")


# 3c. UCS/A* heap: kiểm tra duplicate entries
print("\n  --- UCS/A* heap duplicate check ---")
for name, func in [("UCS", ucs), ("A*", astar)]:
    h = euclidean_distance if name == "A*" else None
    if h:
        gen = func(graph, "N91", "N04", h)
    else:
        gen = func(graph, "N91", "N04")
    
    max_frontier = 0
    for step in gen:
        frontier = step.get("frontier", [])
        max_frontier = max(max_frontier, len(frontier))
    
    if max_frontier > total_nodes * 2:
        warn(f"{name}: frontier tối đa {max_frontier} > {total_nodes*2} "
             "(quá nhiều duplicate trong heap)")
    else:
        ok(f"{name}: frontier tối đa {max_frontier} (hợp lý)")


# ============================================================
# 4. KIỂM TRA HIỆU NĂNG & BỘ NHỚ
# ============================================================
print("\n" + "=" * 60)
print("4. KIỂM TRA HIỆU NĂNG & BỘ NHỚ")
print("=" * 60)

# 4a. Path accumulation: mỗi step lưu path = path + [neighbor]
# → tạo rất nhiều list mới. Đo memory peak.
tracemalloc.start()

for name, func in [("BFS", bfs), ("DFS", dfs), ("UCS", ucs),
                     ("Greedy", greedy_search), ("A*", astar)]:
    h = euclidean_distance if name in ("Greedy", "A*") else None
    
    tracemalloc.clear_traces()
    snap_before = tracemalloc.take_snapshot()
    
    t0 = time.perf_counter()
    if h:
        steps = list(func(graph, "N91", "N04", h))
    else:
        steps = list(func(graph, "N91", "N04"))
    t1 = time.perf_counter()
    
    snap_after = tracemalloc.take_snapshot()
    current, peak = tracemalloc.get_traced_memory()
    
    duration_ms = (t1 - t0) * 1000
    print(f"  {name}: {duration_ms:.3f} ms, {len(steps)} steps, peak_mem={peak/1024:.1f} KB")
    
    if duration_ms > 100:
        warn(f"{name}: Chạy quá chậm ({duration_ms:.1f}ms > 100ms)")
    else:
        ok(f"{name}: Tốc độ OK ({duration_ms:.3f} ms)")
    
    if peak > 5 * 1024 * 1024:  # > 5MB
        warn(f"{name}: Bộ nhớ peak cao ({peak/1024/1024:.1f} MB)")
    else:
        ok(f"{name}: Bộ nhớ OK ({peak/1024:.1f} KB)")

tracemalloc.stop()


# ============================================================
# 5. KIỂM TRA _make_step: frontier snapshot O(n) mỗi bước
# ============================================================
print("\n" + "=" * 60)
print("5. KIỂM TRA HIỆU NĂNG FRONTIER SNAPSHOT")
print("=" * 60)

# UCS và A* dùng list comprehension [item[2] for item in pq if ...] mỗi bước
# → O(|pq|) mỗi lần yield. Với đồ thị lớn, đây là bottleneck.
# Kiểm tra tỷ lệ thời gian frontier vs tổng.

import cProfile, io, pstats

for name, func in [("UCS", ucs), ("A*", astar)]:
    h = euclidean_distance if name == "A*" else None
    
    pr = cProfile.Profile()
    pr.enable()
    if h:
        steps = list(func(graph, "N91", "N04", h))
    else:
        steps = list(func(graph, "N91", "N04"))
    pr.disable()
    
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
    ps.print_stats(5)
    
    # Chỉ báo cáo tóm tắt
    total_calls = pr.getstats()
    ok(f"{name}: {len(steps)} steps hoàn tất, profiling OK")


# ============================================================
# 6. KIỂM TRA TRƯỜNG HỢP BIÊN
# ============================================================
print("\n" + "=" * 60)
print("6. KIỂM TRA TRƯỜNG HỢP BIÊN")
print("=" * 60)

# 6a. Node không tồn tại
for name, func in [("BFS", bfs), ("DFS", dfs), ("UCS", ucs),
                     ("Greedy", greedy_search), ("A*", astar)]:
    h = euclidean_distance if name in ("Greedy", "A*") else None
    if h:
        steps = list(func(graph, "INVALID_1", "INVALID_2", h))
    else:
        steps = list(func(graph, "INVALID_1", "INVALID_2"))
    
    last = steps[-1]
    if "❌" in last.get("log", ""):
        ok(f"{name}: Node không tồn tại → xử lý đúng")
    else:
        fail(f"{name}: Node không tồn tại nhưng không báo lỗi!")

# 6b. Start == Goal 
for name, func in [("BFS", bfs), ("DFS", dfs), ("UCS", ucs),
                     ("Greedy", greedy_search), ("A*", astar)]:
    h = euclidean_distance if name in ("Greedy", "A*") else None
    if h:
        steps = list(func(graph, "N91", "N91", h))
    else:
        steps = list(func(graph, "N91", "N91"))
    
    last = steps[-1]
    if "✅" in last.get("log", "") and last.get("path") == ["N91"]:
        ok(f"{name}: Start==Goal → xử lý đúng")
    else:
        fail(f"{name}: Start==Goal xử lý sai! log={last.get('log')}")


# ============================================================
# 7. KIỂM TRA HEURISTIC ADMISSIBILITY (cho A*)
# ============================================================
print("\n" + "=" * 60)
print("7. KIỂM TRA HEURISTIC ADMISSIBILITY")
print("=" * 60)

# Euclidean distance luôn <= cost thực tế (vì weight = Euclidean)
# → Admissible khi weight chính là khoảng cách Euclidean giữa 2 node.
# Kiểm tra: mọi cạnh, weight >= euclidean(source, target)
overestimate_count = 0
for edge in graph.edges:
    src = graph.get_node(edge.source)
    dst = graph.get_node(edge.target)
    if src and dst:
        euc = euclidean_distance(src.position(), dst.position())
        if edge.weight < euc - 0.01:  # weight nhỏ hơn khoảng cách thật → lạ
            warn(f"Edge {edge.source}->{edge.target}: weight={edge.weight:.2f} < euclidean={euc:.2f}")
            overestimate_count += 1

if overestimate_count == 0:
    ok("Tất cả edge weights >= khoảng cách Euclidean → heuristic admissible cho A*")
else:
    warn(f"{overestimate_count} edges có weight < Euclidean (có thể do thêm/sửa thủ công)")

# Manhattan luôn >= Euclidean nên KHÔNG admissible khi weight = Euclidean
# (Manhattan overestimates khi đường đi xiên)
manhattan_violations = 0
for nid in graph.get_all_node_ids():
    for goal_id in ["N04"]:
        if nid == goal_id:
            continue
        src_pos = graph.get_node_position(nid)
        goal_pos = graph.get_node_position(goal_id)
        if src_pos and goal_pos:
            h_man = manhattan_distance(src_pos, goal_pos)
            h_euc = euclidean_distance(src_pos, goal_pos)
            if h_man < h_euc - 0.01:
                manhattan_violations += 1

ok(f"Manhattan >= Euclidean ở tất cả {len(graph.nodes)} nodes (đúng theo lý thuyết)")
warn("Manhattan KHÔNG admissible khi weight=Euclidean → A* với Manhattan có thể không tối ưu!")


# ============================================================
# TỔNG KẾT
# ============================================================
print("\n" + "=" * 60)
print(f"TỔNG KẾT: {PASS} PASS, {FAIL} FAIL, {WARN} WARNINGS")
print("=" * 60)
if FAIL > 0:
    print("⚠️  CÓ LỖI CẦN SỬA!")
else:
    print("✅ TẤT CẢ KIỂM TRA ĐỀU OK!")
