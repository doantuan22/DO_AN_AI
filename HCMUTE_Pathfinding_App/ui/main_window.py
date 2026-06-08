"""
main_window.py - Cửa sổ chính của ứng dụng (Redesigned matching UI_demo)
========================================================================
Ghép các thành phần giao diện (MapWidget + ControlPanel),
quản lý luồng hoạt động chính: chọn node, chạy thuật toán,
mô phỏng từng bước, hiển thị kết quả.
"""

import os
import sys
from typing import Optional, Generator

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QMessageBox, QApplication, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QIcon, QPixmap

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
        background-color: #FFFFFF;
        border: 1px solid #DDE6F2;
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
    QLabel#toast {
        background-color: #0F172A;
        color: #FFFFFF;
        border-radius: 12px;
        padding: 12px 18px;
        font-family: 'Segoe UI';
        font-size: 13px;
        font-weight: 800;
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
        self._avatar_path = os.path.join(self._base_dir, "assets", "avata01.png")
        
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
        self._app_state = "idle"
        
        # ── Xây dựng giao diện ──
        self._setup_window()
        self._setup_ui()
        self._connect_signals()
        
        # ── Tải dữ liệu ──
        self._load_data()
        self._set_app_state("idle")
    
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
        
        rail_logo = QLabel()
        rail_logo.setObjectName("railLogo")
        rail_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rail_logo.setFixedSize(54, 54)
        logo_path = os.path.join(self._base_dir, "assets", "logo.png")
        if os.path.exists(logo_path):
            logo_pixmap = QPixmap(logo_path).scaled(
                42,
                42,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            rail_logo.setPixmap(logo_pixmap)
        else:
            rail_logo.setText("KTL")
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

        self._toast_label = QLabel(central)
        self._toast_label.setObjectName("toast")
        self._toast_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._toast_label.hide()
    
    def _connect_signals(self):
        """Kết nối các signal/slot điều khiển."""
        # Click chọn trên bản đồ
        self._map_widget.node_clicked.connect(self._on_node_clicked)
        self._map_widget.graph_edit_clicked.connect(self._on_edit_graph)
        self._map_widget.sample_walk_clicked.connect(self._on_sample_walk)
        self._map_widget.algorithm_speed_changed.connect(self._on_algorithm_speed_changed)
        
        # Nút điều khiển Panel
        self._control_panel.start_clicked.connect(self._on_start)
        self._control_panel.pause_clicked.connect(self._on_pause)
        self._control_panel.resume_clicked.connect(self._on_resume)
        self._control_panel.stop_clicked.connect(self._on_stop)
        self._control_panel.reset_clicked.connect(self._on_reset)
        self._control_panel.graph_edit_clicked.connect(self._on_edit_graph)
        self._control_panel.clear_start_clicked.connect(self._clear_start)
        self._control_panel.clear_goal_clicked.connect(self._clear_goal)
        
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
            self._sync_ready_state()
            
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

        # Click lại node đang được chọn sẽ bỏ chọn node đó. Cách này giúp người dùng
        # sửa nhanh điểm đi/điểm đến trực tiếp trên bản đồ mà không cần dùng nút xóa.
        if node_id == self._start_node:
            self._clear_start()
            return
        if node_id == self._goal_node:
            self._clear_goal()
            return

        if self._start_node is None:
            self._set_start(node_id)
            self._click_count = 1 if self._goal_node is None else 2
        elif self._goal_node is None:
            self._set_goal(node_id)
            self._click_count = 2
        else:
            # Đã chọn cả hai -> click node khác sẽ bắt đầu một cặp lựa chọn mới.
            self._map_widget.full_reset()
            self._set_start(node_id)
            self._goal_node = None
            self._control_panel.set_goal_display("(Chọn trên bản đồ)")
            self._set_combo_to_node(self._control_panel.goal_combo, None)
            self._click_count = 1
            self._sync_ready_state()
            
    def _set_start(self, node_id: str):
        """Cập nhật điểm bắt đầu."""
        self._start_node = node_id
        name = self._graph.get_node_name(node_id)
        self._map_widget.set_start_node(node_id)
        self._control_panel.set_start_display(name)
        self._control_panel.add_log(f"📍 Điểm bắt đầu: {name}")
        self._map_widget.pulse_node(node_id)
        
        # Đồng bộ Combo Box
        for i in range(self._control_panel.start_combo.count()):
            if self._control_panel.start_combo.itemData(i) == node_id:
                self._control_panel.start_combo.blockSignals(True)
                self._control_panel.start_combo.setCurrentIndex(i)
                self._control_panel.start_combo.blockSignals(False)
                break
        self._sync_ready_state()
                
    def _set_goal(self, node_id: str):
        """Cập nhật điểm đích."""
        self._goal_node = node_id
        name = self._graph.get_node_name(node_id)
        self._map_widget.set_goal_node(node_id)
        self._control_panel.set_goal_display(name)
        self._control_panel.add_log(f"⭐ Điểm đích: {name}")
        self._map_widget.pulse_node(node_id)
        
        # Đồng bộ Combo Box
        for i in range(self._control_panel.goal_combo.count()):
            if self._control_panel.goal_combo.itemData(i) == node_id:
                self._control_panel.goal_combo.blockSignals(True)
                self._control_panel.goal_combo.setCurrentIndex(i)
                self._control_panel.goal_combo.blockSignals(False)
                break
        self._sync_ready_state()

    def _clear_start(self):
        """Xóa riêng điểm bắt đầu mà không ảnh hưởng graph."""
        if self._is_running:
            return
        self._start_node = None
        self._click_count = 0 if not self._goal_node else 1
        self._map_widget.clear_start_node()
        self._control_panel.set_start_display("(Chọn trên bản đồ)")
        self._set_combo_to_node(self._control_panel.start_combo, None)
        self._control_panel.add_log("↺ Đã xóa điểm bắt đầu")
        self._sync_ready_state()

    def _clear_goal(self):
        """Xóa riêng điểm đích mà không ảnh hưởng graph."""
        if self._is_running:
            return
        self._goal_node = None
        self._click_count = 1 if self._start_node else 0
        self._map_widget.clear_goal_node()
        self._control_panel.set_goal_display("(Chọn trên bản đồ)")
        self._set_combo_to_node(self._control_panel.goal_combo, None)
        self._control_panel.add_log("↺ Đã xóa điểm đến")
        self._sync_ready_state()

    def _sync_ready_state(self):
        """Đồng bộ trạng thái chọn điểm với header và nút Start."""
        ready = bool(self._start_node and self._goal_node)
        self._control_panel.set_ready_to_start(ready)
        if self._is_running:
            return
        if ready:
            self._set_app_state("ready")
        elif self._start_node and not self._goal_node:
            self._set_app_state("selecting_goal")
        elif self._goal_node and not self._start_node:
            self._set_app_state("selecting_start")
        else:
            self._set_app_state("idle")
                
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
        self._final_path = []
        self._final_cost = 0.0
        self._map_widget.set_sample_walk_enabled(False)
        self._sync_ready_state()
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
        self._map_widget.set_graph_edit_enabled(False)
        self._set_app_state("running")
        
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
            
            # Cập nhật bản đồ (incremental — chỉ đổi node thay đổi trạng thái)
            self._map_widget.update_step(current, visited, frontier)
                
            if log:
                self._control_panel.add_log(log)
                
            # Cập nhật stats thời gian thực
            elapsed = self._exec_timer.elapsed_live()
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
            self._map_widget.set_sample_walk_enabled(True)
            self._show_toast("Đã tìm thấy lộ trình tối ưu")
            
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
        self._map_widget.set_graph_edit_enabled(True)
        self._set_app_state("completed" if self._final_path else "error")
        
    def _on_pause(self):
        self._is_paused = True
        self._control_panel.add_log("⏸️ Tạm dừng mô phỏng")
        self._set_app_state("paused")
        
    def _on_resume(self):
        self._is_paused = False
        self._control_panel.add_log("▶️ Tiếp tục mô phỏng")
        self._set_app_state("running")
        
    def _on_stop(self):
        self._timer.stop()
        self._is_running = False
        self._is_paused = False
        self._algorithm_gen = None
        self._exec_timer.stop()
        
        self._control_panel.add_log("⏹️ Đã dừng tìm kiếm")
        self._control_panel.set_finished_state()
        self._map_widget.set_graph_edit_enabled(True)
        self._map_widget.set_sample_walk_enabled(False)
        self._set_app_state("idle")
        
    def _on_reset(self):
        self._timer.stop()
        self._is_running = False
        self._is_paused = False
        self._algorithm_gen = None
        
        self._map_widget.full_reset()
        self._start_node = None
        self._goal_node = None
        self._click_count = 0
        self._final_path = []
        self._final_cost = 0.0
        
        self._control_panel.set_finished_state()
        self._map_widget.set_graph_edit_enabled(True)
        self._map_widget.set_sample_walk_enabled(False)
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
        self._sync_ready_state()

    def _on_sample_walk(self):
        """Cho avatar đi mẫu theo lộ trình đã tìm được."""
        if not self._final_path or len(self._final_path) < 2:
            self._control_panel.add_log("⚠️ Chưa có lộ trình để đi mẫu")
            return
        if not os.path.exists(self._avatar_path):
            self._control_panel.add_log("⚠️ Không tìm thấy assets/avata01.png")
            return
        self._map_widget.animate_avatar_along_path(self._final_path, self._avatar_path)
        self._control_panel.add_log("▶ Đi mẫu theo lộ trình đã tìm được")

    def _on_algorithm_speed_changed(self, speed_name: str):
        """Cập nhật tốc độ mô phỏng thuật toán từ nút nổi trên bản đồ."""
        speed_delays = {
            "Nhanh": 140,
            "Trung bình": 400,
            "Chậm": 750,
        }
        self._step_delay = speed_delays.get(speed_name, 400)
        if self._timer.isActive():
            self._timer.setInterval(self._step_delay)
        self._control_panel.add_log(f"⏱ Tốc độ xử lý: {speed_name}")
        
    def _update_status(self, text: str, color: str):
        """Cập nhật trạng thái hiển thị trên header."""
        self._status_label.setText(
            f"<span style='color: {color}; font-size: 14px;'>●</span>&nbsp;Trạng thái: "
            f"<span style='color: {color}; font-weight: bold;'>{text}</span>"
        )

    def _set_app_state(self, state: str):
        """State UI tập trung để header, panel và feedback luôn đồng bộ."""
        self._app_state = state
        labels = {
            "idle": ("Sẵn sàng", "#22C55E"),
            "selecting_start": ("Chọn điểm đi", "#0B74FF"),
            "selecting_goal": ("Chọn điểm đến", "#0B74FF"),
            "ready": ("Sẵn sàng chạy", "#22C55E"),
            "running": ("Đang tìm đường", "#F59E0B"),
            "paused": ("Tạm dừng", "#F59E0B"),
            "completed": ("Hoàn tất", "#22C55E"),
            "error": ("Lỗi", "#EF4444"),
        }
        text, color = labels.get(state, labels["idle"])
        self._update_status(text, color)

    def _show_toast(self, message: str, timeout_ms: int = 2600):
        self._toast_label.setText(message)
        self._toast_label.adjustSize()
        self._position_toast()
        self._toast_label.show()
        self._toast_label.raise_()
        QTimer.singleShot(timeout_ms, self._toast_label.hide)

    def _position_toast(self):
        if not hasattr(self, "_toast_label"):
            return
        x = max(0, (self.centralWidget().width() - self._toast_label.width()) // 2)
        self._toast_label.move(x, 86)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_toast()
