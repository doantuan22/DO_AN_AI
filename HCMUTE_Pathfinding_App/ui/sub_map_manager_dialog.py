# Dialog quản lý bản đồ con bằng cách chọn node trực tiếp trên bản đồ chính

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap, QWheelEvent
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.graph import Graph
from services.sub_map_store import SubMap, SubMapStore


class _MainMapPicker(QGraphicsView):
    node_selected = pyqtSignal(str)

    def __init__(self, graph: Graph, map_path: str | Path, parent=None):
        super().__init__(parent)
        self.graph = graph
        self.map_path = Path(map_path)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("QGraphicsView { background:#EEF3F8; border:1px solid #D8E2EF; border-radius:8px; }")
        self._node_items: dict[str, QGraphicsEllipseItem] = {}
        self._selected_node_id: Optional[str] = None
        self._load()

    def _load(self) -> None:
        self._scene.clear()
        self._node_items.clear()

        pixmap = QPixmap(str(self.map_path))
        if pixmap.isNull():
            pixmap = QPixmap(1122, 1402)
            pixmap.fill(QColor("#FFFFFF"))
        root = QGraphicsPixmapItem(pixmap)
        root.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self._scene.addItem(root)

        for edge in self.graph.edges:
            source = self.graph.get_node(edge.source)
            target = self.graph.get_node(edge.target)
            if source is None or target is None:
                continue
            line = QGraphicsLineItem(source.x, source.y, target.x, target.y)
            line.setPen(QPen(QColor(120, 140, 170, 130), 2))
            line.setZValue(2)
            self._scene.addItem(line)

        for node_id in self.graph.get_all_node_ids():
            node = self.graph.get_node(node_id)
            if node is None:
                continue
            item = QGraphicsEllipseItem(-7.5, -7.5, 15, 15)
            item.setPos(node.x, node.y)
            item.setBrush(QColor("#0B74FF"))
            item.setPen(QPen(QColor("#FFFFFF"), 2.4))
            item.setZValue(10)
            item.setToolTip(f"{self.graph.get_node_name(node_id)} ({node_id})")
            self._scene.addItem(item)
            self._node_items[node_id] = item

            label = QGraphicsSimpleTextItem(node_id)
            label.setBrush(QColor("#102A56"))
            label.setPos(node.x + 10, node.y - 10)
            label.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
            label.setZValue(11)
            self._scene.addItem(label)

        self._scene.setSceneRect(self._scene.itemsBoundingRect().adjusted(-40, -40, 40, 40))
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def set_selected_node(self, node_id: Optional[str]) -> None:
        self._selected_node_id = node_id
        for item_id, item in self._node_items.items():
            selected = item_id == node_id
            radius = 12 if selected else 7.5
            item.setRect(-radius, -radius, radius * 2, radius * 2)
            item.setBrush(QColor("#E53935") if selected else QColor("#0B74FF"))
            item.setPen(QPen(QColor("#FFFFFF"), 3 if selected else 2.4))
            item.setZValue(20 if selected else 10)
        if node_id and node_id in self._node_items:
            self.centerOn(self._node_items[node_id])

    def mousePressEvent(self, event):
        if event is not None and event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            node_id = self._nearest_node(scene_pos.x(), scene_pos.y())
            if node_id:
                self.node_selected.emit(node_id)
                return
        super().mousePressEvent(event)

    def wheelEvent(self, event: QWheelEvent | None) -> None:
        if event is None:
            return
        factor = 1.18 if event.angleDelta().y() > 0 else 1 / 1.18
        self.scale(factor, factor)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if not self._scene.sceneRect().isEmpty():
            self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            self.set_selected_node(self._selected_node_id)

    def _nearest_node(self, x: float, y: float) -> Optional[str]:
        best_id: Optional[str] = None
        best_distance = 24.0
        for node_id, node in self.graph.nodes.items():
            distance = ((node.x - x) ** 2 + (node.y - y) ** 2) ** 0.5
            if distance <= best_distance:
                best_distance = distance
                best_id = node_id
        return best_id


class _SubMapForm(QDialog):
    def __init__(self, parent=None, item: Optional[SubMap] = None):
        super().__init__(parent)
        self.setWindowTitle("Sửa bản đồ con" if item else "Thêm bản đồ con")
        self.resize(540, 230)
        root = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit(item.name if item else "")
        self.floor_spin = QSpinBox()
        self.floor_spin.setRange(-20, 200)
        self.floor_spin.setValue(item.floor if item else 1)

        image_row = QHBoxLayout()
        self.image_edit = QLineEdit()
        self.image_edit.setReadOnly(True)
        choose = QPushButton("Chọn ảnh...")
        choose.clicked.connect(self._choose_image)
        image_row.addWidget(self.image_edit, 1)
        image_row.addWidget(choose)

        form.addRow("Tên bản đồ con:", self.name_edit)
        form.addRow("Tầng:", self.floor_spin)
        form.addRow("Ảnh mới:" if item else "Ảnh bản đồ:", image_row)
        if item:
            form.addRow("Ảnh hiện tại:", QLabel(item.image))
            form.addRow("File node/cạnh:", QLabel(item.graph_file))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        root.addLayout(form)
        root.addWidget(buttons)

    def _choose_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn ảnh bản đồ",
            "",
            "Ảnh (*.png *.jpg *.jpeg *.bmp *.webp)",
        )
        if path:
            self.image_edit.setText(path)

    def _validate(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Thiếu thông tin", "Hãy nhập tên bản đồ con.")
            return
        self.accept()


class _CopySubMapDialog(QDialog):
    def __init__(self, graph: Graph, store: SubMapStore, target_node_id: str, parent=None):
        super().__init__(parent)
        self.graph = graph
        self.store = store
        self.target_node_id = target_node_id
        self.setWindowTitle("Copy bản đồ con")
        self.resize(560, 260)

        root = QVBoxLayout(self)
        form = QFormLayout()

        self.source_node_combo = QComboBox()
        self.source_map_combo = QComboBox()
        self.name_edit = QLineEdit()
        self.floor_spin = QSpinBox()
        self.floor_spin.setRange(-20, 200)

        for node_id in graph.get_all_node_ids():
            if node_id == target_node_id or not store.has_sub_maps(node_id):
                continue
            self.source_node_combo.addItem(f"{graph.get_node_name(node_id)} ({node_id})", node_id)

        self.source_node_combo.currentIndexChanged.connect(self._reload_maps)
        self.source_map_combo.currentIndexChanged.connect(self._sync_selected_map)

        form.addRow("Node nguồn:", self.source_node_combo)
        form.addRow("Bản đồ con nguồn:", self.source_map_combo)
        form.addRow("Tên bản đồ mới:", self.name_edit)
        form.addRow("Tầng:", self.floor_spin)

        note = QLabel(
            "Bản copy sẽ thuộc node đang chọn trên bản đồ chính. Ảnh và node/cạnh "
            "được ghi sang các file riêng để không ảnh hưởng bản gốc."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#5F6368")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)

        root.addLayout(form)
        root.addWidget(note)
        root.addWidget(buttons)
        self._reload_maps()

    def source_sub_map_id(self) -> str:
        return str(self.source_map_combo.currentData() or "")

    def copy_name(self) -> str:
        return self.name_edit.text().strip()

    def copy_floor(self) -> int:
        return self.floor_spin.value()

    def _reload_maps(self):
        node_id = str(self.source_node_combo.currentData() or "")
        self.source_map_combo.blockSignals(True)
        self.source_map_combo.clear()
        for item in self.store.list_for_node(node_id):
            self.source_map_combo.addItem(f"Tầng {item.floor} - {item.name}", item.id)
        self.source_map_combo.blockSignals(False)
        self._sync_selected_map()

    def _sync_selected_map(self):
        sub_map_id = self.source_sub_map_id()
        if not sub_map_id:
            self.name_edit.clear()
            self.floor_spin.setValue(1)
            return
        try:
            item = self.store.get(sub_map_id)
        except (KeyError, ValueError):
            return
        self.name_edit.setText(item.name)
        self.floor_spin.setValue(item.floor)

    def _validate(self):
        if not self.source_sub_map_id():
            QMessageBox.information(self, "Chưa có dữ liệu nguồn", "Không tìm thấy bản đồ con ở node khác để copy.")
            return
        if not self.copy_name():
            QMessageBox.warning(self, "Thiếu tên", "Hãy nhập tên bản đồ con mới.")
            return
        self.accept()


class SubMapManagerDialog(QDialog):
    def __init__(self, graph: Graph, store: SubMapStore, map_path: str | Path | None = None, parent=None):
        super().__init__(parent)
        self.graph = graph
        self.store = store
        self.map_path = Path(map_path) if map_path else store.base_dir / "assets" / "map.png"
        self._selected_node_id: Optional[str] = None

        self.setWindowTitle("Chỉnh sửa bản đồ con")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)
        self.resize(1320, 820)

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        self.main_map = _MainMapPicker(graph, self.map_path, self)
        self.main_map.node_selected.connect(self._select_node)
        root.addWidget(self.main_map, 1)

        panel = QWidget()
        panel.setFixedWidth(430)
        side = QVBoxLayout(panel)
        side.setContentsMargins(0, 0, 0, 0)
        side.setSpacing(10)

        title = QLabel("Cài đặt bản đồ con")
        title.setStyleSheet("font-size:20px;font-weight:800;color:#0B63E5")
        scope_note = QLabel("Mỗi node có thể có nhiều bản đồ con trong cùng một tầng, miễn là tên bản đồ khác nhau.")
        scope_note.setWordWrap(True)
        scope_note.setStyleSheet("color:#5F6368")
        self.selected_label = QLabel("Chọn một node trên bản đồ chính")
        self.selected_label.setWordWrap(True)
        self.selected_label.setStyleSheet("color:#0F172A;font-weight:700")

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(lambda _: self._open_editor())

        actions_1 = QHBoxLayout()
        add_button = QPushButton("Thêm bản đồ con")
        add_button.clicked.connect(self._add)
        edit_meta_button = QPushButton("Sửa thông tin")
        edit_meta_button.clicked.connect(self._edit)
        actions_1.addWidget(add_button)
        actions_1.addWidget(edit_meta_button)

        actions_2 = QHBoxLayout()
        open_editor_button = QPushButton("Chỉnh node / cạnh / vị trí")
        open_editor_button.clicked.connect(self._open_editor)
        delete_button = QPushButton("Xóa bản đồ con")
        delete_button.clicked.connect(self._delete)
        actions_2.addWidget(open_editor_button)
        actions_2.addWidget(delete_button)

        actions_3 = QHBoxLayout()
        copy_button = QPushButton("Copy bản đồ con")
        copy_button.clicked.connect(self._copy_from_other_node)
        actions_3.addWidget(copy_button)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(150)
        self.log_text.setStyleSheet(
            "QTextEdit { background:#FFFFFF; border:1px solid #D8E2EF; border-radius:8px; padding:8px; }"
        )

        close = QPushButton("Đóng")
        close.clicked.connect(self.accept)

        side.addWidget(title)
        side.addWidget(scope_note)
        side.addWidget(self.selected_label)
        side.addWidget(QLabel("Bản đồ con của node đang chọn:"))
        side.addWidget(self.list_widget, 1)
        side.addLayout(actions_1)
        side.addLayout(actions_2)
        side.addLayout(actions_3)
        side.addWidget(QLabel("Thông báo:"))
        side.addWidget(self.log_text)
        side.addWidget(close)
        root.addWidget(panel)

        self._log("Chọn node trực tiếp trên bản đồ chính để thêm hoặc chỉnh sửa bản đồ con.")

    def _node_id(self) -> str:
        return self._selected_node_id or ""

    def _selected(self) -> Optional[SubMap]:
        item = self.list_widget.currentItem()
        if item is None:
            return None
        try:
            return self.store.get(str(item.data(Qt.ItemDataRole.UserRole)))
        except (KeyError, ValueError) as exc:
            self._log(f"Không thể đọc bản đồ con: {exc}")
            return None

    def _select_node(self, node_id: str):
        self._selected_node_id = node_id
        self.main_map.set_selected_node(node_id)
        self.selected_label.setText(f"Node đang chọn: {self.graph.get_node_name(node_id)} ({node_id})")
        self._reload()
        self._log(f"Đã chọn node {node_id}.")

    def _reload(self):
        self.list_widget.clear()
        if not self._selected_node_id:
            return
        for sub_map in self.store.list_for_node(self._selected_node_id):
            item = QListWidgetItem(
                f"Tầng {sub_map.floor}  -  {sub_map.name}\n"
                f"Ảnh: {sub_map.image}\n"
                f"Node/cạnh: {sub_map.graph_file}"
            )
            item.setData(Qt.ItemDataRole.UserRole, sub_map.id)
            self.list_widget.addItem(item)
        if self.list_widget.count() == 0:
            self._log(f"Node {self._selected_node_id} chưa có bản đồ con.")

    def _add(self):
        node_id = self._node_id()
        if not node_id:
            QMessageBox.information(self, "Chưa chọn node", "Hãy chọn node trên bản đồ chính trước.")
            return
        dialog = _SubMapForm(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if not dialog.image_edit.text():
            QMessageBox.warning(self, "Thiếu ảnh", "Bản đồ con bắt buộc phải có ảnh.")
            return
        try:
            created = self.store.create(
                node_id,
                dialog.name_edit.text(),
                dialog.floor_spin.value(),
                dialog.image_edit.text(),
            )
            self._reload()
            self._select(created.id)
            self._log(f"Đã thêm bản đồ con '{created.name}' cho node {node_id}.")
        except Exception as exc:
            QMessageBox.warning(self, "Không thể thêm", str(exc))
            self._log(f"Lỗi thêm bản đồ con: {exc}")

    def _edit(self):
        current = self._selected()
        if not current:
            QMessageBox.information(self, "Chưa chọn", "Hãy chọn một bản đồ con trong danh sách.")
            return
        dialog = _SubMapForm(self, current)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            updated = self.store.update(
                current.id,
                name=dialog.name_edit.text(),
                floor=dialog.floor_spin.value(),
                source_image=dialog.image_edit.text() or None,
                rename_graph_file=True,
            )
            self._reload()
            self._select(updated.id)
            self._log(f"Đã cập nhật thông tin bản đồ con '{updated.name}'.")
        except Exception as exc:
            QMessageBox.warning(self, "Không thể cập nhật", str(exc))
            self._log(f"Lỗi cập nhật bản đồ con: {exc}")

    def _copy_from_other_node(self):
        target_node_id = self._node_id()
        if not target_node_id:
            QMessageBox.information(self, "Chưa chọn node đích", "Hãy chọn node đích trên bản đồ chính trước.")
            return
        dialog = _CopySubMapDialog(self.graph, self.store, target_node_id, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            copied = self.store.copy_to_node(
                dialog.source_sub_map_id(),
                target_node_id,
                name=dialog.copy_name(),
                floor=dialog.copy_floor(),
            )
            self._reload()
            self._select(copied.id)
            self._log(
                f"Đã copy bản đồ con '{copied.name}' sang node {target_node_id}. "
                "Hãy mở chỉnh sửa để đặt lại vị trí đứng nếu cần."
            )
        except Exception as exc:
            QMessageBox.warning(self, "Không thể copy", str(exc))
            self._log(f"Lỗi copy bản đồ con: {exc}")

    def _delete(self):
        current = self._selected()
        if not current:
            QMessageBox.information(self, "Chưa chọn", "Hãy chọn một bản đồ con cần xóa.")
            return
        box = QMessageBox(self)
        box.setWindowTitle("Xóa bản đồ con")
        box.setText(f"Xóa '{current.name}' khỏi node {current.main_node_id}?")
        metadata = box.addButton("Chỉ xóa liên kết", QMessageBox.ButtonRole.AcceptRole)
        files = box.addButton("Xóa cả ảnh và JSON", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.exec()
        if box.clickedButton() not in (metadata, files):
            return
        try:
            self.store.delete(current.id, delete_files=box.clickedButton() == files)
            self._reload()
            self._log(f"Đã xóa bản đồ con '{current.name}'.")
        except Exception as exc:
            QMessageBox.warning(self, "Không thể xóa", str(exc))
            self._log(f"Lỗi xóa bản đồ con: {exc}")

    def _open_editor(self):
        current = self._selected()
        if not current:
            QMessageBox.information(self, "Chưa chọn", "Hãy chọn một bản đồ con để chỉnh sửa.")
            return
        from ui.sub_map_editor_dialog import SubMapEditorDialog

        SubMapEditorDialog(current.id, self.store, self).exec()
        self._reload()
        self._select(current.id)
        self._log(f"Đã mở/chỉnh sửa node, cạnh và vị trí hiện tại của '{current.name}'.")

    def _select(self, sub_map_id: str):
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            if item and item.data(Qt.ItemDataRole.UserRole) == sub_map_id:
                self.list_widget.setCurrentRow(row)
                break

    def _log(self, message: str):
        self.log_text.append(f"- {message}")
