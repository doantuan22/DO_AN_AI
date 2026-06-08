"""
map_widget.py - Widget hiển thị bản đồ HCMUTE (Redesigned matching UI_demo)
========================================================================
Sử dụng QGraphicsView/QGraphicsScene để hiển thị:
- Ảnh bản đồ nền
- Các node với màu sắc theo trạng thái
- Các cạnh nối các node
- Đường đi kết quả highlight
- Bản chú thích (legend) nổi cố định
- Các nút zoom nổi cố định (+ / - / 🎯)
- Bong bóng thông tin (tooltip) ghim mốc Bắt đầu/Đích cực đẹp
"""

import os
import math
from typing import Optional, Dict, List, Tuple, Any

from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
    QGraphicsLineItem, QGraphicsTextItem, QGraphicsPixmapItem,
    QGraphicsPathItem, QGraphicsRectItem, QWidget, QFrame,
    QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QMenu
)
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal, QTimer
from PyQt6.QtGui import (
    QPixmap, QPen, QBrush, QColor, QFont, QPainter,
    QPainterPath, QRadialGradient, QLinearGradient, QFontMetrics,
    QMouseEvent, QWheelEvent, QResizeEvent, QAction
)

from core.graph import Graph


# ──────────────────────────────────────────────────────────────
# Bảng màu hiển thị
# ──────────────────────────────────────────────────────────────

class MapColors:
    """Định nghĩa hệ màu cho bản đồ."""
    EDGE_NORMAL = QColor(172, 181, 204, 150)          # Xám xanh sáng
    EDGE_PATH = QColor(0, 204, 186)                   # Xanh ngọc giống UI demo
    
    NODE_NORMAL = QColor(16, 117, 245)                # Xanh dương Google
    NODE_START = QColor(15, 190, 90)                  # Xanh lá
    NODE_GOAL = QColor(234, 67, 53)                   # Đỏ
    NODE_CURRENT = QColor(255, 152, 0)                # Cam
    NODE_VISITED = QColor(186, 154, 240)              # Tím nhạt
    NODE_FRONTIER = QColor(255, 213, 79)              # Vàng
    NODE_PATH = QColor(0, 170, 80)                    # Xanh lá đậm
    
    NODE_BORDER = QColor(255, 255, 255)               # Viền trắng
    NODE_BORDER_START = QColor(0, 150, 60)            # Viền xanh lá đậm
    NODE_BORDER_GOAL = QColor(200, 30, 30)            # Viền đỏ đậm
    
    TEXT_LABEL = QColor(32, 33, 36)                   # Màu chữ Google Dark Grey
    TEXT_LABEL_BG = QColor(255, 255, 255, 230)        # Nền trắng mờ
    TEXT_LABEL_BORDER = QColor(218, 220, 224)         # Viền xám mờ


# Helper xác định icon dựa trên tên địa điểm
def get_node_icon(name: str) -> str:
    if "Cổng" in name:
        return "📍"
    elif "Khối" in name or "Khoa" in name or "Tòa" in name:
        return "🏢"
    elif "Xưởng" in name:
        return "🛠️"
    elif "Thư viện" in name:
        return "📖"
    elif "Ký túc xá" in name or "KTX" in name:
        return "🏠"
    elif "Sân" in name or "thi đấu" in name or "bong" in name:
        return "⚽"
    elif "Căn tin" in name:
        return "🍴"
    elif "Nhà xe" in name or "Bãi xe" in name:
        return "🅿️"
    elif "Hồ" in name:
        return "🌊"
    elif "Hội trường" in name:
        return "🎭"
    elif "Trung tâm" in name:
        return "🏢"
    return "🏫"


# ──────────────────────────────────────────────────────────────
# MapPinTooltip - Bong bóng ghim mốc Start/Goal cực đẹp
# ──────────────────────────────────────────────────────────────

class MapPinTooltip(QGraphicsPathItem):
    """
    Bong bóng thoại hiển thị thông tin BẮT ĐẦU / ĐÍCH trên bản đồ.
    Có mũi nhọn hướng xuống node, thiết kế shadow và bo góc cao cấp.
    """
    def __init__(self, name: str, is_start: bool, parent=None):
        super().__init__(parent)
        self.name = name
        self.is_start = is_start
        
        # Cấu hình màu sắc
        self.accent_color = QColor(15, 190, 90) if is_start else QColor(234, 67, 53)
        self.bg_color = QColor(255, 255, 255)
        
        # Font chữ đo đạc độ rộng
        title_font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        name_font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        
        title_text = "BẮT ĐẦU" if is_start else "ĐÍCH"
        fm_title = QFontMetrics(title_font)
        fm_name = QFontMetrics(name_font)
        
        # Chiều rộng bong bóng = chiều dài text dài nhất + padding
        w = max(fm_title.horizontalAdvance(title_text), fm_name.horizontalAdvance(name)) + 24
        w = max(w, 90)  # Chiều rộng tối thiểu
        h = 42          # Chiều cao cố định
        
        self.w = w
        self.h = h
        
        # Vẽ bong bóng chỉ xuống (0, 0)
        # (0, 0) là đỉnh nhọn của mũi tên hướng vào node
        path = QPainterPath()
        # Hình hộp bo tròn ở trên
        path.addRoundedRect(QRectF(-w/2, -h - 8, w, h), 6, 6)
        
        # Mũi tên chỉ xuống
        path.moveTo(-6, -8)
        path.lineTo(0, 0)
        path.lineTo(6, -8)
        path.closeSubpath()
        
        self.setPath(path)
        
        # Định dạng style cho ghim
        self.setBrush(QBrush(self.bg_color))
        self.setPen(QPen(self.accent_color, 2))
        self.setZValue(25)  # Hiển thị trên tất cả node/cạnh
        
        # Thêm text nội dung vào bên trong. QTextDocument có margin mặc định,
        # nên cần set margin = 0 và textWidth đúng bằng thân tooltip để text nằm chính giữa.
        self.text_item = QGraphicsTextItem(self)
        self.text_item.setZValue(26)
        
        # HTML hiển thị title và nội dung
        html = f"""
            <div style='text-align: center; line-height: 1.15;'>
                <span style='color: {self.accent_color.name()}; font-family: Segoe UI; font-size: 8pt; font-weight: 800;'>{title_text}</span><br>
                <span style='color: #202124; font-family: Segoe UI; font-size: 9pt; font-weight: 800;'>{name}</span>
            </div>
        """
        self.text_item.document().setDocumentMargin(0)
        self.text_item.setTextWidth(w)
        self.text_item.setHtml(html)
        # Căn giữa theo đúng khung bo góc, không lệch trái/phải theo font render.
        self.text_item.setPos(-w / 2, -h - 8 + 5)


# ──────────────────────────────────────────────────────────────
# Node Item - Đại diện cho một node trên bản đồ
# ──────────────────────────────────────────────────────────────

class NodeItem(QGraphicsEllipseItem):
    """
    Custom QGraphicsEllipseItem đại diện cho một node trên bản đồ.
    Hỗ trợ hover effect phóng to, đổi màu động.
    """
    
    NODE_RADIUS = 7.5      # Bán kính node thông thường
    NODE_RADIUS_BIG = 11.5 # Bán kính node được highlight
    CLICK_RADIUS = 16      # Bán kính phát hiện click
    
    def __init__(self, node_id: str, x: float, y: float, name: str = ""):
        r = self.NODE_RADIUS
        super().__init__(-r, -r, r * 2, r * 2)
        
        self.node_id = node_id
        self.node_name = name
        self.setPos(x, y)
        
        # Style mặc định
        self.setBrush(QBrush(MapColors.NODE_NORMAL))
        self.setPen(QPen(MapColors.NODE_BORDER, 2.5))
        
        self.setAcceptHoverEvents(True)
        self.setToolTip(name if name else node_id)
        self.setZValue(10)
        
        self._state = "normal"
        self._hover = False
        self.setOpacity(0.95)
    
    def set_state(self, state: str):
        """Đặt trạng thái và tự động cập nhật màu sắc & kích thước node."""
        self._state = state
        
        color_map = {
            "normal": (MapColors.NODE_NORMAL, MapColors.NODE_BORDER, self.NODE_RADIUS),
            "start": (MapColors.NODE_START, MapColors.NODE_BORDER_START, self.NODE_RADIUS_BIG),
            "goal": (MapColors.NODE_GOAL, MapColors.NODE_BORDER_GOAL, self.NODE_RADIUS_BIG),
            "current": (MapColors.NODE_CURRENT, QColor(255, 255, 255), self.NODE_RADIUS_BIG),
            "visited": (MapColors.NODE_VISITED, MapColors.NODE_BORDER, self.NODE_RADIUS),
            "frontier": (MapColors.NODE_FRONTIER, MapColors.NODE_BORDER, self.NODE_RADIUS),
            "path": (MapColors.NODE_PATH, QColor(255, 255, 255), self.NODE_RADIUS_BIG),
        }
        
        color, border, radius = color_map.get(state, color_map["normal"])
        
        self.setRect(-radius, -radius, radius * 2, radius * 2)
        self.setBrush(QBrush(color))
        self.setPen(QPen(border, 2.5 if radius == self.NODE_RADIUS else 3.0))
        
        # Z-value order
        z_order = {
            "normal": 10, "visited": 11, "frontier": 12,
            "current": 15, "path": 14, "start": 16, "goal": 16
        }
        self.setZValue(z_order.get(state, 10))
    
    def hoverEnterEvent(self, event):
        self._hover = True
        self.setScale(1.25)
        self.setOpacity(1.0)
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        self._hover = False
        self.setScale(1.0)
        self.setOpacity(0.95)
        super().hoverLeaveEvent(event)


class PulseRing(QGraphicsEllipseItem):
    """Vòng pulse/ripple không block UI, được MapWidget cập nhật bằng QTimer."""

    def __init__(
        self,
        x: float,
        y: float,
        color: QColor,
        start_radius: float = 10,
        end_radius: float = 34,
        max_frames: int = 18,
        delay_frames: int = 0,
        fill_alpha: int = 28,
    ):
        super().__init__(-start_radius, -start_radius, start_radius * 2, start_radius * 2)
        self.setPos(x, y)
        self.color = QColor(color)
        self.frame = -delay_frames
        self.max_frames = max_frames
        self.start_radius = start_radius
        self.end_radius = end_radius
        self.fill_alpha = fill_alpha
        self.setBrush(QBrush(QColor(color.red(), color.green(), color.blue(), fill_alpha)))
        self.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 160), 2.4))
        self.setZValue(9)

    def advance_frame(self) -> bool:
        self.frame += 1
        if self.frame < 0:
            return False
        t = self.frame / self.max_frames
        radius = self.start_radius + (self.end_radius - self.start_radius) * t
        alpha = max(0, int(150 * (1.0 - t)))
        fill_alpha = max(0, int(self.fill_alpha * (1.0 - t)))
        self.setRect(-radius, -radius, radius * 2, radius * 2)
        self.setBrush(QBrush(QColor(self.color.red(), self.color.green(), self.color.blue(), fill_alpha)))
        self.setPen(QPen(QColor(self.color.red(), self.color.green(), self.color.blue(), alpha), 2.2))
        return self.frame >= self.max_frames


# ──────────────────────────────────────────────────────────────
# Map Widget chính
# ──────────────────────────────────────────────────────────────

class MapWidget(QGraphicsView):
    """
    Widget hiển thị bản đồ HCMUTE với cấu trúc widget nổi cố định.
    Không bị méo mó, lệch vị trí khi zoom/resize.
    """
    
    node_clicked = pyqtSignal(str)
    graph_edit_clicked = pyqtSignal()
    sample_walk_clicked = pyqtSignal()
    algorithm_speed_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._scene = QGraphicsScene()
        self.setScene(self._scene)
        
        # Cấu hình tối ưu hiển thị của View
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing |
            QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.setStyleSheet("""
            QGraphicsView {
                border: 1px solid #DDE7F5;
                border-radius: 10px;
                background-color: #F5F8FC;
            }
        """)
        
        # Danh sách lưu trữ items
        self._graph: Optional[Graph] = None
        self._map_pixmap: Optional[QGraphicsPixmapItem] = None
        self._node_items: Dict[str, NodeItem] = {}
        self._edge_items: List[QGraphicsLineItem] = []
        self._path_items: List[QGraphicsLineItem] = []
        self._label_items: List[Any] = []
        self._pulse_items: List[PulseRing] = []
        self._edge_visible = True
        self._graph_overlay_hidden = False
        self._edge_width = 2.5
        self._edge_opacity = 180
        self._route_timer = QTimer(self)
        self._route_timer.timeout.connect(self._animate_route_step)
        self._route_flow_timer = QTimer(self)
        self._route_flow_timer.timeout.connect(self._animate_route_flow)
        self._route_segments: List[Tuple[float, float, float, float]] = []
        self._route_segment_index = 0
        self._route_segment_progress = 0
        self._route_active_line: Optional[QGraphicsLineItem] = None
        self._route_active_glow: Optional[QGraphicsLineItem] = None
        self._route_dot: Optional[QGraphicsEllipseItem] = None
        self._route_flow_items: List[QGraphicsLineItem] = []
        self._route_segment_items: List[List[QGraphicsLineItem]] = []
        self._route_flow_phase = 0.0
        self._avatar_timer = QTimer(self)
        self._avatar_timer.timeout.connect(self._animate_avatar_step)
        self._avatar_item: Optional[QGraphicsPixmapItem] = None
        self._avatar_segments: List[Tuple[float, float, float, float]] = []
        self._avatar_segment_index = 0
        self._avatar_segment_progress = 0
        self._avatar_step_count = 20
        self._avatar_hiding_route = False
        self._last_current_node: Optional[str] = None
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._tick_pulses)
        
        # Trạng thái chọn điểm đi & đến
        self._start_node: Optional[str] = None
        self._goal_node: Optional[str] = None
        
        # Tooltips ghim điểm Bắt đầu / Đích
        self._start_tooltip: Optional[MapPinTooltip] = None
        self._goal_tooltip: Optional[MapPinTooltip] = None
        
        # Các widget nổi (Legend, Zoom, Lớp bản đồ)
        self._legend_card: Optional[QFrame] = None
        self._zoom_card: Optional[QFrame] = None
        self._graph_edit_button: Optional[QPushButton] = None
        self._graph_toggle_button: Optional[QPushButton] = None
        self._sample_walk_button: Optional[QPushButton] = None
        self._speed_button: Optional[QPushButton] = None
        self._speed_name = "Trung bình"
        
        # Khởi tạo các widget nổi
        self._setup_floating_controls()

    def _set_canvas_background(self, color: QColor):
        """Đồng bộ nền ngoài ảnh bản đồ với màu nền thực của map khi zoom out."""
        self.setBackgroundBrush(QBrush(color))
        self._scene.setBackgroundBrush(QBrush(color))
        self.viewport().setStyleSheet(f"background-color: {color.name()};")
    
    def _setup_floating_controls(self):
        """Khởi tạo và cấu hình các widget nổi cố định phía trên View."""
        # 1. Legend Card (Góc trên bên trái)
        self._legend_card = QFrame(self)
        self._legend_card.setObjectName("legendCard")
        self._legend_card.setStyleSheet("""
            QFrame#legendCard {
                background-color: rgba(255, 255, 255, 0.95);
                border: 1px solid rgba(215, 227, 244, 0.95);
                border-radius: 10px;
            }
            QLabel {
                font-family: 'Segoe UI';
                font-size: 13px;
                color: #12326B;
                font-weight: bold;
            }
        """)
        legend_layout = QHBoxLayout(self._legend_card)
        legend_layout.setContentsMargins(14, 9, 14, 9)
        legend_layout.setSpacing(20)
        
        node_dot = QLabel("<span style='color: #4285F4; font-size: 14px;'>●</span> Node")
        edge_line = QLabel("<span style='color: #C0C5CD; font-size: 14px;'>━</span> Đường nội bộ")
        path_line = QLabel("<span style='color: #00E676; font-size: 14px;'>━</span> Lộ trình tối ưu")
        
        legend_layout.addWidget(node_dot)
        legend_layout.addWidget(edge_line)
        legend_layout.addWidget(path_line)
        self._legend_card.show()
        
        # 2. Zoom Controls Card (Góc trên bên phải)
        self._zoom_card = QFrame(self)
        self._zoom_card.setObjectName("zoomCard")
        self._zoom_card.setStyleSheet("""
            QFrame#zoomCard {
                background-color: rgba(255, 255, 255, 0.95);
                border: 1px solid rgba(215, 227, 244, 0.95);
                border-radius: 8px;
                padding: 2px;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                font-family: 'Segoe UI';
                font-size: 18px;
                font-weight: bold;
                color: #123D91;
                min-height: 34px;
                min-width: 34px;
            }
            QPushButton:hover {
                background-color: #F1F3F4;
                color: #1A73E8;
            }
        """)
        zoom_layout = QVBoxLayout(self._zoom_card)
        zoom_layout.setContentsMargins(2, 2, 2, 2)
        zoom_layout.setSpacing(4)
        
        self.btn_zoom_in = QPushButton("+")
        self.btn_zoom_out = QPushButton("−")
        self.btn_zoom_reset = QPushButton("🎯")
        
        self.btn_zoom_in.clicked.connect(self.zoom_in)
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        self.btn_zoom_reset.clicked.connect(self.zoom_reset)
        
        zoom_layout.addWidget(self.btn_zoom_in)
        zoom_layout.addWidget(self.btn_zoom_out)
        zoom_layout.addWidget(self.btn_zoom_reset)
        self._zoom_card.show()
        
        # 3. Graph overlay actions (Góc dưới bên trái)
        self._graph_toggle_button = QPushButton(self)
        self._graph_toggle_button.setObjectName("graphToggleButton")
        self._graph_toggle_button.setText("◉")
        self._graph_toggle_button.setToolTip("Tạm ẩn đồ thị")
        self._graph_toggle_button.clicked.connect(self.toggle_graph_overlay)
        self._graph_toggle_button.setStyleSheet("""
            QPushButton#graphToggleButton {
                background-color: rgba(255, 255, 255, 0.95);
                border: 1px solid rgba(215, 227, 244, 0.95);
                border-radius: 12px;
                color: #00A889;
                font-family: 'Segoe UI';
                font-size: 21px;
                font-weight: 900;
                min-height: 48px;
                min-width: 48px;
            }
            QPushButton#graphToggleButton:hover {
                background-color: #ECFDF8;
                border-color: #00C896;
            }
        """)
        self._graph_toggle_button.show()

        self._sample_walk_button = QPushButton(self)
        self._sample_walk_button.setObjectName("sampleWalkButton")
        self._sample_walk_button.setText("▶")
        self._sample_walk_button.setToolTip("Đi mẫu theo lộ trình")
        self._sample_walk_button.setEnabled(False)
        self._sample_walk_button.clicked.connect(self.sample_walk_clicked.emit)
        self._sample_walk_button.setStyleSheet("""
            QPushButton#sampleWalkButton {
                background-color: rgba(255, 255, 255, 0.95);
                border: 1px solid rgba(215, 227, 244, 0.95);
                border-radius: 12px;
                color: #0B74FF;
                font-family: 'Segoe UI';
                font-size: 19px;
                font-weight: 900;
                min-height: 48px;
                min-width: 48px;
            }
            QPushButton#sampleWalkButton:hover {
                background-color: #EEF5FF;
                border-color: #0B74FF;
            }
            QPushButton#sampleWalkButton:disabled {
                color: #CBD5E1;
                background-color: rgba(248, 250, 252, 0.88);
                border-color: #E2E8F0;
            }
        """)
        self._sample_walk_button.show()

        self._speed_button = QPushButton(self)
        self._speed_button.setObjectName("speedButton")
        self._speed_button.setText("⏱")
        self._speed_button.setToolTip("Tốc độ xử lý: Trung bình")
        self._speed_button.clicked.connect(self._show_speed_menu)
        self._speed_button.setStyleSheet("""
            QPushButton#speedButton {
                background-color: rgba(255, 255, 255, 0.95);
                border: 1px solid rgba(215, 227, 244, 0.95);
                border-radius: 12px;
                color: #0B74FF;
                font-family: 'Segoe UI';
                font-size: 20px;
                font-weight: 900;
                min-height: 48px;
                min-width: 48px;
            }
            QPushButton#speedButton:hover {
                background-color: #EEF5FF;
                border-color: #0B74FF;
            }
        """)
        self._speed_button.show()

        self._graph_edit_button = QPushButton(self)
        self._graph_edit_button.setObjectName("graphEditButton")
        self._graph_edit_button.setText("⚙")
        self._graph_edit_button.setToolTip("Chỉnh sửa node / cạnh")
        self._graph_edit_button.clicked.connect(self.graph_edit_clicked.emit)
        self._graph_edit_button.setStyleSheet("""
            QPushButton#graphEditButton {
                background-color: rgba(255, 255, 255, 0.95);
                border: 1px solid rgba(215, 227, 244, 0.95);
                border-radius: 12px;
                color: #0B74FF;
                font-family: 'Segoe UI';
                font-size: 22px;
                font-weight: 900;
                min-height: 48px;
                min-width: 48px;
            }
            QPushButton#graphEditButton:hover {
                background-color: #EEF5FF;
                border-color: #0B74FF;
            }
            QPushButton#graphEditButton:disabled {
                color: #CBD5E1;
                background-color: rgba(248, 250, 252, 0.88);
                border-color: #E2E8F0;
            }
        """)
        self._graph_edit_button.show()

    def set_graph_edit_enabled(self, enabled: bool):
        """Bật/tắt nút chỉnh sửa graph nổi theo trạng thái chạy thuật toán."""
        if self._graph_edit_button:
            self._graph_edit_button.setEnabled(enabled)

    def set_sample_walk_enabled(self, enabled: bool):
        """Bật nút đi mẫu khi đã có đường đi hợp lệ."""
        if self._sample_walk_button:
            self._sample_walk_button.setEnabled(enabled)

    def _show_speed_menu(self):
        """Hiển thị menu chọn tốc độ mô phỏng thuật toán."""
        if self._speed_button is None:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #DDE6F2;
                border-radius: 8px;
                padding: 6px;
                font-family: 'Segoe UI';
                font-size: 13px;
                color: #0F172A;
            }
            QMenu::item {
                padding: 8px 26px 8px 12px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background-color: #EEF5FF;
                color: #0B74FF;
            }
        """)

        for speed_name in ("Nhanh", "Trung bình", "Chậm"):
            action = QAction(speed_name, menu)
            action.setCheckable(True)
            action.setChecked(speed_name == self._speed_name)
            action.triggered.connect(lambda checked=False, name=speed_name: self.set_algorithm_speed(name))
            menu.addAction(action)

        menu.exec(self._speed_button.mapToGlobal(self._speed_button.rect().bottomLeft()))

    def set_algorithm_speed(self, speed_name: str):
        """Cập nhật tốc độ được chọn và phát signal cho MainWindow."""
        if speed_name not in {"Nhanh", "Trung bình", "Chậm"}:
            return
        self._speed_name = speed_name
        if self._speed_button:
            self._speed_button.setToolTip(f"Tốc độ xử lý: {speed_name}")
        self.algorithm_speed_changed.emit(speed_name)

    def toggle_graph_overlay(self):
        """Tạm ẩn/hiện node, cạnh, nhãn và route trên bản đồ."""
        self.set_graph_overlay_hidden(not self._graph_overlay_hidden)

    def set_graph_overlay_hidden(self, hidden: bool):
        """Ẩn hiện lớp đồ thị mà không thay đổi dữ liệu graph hay JSON."""
        self._graph_overlay_hidden = hidden
        visible = not hidden

        for item in self._node_items.values():
            item.setVisible(visible)
        for item in self._edge_items:
            item.setVisible(visible and self._edge_visible)
        for item in self._path_items:
            item.setVisible(visible)
        for item in self._label_items:
            item.setVisible(visible)
        for item in self._pulse_items:
            item.setVisible(visible)
        if self._avatar_item:
            self._avatar_item.setVisible(visible)

        if self._start_tooltip:
            self._start_tooltip.setVisible(visible)
        if self._goal_tooltip:
            self._goal_tooltip.setVisible(visible)

        if hidden:
            self._route_timer.stop()
            self._route_flow_timer.stop()
        elif self._route_flow_items:
            self._route_flow_timer.start(42)
        if hidden:
            self._avatar_timer.stop()
        elif self._avatar_item and self._avatar_segments:
            self._avatar_timer.start(28)

        if self._graph_toggle_button:
            self._graph_toggle_button.setText("◎" if hidden else "◉")
            self._graph_toggle_button.setToolTip("Hiển thị lại đồ thị" if hidden else "Tạm ẩn đồ thị")
        
    def setup_map(self, graph: Graph, map_image_path: str):
        """Khởi tạo toàn bộ bản đồ."""
        self._graph = graph
        
        # Xóa các item khỏi scene
        self._scene.clear()
        self._node_items.clear()
        self._edge_items.clear()
        self._path_items.clear()
        self._label_items.clear()
        self._pulse_items.clear()
        self._route_timer.stop()
        self._route_flow_timer.stop()
        self._avatar_timer.stop()
        self._route_dot = None
        self._route_active_line = None
        self._route_active_glow = None
        self._route_flow_items.clear()
        self._route_segment_items.clear()
        self._avatar_item = None
        self._avatar_segments = []
        self._last_current_node = None
        self._start_tooltip = None
        self._goal_tooltip = None
        
        # 1. Vẽ bản đồ nền
        loaded = False
        if os.path.exists(map_image_path):
            pixmap = QPixmap(map_image_path)
            if not pixmap.isNull():
                image = pixmap.toImage()
                bg_color = QColor("#F5F8FC")
                if not image.isNull():
                    # Lấy màu nền từ góc ảnh map để vùng ngoài scene không bị trắng lệch tông.
                    bg_color = QColor(image.pixelColor(8, 8))
                self._set_canvas_background(bg_color)
                self._map_pixmap = self._scene.addPixmap(pixmap)
                if self._map_pixmap is not None:
                    self._map_pixmap.setZValue(0)
                    self._map_pixmap.setOpacity(0.82)
                    self._scene.setSceneRect(QRectF(pixmap.rect()))
                    overlay = self._scene.addRect(
                        QRectF(pixmap.rect()),
                        QPen(Qt.PenStyle.NoPen),
                        QBrush(QColor(245, 248, 252, 48))
                    )
                    if overlay is not None:
                        overlay.setZValue(1)
                    loaded = True
        
        if not loaded:
            self._scene.setSceneRect(0, 0, 1122, 1402)
            self._set_canvas_background(QColor("#F0F4F8"))
            bg = self._scene.addRect(0, 0, 1122, 1402,
                                     QPen(Qt.PenStyle.NoPen),
                                     QBrush(QColor("#F0F4F8")))
            if bg is not None:
                bg.setZValue(0)
                
        # 2. Vẽ các cạnh, node và nhãn
        self._draw_edges()
        self._draw_nodes()
        self._draw_labels()
        self.set_graph_overlay_hidden(self._graph_overlay_hidden)
        
        # 3. Fit view
        self.zoom_reset()
    
    def _draw_edges(self):
        """Vẽ đường đi kết nối các node."""
        if not self._graph:
            return
        
        edge_color = QColor(MapColors.EDGE_NORMAL)
        edge_color.setAlpha(self._edge_opacity)
        pen = QPen(edge_color, self._edge_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        
        for edge in self._graph.edges:
            src = self._graph.get_node(edge.source)
            dst = self._graph.get_node(edge.target)
            if src and dst:
                line = self._scene.addLine(src.x, src.y, dst.x, dst.y, pen)
                if line is not None:
                    line.setZValue(2)
                    line.setVisible(self._edge_visible and not self._graph_overlay_hidden)
                    self._edge_items.append(line)
                    
    def _draw_nodes(self):
        """Vẽ toàn bộ node."""
        if not self._graph:
            return
        for node_id, node in self._graph.nodes.items():
            item = NodeItem(node_id, node.x, node.y, node.name)
            item.setVisible(not self._graph_overlay_hidden)
            self._scene.addItem(item)
            self._node_items[node_id] = item
            
    def _draw_labels(self):
        """Vẽ tên các tòa nhà/vị trí quan trọng theo kiểu nhãn Google Maps."""
        if not self._graph:
            return
            
        font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        
        for node_id, node in self._graph.nodes.items():
            display_name = node.name
            if not display_name:
                continue
                
            icon = get_node_icon(display_name)
            full_text = f" {icon} {display_name} "
            
            # Text item
            text = QGraphicsTextItem()
            text.setFont(font)
            text.setDefaultTextColor(MapColors.TEXT_LABEL)
            text.setZValue(8)
            text.setHtml(f"<div style='font-family: Segoe UI; font-size: 9px; font-weight: bold;'>{full_text}</div>")
            
            # Tính toán vị trí nhãn
            text_width = text.boundingRect().width()
            text_height = text.boundingRect().height()
            
            tx = node.x + 12
            ty = node.y - text_height / 2
            text.setPos(tx, ty)
            
            # Vẽ nền nhãn bo góc
            bg_rect = self._scene.addRect(
                tx, ty + 2,
                text_width, text_height - 4,
                QPen(MapColors.TEXT_LABEL_BORDER, 1),
                QBrush(MapColors.TEXT_LABEL_BG)
            )
            if bg_rect is not None:
                bg_rect.setZValue(7)
                bg_rect.setVisible(not self._graph_overlay_hidden)
                self._label_items.append(bg_rect)
                
            self._scene.addItem(text)
            text.setVisible(not self._graph_overlay_hidden)
            self._label_items.append(text)
            
    # ──────────────────────────────────────────────────
    # Các hàm Zoom thủ công & Reset
    # ──────────────────────────────────────────────────
    
    def zoom_in(self):
        self.scale(1.2, 1.2)
        
    def zoom_out(self):
        self.scale(1.0 / 1.2, 1.0 / 1.2)
        
    def zoom_reset(self):
        self.resetTransform()
        if not self._scene.sceneRect().isEmpty():
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
    
    def set_edge_display(self, visible: bool, width: float, opacity: int):
        """Cập nhật cách hiển thị cạnh trên bản đồ."""
        self._edge_visible = visible
        self._edge_width = max(0.5, float(width))
        self._edge_opacity = max(20, min(255, int(opacity)))
        
        edge_color = QColor(MapColors.EDGE_NORMAL)
        edge_color.setAlpha(self._edge_opacity)
        pen = QPen(edge_color, self._edge_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        
        for item in self._edge_items:
            item.setPen(pen)
            item.setVisible(self._edge_visible and not self._graph_overlay_hidden)
    
    def edge_display(self) -> Tuple[bool, float, int]:
        """Trả về cấu hình hiển thị cạnh hiện tại."""
        return self._edge_visible, self._edge_width, self._edge_opacity

    # ──────────────────────────────────────────────────
    # Xử lý Click chọn địa điểm
    # ──────────────────────────────────────────────────
    
    def mousePressEvent(self, event: QMouseEvent | None):
        if event is None:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            clicked_node = self._find_nearest_node(scene_pos.x(), scene_pos.y())
            if clicked_node:
                self.node_clicked.emit(clicked_node)
                return
        super().mousePressEvent(event)
        
    def _find_nearest_node(self, x: float, y: float) -> Optional[str]:
        if self._graph_overlay_hidden:
            return None
        min_dist = float('inf')
        nearest = None
        for node_id, item in self._node_items.items():
            dx = item.x() - x
            dy = item.y() - y
            dist = math.sqrt(dx*dx + dy*dy)
            if dist < NodeItem.CLICK_RADIUS and dist < min_dist:
                min_dist = dist
                nearest = node_id
        return nearest
        
    def wheelEvent(self, event: QWheelEvent | None):
        if event is None:
            return
        factor = 1.12
        if event.angleDelta().y() > 0:
            self.scale(factor, factor)
        else:
            self.scale(1.0 / factor, 1.0 / factor)

    # ──────────────────────────────────────────────────
    # Thiết lập Start / Goal & Vẽ Ghim (Tooltip)
    # ──────────────────────────────────────────────────
    
    def set_start_node(self, node_id: str):
        """Đặt node xuất phát và ghim bong bóng BẮT ĐẦU."""
        # 1. Reset node xuất phát cũ
        if self._start_node and self._start_node in self._node_items:
            self._node_items[self._start_node].set_state("normal")
        if self._start_tooltip:
            self._scene.removeItem(self._start_tooltip)
            self._start_tooltip = None
            
        # 2. Tạo trạng thái & ghim mới
        self._start_node = node_id
        if node_id in self._node_items:
            self._node_items[node_id].set_state("start")
            node = self._graph.get_node(node_id) if self._graph else None
            if node:
                display_name = self._graph.get_node_name(node_id) if self._graph else node_id
                self._start_tooltip = MapPinTooltip(display_name, is_start=True)
                self._start_tooltip.setPos(node.x, node.y - 12)
                self._start_tooltip.setVisible(not self._graph_overlay_hidden)
                self._scene.addItem(self._start_tooltip)
                self.pulse_node(node_id, MapColors.NODE_START)
                
    def set_goal_node(self, node_id: str):
        """Đặt node đích và ghim bong bóng ĐÍCH."""
        # 1. Reset node đích cũ
        if self._goal_node and self._goal_node in self._node_items:
            self._node_items[self._goal_node].set_state("normal")
        if self._goal_tooltip:
            self._scene.removeItem(self._goal_tooltip)
            self._goal_tooltip = None
            
        # 2. Tạo trạng thái & ghim mới
        self._goal_node = node_id
        if node_id in self._node_items:
            self._node_items[node_id].set_state("goal")
            node = self._graph.get_node(node_id) if self._graph else None
            if node:
                display_name = self._graph.get_node_name(node_id) if self._graph else node_id
                self._goal_tooltip = MapPinTooltip(display_name, is_start=False)
                self._goal_tooltip.setPos(node.x, node.y - 12)
                self._goal_tooltip.setVisible(not self._graph_overlay_hidden)
                self._scene.addItem(self._goal_tooltip)
                self.pulse_node(node_id, MapColors.EDGE_PATH)

    def clear_start_node(self):
        """Xóa marker start nhưng giữ nguyên goal và các node khác."""
        if self._start_tooltip:
            self._scene.removeItem(self._start_tooltip)
            self._start_tooltip = None
        if self._start_node and self._start_node in self._node_items:
            self._node_items[self._start_node].set_state("normal")
        self._start_node = None
        if self._goal_node and self._goal_node in self._node_items:
            self._node_items[self._goal_node].set_state("goal")

    def clear_goal_node(self):
        """Xóa marker goal nhưng giữ nguyên start và các node khác."""
        if self._goal_tooltip:
            self._scene.removeItem(self._goal_tooltip)
            self._goal_tooltip = None
        if self._goal_node and self._goal_node in self._node_items:
            self._node_items[self._goal_node].set_state("normal")
        self._goal_node = None
        if self._start_node and self._start_node in self._node_items:
            self._node_items[self._start_node].set_state("start")

    def pulse_node(self, node_id: str, color: Optional[QColor] = None):
        """Tạo ripple/pulse 300ms quanh node được chọn hoặc đang duyệt."""
        if self._graph_overlay_hidden:
            return
        item = self._node_items.get(node_id)
        if item is None:
            return
        pulse_color = color or {
            "start": MapColors.NODE_START,
            "goal": MapColors.EDGE_PATH,
            "current": MapColors.NODE_CURRENT,
            "path": MapColors.EDGE_PATH,
        }.get(item._state, MapColors.NODE_NORMAL)

        # Click feedback: node bật nhẹ, sau đó trả về scale bình thường nếu không hover.
        item.setScale(1.35)
        QTimer.singleShot(130, lambda: item.setScale(1.25 if item._hover else 1.0))

        # Modern ripple: halo có fill nhẹ + 2 vòng trễ nhau để tạo cảm giác chọn điểm.
        rings = [
            PulseRing(item.x(), item.y(), pulse_color, 8, 30, 16, 0, 34),
            PulseRing(item.x(), item.y(), pulse_color, 10, 42, 22, 3, 18),
            PulseRing(item.x(), item.y(), pulse_color, 12, 54, 28, 7, 10),
        ]
        for ring in rings:
            self._scene.addItem(ring)
            self._pulse_items.append(ring)
        if not self._pulse_timer.isActive():
            self._pulse_timer.start(16)

    def _tick_pulses(self):
        remaining: List[PulseRing] = []
        for ring in self._pulse_items:
            done = ring.advance_frame()
            if done:
                self._scene.removeItem(ring)
            else:
                remaining.append(ring)
        self._pulse_items = remaining
        if not self._pulse_items:
            self._pulse_timer.stop()

    # ──────────────────────────────────────────────────
    # Highlight thuật toán tìm đường
    # ──────────────────────────────────────────────────
    
    def highlight_current(self, node_id: str):
        if node_id in self._node_items:
            if node_id != self._start_node and node_id != self._goal_node:
                self._node_items[node_id].set_state("current")
                
    def highlight_visited(self, node_ids: List[str]):
        for nid in node_ids:
            if nid in self._node_items:
                if nid != self._start_node and nid != self._goal_node:
                    self._node_items[nid].set_state("visited")
                    
    def highlight_frontier(self, node_ids: List[str]):
        for nid in node_ids:
            if nid in self._node_items:
                if (nid != self._start_node and nid != self._goal_node
                        and self._node_items[nid]._state != "current"):
                    self._node_items[nid].set_state("frontier")
                    
    def highlight_path(self, path: List[str]):
        """Vẽ lộ trình tối ưu bằng animation từng segment."""
        if not path or not self._graph:
            return
        
        self.clear_path()

        self._route_segments = []
        for i in range(len(path) - 1):
            src = self._graph.get_node(path[i])
            dst = self._graph.get_node(path[i + 1])
            if src and dst:
                self._route_segments.append((src.x, src.y, dst.x, dst.y))
                    
        # Highlight các node trung gian nằm trên đường đi ngay, còn line được draw dần bằng timer.
        for nid in path:
            if nid in self._node_items:
                if nid == self._start_node:
                    self._node_items[nid].set_state("start")
                elif nid == self._goal_node:
                    self._node_items[nid].set_state("goal")
                else:
                    self._node_items[nid].set_state("path")

        if not self._route_segments:
            return

        first_x, first_y, _, _ = self._route_segments[0]
        self._route_dot = self._scene.addEllipse(
            -6, -6, 12, 12,
            QPen(QColor("#FFFFFF"), 2),
            QBrush(MapColors.EDGE_PATH)
        )
        if self._route_dot is not None:
            self._route_dot.setPos(first_x, first_y)
            self._route_dot.setZValue(18)
            self._route_dot.setVisible(not self._graph_overlay_hidden)
            self._path_items.append(self._route_dot)

        self._route_segment_index = 0
        self._route_segment_progress = 0
        self._route_active_line = None
        self._route_active_glow = None
        self._route_flow_items.clear()
        self._route_segment_items.clear()
        self._route_flow_phase = 0.0
        self._route_timer.start(18)

    def _animate_route_step(self):
        """Tick animation vẽ route bằng QTimer để không khóa event loop."""
        if self._route_segment_index >= len(self._route_segments):
            self._route_timer.stop()
            self._start_route_flow()
            return

        sx, sy, ex, ey = self._route_segments[self._route_segment_index]
        if self._route_active_line is None:
            glow_pen = QPen(QColor(0, 209, 178, 80), 13)
            glow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            glow_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            line_pen = QPen(MapColors.EDGE_PATH, 6.8)
            line_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            line_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)

            self._route_active_glow = self._scene.addLine(sx, sy, sx, sy, glow_pen)
            self._route_active_line = self._scene.addLine(sx, sy, sx, sy, line_pen)
            segment_items: List[QGraphicsLineItem] = []
            if self._route_active_glow is not None:
                self._route_active_glow.setZValue(4)
                self._route_active_glow.setVisible(not self._graph_overlay_hidden)
                self._path_items.append(self._route_active_glow)
                segment_items.append(self._route_active_glow)
            if self._route_active_line is not None:
                self._route_active_line.setZValue(6)
                self._route_active_line.setVisible(not self._graph_overlay_hidden)
                self._path_items.append(self._route_active_line)
                segment_items.append(self._route_active_line)
            self._route_segment_items.append(segment_items)

        self._route_segment_progress += 1
        t = min(1.0, self._route_segment_progress / 12.0)
        ix = sx + (ex - sx) * t
        iy = sy + (ey - sy) * t

        if self._route_active_glow is not None:
            self._route_active_glow.setLine(sx, sy, ix, iy)
        if self._route_active_line is not None:
            self._route_active_line.setLine(sx, sy, ix, iy)
        if self._route_dot is not None:
            self._route_dot.setPos(ix, iy)

        if t >= 1.0:
            self._route_segment_index += 1
            self._route_segment_progress = 0
            self._route_active_line = None
            self._route_active_glow = None

    def _start_route_flow(self):
        """Phủ lớp dash chuyển động lên route để tạo cảm giác luồng navigation."""
        if self._route_flow_items:
            return

        # Lớp route nền đã được vẽ trong _animate_route_step. Lớp dưới đây chỉ là
        # highlight chuyển động, dùng dashOffset để chạy mượt mà không cần vẽ lại scene.
        for index, (sx, sy, ex, ey) in enumerate(self._route_segments):
            flow_pen = QPen(QColor("#E9FFFB"), 3.6)
            flow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            flow_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            flow_pen.setDashPattern([7, 10])

            flow_line = self._scene.addLine(sx, sy, ex, ey, flow_pen)
            if flow_line is not None:
                flow_line.setZValue(7)
                flow_line.setVisible(not self._graph_overlay_hidden)
                self._route_flow_items.append(flow_line)
                self._path_items.append(flow_line)
                if index < len(self._route_segment_items):
                    self._route_segment_items[index].append(flow_line)

        self._route_flow_phase = 0.0
        if self._route_flow_items:
            self._route_flow_timer.start(42)

    def _animate_route_flow(self):
        """Dịch dash offset liên tục để route có hiệu ứng chuyển động sau khi hoàn tất."""
        if not self._route_flow_items:
            self._route_flow_timer.stop()
            return

        self._route_flow_phase = (self._route_flow_phase + 1.8) % 34
        for index, item in enumerate(self._route_flow_items):
            pen = item.pen()
            # Xen kẽ cyan và blue rất nhẹ để route có chiều sâu nhưng không rối bản đồ.
            if index % 2 == 0:
                pen.setColor(QColor("#E9FFFB"))
                pen.setWidthF(3.6)
            else:
                pen.setColor(QColor("#0B74FF"))
                pen.setWidthF(2.4)
            pen.setDashPattern([7, 10])
            pen.setDashOffset(-self._route_flow_phase - index * 2.0)
            item.setPen(pen)

    def animate_avatar_along_path(self, path: List[str], avatar_path: str):
        """Hiển thị avatar nhỏ và cho đi mẫu từ node bắt đầu đến node đích."""
        if not self._graph or len(path) < 2:
            return

        pixmap = QPixmap(avatar_path)
        if pixmap.isNull():
            return

        self._clear_avatar()
        self._ensure_full_route_drawn()

        target_size = int(NodeItem.NODE_RADIUS_BIG * 2 * 1.33)
        avatar = pixmap.scaled(
            target_size,
            target_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self._avatar_segments = []
        for i in range(len(path) - 1):
            src = self._graph.get_node(path[i])
            dst = self._graph.get_node(path[i + 1])
            if src and dst:
                self._avatar_segments.append((src.x, src.y, dst.x, dst.y))

        if not self._avatar_segments:
            return

        sx, sy, _, _ = self._avatar_segments[0]
        self._avatar_item = self._scene.addPixmap(avatar)
        if self._avatar_item is None:
            return
        self._avatar_item.setZValue(24)
        self._avatar_item.setOffset(-avatar.width() / 2, -avatar.height() / 2)
        self._avatar_item.setPos(sx, sy)
        self._avatar_item.setVisible(not self._graph_overlay_hidden)

        self._avatar_segment_index = 0
        self._avatar_segment_progress = 0
        self._avatar_step_count = 22
        self._restore_full_route_visibility()
        self._avatar_hiding_route = True
        self._avatar_timer.start(28)

    def _ensure_full_route_drawn(self):
        """Hoàn tất visual route nếu người dùng bấm đi mẫu trước khi draw animation xong."""
        if not self._route_segments:
            return

        self._route_timer.stop()
        while len(self._route_segment_items) < len(self._route_segments):
            sx, sy, ex, ey = self._route_segments[len(self._route_segment_items)]
            glow_pen = QPen(QColor(0, 209, 178, 80), 13)
            glow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            glow_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            line_pen = QPen(MapColors.EDGE_PATH, 6.8)
            line_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            line_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)

            segment_items: List[QGraphicsLineItem] = []
            glow = self._scene.addLine(sx, sy, ex, ey, glow_pen)
            line = self._scene.addLine(sx, sy, ex, ey, line_pen)
            if glow is not None:
                glow.setZValue(4)
                glow.setVisible(not self._graph_overlay_hidden)
                self._path_items.append(glow)
                segment_items.append(glow)
            if line is not None:
                line.setZValue(6)
                line.setVisible(not self._graph_overlay_hidden)
                self._path_items.append(line)
                segment_items.append(line)
            self._route_segment_items.append(segment_items)

        if not self._route_flow_items:
            self._start_route_flow()

    def _animate_avatar_step(self):
        """Tick di chuyển avatar dọc theo route bằng QTimer."""
        if self._avatar_item is None or self._avatar_segment_index >= len(self._avatar_segments):
            self._avatar_timer.stop()
            self._restore_full_route_visibility()
            return

        sx, sy, ex, ey = self._avatar_segments[self._avatar_segment_index]
        self._avatar_segment_progress += 1
        t = min(1.0, self._avatar_segment_progress / float(self._avatar_step_count))
        # Smoothstep giúp chuyển động dịu hơn tuyến tính.
        eased = t * t * (3 - 2 * t)
        x = sx + (ex - sx) * eased
        y = sy + (ey - sy) * eased
        self._avatar_item.setPos(x, y)
        self._update_route_visibility_for_avatar(x, y)

        if t >= 1.0:
            self._avatar_segment_index += 1
            self._avatar_segment_progress = 0
            if self._avatar_segment_index >= len(self._avatar_segments):
                self._avatar_timer.stop()
                self._restore_full_route_visibility()

    def _update_route_visibility_for_avatar(self, avatar_x: float, avatar_y: float):
        """Avatar đi đến đâu thì phần route phía sau biến mất đến đó."""
        if not self._avatar_hiding_route:
            return

        for index, items in enumerate(self._route_segment_items):
            if index < self._avatar_segment_index:
                for item in items:
                    item.setVisible(False)
            elif index == self._avatar_segment_index and index < len(self._route_segments):
                _, _, ex, ey = self._route_segments[index]
                for item in items:
                    item.setLine(avatar_x, avatar_y, ex, ey)
                    item.setVisible(not self._graph_overlay_hidden)
            else:
                sx, sy, ex, ey = self._route_segments[index]
                for item in items:
                    item.setLine(sx, sy, ex, ey)
                    item.setVisible(not self._graph_overlay_hidden)

        if self._route_dot is not None:
            self._route_dot.setVisible(False)

    def _restore_full_route_visibility(self):
        """Khi avatar tới đích, hiện lại route đầy đủ như kết quả ban đầu."""
        self._avatar_hiding_route = False
        for index, items in enumerate(self._route_segment_items):
            if index >= len(self._route_segments):
                continue
            sx, sy, ex, ey = self._route_segments[index]
            for item in items:
                item.setLine(sx, sy, ex, ey)
                item.setVisible(not self._graph_overlay_hidden)
        if self._route_dot is not None and self._route_segments:
            _, _, ex, ey = self._route_segments[-1]
            self._route_dot.setPos(ex, ey)
            self._route_dot.setVisible(not self._graph_overlay_hidden)
        if self._route_flow_items and not self._graph_overlay_hidden:
            self._route_flow_timer.start(42)

    def _clear_avatar(self):
        self._avatar_timer.stop()
        if self._avatar_item is not None:
            self._scene.removeItem(self._avatar_item)
        self._avatar_item = None
        self._avatar_segments = []
        self._avatar_hiding_route = False
                    
    def clear_path(self):
        self._route_timer.stop()
        self._route_flow_timer.stop()
        self._route_segments = []
        self._route_active_line = None
        self._route_active_glow = None
        self._route_dot = None
        self._route_flow_items.clear()
        self._route_segment_items.clear()
        self._clear_avatar()
        for item in self._path_items:
            self._scene.removeItem(item)
        self._path_items.clear()
        
    def reset_all_nodes(self):
        """Khôi phục trạng thái ban đầu của các node trừ ghim Start/Goal."""
        for nid, item in self._node_items.items():
            item.set_state("normal")
        self.clear_path()
        
        if self._start_node and self._start_node in self._node_items:
            self._node_items[self._start_node].set_state("start")
        if self._goal_node and self._goal_node in self._node_items:
            self._node_items[self._goal_node].set_state("goal")
    
    def update_step(self, current: str, visited: List[str], frontier: List[str]):
        """
        Cập nhật trạng thái node theo bước mô phỏng — chỉ thay đổi incremental.
        Hiệu năng O(delta) thay vì O(n) như reset_all_nodes + re-highlight.
        """
        # Tính desired state cho mỗi node
        visited_set = set(visited)
        frontier_set = set(frontier)
        protected = {self._start_node, self._goal_node}
        
        for nid, item in self._node_items.items():
            if nid in protected:
                continue  # Không đổi trạng thái start/goal
            
            # Xác định trạng thái mong muốn
            if nid == current:
                desired = "current"
            elif nid in frontier_set:
                desired = "frontier"
            elif nid in visited_set:
                desired = "visited"
            else:
                desired = "normal"
            
            # Chỉ cập nhật nếu thực sự thay đổi
            if item._state != desired:
                item.set_state(desired)
                if desired == "current" and nid != self._last_current_node:
                    self.pulse_node(nid, MapColors.NODE_CURRENT)
                    self._last_current_node = nid
            
    def full_reset(self):
        """Xóa hoàn toàn ghim, đường đi và đưa bản đồ về trạng thái ban đầu."""
        if self._start_tooltip:
            self._scene.removeItem(self._start_tooltip)
            self._start_tooltip = None
        if self._goal_tooltip:
            self._scene.removeItem(self._goal_tooltip)
            self._goal_tooltip = None
            
        self._start_node = None
        self._goal_node = None
        for nid, item in self._node_items.items():
            item.set_state("normal")
        self.clear_path()

    # ──────────────────────────────────────────────────
    # Định vị các widget nổi khi resize
    # ──────────────────────────────────────────────────
    
    def resizeEvent(self, event: QResizeEvent | None):
        """Tự động giữ tỷ lệ fit view bản đồ và cố định góc các widget điều khiển nổi."""
        super().resizeEvent(event)
        if not self._scene.sceneRect().isEmpty():
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            
        # Cập nhật vị trí Legend Card (Top-Left)
        if self._legend_card:
            self._legend_card.move(16, 16)
            self._legend_card.adjustSize()
            
        # Cập nhật vị trí Zoom Controls (Top-Right)
        if self._zoom_card:
            self._zoom_card.move(self.width() - self._zoom_card.width() - 16, 16)
            self._zoom_card.adjustSize()
            
        # Cập nhật vị trí nút ẩn/hiện graph và chỉnh sửa graph (Bottom-Left)
        bottom_y = self.height() - 64
        if self._graph_toggle_button:
            self._graph_toggle_button.adjustSize()
            bottom_y = self.height() - self._graph_toggle_button.height() - 16
            self._graph_toggle_button.move(16, bottom_y)
        if self._sample_walk_button:
            self._sample_walk_button.adjustSize()
            x = 16
            if self._graph_toggle_button:
                x += self._graph_toggle_button.width() + 10
            self._sample_walk_button.move(x, bottom_y)
        if self._speed_button:
            self._speed_button.adjustSize()
            x = 16
            if self._graph_toggle_button:
                x += self._graph_toggle_button.width() + 10
            if self._sample_walk_button:
                x += self._sample_walk_button.width() + 10
            self._speed_button.move(x, bottom_y)
        if self._graph_edit_button:
            self._graph_edit_button.adjustSize()
            x = 16
            if self._graph_toggle_button:
                x += self._graph_toggle_button.width() + 10
            if self._sample_walk_button:
                x += self._sample_walk_button.width() + 10
            if self._speed_button:
                x += self._speed_button.width() + 10
            self._graph_edit_button.move(x, bottom_y)
