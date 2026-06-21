"""Canvas hiển thị/chỉnh sửa ảnh, graph và marker của bản đồ con."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, Optional, List

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap, QTransform, QWheelEvent
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
)

from ui.map_widget import MapColors, MapPinTooltip, PulseRing


class _MovablePoint(QGraphicsEllipseItem):
    def __init__(self, key: str, radius: float, color: QColor, movable: bool, callback, parent=None):
        super().__init__(-radius, -radius, radius * 2, radius * 2, parent)
        self.key = key
        self.callback = callback
        self.setBrush(color)
        self.setPen(QPen(Qt.GlobalColor.white, 2))
        self.setZValue(20)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, movable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, movable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, movable)
        self.setCursor(Qt.CursorShape.OpenHandCursor if movable else Qt.CursorShape.ArrowCursor)

    def set_movable(self, movable: bool) -> None:
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, movable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, movable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, movable)
        self.setCursor(Qt.CursorShape.OpenHandCursor if movable else Qt.CursorShape.ArrowCursor)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged and self.callback:
            point = value if isinstance(value, QPointF) else self.pos()
            self.callback(self.key, point.x(), point.y())
        return super().itemChange(change, value)



class SubMapWidget(QGraphicsView):
    node_moved = pyqtSignal(str, float, float)
    entry_moved = pyqtSignal(float, float)
    node_clicked = pyqtSignal(str)
    map_clicked = pyqtSignal(float, float)

    def __init__(self, editable: bool = False, parent=None):
        super().__init__(parent)
        self.editable = editable
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setStyleSheet("QGraphicsView { background:#EEF3F8; border:1px solid #D8E2EF; border-radius:8px; }")
        self._root: Optional[QGraphicsPixmapItem] = None
        self._graph: Dict[str, Any] = {"nodes": [], "edges": []}
        self._node_items: Dict[str, _MovablePoint] = {}
        self._edge_items: list[tuple[str, str, QGraphicsLineItem]] = []
        self._rotation = 0.0
        self._interaction_mode = "select"
        self._show_edges = True
        self._start_node: Optional[str] = None
        self._goal_node: Optional[str] = None
        self._selected_node_id: Optional[str] = None
        self._path_nodes: list[str] = []
        self._path_items: list[QGraphicsItem] = []
        
        # --- Animation variables ---
        from PyQt6.QtCore import QTimer
        self._route_timer = QTimer(self)
        self._route_timer.timeout.connect(self._animate_route_step)
        self._route_flow_timer = QTimer(self)
        self._route_flow_timer.timeout.connect(self._animate_route_flow)
        self._avatar_timer = QTimer(self)
        self._avatar_timer.timeout.connect(self._animate_avatar_step)
        self._firework_timer = QTimer(self)
        self._firework_timer.timeout.connect(self._animate_fireworks)
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._tick_pulses)
        
        self._route_segments = []
        self._route_segment_items = []
        self._route_flow_items = []
        self._route_active_line = None
        self._route_active_glow = None
        self._route_dot = None
        self._route_flow_phase = 0.0
        self._route_segment_index = 0
        self._route_segment_progress = 0
        
        self._avatar_item = None
        self._firework_particles = []
        self._pulse_items = []
        self._avatar_segments = []
        self._avatar_segment_index = 0
        self._avatar_segment_progress = 0
        self._avatar_step_count = 22
        self._avatar_hiding_route = False
        
        self._entry_tooltip = None

    def load_map(
        self,
        image_path: str | Path,
        graph: Dict[str, Any],
        rotation: float = 0,
        show_edges: bool = True,
    ) -> None:
        self.reset_path()
        self._pulse_timer.stop()
        self._pulse_items.clear()
        self._firework_timer.stop()
        self._firework_particles.clear()
        self._avatar_timer.stop()
        self._avatar_item = None
        self._entry_tooltip = None
        
        self._scene.clear()
        self._node_items.clear()
        self._edge_items.clear()
        self._graph = graph
        self._show_edges = bool(show_edges)
        self._start_node = None
        self._goal_node = None
        self._selected_node_id = None
        self._path_nodes = []
        pixmap = QPixmap(str(image_path))
        image_missing = pixmap.isNull()
        if image_missing:
            pixmap = QPixmap(900, 650)
            pixmap.fill(QColor("#FFFFFF"))
        self._root = QGraphicsPixmapItem(pixmap)
        self._root.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self._root.setTransformOriginPoint(pixmap.width() / 2, pixmap.height() / 2)
        self._scene.addItem(self._root)

        nodes = {str(node.get("id")): node for node in graph.get("nodes", [])}
        
        # Đảm bảo có node __entry__ nếu cần (fallback cho đồ thị cũ chưa lưu __entry__)
        if "__entry__" not in nodes:
            nodes["__entry__"] = {"id": "__entry__", "name": "Cổng vào", "x": 0, "y": 0}

        for node_id, node in nodes.items():
            if node_id == "__entry__":
                item = _MovablePoint(node_id, 11, QColor("#E53935"), self.editable, self._on_point_moved, self._root)
                item.setPos(float(node.get("x", 0)), float(node.get("y", 0)))
                item.setZValue(30)
                # Thay thế chữ đơn giản bằng Tooltip chuyên nghiệp
                if not self.editable:
                    self._entry_tooltip = MapPinTooltip("Bạn đang ở đây", is_start=True)
                    self._entry_tooltip.setPos(float(node.get("x", 0)), float(node.get("y", 0)) - 14)
                    self._entry_tooltip.setVisible(True)
                    self._scene.addItem(self._entry_tooltip)
            else:
                item = _MovablePoint(node_id, 8, QColor("#0B74FF"), self.editable, self._on_point_moved, self._root)
                item.setPos(float(node.get("x", 0)), float(node.get("y", 0)))
                display_name = "" if node.get("hide_name") else str(node.get("name") or node_id)
                label = QGraphicsSimpleTextItem(display_name, item)
                label.setBrush(QColor("#102A56"))
                label.setPos(11, -9)
                label.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
            self._node_items[node_id] = item

        self._draw_edges(graph)
        if image_missing:
            missing = QGraphicsSimpleTextItem("Không tìm thấy ảnh bản đồ con", self._root)
            missing.setBrush(QColor("#D93025")); missing.setPos(30, 30); missing.setZValue(40)
        self.set_rotation(rotation)
        self._apply_interaction_mode()
        self._scene.setSceneRect(self._scene.itemsBoundingRect().adjusted(-80, -80, 80, 80))
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def set_interaction_mode(self, mode: str) -> None:
        self._interaction_mode = mode
        self._apply_interaction_mode()

    def _apply_interaction_mode(self) -> None:
        if not self.editable:
            # Chế độ xem: luôn cho phép kéo bản đồ
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            for item in self._node_items.values():
                item.set_movable(False)
            return
        pan_mode = self._interaction_mode == "pan"
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag if pan_mode else QGraphicsView.DragMode.NoDrag)
        movable = self._interaction_mode == "select"
        for item in self._node_items.values():
            item.set_movable(movable)

    def highlight_node(self, node_id: str) -> None:
        """Highlight a node to indicate it is selected. Reset others."""
        for nid, item in self._node_items.items():
            if nid == "__entry__":
                if nid == node_id:
                    item.setBrush(QColor("#FF5252"))  # Đỏ sáng khi chọn
                    item.setPen(QPen(QColor("#FFFFFF"), 3))
                    item.setZValue(35)
                else:
                    item.setBrush(QColor("#E53935"))  # Trở lại màu đỏ mặc định
                    item.setPen(QPen(Qt.GlobalColor.white, 2))
                    item.setZValue(30)
                continue
            if nid == node_id:
                item.setBrush(QColor("#FF9800"))
                item.setPen(QPen(QColor("#FFFFFF"), 3))
                item.setZValue(25)
            else:
                item.setBrush(QColor("#0B74FF"))
                item.setPen(QPen(Qt.GlobalColor.white, 2))
                item.setZValue(20)

    def set_start_node(self, node_id: str) -> None:
        if node_id in self._node_items:
            item = self._node_items[node_id]
            item.setBrush(QColor("#E53935"))
            item.setPen(QPen(QColor("#FFFFFF"), 3))
            item.setZValue(30)
            self._start_node = node_id

    def set_goal_node(self, node_id: str) -> None:
        # Reset node đích cũ
        if self._goal_node and self._goal_node in self._node_items and self._goal_node != "__entry__":
            old = self._node_items[self._goal_node]
            old.setBrush(QColor("#0B74FF"))
            old.setPen(QPen(Qt.GlobalColor.white, 2))
            old.setZValue(20)
        # Highlight node đích mới
        if node_id in self._node_items:
            item = self._node_items[node_id]
            item.setBrush(QColor("#00C896"))
            item.setPen(QPen(QColor("#FFFFFF"), 3))
            item.setZValue(25)
            self._goal_node = node_id

    def clear_goal_node(self) -> None:
        if self._goal_node and self._goal_node in self._node_items and self._goal_node != "__entry__":
            item = self._node_items[self._goal_node]
            item.setBrush(QColor("#0B74FF"))
            item.setPen(QPen(Qt.GlobalColor.white, 2))
            item.setZValue(20)
        self._goal_node = None

    def set_rotation(self, angle: float) -> None:
        self._rotation = float(angle) % 360
        if self._root:
            self._root.setRotation(self._rotation)
            self._scene.setSceneRect(self._scene.itemsBoundingRect().adjusted(-80, -80, 80, 80))

    def rotation(self) -> float:
        return self._rotation

    def refresh_graph(self, graph: Dict[str, Any]) -> None:
        if self._root:
            image_path = self._root.pixmap()
            self._rebuild_from_pixmap(image_path, graph)

    def _rebuild_from_pixmap(self, pixmap: QPixmap, graph: Dict[str, Any]) -> None:
        temp = QGraphicsPixmapItem(pixmap)
        # load_map cần path; dựng trực tiếp bằng ảnh tạm không cần ghi file.
        self._scene.clear()
        self._root = temp
        self._scene.addItem(temp)
        temp.setTransformOriginPoint(pixmap.width() / 2, pixmap.height() / 2)
        self._graph = graph
        nodes = {str(n.get("id")): n for n in graph.get("nodes", [])}
        self._node_items = {}
        self._edge_items = []
        for node_id, node in nodes.items():
            if node_id == "__entry__":
                item = _MovablePoint(node_id, 11, QColor("#E53935"), self.editable, self._on_point_moved, temp)
                item.setPos(float(node["x"]), float(node["y"]))
                item.setZValue(30)
                if not self.editable:
                    self._entry_tooltip = MapPinTooltip("Bạn đang ở đây", is_start=True)
                    self._entry_tooltip.setPos(float(node["x"]), float(node["y"]) - 14)
                    self._entry_tooltip.setVisible(True)
                    self._scene.addItem(self._entry_tooltip)
            else:
                item = _MovablePoint(node_id, 8, QColor("#0B74FF"), self.editable, self._on_point_moved, temp)
                item.setPos(float(node["x"]), float(node["y"]))
                display_name = "" if node.get("hide_name") else str(node.get("name") or node_id)
                label = QGraphicsSimpleTextItem(display_name, item)
                label.setBrush(QColor("#102A56"))
                label.setPos(11, -9)
                label.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
            self._node_items[node_id] = item
        self._draw_edges(graph)
        self._apply_interaction_mode()
        self.set_rotation(self._rotation)

    def _on_point_moved(self, key: str, x: float, y: float) -> None:
        self.node_moved.emit(key, x, y)
        self._update_edges_for(key)

    def _draw_edges(self, graph: Dict[str, Any]) -> None:
        if not self._root:
            return
        for edge in graph.get("edges", []):
            source, target = str(edge.get("from", "")), str(edge.get("to", ""))
            if source not in self._node_items or target not in self._node_items:
                continue
            a, b = self._node_items[source].pos(), self._node_items[target].pos()
            line = QGraphicsLineItem(a.x(), a.y(), b.x(), b.y(), self._root)
            line.setPen(QPen(QColor(28, 100, 242, 180), 3))
            line.setZValue(5)
            line.setVisible(self._show_edges)
            self._edge_items.append((source, target, line))

    def _update_edges_for(self, node_id: str) -> None:
        for source, target, line in self._edge_items:
            if node_id not in (source, target):
                continue
            a, b = self._node_items[source].pos(), self._node_items[target].pos()
            line.setLine(a.x(), a.y(), b.x(), b.y())

    # ──────────────────────────────────────────────────────────────
    # Hỗ trợ Vẽ thuật toán tìm đường (Tương thích MapWidget)
    # ──────────────────────────────────────────────────────────────

    def update_state(self, visited: List[str], frontier: List[str], current: Optional[str] = None) -> None:
        for nid, item in self._node_items.items():
            if nid == "__entry__":
                continue  # Bỏ qua cổng vào, giữ màu gốc
            if current and nid == current:
                item.setBrush(QColor("#FF9800")) # Current (Cam)
            elif nid in visited:
                item.setBrush(QColor("#BA9AF0")) # Visited (Tím nhạt)
            elif nid in frontier:
                item.setBrush(QColor("#FFD54F")) # Frontier (Vàng)
            else:
                item.setBrush(QColor("#0B74FF")) # Trạng thái thường (Xanh dương)

    def draw_path(self, path_nodes: List[str]) -> None:
        self.reset_path()
        if not self._root or len(path_nodes) < 2:
            return
            
        self._route_segments = []
        for i in range(len(path_nodes) - 1):
            source = path_nodes[i]
            target = path_nodes[i + 1]
            if source in self._node_items and target in self._node_items:
                p1 = self._node_items[source].pos()
                p2 = self._node_items[target].pos()
                self._route_segments.append((p1.x(), p1.y(), p2.x(), p2.y()))
                
        if not self._route_segments:
            return

        first_x, first_y, _, _ = self._route_segments[0]
        from PyQt6.QtGui import QBrush
        self._route_dot = self._scene.addEllipse(
            -6, -6, 12, 12,
            QPen(QColor("#FFFFFF"), 2),
            QBrush(MapColors.EDGE_PATH)
        )
        if self._route_dot is not None:
            self._route_dot.setPos(first_x, first_y)
            self._route_dot.setZValue(18)
            self._route_dot.setVisible(True)
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
                self._route_active_glow.setVisible(True)
                self._path_items.append(self._route_active_glow)
                segment_items.append(self._route_active_glow)
            if self._route_active_line is not None:
                self._route_active_line.setZValue(6)
                self._route_active_line.setVisible(True)
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
        if self._route_flow_items:
            return
        for index, (sx, sy, ex, ey) in enumerate(self._route_segments):
            flow_pen = QPen(QColor("#E9FFFB"), 3.6)
            flow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            flow_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            flow_pen.setDashPattern([7, 10])

            flow_line = self._scene.addLine(sx, sy, ex, ey, flow_pen)
            if flow_line is not None:
                flow_line.setZValue(7)
                flow_line.setVisible(True)
                self._route_flow_items.append(flow_line)
                self._path_items.append(flow_line)
                if index < len(self._route_segment_items):
                    self._route_segment_items[index].append(flow_line)

        self._route_flow_phase = 0.0
        if self._route_flow_items:
            self._route_flow_timer.start(42)

    def _animate_route_flow(self):
        if not self._route_flow_items:
            self._route_flow_timer.stop()
            return
        self._route_flow_phase = (self._route_flow_phase + 1.8) % 34
        for index, item in enumerate(self._route_flow_items):
            pen = item.pen()
            if index % 2 == 0:
                pen.setColor(QColor("#E9FFFB"))
                pen.setWidthF(3.6)
            else:
                pen.setColor(QColor("#0B74FF"))
                pen.setWidthF(2.4)
            pen.setDashPattern([7, 10])
            pen.setDashOffset(-self._route_flow_phase - index * 2.0)
            item.setPen(pen)

    def reset_path(self) -> None:
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
            if self._root and item.scene():
                self._scene.removeItem(item)
        self._path_items.clear()
        
        for nid, item in self._node_items.items():
            if nid == "__entry__":
                item.setBrush(QColor("#E53935"))
            else:
                item.setBrush(QColor("#0B74FF"))

    def pulse_node(self, node_id: str, color: Optional[QColor] = None):
        item = self._node_items.get(node_id)
        if item is None:
            return
        pulse_color = color or QColor("#0B74FF")

        item.setScale(1.35)
        QTimer.singleShot(130, lambda: item.setScale(1.0))

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

    def animate_avatar_along_path(self, path: List[str], avatar_path: str):
        if not path or len(path) < 2:
            return
        pixmap = QPixmap(avatar_path)
        if pixmap.isNull():
            return

        self._clear_avatar()
        self._ensure_full_route_drawn()

        target_size = 30
        avatar = pixmap.scaled(
            target_size,
            target_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self._avatar_segments = []
        for i in range(len(path) - 1):
            src = self._node_items.get(path[i])
            dst = self._node_items.get(path[i + 1])
            if src and dst:
                self._avatar_segments.append((src.x(), src.y(), dst.x(), dst.y()))

        if not self._avatar_segments:
            return

        sx, sy, _, _ = self._avatar_segments[0]
        self._avatar_item = self._scene.addPixmap(avatar)
        if self._avatar_item is None:
            return
        self._avatar_item.setZValue(24)
        self._avatar_item.setOffset(-avatar.width() / 2, -avatar.height() / 2)
        self._avatar_item.setPos(sx, sy)
        self._avatar_item.setVisible(True)

        self._avatar_segment_index = 0
        self._avatar_segment_progress = 0
        self._avatar_step_count = 22
        self._restore_full_route_visibility()
        self._avatar_hiding_route = True
        self._avatar_timer.start(28)

    def _ensure_full_route_drawn(self):
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
                glow.setVisible(True)
                self._path_items.append(glow)
                segment_items.append(glow)
            if line is not None:
                line.setZValue(6)
                line.setVisible(True)
                self._path_items.append(line)
                segment_items.append(line)
            self._route_segment_items.append(segment_items)

        if not self._route_flow_items:
            self._start_route_flow()

    def _animate_avatar_step(self):
        if self._avatar_item is None or self._avatar_segment_index >= len(self._avatar_segments):
            self._avatar_timer.stop()
            self._restore_full_route_visibility()
            if self._avatar_segments:
                _, _, ex, ey = self._avatar_segments[-1]
                self._spawn_fireworks(ex, ey)
            return

        sx, sy, ex, ey = self._avatar_segments[self._avatar_segment_index]
        self._avatar_segment_progress += 1
        t = min(1.0, self._avatar_segment_progress / float(self._avatar_step_count))
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
                self._spawn_fireworks(ex, ey)

    def _spawn_fireworks(self, x: float, y: float):
        colors = [
            QColor("#0B74FF"), QColor("#00D1B2"), QColor("#22C55E"),
            QColor("#F59E0B"), QColor("#EF4444"), QColor("#FFFFFF"),
        ]
        burst_count = 22
        for i in range(burst_count):
            angle = (math.tau / burst_count) * i
            speed = 2.4 + (i % 5) * 0.42
            radius = 3.2 if i % 3 else 4.4
            color = colors[i % len(colors)]
            item = self._scene.addEllipse(
                -radius, -radius, radius * 2, radius * 2,
                QPen(Qt.PenStyle.NoPen), QBrush(color)
            )
            if item is None:
                continue
            item.setPos(x, y)
            item.setZValue(30)
            self._firework_particles.append({
                "item": item,
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed - 0.65,
                "life": 0,
                "max_life": 34 + (i % 6),
            })

        self.pulse_node(self._goal_node, MapColors.EDGE_PATH)
        if not self._firework_timer.isActive():
            self._firework_timer.start(16)

    def _animate_fireworks(self):
        remaining = []
        for particle in self._firework_particles:
            item = particle["item"]
            particle["life"] += 1
            particle["vy"] += 0.055
            item.moveBy(particle["vx"], particle["vy"])
            t = particle["life"] / particle["max_life"]
            item.setOpacity(max(0.0, 1.0 - t))
            item.setScale(1.0 + t * 0.85)
            if particle["life"] >= particle["max_life"]:
                self._scene.removeItem(item)
            else:
                remaining.append(particle)
        self._firework_particles = remaining
        if not self._firework_particles:
            self._firework_timer.stop()

    def _update_route_visibility_for_avatar(self, avatar_x: float, avatar_y: float):
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
                    item.setVisible(True)
            else:
                sx, sy, ex, ey = self._route_segments[index]
                for item in items:
                    item.setLine(sx, sy, ex, ey)
                    item.setVisible(True)
        if self._route_dot is not None:
            self._route_dot.setVisible(False)

    def _restore_full_route_visibility(self):
        self._avatar_hiding_route = False
        for index, items in enumerate(self._route_segment_items):
            if index >= len(self._route_segments):
                continue
            sx, sy, ex, ey = self._route_segments[index]
            for item in items:
                item.setLine(sx, sy, ex, ey)
                item.setVisible(True)
        if self._route_dot is not None and self._route_segments:
            _, _, ex, ey = self._route_segments[-1]
            self._route_dot.setPos(ex, ey)
            self._route_dot.setVisible(True)
        if self._route_flow_items:
            self._route_flow_timer.start(42)

    def _clear_avatar(self):
        self._avatar_timer.stop()
        if hasattr(self, '_clear_fireworks'):
            self._clear_fireworks()
        else:
            self._firework_timer.stop()
            for particle in self._firework_particles:
                self._scene.removeItem(particle["item"])
            self._firework_particles.clear()
            
        if self._avatar_item is not None:
            self._scene.removeItem(self._avatar_item)
        self._avatar_item = None
        self._avatar_segments = []
        self._avatar_hiding_route = False

    def wheelEvent(self, event: QWheelEvent | None) -> None:
        if event is None:
            return
        factor = 1.18 if event.angleDelta().y() > 0 else 1 / 1.18
        self.scale(factor, factor)

    def mousePressEvent(self, event) -> None:
        if event is not None and event.button() == Qt.MouseButton.LeftButton:
            local_pos = self._event_to_map_pos(event)
            if local_pos is not None:
                x, y = local_pos.x(), local_pos.y()
                clicked_node = self._nearest_node(x, y)
                if self.editable:
                    if self._interaction_mode in {"add_node", "set_entry"}:
                        self.map_clicked.emit(x, y)
                        return
                    if self._interaction_mode == "move_node":
                        if clicked_node:
                            self.node_clicked.emit(clicked_node)
                        else:
                            self.map_clicked.emit(x, y)
                        return
                    if clicked_node and self._interaction_mode in {"select", "add_edge", "delete_edge", "delete_node"}:
                        self.node_clicked.emit(clicked_node)
                        if self._interaction_mode != "select":
                            return
                else:
                    # Chế độ xem: click node để chọn đích
                    if clicked_node:
                        self.node_clicked.emit(clicked_node)
        super().mousePressEvent(event)

    def _event_to_map_pos(self, event) -> Optional[QPointF]:
        if self._root is None:
            return None
        scene_pos = self.mapToScene(event.pos())
        return self._root.mapFromScene(scene_pos)

    def _nearest_node(self, x: float, y: float) -> Optional[str]:
        best_id: Optional[str] = None
        best_distance = 18.0
        for node_id, item in self._node_items.items():
            pos = item.pos()
            distance = ((pos.x() - x) ** 2 + (pos.y() - y) ** 2) ** 0.5
            if distance <= best_distance:
                best_id = node_id
                best_distance = distance
        return best_id

    def reset_view(self) -> None:
        self.resetTransform()
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
