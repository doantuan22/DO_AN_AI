# Mô hình đồ thị HCMUTE: node, cạnh, adjacency list
# Hỗ trợ đọc/lưu JSON và các thao tác CRUD trên đồ thị

import json
import os
import math
from typing import Dict, List, Tuple, Optional, Any


# Node trên bản đồ: ID, tọa độ pixel, tên hiển thị
class Node:
    
    def __init__(self, node_id: str, x: int, y: int, name: str = ""):
        self.id = node_id
        self.x = x
        self.y = y
        self.name = name
    
    # Trả về tọa độ pixel (x, y)
    def position(self) -> Tuple[int, int]:
        return (self.x, self.y)
    
    def __repr__(self) -> str:
        return f"Node({self.id}, pos=({self.x}, {self.y}), name='{self.name}')"
    
    def __eq__(self, other) -> bool:
        if isinstance(other, Node):
            return self.id == other.id
        return False
    
    def __hash__(self) -> int:
        return hash(self.id)


# Cạnh nối hai node, weight là khoảng cách/chi phí
class Edge:
    
    def __init__(self, source: str, target: str, weight: float):
        self.source = source
        self.target = target
        self.weight = weight
    
    def __repr__(self) -> str:
        return f"Edge({self.source} -> {self.target}, w={self.weight})"


# Đồ thị vô hướng lưu bằng danh sách kề
class Graph:
    
    # Tên mặc định khi JSON chưa có field name
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
        "N12": "",
        "N13": "Khối B (dưới)",
        "N14": "Khối Thư viện",
        "N15": "P. Công tác HSSV",
        "N16": "Xưởng Khung gầm",
        "N17": "Xưởng Nhiệt ĐL",
        "N18": "Xưởng Cơ khí ĐL",
        "N19": "Khu thực hành",
        "N20": "",
        "N21": "",
        "N22": "Khối D",
        "N23": "",
        "N24": "",
        "N25": "",
        "N26": "Khối A (trên)",
        "N27": "",
        "N28": "",
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
        # Danh sách kề: {node_id -> [(neighbor_id, weight), ...]}
        self.adjacency: Dict[str, List[Tuple[str, float]]] = {}
        self._image_width: int = 0
        self._image_height: int = 0
    
    @property
    def image_size(self) -> Tuple[int, int]:
        return (self._image_width, self._image_height)
    
    # Đọc JSON, tạo node/edge và adjacency list
    def load_from_json(self, filepath: str) -> bool:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Không tìm thấy file dữ liệu: {filepath}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"File JSON không hợp lệ: {e}")

        if not isinstance(data, dict):
            raise ValueError("Dữ liệu đồ thị phải là một JSON object")

        image_size = data.get("image_size", {})
        if not isinstance(image_size, dict):
            raise ValueError("image_size phải là một JSON object")
        try:
            image_width = max(0, int(image_size.get("width", 0)))
            image_height = max(0, int(image_size.get("height", 0)))
        except (TypeError, ValueError) as exc:
            raise ValueError("Kích thước ảnh phải là số nguyên") from exc

        new_nodes: Dict[str, Node] = {}
        new_edges: List[Edge] = []
        new_adjacency: Dict[str, List[Tuple[str, float]]] = {}

        nodes_data = data.get("nodes", [])
        if not isinstance(nodes_data, list):
            raise ValueError("nodes phải là một danh sách")
        for node_data in nodes_data:
            if not isinstance(node_data, dict):
                raise ValueError("Mỗi node phải là một JSON object")
            node_id = str(node_data.get("id", "")).strip()
            if not node_id:
                raise ValueError("Node ID không được để trống")
            if node_id in new_nodes:
                raise ValueError(f"Node '{node_id}' bị trùng trong file JSON")
            try:
                x = int(node_data.get("x", 0))
                y = int(node_data.get("y", 0))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Tọa độ của node '{node_id}' không hợp lệ") from exc
            # name="" nghĩa là người dùng chủ động ẩn tên
            if "name" in node_data:
                name = str(node_data.get("name", ""))
            else:
                name = self.NODE_NAMES.get(node_id, "")

            node = Node(node_id, x, y, name)
            new_nodes[node_id] = node
            new_adjacency[node_id] = []

        edges_data = data.get("edges", [])
        if not isinstance(edges_data, list):
            raise ValueError("edges phải là một danh sách")
        seen_edges = set()
        for edge_data in edges_data:
            if not isinstance(edge_data, dict):
                raise ValueError("Mỗi cạnh phải là một JSON object")
            # Hỗ trợ cả format from/to và source/target
            source = str(edge_data.get("from", edge_data.get("source", ""))).strip()
            target = str(edge_data.get("to", edge_data.get("target", ""))).strip()
            if source not in new_nodes or target not in new_nodes:
                raise ValueError(f"Cạnh {source} - {target} tham chiếu node không tồn tại")
            if source == target:
                raise ValueError(f"Cạnh {source} - {target} không được tự nối")
            edge_key = frozenset((source, target))
            if edge_key in seen_edges:
                raise ValueError(f"Cạnh {source} - {target} bị trùng trong file JSON")
            seen_edges.add(edge_key)
            weight = self._validate_weight(edge_data.get("weight", 1.0))
            edge = Edge(source, target, weight)
            new_edges.append(edge)
            new_adjacency[source].append((target, weight))
            new_adjacency[target].append((source, weight))

        self.nodes = new_nodes
        self.edges = new_edges
        self.adjacency = new_adjacency
        self._image_width = image_width
        self._image_height = image_height
        return True

    def load_from_dict(self, data: Dict[str, Any]) -> bool:
        if not isinstance(data, dict):
            raise ValueError("Dữ liệu đồ thị phải là một JSON object")

        image_size = data.get("image_size", {})
        if not isinstance(image_size, dict):
            image_size = {}
        try:
            image_width = max(0, int(image_size.get("width", 0)))
            image_height = max(0, int(image_size.get("height", 0)))
        except (TypeError, ValueError) as exc:
            raise ValueError("Kích thước ảnh phải là số nguyên") from exc

        new_nodes: Dict[str, Node] = {}
        new_edges: List[Edge] = []
        new_adjacency: Dict[str, List[Tuple[str, float]]] = {}

        nodes_data = data.get("nodes", [])
        if not isinstance(nodes_data, list):
            raise ValueError("nodes phải là một danh sách")
        for node_data in nodes_data:
            if not isinstance(node_data, dict):
                raise ValueError("Mỗi node phải là một JSON object")
            node_id = str(node_data.get("id", "")).strip()
            if not node_id:
                raise ValueError("Node ID không được để trống")
            if node_id in new_nodes:
                raise ValueError(f"Node '{node_id}' bị trùng trong dữ liệu")
            try:
                x = int(node_data.get("x", 0))
                y = int(node_data.get("y", 0))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Tọa độ của node '{node_id}' không hợp lệ") from exc
            if "name" in node_data:
                name = str(node_data.get("name", ""))
            else:
                name = self.NODE_NAMES.get(node_id, "")

            node = Node(node_id, x, y, name)
            new_nodes[node_id] = node
            new_adjacency[node_id] = []

        edges_data = data.get("edges", [])
        if not isinstance(edges_data, list):
            raise ValueError("edges phải là một danh sách")
        seen_edges = set()
        for edge_data in edges_data:
            if not isinstance(edge_data, dict):
                raise ValueError("Mỗi cạnh phải là một JSON object")
            source = str(edge_data.get("from", edge_data.get("source", ""))).strip()
            target = str(edge_data.get("to", edge_data.get("target", ""))).strip()
            if source not in new_nodes or target not in new_nodes:
                raise ValueError(f"Cạnh {source} - {target} tham chiếu node không tồn tại")
            if source == target:
                raise ValueError(f"Cạnh {source} - {target} không được tự nối")
            edge_key = frozenset((source, target))
            if edge_key in seen_edges:
                raise ValueError(f"Cạnh {source} - {target} bị trùng trong dữ liệu")
            seen_edges.add(edge_key)
            weight = self._validate_weight(edge_data.get("weight", 1.0))
            edge = Edge(source, target, weight)
            new_edges.append(edge)
            new_adjacency[source].append((target, weight))
            new_adjacency[target].append((source, weight))

        self.nodes = new_nodes
        self.edges = new_edges
        self.adjacency = new_adjacency
        self._image_width = image_width
        self._image_height = image_height
        return True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Graph":
        graph = cls()
        graph.load_from_dict(data)
        return graph
    
    # Chuyển đồ thị thành dict để lưu JSON
    def to_dict(self) -> Dict[str, Any]:
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
    
    # Ghi đồ thị ra file JSON
    def save_to_json(self, filepath: str) -> bool:
        directory = os.path.dirname(filepath)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        return True
    
    # Thêm node mới vào đồ thị
    def add_node(self, node_id: str, x: int, y: int, name: str = "") -> Node:
        node_id = node_id.strip()
        if not node_id:
            raise ValueError("Node ID không được để trống")
        if node_id in self.nodes:
            raise ValueError(f"Node '{node_id}' đã tồn tại")
        
        node = Node(node_id, int(x), int(y), name.strip())
        self.nodes[node_id] = node
        self.adjacency[node_id] = []
        return node
    
    # Cập nhật tọa độ và tên node
    def update_node(self, node_id: str, x: int, y: int, name: str = "") -> Node:
        node = self.nodes.get(node_id)
        if node is None:
            raise ValueError(f"Node '{node_id}' không tồn tại")
        
        node.x = int(x)
        node.y = int(y)
        node.name = name.strip()
        return node
    
    # Xóa node cùng toàn bộ cạnh liên quan
    def delete_node(self, node_id: str) -> None:
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
    
    # Thêm cạnh vô hướng, tự tính weight nếu không truyền
    def add_edge(self, source: str, target: str, weight: Optional[float] = None) -> Edge:
        if source not in self.nodes or target not in self.nodes:
            raise ValueError("Hai node của cạnh phải tồn tại")
        if source == target:
            raise ValueError("Không thể tạo cạnh tự nối chính nó")
        if self.edge_exists(source, target):
            raise ValueError(f"Cạnh {source} - {target} đã tồn tại")
        
        if weight is None:
            weight = self.calculate_euclidean_weight(source, target)
        weight = self._validate_weight(weight)
        edge = Edge(source, target, weight)
        self.edges.append(edge)
        self.adjacency[source].append((target, weight))
        self.adjacency[target].append((source, weight))
        return edge
    
    # Cập nhật trọng số cạnh
    def update_edge(self, source: str, target: str, weight: float) -> Edge:
        edge = self._find_edge(source, target)
        if edge is None:
            raise ValueError(f"Cạnh {source} - {target} không tồn tại")
        
        weight = self._validate_weight(weight)
        edge.weight = weight
        self._set_adjacency_weight(source, target, weight)
        self._set_adjacency_weight(target, source, weight)
        return edge
    
    # Xóa cạnh vô hướng giữa hai node
    def delete_edge(self, source: str, target: str) -> None:
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
        return self._find_edge(source, target) is not None
    
    # Tính weight = khoảng cách Euclidean giữa 2 node
    def calculate_euclidean_weight(self, source: str, target: str) -> float:
        src = self.nodes.get(source)
        dst = self.nodes.get(target)
        if src is None or dst is None:
            raise ValueError("Hai node của cạnh phải tồn tại")
        return math.sqrt((src.x - dst.x) ** 2 + (src.y - dst.y) ** 2)

    @staticmethod
    def _validate_weight(weight: Any) -> float:
        try:
            value = float(weight)
        except (TypeError, ValueError) as exc:
            raise ValueError("Trọng số cạnh phải là một số") from exc
        if not math.isfinite(value) or value <= 0:

            
            raise ValueError("Trọng số cạnh phải là số hữu hạn lớn hơn 0")
        return value
    
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
        return self.nodes.get(node_id)
    
    # Lấy danh sách (neighbor_id, weight) của node
    def get_neighbors(self, node_id: str) -> List[Tuple[str, float]]:
        return self.adjacency.get(node_id, [])
    
    def get_edge_weight(self, source: str, target: str) -> Optional[float]:
        for neighbor, weight in self.adjacency.get(source, []):
            if neighbor == target:
                return weight
        return None
    
    def get_all_node_ids(self) -> List[str]:
        return sorted(self.nodes.keys())
    
    # Lấy tên node, fallback về ID nếu rỗng
    def get_node_name(self, node_id: str) -> str:
        node = self.nodes.get(node_id)
        if node is None:
            return node_id
        return node.name if node.name else node_id
    
    def get_node_position(self, node_id: str) -> Optional[Tuple[int, int]]:
        node = self.nodes.get(node_id)
        return node.position() if node else None
    
    # Tính tổng weight của đường đi
    def calculate_path_cost(self, path: List[str]) -> float:
        if len(path) < 2:
            return 0.0
        
        total_cost = 0.0
        for i in range(len(path) - 1):
            weight = self.get_edge_weight(path[i], path[i + 1])
            if weight is not None:
                total_cost += weight
            else:
                return float('inf')
        return total_cost
    
    def node_exists(self, node_id: str) -> bool:
        return node_id in self.nodes
    
    def __len__(self) -> int:
        return len(self.nodes)
    
    def __repr__(self) -> str:
        return f"Graph(nodes={len(self.nodes)}, edges={len(self.edges)})"
