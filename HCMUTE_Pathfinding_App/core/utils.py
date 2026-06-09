"""Các hàm tiện ích format log, thời gian và đo runtime."""

import time
from datetime import datetime
from typing import List, Optional


def format_time_ms(milliseconds: float) -> str:
    """Format milliseconds thành ms hoặc giây."""
    if milliseconds < 1000:
        return f"{milliseconds:.2f} ms"
    else:
        return f"{milliseconds / 1000:.2f} s"


def format_distance(distance: float) -> str:
    """Format khoảng cách hiển thị trên UI."""
    return f"{distance:.1f} m"


def get_timestamp() -> str:
    """Lấy timestamp HH:MM:SS cho log."""
    return datetime.now().strftime("%H:%M:%S")


def format_path_log(path: List[str], node_names: dict, 
                     edge_weights: Optional[dict] = None) -> str:
    """Format path thành chuỗi route ngắn cho log."""
    if not path:
        return "Không có đường đi."
    
    route = " → ".join(node_names.get(nid, nid) for nid in path)
    return route


def format_path_details(path: List[str], node_names: dict,
                        get_weight_func) -> str:
    """Format từng chặng path kèm weight để đưa vào log."""
    if len(path) < 2:
        return ""
    
    details = []
    for i in range(len(path) - 1):
        src_name = node_names.get(path[i], path[i])
        dst_name = node_names.get(path[i + 1], path[i + 1])
        weight = get_weight_func(path[i], path[i + 1])
        if weight is not None:
            details.append(f"  {src_name} → {dst_name}: {weight:.1f} m")
        else:
            details.append(f"  {src_name} → {dst_name}: N/A")
    
    return "\n".join(details)


class Timer:
    """Đo thời gian chạy thuật toán bằng perf_counter."""
    
    def __init__(self):
        self._start_time: Optional[float] = None
        self._elapsed_ms: float = 0.0
    
    def start(self):
        """Bắt đầu đo thời gian."""
        self._start_time = time.perf_counter()
    
    def stop(self) -> float:
        """Dừng timer và trả về milliseconds."""
        if self._start_time is not None:
            self._elapsed_ms = (time.perf_counter() - self._start_time) * 1000
            self._start_time = None
        return self._elapsed_ms
    
    @property
    def elapsed_ms(self) -> float:
        """Thời gian đã đo gần nhất."""
        return self._elapsed_ms

    def elapsed_live(self) -> float:
        """Lấy thời gian đang chạy mà không dừng timer."""
        if self._start_time is not None:
            return (time.perf_counter() - self._start_time) * 1000
        return self._elapsed_ms
