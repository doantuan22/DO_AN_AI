# Hàm heuristic cho Greedy và A* (Euclidean, Manhattan)

import math
from typing import Tuple


# Khoảng cách đường thẳng giữa 2 điểm
def euclidean_distance(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
    dx = pos1[0] - pos2[0]
    dy = pos1[1] - pos2[1]
    return math.sqrt(dx * dx + dy * dy)


# Khoảng cách theo trục x/y 
def manhattan_distance(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])


# Mapping tên hiển thị -> hàm heuristic
HEURISTIC_FUNCTIONS = {
    "Euclidean": euclidean_distance,
    "Manhattan": manhattan_distance,
}


# Lấy hàm heuristic theo tên từ UI
def get_heuristic_function(name: str):
    func = HEURISTIC_FUNCTIONS.get(name)
    if func is None:
        available = ", ".join(HEURISTIC_FUNCTIONS.keys())
        raise ValueError(f"Heuristic '{name}' không hợp lệ. Các heuristic có sẵn: {available}")
    return func
