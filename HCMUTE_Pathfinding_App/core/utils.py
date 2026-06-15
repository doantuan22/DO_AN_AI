# Hàm tiện ích: format log, thời gian, đo runtime
# Dùng chung cho cả UI và thuật toán

import time
from datetime import datetime
from typing import List, Optional


# Format milliseconds thành dạng đọc được
def format_time_ms(milliseconds: float) -> str:
    if milliseconds < 1000:
        return f"{milliseconds:.2f} ms"
    else:
        return f"{milliseconds / 1000:.2f} s"


# Format khoảng cách hiển thị trên UI
def format_distance(distance: float) -> str:
    return f"{distance:.1f} m"


# Lấy timestamp HH:MM:SS cho log
def get_timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


# Format path thành chuỗi route ngắn
def format_path_log(path: List[str], node_names: dict, 
                     edge_weights: Optional[dict] = None) -> str:
    if not path:
        return "Không có đường đi."
    
    route = " → ".join(node_names.get(nid, nid) for nid in path)
    return route


# Format từng chặng path kèm weight chi tiết
def format_path_details(path: List[str], node_names: dict,
                        get_weight_func) -> str:
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


# Đo thời gian chạy thuật toán bằng perf_counter 
class Timer:
    
    def __init__(self):
        self._start_time: Optional[float] = None
        self._elapsed_ms: float = 0.0
    
    # Bắt đầu đo
    def start(self):
        self._start_time = time.perf_counter()
    
    # Dừng timer, trả về ms
    def stop(self) -> float:
        if self._start_time is not None:
            self._elapsed_ms = (time.perf_counter() - self._start_time) * 1000
            self._start_time = None
        return self._elapsed_ms
    
    @property
    def elapsed_ms(self) -> float:
        return self._elapsed_ms

    # Lấy thời gian đang chạy mà không dừng timer
    def elapsed_live(self) -> float:
        if self._start_time is not None:
            return (time.perf_counter() - self._start_time) * 1000
        return self._elapsed_ms
