"""
main_window.py - Cửa sổ chính của ứng dụng (Redesigned matching UI_demo)
========================================================================
Ghép các thành phần giao diện (MapWidget + ControlPanel),
quản lý luồng hoạt động chính: chọn node, chạy thuật toán,
mô phỏng từng bước, hiển thị kết quả.
"""

import os
import sys
import time
from typing import Optional, Generator

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QMessageBox, QApplication, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QIcon

from core.graph import Graph
from core.algorithms import get_algorithm, needs_heuristic, ALGORITHM_MAP
from core.heuristic import get_heuristic_function
from core.utils import Timer, get_timestamp
from ui.map_widget import MapWidget
from ui.control_panel import ControlPanel
from ui.graph_editor_dialog import GraphEditorDialog


# ──────────────────────────────────────────────────────────────
# Stylesheet cho MainWindow - Phong cách Google Maps tối giản hiện đại
# ──────────────────────────────────────────────────────────────

MAIN_WINDOW_STYLE = """
    QMainWindow {
        background-color: #F7FAFF;
    }
    
    QWidget#appRoot {
        background-color: #F7FAFF;
    }
    
    QFrame#sideRail {
        background-color: #FFFFFF;
        border-right: 1px solid #E6EDF7;
    }
    QLabel#railLogo {
        background-color: #1473E6;
        color: white;
        font-family: 'Segoe UI';
        font-size: 16px;
        font-weight: 800;
        border-radius: 14px;
    }
    
    /* Header */
    QFrame#header {
        background-color: #FFFFFF;
        border-bottom: 1px solid #E6EDF7;
        min-height: 64px;
        max-height: 64px;
    }
    QLabel#headerTitle {
        color: #0B63E5;
        font-family: 'Segoe UI';
        font-size: 24px;
        font-weight: 800;
    }
    QLabel#headerMenuBtn {
        color: #0B63E5;
        font-family: 'Segoe UI';
        font-size: 24px;
        font-weight: 700;
        padding-left: 2px;
        padding-right: 8px;
    }
    QLabel#headerStatus {
        color: #15346F;
        font-family: 'Segoe UI';
        font-size: 13px;
        padding-right: 18px;
    }
"""


class MainWindow(QMainWindow):
    """
    Cửa sổ chính của ứng dụng Tìm đường HCMUTE.
    Giao diện Header màu trắng nhẹ nhàng, đồng nhất với Bản đồ & Control Panel.
    """
    
    def __init__(self):
        super().__init__()
        
        # ── Xác định đường dẫn gốc của project ──
        if getattr(sys, 'frozen', False):
            self._base_dir = os.path.dirname(sys.executable)
        else:
            self._base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._json_path = os.path.join(self._base_dir, "data", "hcmute_graph_nodes_edges.json")
        self._map_path = os.path.join(self._base_dir, "assets", "map.png")
        
        # ── Khởi tạo dữ liệu ──
        self._graph = Graph()
        self._timer = QTimer()
        self._timer.timeout.connect(self._execute_step)
        
        self._algorithm_gen: Optional[Generator] = None
        self._is_running = False
        self._is_paused = False
        self._exec_timer = Timer()
        
        self._start_node: Optional[str] = None
        self._goal_node: Optional[str] = None
        self._click_count = 0  # Đếm click để chọn start/goal
        
        self._step_delay = 400  # ms giữa các bước mô phỏng
        self._total_visited = 0
        self._final_path = []
        self._final_cost = 0.0
        
        # ── Xây dựng giao diện ──
        self._setup_window()
        self._setup_ui()
        self._connect_signals()
        
        # ── Tải dữ liệu ──
        self._load_data()
    
    def _setup_window(self):
        """Cấu hình cửa sổ chính."""
        self.setWindowTitle("Hệ thống dẫn đường trong khuôn viên HCMUTE")
        self.setMinimumSize(1280, 780)
        self.resize(1480, 860)
        self.setStyleSheet(MAIN_WINDOW_STYLE)
        
        # Căn giữa màn hình
        screen = QApplication.primaryScreen()
        if screen:
            screen_rect = screen.availableGeometry()
            x = (screen_rect.width() - self.width()) // 2
            y = (screen_rect.height() - self.height()) // 2
            self.move(x, y)
    
    def _setup_ui(self):
        """Xây dựng layout giao diện chính."""
        central = QWidget()
        central.setObjectName("appRoot")
        self.setCentralWidget(central)
        
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        
        # ── Rail trái giống UI demo ──
        side_rail = QFrame()
        side_rail.setObjectName("sideRail")
        side_rail.setFixedWidth(82)
        side_layout = QVBoxLayout(side_rail)
        side_layout.setContentsMargins(14, 20, 14, 14)
        side_layout.setSpacing(0)
        
        rail_logo = QLabel("KTL")
        rail_logo.setObjectName("railLogo")
        rail_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rail_logo.setFixedSize(54, 54)
        side_layout.addWidget(rail_logo, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        side_layout.addStretch()
        root_layout.addWidget(side_rail)
        
        app_area = QWidget()
        app_layout = QVBoxLayout(app_area)
        app_layout.setContentsMargins(0, 0, 0, 0)
        app_layout.setSpacing(0)
        root_layout.addWidget(app_area, 1)
        
        # ── Header ──
        header = QFrame()
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 14, 0)
        header_layout.setSpacing(12)
        
        menu_btn = QLabel("☰")
        menu_btn.setObjectName("headerMenuBtn")
        
        title_label = QLabel("Hệ thống dẫn đường")
        title_label.setObjectName("headerTitle")
        
        self._status_label = QLabel()
        self._status_label.setObjectName("headerStatus")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._update_status("Sẵn sàng", "#34A853")
        
        header_layout.addWidget(menu_btn)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self._status_label)
        
        app_layout.addWidget(header)
        
        # ── Body: Map + Control Panel ──
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(18, 16, 18, 18)
        body_layout.setSpacing(16)
        
        self._map_widget = MapWidget()
        body_layout.addWidget(self._map_widget, 1)
        
        self._control_panel = ControlPanel()
        body_layout.addWidget(self._control_panel)
        
        app_layout.addWidget(body, 1)
    
    def _connect_signals(self):
        """Kết nối các signal/slot điều khiển."""
        # Click chọn trên bản đồ
        self._map_widget.node_clicked.connect(self._on_node_clicked)
        
        # Nút điều khiển Panel
        self._control_panel.start_clicked.connect(self._on_start)
        self._control_panel.pause_clicked.connect(self._on_pause)
        self._control_panel.resume_clicked.connect(self._on_resume)
        self._control_panel.stop_clicked.connect(self._on_stop)
        self._control_panel.reset_clicked.connect(self._on_reset)
        self._control_panel.graph_edit_clicked.connect(self._on_edit_graph)
        
        # Combo box chọn địa điểm
        self._control_panel.start_combo.currentIndexChanged.connect(
            self._on_start_combo_changed)
        self._control_panel.goal_combo.currentIndexChanged.connect(
            self._on_goal_combo_changed)
    
    def _load_data(self):
        """Tải dữ liệu đồ thị JSON và ảnh nền bản đồ."""
        try:
            # Tải đồ thị
            self._graph.load_from_json(self._json_path)
            self._control_panel.add_log("✅ Khởi tạo đồ thị HCMUTE thành công")
            self._control_panel.add_log(
                f"   📊 {len(self._graph.nodes)} node, {len(self._graph.edges)} cạnh")
            
            # Thiết lập bản đồ
            self._map_widget.setup_map(self._graph, self._map_path)
            self._control_panel.add_log("✅ Tải bản đồ HCMUTE thành công")
            
            # Điền danh sách combo box
            self._populate_node_combos()
            
        except FileNotFoundError as e:
            self._control_panel.add_log(f"❌ Lỗi tải file: {e}")
            QMessageBox.critical(self, "Lỗi tải dữ liệu", str(e))
        except Exception as e:
            self._control_panel.add_log(f"❌ Lỗi không xác định: {e}")
            QMessageBox.critical(self, "Lỗi", f"Đã xảy ra lỗi: {e}")
    
    def _populate_node_combos(self):
        """Cập nhật danh sách node trong combo box và giữ lựa chọn hiện tại nếu còn hợp lệ."""
        node_list = [
            (nid, self._graph.get_node_name(nid))
            for nid in self._graph.get_all_node_ids()
        ]
        self._control_panel.start_combo.blockSignals(True)
        self._control_panel.goal_combo.blockSignals(True)
        self._control_panel.populate_node_combos(node_list)
        self._set_combo_to_node(self._control_panel.start_combo, self._start_node)
        self._set_combo_to_node(self._control_panel.goal_combo, self._goal_node)
        self._control_panel.start_combo.blockSignals(False)
        self._control_panel.goal_combo.blockSignals(False)
    
    @staticmethod
    def _set_combo_to_node(combo, node_id: Optional[str]):
        if not node_id:
            combo.setCurrentIndex(0)
            return
        for i in range(combo.count()):
            if combo.itemData(i) == node_id:
                combo.setCurrentIndex(i)
                return
        combo.setCurrentIndex(0)
    
    def _on_node_clicked(self, node_id: str):
        """Xử lý click chọn node trên bản đồ."""
        if self._is_running:
            return
            
        name = self._graph.get_node_name(node_id)
        
        if self._click_count == 0:
            self._set_start(node_id)
            self._click_count = 1
        elif self._click_count == 1:
            if node_id == self._start_node:
                self._control_panel.add_log("⚠️ Điểm đích không được trùng điểm bắt đầu!")
                return
            self._set_goal(node_id)
            self._click_count = 2
        else:
            # Đã chọn cả hai -> Click lại sẽ reset chọn điểm bắt đầu mới
            self._map_widget.full_reset()
            self._set_start(node_id)
            self._goal_node = None
            self._control_panel.set_goal_display("(Chọn trên bản đồ)")
            self._click_count = 1
            
    def _set_start(self, node_id: str):
        """Cập nhật điểm bắt đầu."""
        self._start_node = node_id
        name = self._graph.get_node_name(node_id)
        self._map_widget.set_start_node(node_id)
        self._control_panel.set_start_display(name)
        self._control_panel.add_log(f"📍 Điểm bắt đầu: {name}")
        
        # Đồng bộ Combo Box
        for i in range(self._control_panel.start_combo.count()):
            if self._control_panel.start_combo.itemData(i) == node_id:
                self._control_panel.start_combo.blockSignals(True)
                self._control_panel.start_combo.setCurrentIndex(i)
                self._control_panel.start_combo.blockSignals(False)
                break
                
    def _set_goal(self, node_id: str):
        """Cập nhật điểm đích."""
        self._goal_node = node_id
        name = self._graph.get_node_name(node_id)
        self._map_widget.set_goal_node(node_id)
        self._control_panel.set_goal_display(name)
        self._control_panel.add_log(f"⭐ Điểm đích: {name}")
        
        # Đồng bộ Combo Box
        for i in range(self._control_panel.goal_combo.count()):
            if self._control_panel.goal_combo.itemData(i) == node_id:
                self._control_panel.goal_combo.blockSignals(True)
                self._control_panel.goal_combo.setCurrentIndex(i)
                self._control_panel.goal_combo.blockSignals(False)
                break
                
    def _on_start_combo_changed(self, index: int):
        node_id = self._control_panel.start_combo.itemData(index)
        if node_id and node_id != self._start_node:
            self._set_start(node_id)
            self._click_count = 2 if self._goal_node else 1
            
    def _on_goal_combo_changed(self, index: int):
        node_id = self._control_panel.goal_combo.itemData(index)
        if node_id and node_id != self._goal_node:
            if node_id == self._start_node:
                self._control_panel.add_log("⚠️ Điểm đích không được trùng điểm bắt đầu!")
                return
            self._set_goal(node_id)
            self._click_count = 2
    
    def _on_edit_graph(self):
        """Mở công cụ chỉnh sửa node/cạnh của bản đồ."""
        if self._is_running:
            QMessageBox.warning(self, "Đang chạy", "Vui lòng dừng thuật toán trước khi chỉnh sửa bản đồ.")
            return
        
        edge_visible, edge_width, edge_opacity = self._map_widget.edge_display()
        dialog = GraphEditorDialog(
            self._graph,
            self._json_path,
            self._map_path,
            edge_visible,
            edge_width,
            edge_opacity,
            self,
        )
        dialog.graph_changed.connect(self._on_graph_changed)
        dialog.edge_display_changed.connect(self._map_widget.set_edge_display)
        dialog.exec()
    
    def _on_graph_changed(self):
        """Dựng lại map và lựa chọn sau khi graph được chỉnh sửa."""
        edge_display = self._map_widget.edge_display()
        
        if self._start_node and not self._graph.node_exists(self._start_node):
            self._start_node = None
            self._control_panel.set_start_display("(Chọn trên bản đồ)")
        if self._goal_node and not self._graph.node_exists(self._goal_node):
            self._goal_node = None
            self._control_panel.set_goal_display("(Chọn trên bản đồ)")
        
        self._map_widget.setup_map(self._graph, self._map_path)
        self._map_widget.set_edge_display(*edge_display)
        
        if self._start_node:
            self._map_widget.set_start_node(self._start_node)
            self._control_panel.set_start_display(self._graph.get_node_name(self._start_node))
        if self._goal_node:
            self._map_widget.set_goal_node(self._goal_node)
            self._control_panel.set_goal_display(self._graph.get_node_name(self._goal_node))
        
        self._populate_node_combos()
        self._control_panel.reset_stats()
        self._control_panel.add_log(
            f"🛠️ Đã cập nhật bản đồ: {len(self._graph.nodes)} node, {len(self._graph.edges)} cạnh"
        )
            
    # ──────────────────────────────────────────────────
    # Điều khiển quá trình mô phỏng
    # ──────────────────────────────────────────────────
    
    def _on_start(self):
        """Khởi chạy thuật toán tìm đường."""
        if not self._start_node:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn điểm bắt đầu!")
            return
        if not self._goal_node:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn điểm đích!")
            return
            
        algo_name = self._control_panel.get_selected_algorithm()
        heuristic_name = self._control_panel.get_selected_heuristic()
        
        self._control_panel.add_log("")
        self._control_panel.add_log("="*45)
        self._control_panel.add_log(f"🚀 Chạy thuật toán: {algo_name}")
        self._control_panel.add_log(
            f"📍 {self._graph.get_node_name(self._start_node)} → "
            f"{self._graph.get_node_name(self._goal_node)}"
        )
        
        if needs_heuristic(algo_name):
            self._control_panel.add_log(f"📐 Heuristic: {heuristic_name}")
            
        self._control_panel.add_log("⏳ Đang tính toán...")
        
        self._map_widget.reset_all_nodes()
        self._control_panel.reset_stats()
        
        # Khởi tạo thuật toán và generator
        algo_func = get_algorithm(algo_name)
        if needs_heuristic(algo_name):
            h_func = get_heuristic_function(heuristic_name)
            self._algorithm_gen = algo_func(
                self._graph, self._start_node, self._goal_node, h_func)
        else:
            self._algorithm_gen = algo_func(
                self._graph, self._start_node, self._goal_node)
                
        self._exec_timer.start()
        
        self._is_running = True
        self._is_paused = False
        self._total_visited = 0
        self._final_path = []
        self._final_cost = 0.0
        
        self._control_panel.set_running_state(True)
        self._update_status("Đang chạy", "#1A73E8")
        
        # Khởi động Timer bước chạy
        self._timer.start(self._step_delay)
        
    def _execute_step(self):
        """Thực hiện một bước trong generator thuật toán."""
        if not self._algorithm_gen or not self._is_running or self._is_paused:
            return
            
        try:
            step = next(self._algorithm_gen)
            
            current = step.get("current", "")
            visited = step.get("visited", [])
            frontier = step.get("frontier", [])
            path = step.get("path", [])
            cost = step.get("cost", 0)
            log = step.get("log", "")
            
            self._total_visited = len(visited)
            
            # Cập nhật bản đồ
            self._map_widget.reset_all_nodes()
            self._map_widget.highlight_visited(visited)
            self._map_widget.highlight_frontier(frontier)
            if current:
                self._map_widget.highlight_current(current)
                
            if log:
                self._control_panel.add_log(log)
                
            # Cập nhật stats thời gian thực
            elapsed = (time.perf_counter() - self._exec_timer._start_time) * 1000 \
                if self._exec_timer._start_time else 0
            self._control_panel.update_stats(
                distance=cost if cost > 0 else None,
                node_count=self._total_visited,
                time_ms=elapsed
            )
            
            # Kiểm tra hoàn thành
            if log and ("✅" in log or "❌" in log):
                self._final_path = path
                self._final_cost = cost
                self._on_algorithm_finished()
                
        except StopIteration:
            self._on_algorithm_finished()
            
    def _on_algorithm_finished(self):
        """Xử lý khi kết thúc duyệt."""
        self._timer.stop()
        exec_time = self._exec_timer.stop()
        self._is_running = False
        
        if self._final_path and len(self._final_path) > 1:
            self._map_widget.highlight_path(self._final_path)
            
            # Báo cáo kết quả
            algo_name = self._control_panel.get_selected_algorithm()
            self._control_panel.add_log("")
            self._control_panel.add_log("─"*45)
            self._control_panel.add_log(f"📊 KẾT QUẢ THUẬT TOÁN {algo_name}")
            self._control_panel.add_log("─"*45)
            
            route = " → ".join(self._graph.get_node_name(n) for n in self._final_path)
            self._control_panel.add_log(f"⭐ Lộ trình: {route}")
            
            self._control_panel.add_log("📋 Chi tiết:")
            for i in range(len(self._final_path) - 1):
                src = self._graph.get_node_name(self._final_path[i])
                dst = self._graph.get_node_name(self._final_path[i + 1])
                w = self._graph.get_edge_weight(self._final_path[i], self._final_path[i + 1])
                w_str = f"{w:.1f}" if w is not None else "N/A"
                self._control_panel.add_log(f"   {src} → {dst}: {w_str} m")
                
            self._control_panel.add_log(f"🛣️ Tổng quãng đường: {self._final_cost:.1f} m")
            self._control_panel.add_log(f"🔍 Số node đã duyệt: {self._total_visited}")
            self._control_panel.add_log(f"⏱️ Thời gian xử lý: {exec_time:.2f} ms")
            self._control_panel.add_log("✅ Tính toán hoàn tất!")
            
        self._control_panel.update_stats(
            distance=self._final_cost if self._final_cost > 0 else 0,
            node_count=self._total_visited,
            time_ms=exec_time
        )
        self._control_panel.set_finished_state()
        self._update_status("Hoàn tất", "#34A853")
        
    def _on_pause(self):
        self._is_paused = True
        self._control_panel.add_log("⏸️ Tạm dừng mô phỏng")
        self._update_status("Tạm dừng", "#F9AB00")
        
    def _on_resume(self):
        self._is_paused = False
        self._control_panel.add_log("▶️ Tiếp tục mô phỏng")
        self._update_status("Đang chạy", "#1A73E8")
        
    def _on_stop(self):
        self._timer.stop()
        self._is_running = False
        self._is_paused = False
        self._algorithm_gen = None
        self._exec_timer.stop()
        
        self._control_panel.add_log("⏹️ Đã dừng tìm kiếm")
        self._control_panel.set_finished_state()
        self._update_status("Đã dừng", "#D93025")
        
    def _on_reset(self):
        self._timer.stop()
        self._is_running = False
        self._is_paused = False
        self._algorithm_gen = None
        
        self._map_widget.full_reset()
        self._start_node = None
        self._goal_node = None
        self._click_count = 0
        
        self._control_panel.set_finished_state()
        self._control_panel.reset_stats()
        self._control_panel.clear_log()
        self._control_panel.set_start_display("(Chọn trên bản đồ)")
        self._control_panel.set_goal_display("(Chọn trên bản đồ)")
        
        # Reset combo boxes
        self._control_panel.start_combo.blockSignals(True)
        self._control_panel.start_combo.setCurrentIndex(0)
        self._control_panel.start_combo.blockSignals(False)
        self._control_panel.goal_combo.blockSignals(True)
        self._control_panel.goal_combo.setCurrentIndex(0)
        self._control_panel.goal_combo.blockSignals(False)
        
        self._control_panel.add_log("↻ Đã reset toàn bộ hệ thống")
        self._control_panel.add_log("✅ Khởi tạo đồ thị HCMUTE thành công")
        self._update_status("Sẵn sàng", "#34A853")
        
    def _update_status(self, text: str, color: str):
        """Cập nhật trạng thái hiển thị trên header."""
        self._status_label.setText(
            f"<span style='color: {color}; font-size: 14px;'>●</span>&nbsp;Trạng thái: "
            f"<span style='color: {color}; font-weight: bold;'>{text}</span>"
        )
