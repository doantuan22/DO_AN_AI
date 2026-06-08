"""
test_algorithms.py - Kiểm thử các thuật toán tìm kiếm
========================================================
Sử dụng unittest để kiểm tra tính đúng đắn của BFS, DFS,
UCS, Greedy và A* trên đồ thị mẫu.
"""

import sys
import os
import unittest
import tempfile
from typing import Optional

# Thêm thư mục gốc vào sys.path để import được các module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.graph import Graph, Node, Edge
from core.algorithms import bfs, dfs, ucs, greedy_search, astar
from core.heuristic import euclidean_distance, manhattan_distance


class TestGraphSetup(unittest.TestCase):
    """Test cấu trúc đồ thị."""
    
    def setUp(self):
        """Tạo đồ thị mẫu cho test."""
        self.graph = Graph()
        
        # Tạo nodes
        nodes = [
            Node("A", 0, 0, "Node A"),
            Node("B", 100, 0, "Node B"),
            Node("C", 100, 100, "Node C"),
            Node("D", 0, 100, "Node D"),
            Node("E", 200, 50, "Node E"),
        ]
        
        for node in nodes:
            self.graph.nodes[node.id] = node
            self.graph.adjacency[node.id] = []
        
        # Tạo edges (undirected)
        edges_data = [
            ("A", "B", 100),
            ("B", "C", 100),
            ("C", "D", 100),
            ("A", "D", 100),
            ("B", "E", 110),
            ("C", "E", 110),
        ]
        
        for src, dst, w in edges_data:
            self.graph.edges.append(Edge(src, dst, w))
            self.graph.adjacency[src].append((dst, w))
            self.graph.adjacency[dst].append((src, w))
    
    def test_graph_nodes(self):
        """Test số lượng node."""
        self.assertEqual(len(self.graph.nodes), 5)
    
    def test_graph_edges(self):
        """Test số lượng cạnh."""
        self.assertEqual(len(self.graph.edges), 6)
    
    def test_node_exists(self):
        """Test kiểm tra node tồn tại."""
        self.assertTrue(self.graph.node_exists("A"))
        self.assertFalse(self.graph.node_exists("Z"))
    
    def test_neighbors(self):
        """Test danh sách node kề."""
        neighbors = self.graph.get_neighbors("B")
        neighbor_ids = [n[0] for n in neighbors]
        self.assertIn("A", neighbor_ids)
        self.assertIn("C", neighbor_ids)
        self.assertIn("E", neighbor_ids)
    
    def test_edge_weight(self):
        """Test trọng số cạnh."""
        self.assertEqual(self.graph.get_edge_weight("A", "B"), 100)
        self.assertIsNone(self.graph.get_edge_weight("A", "E"))
    
    def test_path_cost(self):
        """Test tính chi phí đường đi."""
        cost = self.graph.calculate_path_cost(["A", "B", "C"])
        self.assertEqual(cost, 200)

    def test_load_preserves_empty_node_name(self):
        """Empty JSON name means the node label is intentionally hidden."""
        data = """
        {
          "nodes": [
            {"id": "N11", "x": 10, "y": 20, "name": ""}
          ],
          "edges": []
        }
        """
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as f:
            f.write(data)
            path = f.name
        try:
            graph = Graph()
            graph.load_from_json(path)
            self.assertEqual(graph.get_node("N11").name, "")
            self.assertEqual(graph.get_node_name("N11"), "N11")
        finally:
            os.remove(path)


def _run_algorithm_to_end(gen) -> Optional[dict]:
    """Chạy generator đến hết và trả về bước cuối cùng."""
    last_step: Optional[dict] = None
    for step in gen:
        last_step = step
    return last_step


class TestBFS(unittest.TestCase):
    """Test thuật toán BFS."""
    
    def setUp(self):
        self.graph = Graph()
        nodes = [
            Node("A", 0, 0), Node("B", 100, 0),
            Node("C", 200, 0), Node("D", 0, 100),
        ]
        for n in nodes:
            self.graph.nodes[n.id] = n
            self.graph.adjacency[n.id] = []
        
        edges = [("A", "B", 50), ("B", "C", 60), ("A", "D", 70)]
        for s, d, w in edges:
            self.graph.edges.append(Edge(s, d, w))
            self.graph.adjacency[s].append((d, w))
            self.graph.adjacency[d].append((s, w))
    
    def test_bfs_finds_path(self):
        """BFS tìm được đường đi A -> C."""
        result = _run_algorithm_to_end(bfs(self.graph, "A", "C"))
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("A", result["path"])
        self.assertIn("C", result["path"])
        self.assertTrue("✅" in result["log"])
    
    def test_bfs_same_node(self):
        """BFS với start == goal."""
        result = _run_algorithm_to_end(bfs(self.graph, "A", "A"))
        assert result is not None
        self.assertEqual(result["path"], ["A"])
    
    def test_bfs_no_path(self):
        """BFS khi không có đường đi."""
        # Thêm node cô lập
        self.graph.nodes["Z"] = Node("Z", 500, 500)
        self.graph.adjacency["Z"] = []
        
        result = _run_algorithm_to_end(bfs(self.graph, "A", "Z"))
        assert result is not None
        self.assertTrue("❌" in result["log"])


class TestDFS(unittest.TestCase):
    """Test thuật toán DFS."""
    
    def setUp(self):
        self.graph = Graph()
        nodes = [
            Node("A", 0, 0), Node("B", 100, 0),
            Node("C", 200, 0), Node("D", 0, 100),
        ]
        for n in nodes:
            self.graph.nodes[n.id] = n
            self.graph.adjacency[n.id] = []
        
        edges = [("A", "B", 50), ("B", "C", 60), ("A", "D", 70)]
        for s, d, w in edges:
            self.graph.edges.append(Edge(s, d, w))
            self.graph.adjacency[s].append((d, w))
            self.graph.adjacency[d].append((s, w))
    
    def test_dfs_finds_path(self):
        """DFS tìm được đường đi A -> C."""
        result = _run_algorithm_to_end(dfs(self.graph, "A", "C"))
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("C", result["path"])
        self.assertTrue("✅" in result["log"])
    
    def test_dfs_no_path(self):
        """DFS khi không có đường đi."""
        self.graph.nodes["Z"] = Node("Z", 500, 500)
        self.graph.adjacency["Z"] = []
        
        result = _run_algorithm_to_end(dfs(self.graph, "A", "Z"))
        assert result is not None
        self.assertTrue("❌" in result["log"])


class TestUCS(unittest.TestCase):
    """Test thuật toán UCS."""
    
    def setUp(self):
        self.graph = Graph()
        nodes = [
            Node("A", 0, 0), Node("B", 100, 0),
            Node("C", 200, 0), Node("D", 100, 100),
        ]
        for n in nodes:
            self.graph.nodes[n.id] = n
            self.graph.adjacency[n.id] = []
        
        # A->B->C (tổng: 150) vs A->D->C (tổng: 180)
        edges = [("A", "B", 50), ("B", "C", 100), ("A", "D", 80), ("D", "C", 100)]
        for s, d, w in edges:
            self.graph.edges.append(Edge(s, d, w))
            self.graph.adjacency[s].append((d, w))
            self.graph.adjacency[d].append((s, w))
    
    def test_ucs_optimal_path(self):
        """UCS tìm đường đi có chi phí nhỏ nhất."""
        result = _run_algorithm_to_end(ucs(self.graph, "A", "C"))
        assert result is not None
        self.assertEqual(result["path"], ["A", "B", "C"])
        self.assertAlmostEqual(result["cost"], 150)
    
    def test_ucs_finds_path(self):
        """UCS tìm được đường đi."""
        result = _run_algorithm_to_end(ucs(self.graph, "A", "C"))
        assert result is not None
        self.assertTrue("✅" in result["log"])


class TestGreedy(unittest.TestCase):
    """Test thuật toán Greedy."""
    
    def setUp(self):
        self.graph = Graph()
        nodes = [
            Node("A", 0, 0), Node("B", 50, 0),
            Node("C", 100, 0), Node("D", 50, 50),
        ]
        for n in nodes:
            self.graph.nodes[n.id] = n
            self.graph.adjacency[n.id] = []
        
        edges = [("A", "B", 50), ("B", "C", 50), ("A", "D", 70), ("D", "C", 70)]
        for s, d, w in edges:
            self.graph.edges.append(Edge(s, d, w))
            self.graph.adjacency[s].append((d, w))
            self.graph.adjacency[d].append((s, w))
    
    def test_greedy_finds_path(self):
        """Greedy tìm được đường đi."""
        result = _run_algorithm_to_end(
            greedy_search(self.graph, "A", "C", euclidean_distance))
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("C", result["path"])
        self.assertTrue("✅" in result["log"])


class TestAStar(unittest.TestCase):
    """Test thuật toán A*."""
    
    def setUp(self):
        self.graph = Graph()
        nodes = [
            Node("A", 0, 0), Node("B", 100, 0),
            Node("C", 200, 0), Node("D", 100, 100),
        ]
        for n in nodes:
            self.graph.nodes[n.id] = n
            self.graph.adjacency[n.id] = []
        
        # Đường tối ưu: A -> B -> C (tổng: 150)
        edges = [("A", "B", 50), ("B", "C", 100), ("A", "D", 80), ("D", "C", 100)]
        for s, d, w in edges:
            self.graph.edges.append(Edge(s, d, w))
            self.graph.adjacency[s].append((d, w))
            self.graph.adjacency[d].append((s, w))
    
    def test_astar_optimal(self):
        """A* tìm đường đi tối ưu với Euclidean heuristic."""
        result = _run_algorithm_to_end(
            astar(self.graph, "A", "C", euclidean_distance))
        assert result is not None
        self.assertEqual(result["path"], ["A", "B", "C"])
        self.assertAlmostEqual(result["cost"], 150)
    
    def test_astar_same_as_ucs(self):
        """A* cho kết quả chi phí giống UCS."""
        result_astar = _run_algorithm_to_end(
            astar(self.graph, "A", "C", euclidean_distance))
        result_ucs = _run_algorithm_to_end(
            ucs(self.graph, "A", "C"))
        
        # Chi phí phải bằng nhau
        assert result_astar is not None
        assert result_ucs is not None
        self.assertAlmostEqual(result_astar["cost"], result_ucs["cost"])
    
    def test_astar_no_path(self):
        """A* khi không có đường đi."""
        self.graph.nodes["Z"] = Node("Z", 999, 999)
        self.graph.adjacency["Z"] = []
        
        result = _run_algorithm_to_end(
            astar(self.graph, "A", "Z", euclidean_distance))
        assert result is not None
        self.assertTrue("❌" in result["log"])


class TestHeuristic(unittest.TestCase):
    """Test các hàm heuristic."""
    
    def test_euclidean(self):
        """Test Euclidean distance."""
        d = euclidean_distance((0, 0), (3, 4))
        self.assertAlmostEqual(d, 5.0)
    
    def test_manhattan(self):
        """Test Manhattan distance."""
        d = manhattan_distance((0, 0), (3, 4))
        self.assertEqual(d, 7)
    
    def test_same_point(self):
        """Khoảng cách đến chính mình = 0."""
        self.assertEqual(euclidean_distance((5, 5), (5, 5)), 0)
        self.assertEqual(manhattan_distance((5, 5), (5, 5)), 0)


class TestRealGraph(unittest.TestCase):
    """Test trên đồ thị HCMUTE thật."""
    
    def setUp(self):
        """Tải đồ thị thật từ file JSON."""
        self.graph = Graph()
        json_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "hcmute_graph_nodes_edges.json"
        )
        if os.path.exists(json_path):
            self.graph.load_from_json(json_path)
            self.has_data = True
        else:
            self.has_data = False
    
    def test_real_graph_loaded(self):
        """Đồ thị thật được tải thành công."""
        if not self.has_data:
            self.skipTest("File JSON không tồn tại")
        self.assertGreater(len(self.graph.nodes), 0)
        self.assertGreater(len(self.graph.edges), 0)
    
    def test_bfs_on_real_graph(self):
        """BFS chạy được trên đồ thị HCMUTE."""
        if not self.has_data:
            self.skipTest("File JSON không tồn tại")
        result = _run_algorithm_to_end(bfs(self.graph, "N91", "N05"))
        assert result is not None
        self.assertTrue("✅" in result["log"] or "❌" in result["log"])
    
    def test_astar_on_real_graph(self):
        """A* chạy được trên đồ thị HCMUTE."""
        if not self.has_data:
            self.skipTest("File JSON không tồn tại")
        result = _run_algorithm_to_end(
            astar(self.graph, "N91", "N05", euclidean_distance))
        assert result is not None
        self.assertTrue("✅" in result["log"] or "❌" in result["log"])
    
    def test_all_algorithms_find_same_cost(self):
        """UCS và A* tìm được cùng chi phí tối ưu."""
        if not self.has_data:
            self.skipTest("File JSON không tồn tại")
        
        result_ucs = _run_algorithm_to_end(ucs(self.graph, "N91", "N05"))
        result_astar = _run_algorithm_to_end(
            astar(self.graph, "N91", "N05", euclidean_distance))
        
        if result_ucs is not None and result_astar is not None and \
           "✅" in result_ucs["log"] and "✅" in result_astar["log"]:
            self.assertAlmostEqual(result_ucs["cost"], result_astar["cost"], places=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
