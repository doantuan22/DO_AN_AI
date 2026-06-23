# Cửa sổ chính: ghép MapWidget + ControlPanel
# Quản lý luồng chọn node, chạy thuật toán, mô phỏng và hiển thị kết quả

import os
import sys
from typing import Optional, Generator

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QMessageBox, QApplication, QFrame, QStackedWidget, QComboBox, QPushButton
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QIcon, QPixmap

from core.graph import Graph
from core.algorithms import get_algorithm, needs_heuristic, ALGORITHM_MAP
from core.heuristic import get_heuristic_function
from core.history_store import HistoryStore
from core.utils import Timer, get_timestamp
from services.sub_map_store import SubMapStore
from ui.map_widget import MapWidget
from ui.banner_widget import BannerWidget
from ui.control_panel import ControlPanel
from ui.graph_editor_dialog import GraphEditorDialog
from ui.history_dialog import HistoryDialog
from ui.sub_map_manager_dialog import SubMapManagerDialog
from ui.sub_map_viewer_dialog import SubMapViewerDialog
from ui.help_dialog import HelpDialog
from widgets.sub_map_widget import SubMapWidget



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
    QLabel#headerCredit {
        color: #475569;
        font-family: 'Segoe UI';
        font-size: 13px;
        font-weight: 700;
        padding-right: 24px;
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


# Cửa sổ chính của ứng dụng
class MainWindow(QMainWindow):
    
    def __init__(self):
        super().__init__()
        
        # ── Xác định đường dẫn gốc của project ──
        if getattr(sys, 'frozen', False):
            self._base_dir = os.path.dirname(sys.executable)
        else:
            self._base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._json_path = os.path.join(self._base_dir, "data", "hcmute_graph_nodes_edges.json")
        self._history_db_path = os.path.join(self._base_dir, "data", "path_history.sqlite3")
        self._map_path = os.path.join(self._base_dir, "assets", "map.png")
        self._avatar_path = os.path.join(self._base_dir, "assets", "avata01.png")
        
        # ── Khởi tạo dữ liệu ──
        self._graph = Graph()
        self._history_store = HistoryStore(self._history_db_path)
        self._sub_map_store = SubMapStore(self._base_dir)
        self._sub_graph = Graph()
        self._current_map_mode = "main"
        self._current_submap_node_id: Optional[str] = None
        self._timer = QTimer()
        self._timer.timeout.connect(self._execute_step)
        
        self._algorithm_gen: Optional[Generator] = None
        self._is_running = False
        self._is_paused = False
        self._exec_timer = Timer()
        
        self._start_node: Optional[str] = None
        self._goal_node: Optional[str] = None
        self._click_count = 0  # Đếm click để chọn start/goal
        
        self._step_delay = 140  # ms giữa các bước mô phỏng
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
        # Cấu hình cửa sổ chính
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
        # Xây dựng layout giao diện
        central = QWidget()
        central.setObjectName("appRoot")
        self.setCentralWidget(central)
        
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        
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
        
        self._credit_label = QLabel("NGÔ MINH KHÁNH-24110248 | ĐOÀN ANH TUẤN-24110368 | LÊ VĂN LÂN-24110269")
        self._credit_label.setObjectName("headerCredit")
        self._credit_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        header_layout.addWidget(menu_btn)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self._credit_label)
        header_layout.addWidget(self._status_label)
        
        app_layout.addWidget(header)
        
        # ── Body: Map + Control Panel ──
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(18, 16, 18, 18)
        body_layout.setSpacing(16)
        
        self._map_stack = QStackedWidget()
        body_layout.addWidget(self._map_stack, 1)
        
        self._map_widget = MapWidget()
        self._map_stack.addWidget(self._map_widget)
        
        # ── Bản đồ chi tiết (SubMap) ──
        self._sub_map_container = QWidget()
        sub_map_layout = QVBoxLayout(self._sub_map_container)
        sub_map_layout.setContentsMargins(0, 0, 0, 0)
        sub_map_layout.setSpacing(0)
        
        sub_toolbar = QFrame()
        sub_toolbar.setStyleSheet("background-color: #FFFFFF; border-bottom: 1px solid #DDE7F5;")
        sub_toolbar_layout = QHBoxLayout(sub_toolbar)
        sub_toolbar_layout.setContentsMargins(10, 5, 10, 5)
        
        self._lbl_submap_title = QLabel("Bản đồ chi tiết")
        self._lbl_submap_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #15346F;")
        
        self._combo_submap_floor = QComboBox()
        self._combo_submap_floor.setMinimumWidth(220)
        self._combo_submap_floor.setCursor(Qt.CursorShape.PointingHandCursor)
        self._combo_submap_floor.setStyleSheet("""
            QComboBox {
                background-color: #F8FAFC;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 14px;
                font-family: 'Segoe UI';
                font-size: 13px;
                font-weight: 600;
                color: #1E293B;
            }
            QComboBox:hover {
                background-color: #F1F5F9;
                border-color: #94A3B8;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #64748B;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 4px;
                selection-background-color: #EFF6FF;
                selection-color: #1D4ED8;
                padding: 4px;
            }
        """)
        self._combo_submap_floor.currentIndexChanged.connect(self._on_submap_floor_changed)
        
        self._btn_submap_exit = QPushButton("⮌ Quay lại bản đồ chính")
        self._btn_submap_exit.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_submap_exit.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 6px 14px;
                font-family: 'Segoe UI';
                font-size: 13px;
                font-weight: 600;
                color: #475569;
            }
            QPushButton:hover {
                background-color: #F1F5F9;
                color: #0F172A;
            }
        """)
        self._btn_submap_exit.clicked.connect(self._exit_submap_mode)
        
        lbl_chon = QLabel("Chuyển tầng:")
        lbl_chon.setStyleSheet("font-weight: 600; color: #64748B; font-size: 13px;")
        
        sub_toolbar_layout.addWidget(self._lbl_submap_title)
        sub_toolbar_layout.addStretch()
        sub_toolbar_layout.addWidget(lbl_chon)
        sub_toolbar_layout.addWidget(self._combo_submap_floor)
        sub_toolbar_layout.addSpacing(10)
        sub_toolbar_layout.addWidget(self._btn_submap_exit)
        
        self._sub_map_widget = SubMapWidget(editable=False)
        self._sub_map_widget.node_clicked.connect(self._on_submap_node_clicked)
        
        sub_map_layout.addWidget(sub_toolbar)
        sub_map_layout.addWidget(self._sub_map_widget, 1)
        
        self._map_stack.addWidget(self._sub_map_container)
        
        right_column = QWidget()
        right_column.setFixedWidth(470)
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 14, 0, 0)
        right_layout.setSpacing(12)

        self._banner_widget = BannerWidget(self._base_dir)
        right_layout.addWidget(
            self._banner_widget,
            0,
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter,
        )

        self._control_panel = ControlPanel()
        right_layout.addWidget(self._control_panel, 1)
        body_layout.addWidget(right_column)
        
        app_layout.addWidget(body, 1)

        self._toast_label = QLabel(central)
        self._toast_label.setObjectName("toast")
        self._toast_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._toast_label.hide()
    
    def _connect_signals(self):
        # Kết nối signal/slot điều khiển
        # Click chọn trên bản đồ
        self._map_widget.node_clicked.connect(self._on_node_clicked)
        self._map_widget.graph_edit_clicked.connect(self._on_edit_graph)
        self._map_widget.sub_map_manager_clicked.connect(self._on_manage_sub_maps)
        self._map_widget.history_clicked.connect(self._on_show_history)
        self._map_widget.sample_walk_clicked.connect(self._on_sample_walk)
        self._map_widget.algorithm_speed_changed.connect(self._on_algorithm_speed_changed)
        self._map_widget.help_clicked.connect(self._on_show_help)
        
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
        # Tải dữ liệu đồ thị JSON và ảnh nền bản đồ
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
        # Cập nhật danh sách node trong combo box
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
        # Xử lý click chọn node trên bản đồ
        if self._is_running:
            return

        # Click lại node đang được chọn sẽ bỏ chọn node đó. Cách này giúp người dùng
        # sửa nhanh điểm đi/điểm đến trực tiếp trên bản đồ mà không cần dùng nút xóa.
        if node_id == self._start_node:
            self._clear_start()
            return
        if node_id == self._goal_node:
            if self._app_state == "completed" and self._current_map_mode == "main" and self._sub_map_store.has_sub_maps(node_id):
                self._enter_submap_mode(node_id)
                return
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
        # Cập nhật điểm bắt đầu
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
        # Cập nhật điểm đích
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
        # Xóa điểm bắt đầu
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
        # Xóa điểm đích
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
        # Đồng bộ trạng thái chọn điểm với header và nút Start
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
        if self._current_map_mode == "sub":
            # Ở chế độ bản đồ con, start luôn là __entry__, không xử lý
            return
        if not node_id:
            if self._start_node:
                self._clear_start()
            return
        if node_id == self._goal_node:
            self._control_panel.add_log("⚠️ Điểm bắt đầu không được trùng điểm đích!")
            self._control_panel.start_combo.blockSignals(True)
            self._set_combo_to_node(self._control_panel.start_combo, self._start_node)
            self._control_panel.start_combo.blockSignals(False)
            return
        if node_id != self._start_node:
            self._set_start(node_id)
            self._click_count = 2 if self._goal_node else 1
            
    def _on_goal_combo_changed(self, index: int):
        node_id = self._control_panel.goal_combo.itemData(index)
        if self._current_map_mode == "sub":
            # Chế độ bản đồ con: chọn đích qua submap flow
            if not node_id:
                if self._goal_node:
                    self._goal_node = None
                    self._sub_map_widget.clear_goal_node()
                    self._control_panel.set_goal_display("(Chọn trên bản đồ)")
                    self._sync_ready_state()
                return
            if node_id != self._goal_node:
                self._start_node = "__entry__"
                self._goal_node = node_id
                name = self._sub_graph.get_node_name(node_id)
                self._sub_map_widget.set_goal_node(node_id)
                self._control_panel.set_goal_display(name)
                self._control_panel.add_log(f"⭐ Điểm đích: {name}")
                self._sync_ready_state()
            return
        if not node_id:
            if self._goal_node:
                self._clear_goal()
            return
        if node_id == self._start_node:
            self._control_panel.add_log("⚠️ Điểm đích không được trùng điểm bắt đầu!")
            self._control_panel.goal_combo.blockSignals(True)
            self._set_combo_to_node(self._control_panel.goal_combo, self._goal_node)
            self._control_panel.goal_combo.blockSignals(False)
            return
        if node_id != self._goal_node:
            self._set_goal(node_id)
            self._click_count = 2
    
    def _on_edit_graph(self):
        # Mở công cụ chỉnh sửa node/cạnh
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

    def _on_show_history(self):
        # Mở bảng lịch sử đường đi
        dialog = HistoryDialog(self._history_store, self)
        dialog.exec()

    def _on_show_help(self):
        # Mở hướng dẫn sử dụng
        dialog = HelpDialog(self)
        dialog.exec()

    def _on_manage_sub_maps(self):
        if self._is_running:
            QMessageBox.information(self, "Đang chạy", "Hãy dừng thuật toán trước khi quản lý bản đồ con.")
            return
        SubMapManagerDialog(self._graph, self._sub_map_store, self._map_path, self).exec()
    
    def _on_graph_changed(self):
        # Dựng lại map sau khi graph được chỉnh sửa
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
        # Khởi chạy thuật toán tìm đường
        if not self._start_node:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn điểm bắt đầu!")
            return
        if not self._goal_node:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn điểm đích!")
            return
            
        algo_name = self._control_panel.get_selected_algorithm()
        heuristic_name = self._control_panel.get_selected_heuristic()
        active_graph = self._sub_graph if self._current_map_mode == "sub" else self._graph
        
        self._control_panel.add_log("")
        self._control_panel.add_log("="*45)
        self._control_panel.add_log(f"🚀 Chạy thuật toán: {algo_name}")
        self._control_panel.add_log(
            f"📍 {active_graph.get_node_name(self._start_node)} → "
            f"{active_graph.get_node_name(self._goal_node)}"
        )
        
        if needs_heuristic(algo_name):
            self._control_panel.add_log(f"📐 Heuristic: {heuristic_name}")
            
        self._control_panel.add_log("⏳ Đang tính toán...")
        
        if self._current_map_mode == "main":
            self._map_widget.reset_all_nodes()
        else:
            self._sub_map_widget.reset_path()
        self._control_panel.reset_stats()
        
        # Khởi tạo thuật toán và generator
        algo_func = get_algorithm(algo_name)
        
        if needs_heuristic(algo_name):
            h_func = get_heuristic_function(heuristic_name)
            self._algorithm_gen = algo_func(
                active_graph, self._start_node, self._goal_node, h_func)
        else:
            self._algorithm_gen = algo_func(
                active_graph, self._start_node, self._goal_node)
                
        self._exec_timer.start()
        self._exec_timer.pause() # Dừng timer, chỉ cộng dồn khi thực sự chạy next()
        
        self._is_running = True
        self._is_paused = False
        self._total_visited = 0
        self._final_path = []
        self._final_cost = 0.0
        
        self._control_panel.set_running_state(True)
        if self._current_map_mode == "main":
            self._map_widget.set_graph_edit_enabled(False)
        self._set_app_state("running")
        
        # Khi ẩn node/cạnh, bản đồ là giao diện chính sạch: chạy xong ngay và chỉ hiện route cuối.
        if self._current_map_mode == "main" and self._map_widget.is_graph_overlay_hidden():
            self._execute_all_steps_without_animation()
        else:
            # Khởi động Timer bước chạy để mô phỏng từng bước trên node.
            self._timer.start(self._step_delay)

    def _execute_all_steps_without_animation(self):
        # Chạy generator đến hết, không tô từng bước lên bản đồ
        if not self._algorithm_gen or not self._is_running:
            return

        try:
            while True:
                self._exec_timer.resume()
                try:
                    step = next(self._algorithm_gen)
                except StopIteration:
                    self._exec_timer.pause()
                    break
                self._exec_timer.pause()

                visited = step.get("visited", [])
                path = step.get("path", [])
                cost = step.get("cost", 0)
                log = step.get("log", "")

                self._total_visited = len(visited)
                if log:
                    self._control_panel.add_log(log)
                if log and ("✅" in log or "❌" in log):
                    self._final_path = path
                    self._final_cost = cost
        finally:
            self._exec_timer.pause()


        self._algorithm_gen = None
        self._on_algorithm_finished()
        
    def _execute_step(self):
        # Thực hiện một bước trong generator thuật toán
        if not self._algorithm_gen or not self._is_running or self._is_paused:
            return
            
        self._exec_timer.resume()
        try:
            step = next(self._algorithm_gen)
            self._exec_timer.pause()
            
            current = step.get("current", "")
            visited = step.get("visited", [])
            frontier = step.get("frontier", [])
            path = step.get("path", [])
            cost = step.get("cost", 0)
            log = step.get("log", "")
            
            self._total_visited = len(visited)
            
            # Cập nhật bản đồ (incremental — chỉ đổi node thay đổi trạng thái)
            if self._current_map_mode == "main":
                self._map_widget.update_step(current, visited, frontier)
            else:
                self._sub_map_widget.update_state(visited, frontier, current)
                
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
            self._exec_timer.pause()
            self._on_algorithm_finished()
            
    def _on_algorithm_finished(self):
        # Xử lý khi kết thúc duyệt
        self._timer.stop()
        exec_time = self._exec_timer.stop()
        self._is_running = False
        
        if self._final_path and len(self._final_path) > 1:
            if self._current_map_mode == "main":
                self._map_widget.highlight_path(
                    self._final_path,
                    animate=not self._map_widget.is_graph_overlay_hidden(),
                )
                self._map_widget.set_sample_walk_enabled(True)
            else:
                self._sub_map_widget.draw_path(self._final_path)
            self._show_toast("Đã tìm thấy lộ trình")
            
            # Báo cáo kết quả
            algo_name = self._control_panel.get_selected_algorithm()
            self._control_panel.add_log("")
            self._control_panel.add_log("─"*45)
            self._control_panel.add_log(f"📊 KẾT QUẢ THUẬT TOÁN {algo_name}")
            self._control_panel.add_log("─"*45)
            
            active_graph = self._sub_graph if self._current_map_mode == "sub" else self._graph
            route = " → ".join(active_graph.get_node_name(n) for n in self._final_path)
            self._control_panel.add_log(f"⭐ Lộ trình: {route}")
            
            self._control_panel.add_log("📋 Chi tiết:")
            active_graph = self._sub_graph if self._current_map_mode == "sub" else self._graph
            for i in range(len(self._final_path) - 1):
                src = active_graph.get_node_name(self._final_path[i])
                dst = active_graph.get_node_name(self._final_path[i + 1])
                w = active_graph.get_edge_weight(self._final_path[i], self._final_path[i + 1])
                w_str = f"{w:.1f}" if w is not None else "N/A"
                self._control_panel.add_log(f"   {src} → {dst}: {w_str} m")
                
            self._control_panel.add_log(f"🛣️ Tổng quãng đường: {self._final_cost:.1f} m")
            self._control_panel.add_log(f"🔍 Số node đã duyệt: {self._total_visited}")
            self._control_panel.add_log(f"⏱️ Thời gian xử lý: {exec_time:.2f} ms")
            self._save_history(algo_name, exec_time)
            self._control_panel.add_log("✅ Tính toán hoàn tất!")
            
        self._control_panel.update_stats(
            distance=self._final_cost if self._final_cost > 0 else 0,
            node_count=self._total_visited,
            time_ms=exec_time
        )
        self._control_panel.set_finished_state()
        if self._current_map_mode == "main":
            self._map_widget.set_graph_edit_enabled(True)
        self._set_app_state("completed" if self._final_path else "error")
        if self._final_path and self._goal_node and self._current_map_mode == "main":
            self._offer_sub_map_for_goal()

    def _offer_sub_map_for_goal(self):
        goal_node_id = self._goal_node
        if not goal_node_id or not self._sub_map_store.has_sub_maps(goal_node_id) or self._current_map_mode != "main":
            return
        
        main_node_name = self._graph.get_node_name(goal_node_id) if goal_node_id in self._graph.nodes else goal_node_id
        
        self._control_panel.add_log(f"🏢 Khu vực này có bản đồ chi tiết của {main_node_name}.")
        self._map_widget.show_submap_button(
            goal_node_id, 
            main_node_name, 
            lambda: self._enter_submap_mode(goal_node_id)
        )

    def _enter_submap_mode(self, main_node_id: str):
        submaps = self._sub_map_store.list_for_node(main_node_id)
        if not submaps:
            return
        self._current_map_mode = "sub"
        self._current_submap_node_id = main_node_id
        main_node_name = self._graph.get_node_name(main_node_id) if main_node_id in self._graph.nodes else main_node_id
        self._lbl_submap_title.setText(f"Khu vực: {main_node_name}")
        
        self._combo_submap_floor.blockSignals(True)
        self._combo_submap_floor.clear()
        for item in submaps:
            self._combo_submap_floor.addItem(f"Tầng {item.floor} — {item.name}", item.id)
        self._combo_submap_floor.blockSignals(False)
        
        self._map_stack.setCurrentIndex(1)
        
        # Load bản đồ đầu tiên
        self._combo_submap_floor.setCurrentIndex(0)
        self._on_submap_floor_changed(0)

    def _on_submap_floor_changed(self, index: int):
        sub_map_id = self._combo_submap_floor.currentData()
        if not sub_map_id:
            return
        item = self._sub_map_store.get(str(sub_map_id))
        if not item:
            return
        
        graph_dict = self._sub_map_store.load_graph(item)
        self._sub_map_widget.load_map(
            self._sub_map_store.absolute_path(item.image),
            graph_dict,
            rotation=item.rotation,
            show_edges=True
        )
        
        self._sub_graph = Graph()
        for node in graph_dict.get("nodes", []):
            self._sub_graph.add_node(node["id"], x=node.get("x", 0), y=node.get("y", 0), name=node.get("name", ""))
        for edge in graph_dict.get("edges", []):
            self._sub_graph.add_edge(edge["from"], edge["to"], edge.get("weight", 1.0))
            
        nodes_list = [(nid, n.name) for nid, n in self._sub_graph.nodes.items() if nid != "__entry__"]
        self._control_panel.set_mode_submap(nodes_list)
        
        self._start_node = "__entry__"
        self._goal_node = None
        self._final_path = []
        self._set_app_state("idle")

    def _exit_submap_mode(self):
        self._current_map_mode = "main"
        self._map_stack.setCurrentIndex(0)
        self._sub_map_widget.reset_path()
        nodes_list = [(nid, n.name) for nid, n in self._graph.nodes.items()]
        self._control_panel.set_mode_main(nodes_list)
        self._start_node = None
        self._goal_node = None
        self._final_path = []
        self._set_app_state("idle")
        self._on_reset()

    def _on_submap_node_clicked(self, node_id: str):
        if self._is_running:
            return
        # Node __entry__ là điểm bắt đầu cố định, không cho chọn làm đích
        if node_id == "__entry__":
            return
        # Click lại node đích hiện tại -> bỏ chọn
        if node_id == self._goal_node:
            self._goal_node = None
            self._sub_map_widget.clear_goal_node()
            self._control_panel.set_goal_display("(Chọn trên bản đồ)")
            self._set_combo_to_node(self._control_panel.goal_combo, None)
            self._control_panel.add_log("↺ Đã xóa điểm đến")
            self._sync_ready_state()
            return
        # Đặt điểm đích mới
        self._start_node = "__entry__"
        self._goal_node = node_id
        name = self._sub_graph.get_node_name(node_id)
        self._sub_map_widget.set_goal_node(node_id)
        self._control_panel.set_goal_display(name)
        self._control_panel.add_log(f"⭐ Điểm đích: {name}")
        
        # Đồng bộ Combo Box
        idx = self._control_panel.goal_combo.findData(node_id)
        if idx >= 0:
            self._control_panel.goal_combo.blockSignals(True)
            self._control_panel.goal_combo.setCurrentIndex(idx)
            self._control_panel.goal_combo.blockSignals(False)
        self._sync_ready_state()

    def _save_history(self, algo_name: str, exec_time: float):
        # Lưu kết quả vào SQLite
        if not self._start_node or not self._goal_node or len(self._final_path) < 2:
            return
        try:
            self._history_store.add_route(
                algorithm=algo_name,
                start_node_id=self._start_node,
                start_node_name=self._graph.get_node_name(self._start_node),
                goal_node_id=self._goal_node,
                goal_node_name=self._graph.get_node_name(self._goal_node),
                distance_m=self._final_cost,
                path_node_ids=self._final_path,
                path_names=[self._graph.get_node_name(node_id) for node_id in self._final_path],
                visited_count=self._total_visited,
                elapsed_ms=exec_time,
            )
            self._control_panel.add_log("💾 Đã lưu lịch sử đường đi")
        except Exception as exc:
            self._control_panel.add_log(f"⚠️ Không thể lưu lịch sử: {exc}")
        
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
        
        if self._current_map_mode == "main":
            self._map_widget.full_reset()
        else:
            self._sub_map_widget.reset_path()
            
        self._start_node = None if self._current_map_mode == "main" else "__entry__"
        self._goal_node = None
        self._click_count = 0
        self._final_path = []
        self._final_cost = 0.0
        
        self._control_panel.set_finished_state()
        self._map_widget.set_graph_edit_enabled(True)
        self._map_widget.set_sample_walk_enabled(False)
        self._control_panel.reset_stats()
        self._control_panel.clear_log()
        self._control_panel.set_goal_display("(Chọn trên bản đồ)")
        
        if self._current_map_mode == "sub":
            self._control_panel.set_start_display("Bạn đang ở đây")
        else:
            self._control_panel.set_start_display("(Chọn trên bản đồ)")
        
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
        # Cho avatar đi mẫu theo lộ trình
        if not self._final_path or len(self._final_path) < 2:
            self._control_panel.add_log("⚠️ Chưa có lộ trình để đi mẫu")
            return
        if not os.path.exists(self._avatar_path):
            self._control_panel.add_log("⚠️ Không tìm thấy assets/avata01.png")
            return
            
        if self._current_map_mode == "main":
            self._map_widget.animate_avatar_along_path(self._final_path, self._avatar_path)
        else:
            self._sub_map_widget.animate_avatar_along_path(self._final_path, self._avatar_path)
            
        self._control_panel.add_log("▶ Đi mẫu theo lộ trình đã tìm được")

    def _on_algorithm_speed_changed(self, speed_name: str):
        # Cập nhật tốc độ mô phỏng
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
        # Cập nhật trạng thái hiển thị trên header
        self._status_label.setText(
            f"<span style='color: {color}; font-size: 14px;'>●</span>&nbsp;Trạng thái: "
            f"<span style='color: {color}; font-weight: bold;'>{text}</span>"
        )

    def _set_app_state(self, state: str):
        # State UI tập trung: đồng bộ header, panel, feedback
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
