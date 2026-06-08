"""
control_panel.py - Panel điều khiển bên phải (Redesigned matching UI_demo, no ScrollArea)
====================================================================================
Chứa các widget cho phép người dùng:
- Chọn thuật toán tìm kiếm
- Chọn hàm heuristic
- Xem điểm bắt đầu / điểm đích đã chọn
- Điều khiển: Bắt đầu, Tạm dừng, Tiếp tục, Dừng, Reset
- Xem log thuật toán theo thời gian thực
- Xem thống kê kết quả
Hiển thị đầy đủ, không sử dụng thanh cuộn, không đè nút lên nhau.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTextEdit, QFrame, QSizePolicy, QGridLayout, QScrollArea, QStyle, QApplication
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor, QIcon
from typing import Optional

from core.utils import format_time_ms, get_timestamp


# ──────────────────────────────────────────────────────────────
# Stylesheet chung - Phong cách Google Material / Glassmorphism tối giản
# ──────────────────────────────────────────────────────────────

PANEL_STYLESHEET = """
    QWidget#controlPanel {
        background-color: #FFFFFF;
        border: 1px solid #DDE7F5;
        border-radius: 10px;
    }
    QScrollArea#controlScroll {
        border: none;
        background: transparent;
    }
    QWidget#controlPanelContent {
        background-color: #FFFFFF;
    }
    QScrollBar:vertical {
        background: #F4F7FC;
        width: 10px;
        margin: 4px 2px 4px 2px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical {
        background: #B8C7DC;
        min-height: 42px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical:hover {
        background: #7FA6D9;
    }
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {
        height: 0px;
        background: transparent;
        border: none;
    }
    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {
        background: transparent;
    }
    QScrollBar:horizontal {
        background: #F4F7FC;
        height: 10px;
        margin: 2px 4px 2px 4px;
        border-radius: 5px;
    }
    QScrollBar::handle:horizontal {
        background: #B8C7DC;
        min-width: 42px;
        border-radius: 5px;
    }
    QScrollBar::handle:horizontal:hover {
        background: #7FA6D9;
    }
    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {
        width: 0px;
        background: transparent;
        border: none;
    }
    QScrollBar::add-page:horizontal,
    QScrollBar::sub-page:horizontal {
        background: transparent;
    }
    
    /* Section Headers */
    QLabel[class="sectionHeader"] {
        font-family: 'Segoe UI';
        font-size: 15px;
        font-weight: 800;
        color: #0057E7;
        margin-top: 8px;
        margin-bottom: 4px;
    }
    
    /* ComboBox */
    QComboBox {
        font-family: 'Segoe UI';
        font-size: 13px;
        font-weight: 600;
        padding: 8px 14px;
        border: 1px solid #D7E3F4;
        border-radius: 8px;
        background-color: #FFFFFF;
        color: #12326B;
        min-height: 40px;
    }
    QComboBox:hover {
        border-color: #1A73E8;
        background-color: #FFFFFF;
    }
    QComboBox::drop-down {
        border: none;
        width: 20px;
    }
    QComboBox QAbstractItemView {
        font-size: 12px;
        padding: 4px;
        border: 1px solid #DADCE0;
        border-radius: 6px;
        background-color: #FFFFFF;
        selection-background-color: #E8F0FE;
        selection-color: #1A73E8;
    }
    
    /* Labels */
    QLabel {
        font-family: 'Segoe UI';
        color: #3C4043;
    }
    
    /* Text Edit (Log) */
    QTextEdit {
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 12px;
        border: 1px solid #D7E3F4;
        border-radius: 8px;
        background-color: #FFFFFF;
        color: #0F2E66;
        padding: 8px;
        line-height: 1.3;
    }
    
    /* Control Buttons */
    QPushButton {
        font-family: 'Segoe UI';
        font-size: 13px;
        font-weight: 700;
        border: none;
        border-radius: 8px;
        padding: 8px 6px;
        min-height: 40px;
    }
    
    QPushButton#btnStart {
        color: white;
        background-color: #0B73F6;
    }
    QPushButton#btnStart:hover {
        background-color: #1557B0;
    }
    QPushButton#btnStart:pressed {
        background-color: #11458F;
    }
    QPushButton#btnStart:disabled {
        background-color: #F1F3F4;
        color: #5F6368;
    }
    
    QPushButton#btnPause {
        color: #1A73E8;
        background-color: #E9F2FF;
    }
    QPushButton#btnPause:hover {
        background-color: #D2E3FC;
    }
    QPushButton#btnPause:disabled {
        background-color: #F8F9FA;
        color: #DADCE0;
    }
    
    QPushButton#btnStop {
        color: #D93025;
        background-color: #FDE9E7;
    }
    QPushButton#btnStop:hover {
        background-color: #FAD2CF;
    }
    QPushButton#btnStop:disabled {
        background-color: #F8F9FA;
        color: #DADCE0;
    }
    
    QPushButton#btnReset {
        color: #0B63E5;
        background-color: #EDF6FF;
    }
    QPushButton#btnReset:hover {
        background-color: #E8EAED;
    }
    
    QPushButton#btnGraphEdit {
        color: #188038;
        background-color: #E6F4EA;
    }
    QPushButton#btnGraphEdit:hover {
        background-color: #CEEAD6;
    }
    QPushButton#btnGraphEdit:disabled {
        background-color: #F8F9FA;
        color: #DADCE0;
    }
    
    /* Stat cards */
    QFrame#statCard {
        background-color: #FFFFFF;
        border: 1px solid #DDE7F5;
        border-radius: 8px;
        padding: 10px 8px;
    }
    QFrame#statCard:hover {
        border-color: #D2E3FC;
        background-color: #F8F9FA;
    }
"""


class ControlPanel(QWidget):
    """
    Panel điều khiển bên phải của ứng dụng.
    Được tối ưu hiển thị đầy đủ trực tiếp không cần cuộn, không đè nút lên nhau.
    
    Signals:
        start_clicked: Khi nhấn nút Bắt đầu
        pause_clicked: Khi nhấn nút Tạm dừng
        resume_clicked: Khi nhấn nút Tiếp tục
        stop_clicked: Khi nhấn nút Dừng
        reset_clicked: Khi nhấn nút Reset
        algorithm_changed: Khi thay đổi thuật toán (str)
        heuristic_changed: Khi thay đổi heuristic (str)
    """
    
    start_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    resume_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    reset_clicked = pyqtSignal()
    graph_edit_clicked = pyqtSignal()
    algorithm_changed = pyqtSignal(str)
    heuristic_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("controlPanel")
        self.setFixedWidth(470)
        self.setStyleSheet(PANEL_STYLESHEET)
        
        self._is_paused = False
        self._setup_ui()
    
    def _setup_ui(self):
        """Xây dựng giao diện panel điều khiển phân bổ theo tỷ lệ tự động."""
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        
        scroll = QScrollArea()
        scroll.setObjectName("controlScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        content = QWidget()
        content.setObjectName("controlPanelContent")
        scroll.setWidget(content)
        outer_layout.addWidget(scroll)
        
        main_layout = QVBoxLayout(content)
        main_layout.setContentsMargins(18, 14, 18, 16)
        main_layout.setSpacing(12)
        
        # ── 1. Chọn thuật toán ──
        lbl_algo = QLabel("1. Chọn thuật toán")
        lbl_algo.setProperty("class", "sectionHeader")
        self.algo_combo = QComboBox()
        self.algo_combo.addItems(["BFS", "DFS", "UCS", "Greedy", "A*"])
        self.algo_combo.setCurrentText("A*")
        self.algo_combo.currentTextChanged.connect(self._on_algorithm_changed)
        
        main_layout.addWidget(lbl_algo)
        main_layout.addWidget(self.algo_combo)
        
        # ── 2. Chọn heuristic ──
        lbl_heur = QLabel("2. Hàm heuristic")
        lbl_heur.setProperty("class", "sectionHeader")
        self.heuristic_combo = QComboBox()
        self.heuristic_combo.addItems(["Euclidean", "Manhattan"])
        self.heuristic_combo.currentTextChanged.connect(
            lambda t: self.heuristic_changed.emit(t))
        
        main_layout.addWidget(lbl_heur)
        main_layout.addWidget(self.heuristic_combo)
        
        # ── 2.5 Lựa chọn điểm xuất phát & đích (Thiết kế cực kỳ gọn) ──
        lbl_points = QLabel("Chọn điểm (Nhấn bản đồ hoặc danh sách)")
        lbl_points.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_points.setStyleSheet("color: #70757A; margin-top: 2px;")
        
        points_widget = QWidget()
        points_layout = QVBoxLayout(points_widget)
        points_layout.setContentsMargins(0, 0, 0, 0)
        points_layout.setSpacing(5)
        
        # Điểm đi
        start_row = QHBoxLayout()
        lbl_start = QLabel("● Điểm đi:")
        lbl_start.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_start.setMinimumWidth(86)
        self.start_label = QLabel("(Chọn trên bản đồ)")
        self.start_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.start_label.setStyleSheet("color: #1A73E8;")
        self.start_label.setWordWrap(False)
        self.start_combo = QComboBox()
        self.start_combo.setPlaceholderText("Danh sách...")
        self.start_combo.setMinimumWidth(150)
        self.start_combo.setMaximumWidth(170)
        
        start_row.addWidget(lbl_start)
        start_row.addWidget(self.start_label, 1)
        start_row.addWidget(self.start_combo)
        
        # Điểm đến
        goal_row = QHBoxLayout()
        lbl_goal = QLabel("● Điểm đến:")
        lbl_goal.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_goal.setMinimumWidth(86)
        self.goal_label = QLabel("(Chọn trên bản đồ)")
        self.goal_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.goal_label.setStyleSheet("color: #D93025;")
        self.goal_label.setWordWrap(False)
        self.goal_combo = QComboBox()
        self.goal_combo.setPlaceholderText("Danh sách...")
        self.goal_combo.setMinimumWidth(150)
        self.goal_combo.setMaximumWidth(170)
        
        goal_row.addWidget(lbl_goal)
        goal_row.addWidget(self.goal_label, 1)
        goal_row.addWidget(self.goal_combo)
        
        points_layout.addLayout(start_row)
        points_layout.addLayout(goal_row)
        
        main_layout.addWidget(lbl_points)
        main_layout.addWidget(points_widget)
        
        # ── 3. Điều khiển ── (1 hàng 4 nút theo UI Demo)
        lbl_ctrl = QLabel("3. Điều khiển")
        lbl_ctrl.setProperty("class", "sectionHeader")
        
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(6)
        
        self.btn_start = QPushButton("Bắt đầu")
        self.btn_start.setObjectName("btnStart")
        self.btn_start.clicked.connect(self.start_clicked.emit)
        
        self.btn_pause = QPushButton("Tạm dừng")
        self.btn_pause.setObjectName("btnPause")
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self._on_pause_clicked)
        
        self.btn_stop = QPushButton("Dừng")
        self.btn_stop.setObjectName("btnStop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_clicked.emit)
        
        self.btn_reset = QPushButton("Reset")
        self.btn_reset.setObjectName("btnReset")
        self.btn_reset.clicked.connect(self.reset_clicked.emit)
        
        ctrl_layout.addWidget(self.btn_start)
        ctrl_layout.addWidget(self.btn_pause)
        ctrl_layout.addWidget(self.btn_stop)
        ctrl_layout.addWidget(self.btn_reset)
        
        main_layout.addWidget(lbl_ctrl)
        main_layout.addLayout(ctrl_layout)
        
        self.btn_graph_edit = QPushButton("Chỉnh sửa node / cạnh")
        self.btn_graph_edit.setObjectName("btnGraphEdit")
        self.btn_graph_edit.clicked.connect(self.graph_edit_clicked.emit)
        main_layout.addWidget(self.btn_graph_edit)
        
        self._setup_button_icons()
        
        # ── 4. Bảng log kết quả ──
        lbl_log = QLabel("4. Bản log kết quả")
        lbl_log.setProperty("class", "sectionHeader")
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        # Để log chiếm toàn bộ không gian co giãn linh hoạt
        self.log_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.log_text.setMinimumHeight(190)
        
        main_layout.addWidget(lbl_log)
        main_layout.addWidget(self.log_text)
        
        # ── 5. Thống kê ──
        lbl_stat = QLabel("5. Thống kê")
        lbl_stat.setProperty("class", "sectionHeader")
        
        stat_layout = QHBoxLayout()
        stat_layout.setSpacing(5)
        
        self.stat_distance = self._create_stat_card("Quãng đường", "— m", "🛣️")
        self.stat_nodes = self._create_stat_card("Số node duyệt", "—", "🔍")
        self.stat_time = self._create_stat_card("Thời gian xử lý", "— ms", "⏱️")
        
        stat_layout.addWidget(self.stat_distance["frame"])
        stat_layout.addWidget(self.stat_nodes["frame"])
        stat_layout.addWidget(self.stat_time["frame"])
        
        main_layout.addWidget(lbl_stat)
        main_layout.addLayout(stat_layout)
    
    def _create_stat_card(self, title: str, value: str, icon: str) -> dict:
        """Tạo thẻ thống kê ngang gọn gàng, co giãn tốt."""
        frame = QFrame()
        frame.setObjectName("statCard")
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        # Biểu tượng
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Segoe UI", 13))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedSize(30, 30)
        icon_label.setStyleSheet("""
            background-color: #EEF5FF;
            border-radius: 15px;
            color: #1A73E8;
        """)
        
        # Nội dung text
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(0)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #15346F;")
        title_label.setWordWrap(True)
        
        value_label = QLabel(value)
        value_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        value_label.setStyleSheet("color: #0057E7;")
        
        info_layout.addWidget(title_label)
        info_layout.addWidget(value_label)
        
        layout.addWidget(icon_label)
        layout.addWidget(info_widget, 1)
        
        return {"frame": frame, "title": title_label, "value": value_label, "icon": icon_label}
    
    def _setup_button_icons(self):
        """Dùng icon native của Qt để tránh lỗi hiển thị emoji/ký tự đặc biệt."""
        self._icon_play = self._standard_icon("SP_MediaPlay", "SP_ArrowRight")
        self._icon_pause = self._standard_icon("SP_MediaPause", "SP_TitleBarMinButton")
        self._icon_stop = self._standard_icon("SP_MediaStop", "SP_DialogCancelButton")
        self._icon_reset = self._standard_icon("SP_BrowserReload", "SP_BrowserReload")
        self._icon_edit = self._standard_icon("SP_FileDialogDetailedView", "SP_FileDialogListView")
        
        for button in (self.btn_start, self.btn_pause, self.btn_stop, self.btn_reset, self.btn_graph_edit):
            button.setIconSize(QSize(18, 18))
        
        self.btn_start.setIcon(self._icon_play)
        self.btn_stop.setIcon(self._icon_stop)
        self.btn_reset.setIcon(self._icon_reset)
        self.btn_graph_edit.setIcon(self._icon_edit)
        self._set_pause_button(paused=False)
    
    def _standard_icon(self, preferred: str, fallback: str):
        pixmap = getattr(QStyle.StandardPixmap, preferred, None)
        if pixmap is None:
            pixmap = getattr(QStyle.StandardPixmap, fallback, QStyle.StandardPixmap.SP_FileIcon)
        style = self.style()
        if style is None:
            app = QApplication.instance()
            if app is not None:
                style = app.style()
                
        if style is not None:
            return style.standardIcon(pixmap)
            
        return QIcon()
    
    def _set_pause_button(self, paused: bool):
        if paused:
            self.btn_pause.setText("Tiếp tục")
            self.btn_pause.setIcon(self._icon_play)
        else:
            self.btn_pause.setText("Tạm dừng")
            self.btn_pause.setIcon(self._icon_pause)
    
    # ──────────────────────────────────────────────────
    # Các phương thức cập nhật giao diện
    # ──────────────────────────────────────────────────
    
    def populate_node_combos(self, nodes: list):
        """Điền danh sách các node vào 2 combo box."""
        self.start_combo.clear()
        self.goal_combo.clear()
        
        self.start_combo.addItem("", "")
        self.goal_combo.addItem("", "")
        
        for node_id, name in nodes:
            display_name = name if name else "(khong co ten)"
            display = f"{display_name} ({node_id})"
            self.start_combo.addItem(display, node_id)
            self.goal_combo.addItem(display, node_id)
    
    def set_start_display(self, name: str):
        """Cập nhật text hiển thị điểm bắt đầu."""
        # Giới hạn độ dài để tránh đè nút
        if len(name) > 20:
            name = name[:18] + "..."
        self.start_label.setText(name)
    
    def set_goal_display(self, name: str):
        """Cập nhật text hiển thị điểm đích."""
        if len(name) > 20:
            name = name[:18] + "..."
        self.goal_label.setText(name)
    
    def add_log(self, message: str):
        """Thêm một bản ghi log có định dạng HTML theo style UI Demo."""
        timestamp = get_timestamp()
        
        icon = "<span style='color:#1A73E8;'>●</span>"
        if "✅" in message:
            icon = "<span style='color:#34A853;'>✔</span>"
            message = message.replace("✅", "")
        elif "❌" in message:
            icon = "<span style='color:#EA4335;'>✘</span>"
            message = message.replace("❌", "")
        elif "⚠️" in message:
            icon = "<span style='color:#FBBC05;'>⚠</span>"
            message = message.replace("⚠️", "")
        elif "⭐" in message:
            icon = "<span style='color:#FBBC05;'>★</span>"
            message = message.replace("⭐", "")
        elif "🔍" in message:
            icon = "<span style='color:#1A73E8;'>🔍</span>"
            message = message.replace("🔍", "")
        elif "📍" in message:
            icon = "<span style='color:#34A853;'>📍</span>"
            message = message.replace("📍", "")
        elif "🚀" in message:
            icon = "<span style='color:#1A73E8;'>🚀</span>"
            message = message.replace("🚀", "")
        elif "📐" in message:
            icon = "<span style='color:#1A73E8;'>📐</span>"
            message = message.replace("📐", "")
        elif "🛣️" in message:
            icon = "<span style='color:#1A73E8;'>⊙</span>"
            message = message.replace("🛣️", "")
        elif "⏱️" in message:
            icon = "<span style='color:#1A73E8;'>⊙</span>"
            message = message.replace("⏱️", "")
        elif "⏳" in message:
            icon = "<span style='color:#1A73E8;'>⏳</span>"
            message = message.replace("⏳", "")
        
        # Format theo UI Demo: icon + timestamp + message + timestamp bên phải
        formatted_message = f"""
            <div style='margin-bottom: 2px; line-height: 1.2;'>
                <table width='100%' cellpadding='0' cellspacing='0' border='0'><tr>
                    <td style='white-space: nowrap; vertical-align: top;'>
                        {icon}&nbsp;
                        <span style='color:#70757A; font-size: 10px;'>{timestamp}</span>&nbsp;&nbsp;
                        <span style='color:#202124; font-size: 11px;'>{message.strip()}</span>
                    </td>
                    <td style='text-align: right; white-space: nowrap; vertical-align: top; color:#70757A; font-size: 9px; padding-left: 8px;'>
                        {timestamp}
                    </td>
                </tr></table>
            </div>
        """
        
        self.log_text.append(formatted_message)
        
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)
    
    def clear_log(self):
        """Xóa trắng bảng log."""
        self.log_text.clear()
    
    def update_stats(self, distance: Optional[float] = None, node_count: Optional[int] = None,
                     time_ms: Optional[float] = None):
        """Cập nhật dữ liệu thẻ thống kê."""
        if distance is not None:
            self.stat_distance["value"].setText(f"{distance:.1f} m")
        if node_count is not None:
            self.stat_nodes["value"].setText(str(node_count))
        if time_ms is not None:
            self.stat_time["value"].setText(format_time_ms(time_ms))
    
    def reset_stats(self):
        """Reset các thẻ thống kê về trạng thái ban đầu."""
        self.stat_distance["value"].setText("— m")
        self.stat_nodes["value"].setText("—")
        self.stat_time["value"].setText("— ms")
    
    def get_selected_algorithm(self) -> str:
        """Trả về tên thuật toán đang chọn."""
        return self.algo_combo.currentText()
    
    def get_selected_heuristic(self) -> str:
        """Trả về tên heuristic đang chọn."""
        return self.heuristic_combo.currentText()
    
    # ──────────────────────────────────────────────────
    # Trạng thái các nút điều khiển
    # ──────────────────────────────────────────────────
    
    def set_running_state(self, running: bool):
        """Cập nhật tính năng vô hiệu hóa/bật khi thuật toán đang chạy."""
        self.btn_start.setEnabled(not running)
        self.btn_pause.setEnabled(running)
        self.btn_stop.setEnabled(running)
        self.algo_combo.setEnabled(not running)
        self.heuristic_combo.setEnabled(not running)
        self.start_combo.setEnabled(not running)
        self.goal_combo.setEnabled(not running)
        self.btn_graph_edit.setEnabled(not running)
        
        if running:
            self._is_paused = False
            self._set_pause_button(paused=False)
    
    def set_finished_state(self):
        """Thiết lập trạng thái khi hoàn tất/dừng tìm kiếm."""
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.algo_combo.setEnabled(True)
        self.heuristic_combo.setEnabled(True)
        self.start_combo.setEnabled(True)
        self.goal_combo.setEnabled(True)
        self.btn_graph_edit.setEnabled(True)
        self._is_paused = False
        self._set_pause_button(paused=False)
    
    def _on_pause_clicked(self):
        """Bật tắt tạm dừng/tiếp tục."""
        if self._is_paused:
            self._is_paused = False
            self._set_pause_button(paused=False)
            self.resume_clicked.emit()
        else:
            self._is_paused = True
            self._set_pause_button(paused=True)
            self.pause_clicked.emit()
    
    def _on_algorithm_changed(self, algo_name: str):
        """Cập nhật hiển thị heuristic dựa trên thuật toán."""
        needs_heuristic = algo_name in ("Greedy", "A*")
        self.heuristic_combo.setEnabled(needs_heuristic)
        
        if not needs_heuristic:
            self.heuristic_combo.setStyleSheet("QComboBox { color: #B0BEC5; }")
        else:
            self.heuristic_combo.setStyleSheet("")
        
        self.algorithm_changed.emit(algo_name)
