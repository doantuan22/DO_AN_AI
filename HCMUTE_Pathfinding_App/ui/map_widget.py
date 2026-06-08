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
from typing import Optional, Dict, List, Tuple

from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
    QGraphicsLineItem, QGraphicsTextItem, QGraphicsPixmapItem,
    QGraphicsPathItem, QGraphicsRectItem, QWidget, QFrame,
    QHBoxLayout, QVBoxLayout, QPushButton, QLabel
)
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal, QTimer
from PyQt6.QtGui import (
    QPixmap, QPen, QBrush, QColor, QFont, QPainter,
    QPainterPath, QRadialGradient, QLinearGradient, QFontMetrics,
    QMouseEvent, QWheelEvent, QResizeEvent
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
        
        # Thêm text nội dung vào bên trong
        self.text_item = QGraphicsTextItem(self)
        self.text_item.setZValue(26)
        
        # HTML hiển thị title và nội dung
        html = f"""
            <div style='text-align: center; width: {int(w)}px; line-height: 1.1;'>
                <span style='color: {self.accent_color.name()}; font-family: Segoe UI; font-size: 8px; font-weight: bold;'>{title_text}</span><br>
                <span style='color: #202124; font-family: Segoe UI; font-size: 10px; font-weight: bold;'>{name}</span>
            </div>
        """
        self.text_item.setHtml(html)
        # Căn chỉnh vị trí của text nằm lọt vào bong bóng
        self.text_item.setPos(-w/2 - 4, -h - 8 + 3)


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


# ──────────────────────────────────────────────────────────────
# Map Widget chính
# ──────────────────────────────────────────────────────────────

class MapWidget(QGraphicsView):
    """
    Widget hiển thị bản đồ HCMUTE với cấu trúc widget nổi cố định.
    Không bị méo mó, lệch vị trí khi zoom/resize.
    """
    
    node_clicked = pyqtSignal(str)
    
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
                background-color: #FFFFFF;
            }
        """)
        
        # Danh sách lưu trữ items
        self._graph: Optional[Graph] = None
        self._map_pixmap: Optional[QGraphicsPixmapItem] = None
        self._node_items: Dict[str, NodeItem] = {}
        self._edge_items: List[QGraphicsLineItem] = []
        self._path_items: List[QGraphicsLineItem] = []
        self._edge_visible = True
        self._edge_width = 2.5
        self._edge_opacity = 180
        
        # Trạng thái chọn điểm đi & đến
        self._start_node: Optional[str] = None
        self._goal_node: Optional[str] = None
        
        # Tooltips ghim điểm Bắt đầu / Đích
        self._start_tooltip: Optional[MapPinTooltip] = None
        self._goal_tooltip: Optional[MapPinTooltip] = None
        
        # Các widget nổi (Legend, Zoom, Lớp bản đồ)
        self._legend_card: Optional[QFrame] = None
        self._zoom_card: Optional[QFrame] = None
        self._layers_card: Optional[QPushButton] = None
        
        # Khởi tạo các widget nổi
        self._setup_floating_controls()
    
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
        
        # 3. Layers Card (Góc dưới bên trái)
        self._layers_card = QPushButton(self)
        self._layers_card.setObjectName("layersCard")
        self._layers_card.setText("🥞")
        self._layers_card.setToolTip("Thay đổi lớp bản đồ")
        self._layers_card.setStyleSheet("""
            QPushButton#layersCard {
                background-color: rgba(255, 255, 255, 0.95);
                border: 1px solid rgba(215, 227, 244, 0.95);
                border-radius: 8px;
                font-size: 18px;
                min-height: 44px;
                min-width: 44px;
            }
            QPushButton#layersCard:hover {
                background-color: #F1F3F4;
            }
        """)
        self._layers_card.show()
        
    def setup_map(self, graph: Graph, map_image_path: str):
        """Khởi tạo toàn bộ bản đồ."""
        self._graph = graph
        
        # Xóa các item khỏi scene
        self._scene.clear()
        self._node_items.clear()
        self._edge_items.clear()
        self._path_items.clear()
        self._start_tooltip = None
        self._goal_tooltip = None
        
        # 1. Vẽ bản đồ nền
        loaded = False
        if os.path.exists(map_image_path):
            pixmap = QPixmap(map_image_path)
            if not pixmap.isNull():
                self._map_pixmap = self._scene.addPixmap(pixmap)
                if self._map_pixmap is not None:
                    self._map_pixmap.setZValue(0)
                    self._map_pixmap.setOpacity(0.82)
                    self._scene.setSceneRect(QRectF(pixmap.rect()))
                    loaded = True
        
        if not loaded:
            self._scene.setSceneRect(0, 0, 1122, 1402)
            bg = self._scene.addRect(0, 0, 1122, 1402,
                                     QPen(Qt.PenStyle.NoPen),
                                     QBrush(QColor("#F0F4F8")))
            if bg is not None:
                bg.setZValue(0)
                
        # 2. Vẽ các cạnh, node và nhãn
        self._draw_edges()
        self._draw_nodes()
        self._draw_labels()
        
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
                    line.setVisible(self._edge_visible)
                    self._edge_items.append(line)
                    
    def _draw_nodes(self):
        """Vẽ toàn bộ node."""
        if not self._graph:
            return
        for node_id, node in self._graph.nodes.items():
            item = NodeItem(node_id, node.x, node.y, node.name)
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
                
            self._scene.addItem(text)
            
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
            item.setVisible(self._edge_visible)
    
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
                self._start_tooltip = MapPinTooltip(node.name, is_start=True)
                self._start_tooltip.setPos(node.x, node.y - 12)
                self._scene.addItem(self._start_tooltip)
                
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
                self._goal_tooltip = MapPinTooltip(node.name, is_start=False)
                self._goal_tooltip.setPos(node.x, node.y - 12)
                self._scene.addItem(self._goal_tooltip)

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
        """Vẽ lộ trình tối ưu đậm sắc nét."""
        if not path or not self._graph:
            return
        
        self.clear_path()
        
        # Vẽ nét vẽ neon cyan rộng 6px rất cuốn hút
        pen = QPen(MapColors.EDGE_PATH, 6.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        
        for i in range(len(path) - 1):
            src = self._graph.get_node(path[i])
            dst = self._graph.get_node(path[i + 1])
            if src and dst:
                line = self._scene.addLine(src.x, src.y, dst.x, dst.y, pen)
                if line is not None:
                    line.setZValue(5)
                    self._path_items.append(line)
                    
        # Highlight các node trung gian nằm trên đường đi
        for nid in path:
            if nid in self._node_items:
                if nid == self._start_node:
                    self._node_items[nid].set_state("start")
                elif nid == self._goal_node:
                    self._node_items[nid].set_state("goal")
                else:
                    self._node_items[nid].set_state("path")
                    
    def clear_path(self):
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
            
        # Cập nhật vị trí Lớp bản đồ (Bottom-Left)
        if self._layers_card:
            self._layers_card.move(16, self.height() - self._layers_card.height() - 16)
            self._layers_card.adjustSize()
