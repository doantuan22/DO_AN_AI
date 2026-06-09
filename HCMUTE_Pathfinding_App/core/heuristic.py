"""Các hàm heuristic dùng cho Greedy và A*."""

import math
from typing import Tuple


def euclidean_distance(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
    """Khoảng cách đường thẳng, thường admissible cho bản đồ thực."""
    dx = pos1[0] - pos2[0]
    dy = pos1[1] - pos2[1]
    return math.sqrt(dx * dx + dy * dy)


def manhattan_distance(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
    """Khoảng cách theo trục x/y, phù hợp bản đồ dạng lưới."""
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])


HEURISTIC_FUNCTIONS = {
    "Euclidean": euclidean_distance,
    "Manhattan": manhattan_distance,
}


def get_heuristic_function(name: str):
    """Lấy hàm heuristic theo tên hiển thị trên UI."""
    func = HEURISTIC_FUNCTIONS.get(name)
    if func is None:
        available = ", ".join(HEURISTIC_FUNCTIONS.keys())
        raise ValueError(f"Heuristic '{name}' không hợp lệ. Các heuristic có sẵn: {available}")
    return func
