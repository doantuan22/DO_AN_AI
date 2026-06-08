"""
heuristic.py - Module chứa các hàm heuristic
==============================================
Cung cấp các hàm ước lượng khoảng cách từ node hiện tại
đến node đích, phục vụ cho Greedy Search và A* Search.

Các hàm heuristic cần đảm bảo tính admissible (không bao giờ
ước lượng quá giá trị thực) để A* tìm được đường đi tối ưu.
"""

import math
from typing import Tuple


def euclidean_distance(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
    """
    Tính khoảng cách Euclidean giữa hai điểm.
    
    Công thức: d = sqrt((x2-x1)^2 + (y2-y1)^2)
    
    Đây là heuristic admissible vì khoảng cách đường thẳng luôn
    nhỏ hơn hoặc bằng khoảng cách thực tế trên đồ thị.
    
    Args:
        pos1: Tọa độ (x, y) của điểm thứ nhất
        pos2: Tọa độ (x, y) của điểm thứ hai
        
    Returns:
        Khoảng cách Euclidean
    """
    dx = pos1[0] - pos2[0]
    dy = pos1[1] - pos2[1]
    return math.sqrt(dx * dx + dy * dy)


def manhattan_distance(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
    """
    Tính khoảng cách Manhattan giữa hai điểm.
    
    Công thức: d = |x2-x1| + |y2-y1|
    
    Manhattan distance đo khoảng cách theo các trục tọa độ,
    phù hợp với các bản đồ dạng lưới.
    
    Lưu ý: Trên đồ thị tổng quát, Manhattan distance có thể
    không admissible nếu các cạnh đi theo đường chéo.
    
    Args:
        pos1: Tọa độ (x, y) của điểm thứ nhất
        pos2: Tọa độ (x, y) của điểm thứ hai
        
    Returns:
        Khoảng cách Manhattan
    """
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])


# Mapping tên heuristic -> hàm tương ứng
HEURISTIC_FUNCTIONS = {
    "Euclidean": euclidean_distance,
    "Manhattan": manhattan_distance,
}


def get_heuristic_function(name: str):
    """
    Lấy hàm heuristic theo tên.
    
    Args:
        name: Tên heuristic ("Euclidean" hoặc "Manhattan")
        
    Returns:
        Hàm heuristic tương ứng
        
    Raises:
        ValueError: Nếu tên heuristic không hợp lệ
    """
    func = HEURISTIC_FUNCTIONS.get(name)
    if func is None:
        available = ", ".join(HEURISTIC_FUNCTIONS.keys())
        raise ValueError(f"Heuristic '{name}' không hợp lệ. Các heuristic có sẵn: {available}")
    return func
