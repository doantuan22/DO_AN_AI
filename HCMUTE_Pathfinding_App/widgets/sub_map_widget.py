"""Canvas hiển thị/chỉnh sửa ảnh, graph và marker của bản đồ con."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

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

    def load_map(
        self,
        image_path: str | Path,
        graph: Dict[str, Any],
        rotation: float = 0,
    ) -> None:
        self._scene.clear()
        self._node_items.clear()
        self._edge_items.clear()
        self._graph = graph
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
                label = QGraphicsSimpleTextItem(str(node.get("name") or "Cổng vào"), item)
                label.setBrush(QColor("#B71C1C"))
                label.setPos(15, -11)
                label.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
            else:
                item = _MovablePoint(node_id, 8, QColor("#0B74FF"), self.editable, self._on_point_moved, self._root)
                item.setPos(float(node.get("x", 0)), float(node.get("y", 0)))
                label = QGraphicsSimpleTextItem(str(node.get("name") or node_id), item)
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
        pan_mode = self._interaction_mode == "pan"
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag if pan_mode else QGraphicsView.DragMode.NoDrag)
        movable = self.editable and self._interaction_mode == "select"
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
                label = QGraphicsSimpleTextItem(str(node.get("name") or "Cổng vào"), item)
                label.setBrush(QColor("#B71C1C"))
                label.setPos(15, -11)
                label.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
            else:
                item = _MovablePoint(node_id, 8, QColor("#0B74FF"), self.editable, self._on_point_moved, temp)
                item.setPos(float(node["x"]), float(node["y"]))
                label = QGraphicsSimpleTextItem(str(node.get("name") or node_id), item)
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
            line.setPen(QPen(QColor(28, 100, 242, 180), 3)); line.setZValue(5)
            self._edge_items.append((source, target, line))

    def _update_edges_for(self, node_id: str) -> None:
        for source, target, line in self._edge_items:
            if node_id not in (source, target):
                continue
            a, b = self._node_items[source].pos(), self._node_items[target].pos()
            line.setLine(a.x(), a.y(), b.x(), b.y())

    def wheelEvent(self, event: QWheelEvent | None) -> None:
        if event is None:
            return
        factor = 1.18 if event.angleDelta().y() > 0 else 1 / 1.18
        self.scale(factor, factor)

    def mousePressEvent(self, event) -> None:
        if self.editable and event is not None and event.button() == Qt.MouseButton.LeftButton:
            local_pos = self._event_to_map_pos(event)
            if local_pos is not None:
                x, y = local_pos.x(), local_pos.y()
                clicked_node = self._nearest_node(x, y)
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
