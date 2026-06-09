"""Mô hình đồ thị HCMUTE: node, cạnh, adjacency list và đọc/lưu JSON."""

import json
import os
import math
from typing import Dict, List, Tuple, Optional, Any


class Node:
    """Node trên bản đồ: ID, tọa độ pixel và tên hiển thị."""
    
    def __init__(self, node_id: str, x: int, y: int, name: str = ""):
        self.id = node_id
        self.x = x
        self.y = y
        self.name = name
    
    def position(self) -> Tuple[int, int]:
        """Trả về tọa độ pixel của node."""
        return (self.x, self.y)
    
    def __repr__(self) -> str:
        return f"Node({self.id}, pos=({self.x}, {self.y}), name='{self.name}')"
    
    def __eq__(self, other) -> bool:
        if isinstance(other, Node):
            return self.id == other.id
        return False
    
    def __hash__(self) -> int:
        return hash(self.id)


class Edge:
    """Cạnh nối hai node, weight là khoảng cách/chi phí."""
    
    def __init__(self, source: str, target: str, weight: float):
        self.source = source
        self.target = target
        self.weight = weight
    
    def __repr__(self) -> str:
        return f"Edge({self.source} -> {self.target}, w={self.weight})"


class Graph:
    """Đồ thị vô hướng lưu bằng danh sách kề để thuật toán truy vấn nhanh."""
    
    # Tên mặc định khi JSON chưa có field name.
    NODE_NAMES = {
        "N01": "Sân bóng chuyền",
        "N02": "Ký túc xá B",
        "N03": "Căn tin",
        "N04": "Ký túc xá",
        "N05": "Cổng phụ Lê Văn Chí",
        "N06": "Bãi xe SV (trên)",
        "N07": "Khối C",
        "N08": "Khối B",
        "N09": "Phòng Y tế",
        "N10": "VP Thư viện",
        "N11": "Khối C (dưới)",
        "N12": "",          # Giao lộ nội bộ
        "N13": "Khối B (dưới)",
        "N14": "Khối Thư viện",
        "N15": "P. Công tác HSSV",
        "N16": "Xưởng Khung gầm",
        "N17": "Xưởng Nhiệt ĐL",
        "N18": "Xưởng Cơ khí ĐL",
        "N19": "Khu thực hành",
        "N20": "",          # Giao lộ nội bộ
        "N21": "",          # Giao lộ nội bộ
        "N22": "Khối D",
        "N23": "",          # Giao lộ nội bộ
        "N24": "",          # Giao lộ nội bộ
        "N25": "",          # Giao lộ nội bộ
        "N26": "Khối A (trên)",
        "N27": "",          # Giao lộ nội bộ
        "N28": "",          # Giao lộ nội bộ
        "N30": "Khối F.1",
        "N31": "Khoa CN May",
        "N32": "Xưởng Động cơ",
        "N33": "Khối A",
        "N34": "Khối G (trên)",
        "N36": "Khối G",
        "N37": "Hội trường lớn",
        "N38": "Khối phòng học",
        "N39": "Nhà thi đấu",
        "N44": "Nhà thi đấu (dưới)",
        "N45": "Khối G (dưới)",
        "N46": "Khu thực hành XD",
        "N53": "Khối E.1",
        "N54": "Khối A.5",
        "N55": "Xưởng TT Hàn",
        "N56": "Xưởng bể",
        "N60": "Khối E.2",
        "N61": "Khối A.3",
        "N63": "Khối A.1",
        "N64": "Khối A.2",
        "N65": "Khối A.4",
        "N69": "Trạm điện",
        "N71": "Khối E.2 (dưới)",
        "N72": "Sân tennis",
        "N73": "Khối E.0",
        "N74": "Khối E.3",
        "N76": "Khối E.4",
        "N78": "Khoa CNTT-TT",
        "N79": "Sân bóng đá",
        "N81": "Khu xử lý nước",
        "N86": "Hồ nước",
        "N87": "Bãi xe giáo viên",
        "N88": "Bãi xe SV (dưới)",
        "N89": "Bãi xe SV (phải)",
        "N90": "Cổng phụ Võ Văn Ngân",
        "N91": "Cổng chính",
    }
    
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self.adjacency: Dict[str, List[Tuple[str, float]]] = {}
        self._image_width: int = 0
        self._image_height: int = 0
    
    @property
    def image_size(self) -> Tuple[int, int]:
        """Trả về kích thước ảnh bản đồ gốc."""
        return (self._image_width, self._image_height)
    
    def load_from_json(self, filepath: str) -> bool:
        """Đọc JSON, tạo node/edge và adjacency list cho đồ thị."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Không tìm thấy file dữ liệu: {filepath}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"File JSON không hợp lệ: {e}")
        
        self.nodes.clear()
        self.edges.clear()
        self.adjacency.clear()
        self._image_width = 0
        self._image_height = 0
        
        # Lưu kích thước ảnh để editor giới hạn tọa độ.
        if "image_size" in data:
            self._image_width = data["image_size"].get("width", 0)
            self._image_height = data["image_size"].get("height", 0)
        
        nodes_data = data.get("nodes", [])
        for node_data in nodes_data:
            node_id = node_data.get("id", "")
            x = node_data.get("x", 0)
            y = node_data.get("y", 0)
            # name="" là người dùng chủ động ẩn tên, không fallback.
            if "name" in node_data:
                name = str(node_data.get("name", ""))
            else:
                name = self.NODE_NAMES.get(node_id, "")
            
            node = Node(node_id, x, y, name)
            self.nodes[node_id] = node
            self.adjacency[node_id] = []
        
        edges_data = data.get("edges", [])
        for edge_data in edges_data:
            # Hỗ trợ cả format from/to và source/target.
            source = edge_data.get("from", edge_data.get("source", ""))
            target = edge_data.get("to", edge_data.get("target", ""))
            weight = edge_data.get("weight", 1.0)
            
            if source and target and source in self.nodes and target in self.nodes:
                edge = Edge(source, target, weight)
                self.edges.append(edge)
                
                # Đồ thị vô hướng nên adjacency lưu cả hai chiều.
                self.adjacency[source].append((target, weight))
                self.adjacency[target].append((source, weight))
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đồ thị hiện tại thành dict để lưu JSON."""
        nodes = []
        for node_id in self.get_all_node_ids():
            node = self.nodes[node_id]
            node_data: Dict[str, Any] = {
                "id": node.id,
                "x": int(node.x),
                "y": int(node.y),
            }
            if node.name != node.id:
                node_data["name"] = node.name
            nodes.append(node_data)
        
        return {
            "coordinate_system": "pixel coordinates, origin at top-left of image, x right, y down",
            "image_size": {
                "width": self._image_width,
                "height": self._image_height,
            },
            "weight_unit": "pixels (Euclidean distance between node centers)",
            "nodes": nodes,
            "edges": [
                {"from": edge.source, "to": edge.target, "weight": round(edge.weight, 2)}
                for edge in self.edges
            ],
        }
    
    def save_to_json(self, filepath: str) -> bool:
        """Ghi đồ thị hiện tại ra file JSON."""
        directory = os.path.dirname(filepath)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        return True
    
    def add_node(self, node_id: str, x: int, y: int, name: str = "") -> Node:
        """Thêm node mới vào đồ thị."""
        node_id = node_id.strip()
        if not node_id:
            raise ValueError("Node ID không được để trống")
        if node_id in self.nodes:
            raise ValueError(f"Node '{node_id}' đã tồn tại")
        
        node = Node(node_id, int(x), int(y), name.strip())
        self.nodes[node_id] = node
        self.adjacency[node_id] = []
        return node
    
    def update_node(self, node_id: str, x: int, y: int, name: str = "") -> Node:
        """Cập nhật tọa độ và tên node."""
        node = self.nodes.get(node_id)
        if node is None:
            raise ValueError(f"Node '{node_id}' không tồn tại")
        
        node.x = int(x)
        node.y = int(y)
        node.name = name.strip()
        return node
    
    def delete_node(self, node_id: str) -> None:
        """Xóa node cùng toàn bộ cạnh liên quan."""
        if node_id not in self.nodes:
            raise ValueError(f"Node '{node_id}' không tồn tại")
        
        for neighbor, _ in list(self.adjacency.get(node_id, [])):
            self._remove_adjacency_link(neighbor, node_id)
        self.adjacency.pop(node_id, None)
        self.nodes.pop(node_id, None)
        self.edges = [
            edge for edge in self.edges
            if edge.source != node_id and edge.target != node_id
        ]
    
    def add_edge(self, source: str, target: str, weight: Optional[float] = None) -> Edge:
        """Thêm cạnh vô hướng; tự tính weight nếu không truyền vào."""
        if source not in self.nodes or target not in self.nodes:
            raise ValueError("Hai node của cạnh phải tồn tại")
        if source == target:
            raise ValueError("Không thể tạo cạnh tự nối chính nó")
        if self.edge_exists(source, target):
            raise ValueError(f"Cạnh {source} - {target} đã tồn tại")
        
        if weight is None:
            weight = self.calculate_euclidean_weight(source, target)
        edge = Edge(source, target, float(weight))
        self.edges.append(edge)
        self.adjacency[source].append((target, float(weight)))
        self.adjacency[target].append((source, float(weight)))
        return edge
    
    def update_edge(self, source: str, target: str, weight: float) -> Edge:
        """Cập nhật trọng số cạnh đã có."""
        edge = self._find_edge(source, target)
        if edge is None:
            raise ValueError(f"Cạnh {source} - {target} không tồn tại")
        
        edge.weight = float(weight)
        self._set_adjacency_weight(source, target, float(weight))
        self._set_adjacency_weight(target, source, float(weight))
        return edge
    
    def delete_edge(self, source: str, target: str) -> None:
        """Xóa cạnh vô hướng giữa hai node."""
        before = len(self.edges)
        self.edges = [
            edge for edge in self.edges
            if not self._edge_matches(edge, source, target)
        ]
        if len(self.edges) == before:
            raise ValueError(f"Cạnh {source} - {target} không tồn tại")
        self._remove_adjacency_link(source, target)
        self._remove_adjacency_link(target, source)
    
    def edge_exists(self, source: str, target: str) -> bool:
        """Kiểm tra cạnh vô hướng có tồn tại không."""
        return self._find_edge(source, target) is not None
    
    def calculate_euclidean_weight(self, source: str, target: str) -> float:
        """Tính weight theo khoảng cách Euclidean giữa hai node."""
        src = self.nodes.get(source)
        dst = self.nodes.get(target)
        if src is None or dst is None:
            raise ValueError("Hai node của cạnh phải tồn tại")
        return math.sqrt((src.x - dst.x) ** 2 + (src.y - dst.y) ** 2)
    
    def _find_edge(self, source: str, target: str) -> Optional[Edge]:
        for edge in self.edges:
            if self._edge_matches(edge, source, target):
                return edge
        return None
    
    @staticmethod
    def _edge_matches(edge: Edge, source: str, target: str) -> bool:
        return (
            (edge.source == source and edge.target == target)
            or (edge.source == target and edge.target == source)
        )
    
    def _remove_adjacency_link(self, source: str, target: str) -> None:
        self.adjacency[source] = [
            (neighbor, weight)
            for neighbor, weight in self.adjacency.get(source, [])
            if neighbor != target
        ]
    
    def _set_adjacency_weight(self, source: str, target: str, weight: float) -> None:
        self.adjacency[source] = [
            (neighbor, weight if neighbor == target else old_weight)
            for neighbor, old_weight in self.adjacency.get(source, [])
        ]
    
    def get_node(self, node_id: str) -> Optional[Node]:
        """Lấy node theo ID."""
        return self.nodes.get(node_id)
    
    def get_neighbors(self, node_id: str) -> List[Tuple[str, float]]:
        """Lấy danh sách (neighbor_id, weight) của node."""
        return self.adjacency.get(node_id, [])
    
    def get_edge_weight(self, source: str, target: str) -> Optional[float]:
        """Lấy weight giữa hai node, None nếu không có cạnh."""
        for neighbor, weight in self.adjacency.get(source, []):
            if neighbor == target:
                return weight
        return None
    
    def get_all_node_ids(self) -> List[str]:
        """Lấy danh sách ID node đã sắp xếp."""
        return sorted(self.nodes.keys())
    
    def get_node_name(self, node_id: str) -> str:
        """Lấy tên node; nếu rỗng thì fallback về ID."""
        node = self.nodes.get(node_id)
        if node is None:
            return node_id
        return node.name if node.name else node_id
    
    def get_node_position(self, node_id: str) -> Optional[Tuple[int, int]]:
        """Lấy tọa độ node theo ID."""
        node = self.nodes.get(node_id)
        return node.position() if node else None
    
    def calculate_path_cost(self, path: List[str]) -> float:
        """Tính tổng weight của các cạnh trong path."""
        if len(path) < 2:
            return 0.0
        
        total_cost = 0.0
        for i in range(len(path) - 1):
            weight = self.get_edge_weight(path[i], path[i + 1])
            if weight is not None:
                total_cost += weight
            else:
                # Path không hợp lệ nếu thiếu cạnh giữa hai node liên tiếp.
                return float('inf')
        return total_cost
    
    def node_exists(self, node_id: str) -> bool:
        """Kiểm tra node có trong đồ thị không."""
        return node_id in self.nodes
    
    def __len__(self) -> int:
        """Số lượng node trong đồ thị."""
        return len(self.nodes)
    
    def __repr__(self) -> str:
        return f"Graph(nodes={len(self.nodes)}, edges={len(self.edges)})"
