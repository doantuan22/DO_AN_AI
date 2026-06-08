"""
utils.py - Module chứa các hàm tiện ích
=========================================
Các hàm hỗ trợ: format log, format thời gian, tính khoảng cách, v.v.
"""

import time
from datetime import datetime
from typing import List, Optional


def format_time_ms(milliseconds: float) -> str:
    """
    Format thời gian xử lý ra dạng đọc được.
    
    Args:
        milliseconds: Thời gian tính bằng millisecond
        
    Returns:
        Chuỗi thời gian đã format (vd: "4.82 ms", "1.23 s")
    """
    if milliseconds < 1000:
        return f"{milliseconds:.2f} ms"
    else:
        return f"{milliseconds / 1000:.2f} s"


def format_distance(distance: float) -> str:
    """
    Format khoảng cách ra dạng đọc được.
    
    Args:
        distance: Khoảng cách tính bằng đơn vị pixel
        
    Returns:
        Chuỗi khoảng cách đã format (vd: "195.50 m")
    """
    return f"{distance:.1f} m"


def get_timestamp() -> str:
    """
    Lấy timestamp hiện tại dạng HH:MM:SS.
    
    Returns:
        Chuỗi thời gian hiện tại
    """
    return datetime.now().strftime("%H:%M:%S")


def format_path_log(path: List[str], node_names: dict, 
                     edge_weights: Optional[dict] = None) -> str:
    """
    Format đường đi thành chuỗi log chi tiết.
    
    Args:
        path: Danh sách node ID trên đường đi
        node_names: Dict mapping node_id -> tên hiển thị
        edge_weights: Hàm/dict lấy trọng số cạnh (optional)
        
    Returns:
        Chuỗi log mô tả đường đi
    """
    if not path:
        return "Không có đường đi."
    
    # Tạo chuỗi lộ trình
    route = " → ".join(node_names.get(nid, nid) for nid in path)
    return route


def format_path_details(path: List[str], node_names: dict,
                        get_weight_func) -> str:
    """
    Format chi tiết từng chặng của đường đi.
    
    Args:
        path: Danh sách node ID
        node_names: Dict mapping node_id -> tên
        get_weight_func: Hàm lấy trọng số cạnh (source, target) -> weight
        
    Returns:
        Chuỗi chi tiết các chặng
    """
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
    """
    Lớp đo thời gian thực thi thuật toán.
    
    Sử dụng:
        timer = Timer()
        timer.start()
        # ... thực thi thuật toán ...
        elapsed = timer.stop()  # milliseconds
    """
    
    def __init__(self):
        self._start_time: Optional[float] = None
        self._elapsed_ms: float = 0.0
    
    def start(self):
        """Bắt đầu đo thời gian."""
        self._start_time = time.perf_counter()
    
    def stop(self) -> float:
        """
        Dừng đo thời gian.
        
        Returns:
            Thời gian đã trôi qua (milliseconds)
        """
        if self._start_time is not None:
            self._elapsed_ms = (time.perf_counter() - self._start_time) * 1000
            self._start_time = None
        return self._elapsed_ms
    
    @property
    def elapsed_ms(self) -> float:
        """Thời gian đã đo (milliseconds)."""
        return self._elapsed_ms
