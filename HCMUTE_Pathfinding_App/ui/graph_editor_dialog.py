"""
graph_editor_dialog.py - Dialog chỉnh sửa node/cạnh của bản đồ.
"""

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.graph import Graph
from ui.map_widget import MapWidget


class EditableMapWidget(MapWidget):
    """MapWidget có thêm signal click vùng trống để chỉnh sửa trực quan."""

    map_clicked = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._left_drag_pan = False
        self._is_panning = False
        self._last_pan_pos = None

    def set_left_drag_pan(self, enabled: bool):
        """Bật/tắt kéo bản đồ bằng chuột trái."""
        self._left_drag_pan = enabled

    def mousePressEvent(self, event):
        if event is None:
            return
        if event.button() in (Qt.MouseButton.RightButton, Qt.MouseButton.MiddleButton):
            self._start_pan(event)
            return
        if event.button() == Qt.MouseButton.LeftButton and self._left_drag_pan:
            self._start_pan(event)
            return
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            clicked_node = self._find_nearest_node(scene_pos.x(), scene_pos.y())
            if clicked_node:
                self.node_clicked.emit(clicked_node)
                return
            self.map_clicked.emit(scene_pos.x(), scene_pos.y())
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_panning and event is not None and self._last_pan_pos is not None:
            delta = event.pos() - self._last_pan_pos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            self._last_pan_pos = event.pos()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._is_panning:
            self._is_panning = False
            self._last_pan_pos = None
            self.unsetCursor()
            return
        super().mouseReleaseEvent(event)

    def _start_pan(self, event):
        self._is_panning = True
        self._last_pan_pos = event.pos()
        self.setCursor(Qt.CursorShape.ClosedHandCursor)


class GraphEditorDialog(QDialog):
    """Công cụ thêm/sửa/xóa node, cạnh và chỉnh hiển thị cạnh."""

    graph_changed = pyqtSignal()
    edge_display_changed = pyqtSignal(bool, float, int)

    def __init__(
        self,
        graph: Graph,
        json_path: str,
        map_path: str,
        edge_visible: bool,
        edge_width: float,
        edge_opacity: int,
        parent=None,
    ):
        super().__init__(parent)
        self._graph = graph
        self._json_path = json_path
        self._map_path = map_path
        self._selected_node_id: Optional[str] = None
        self._selected_edge: Optional[tuple[str, str]] = None
        self._visual_edge_first: Optional[str] = None
        self._edge_visible = edge_visible
        self._edge_width = edge_width
        self._edge_opacity = edge_opacity
        self._modified = False

        self.setWindowTitle("Chinh sua ban do")
        self.setMinimumSize(980, 680)
        self.resize(1180, 760)

        self._setup_ui(edge_visible, edge_width, edge_opacity)
        self._reload_all()

    def _setup_ui(self, edge_visible: bool, edge_width: float, edge_opacity: int):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        self._status_label = QLabel("Chua co thay doi")
        self._status_label.setStyleSheet("color: #5F6368;")

        tabs = QTabWidget()
        tabs.addTab(self._create_visual_tab(), "Ban do truc quan")
        tabs.addTab(self._create_nodes_tab(), "Node")
        tabs.addTab(self._create_edges_tab(), "Canh")
        tabs.addTab(self._create_display_tab(edge_visible, edge_width, edge_opacity), "Hien thi canh")

        bottom = QHBoxLayout()
        self.btn_save = QPushButton("Luu JSON")
        self.btn_save.clicked.connect(self._save)
        btn_close = QPushButton("Dong")
        btn_close.clicked.connect(self.close)
        bottom.addWidget(self._status_label, 1)
        bottom.addWidget(self.btn_save)
        bottom.addWidget(btn_close)

        root.addWidget(tabs, 1)
        root.addLayout(bottom)

    def _create_visual_tab(self) -> QWidget:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.editor_map = EditableMapWidget()
        self.editor_map.setup_map(self._graph, self._map_path)
        self.editor_map.set_edge_display(self._edge_visible, self._edge_width, self._edge_opacity)
        self.editor_map.node_clicked.connect(self._on_visual_node_clicked)
        self.editor_map.map_clicked.connect(self._on_visual_map_clicked)

        side = QGroupBox("Thao tac truc tiep")
        side.setFixedWidth(310)
        side_layout = QVBoxLayout(side)
        side_layout.setSpacing(8)

        self.visual_mode_combo = QComboBox()
        self.visual_mode_combo.addItems([
            "Di chuyen ban do",
            "Chon node",
            "Them node tai vi tri click",
            "Di chuyen node da chon",
            "Them canh bang 2 click",
            "Xoa canh bang 2 click",
            "Xoa node duoc click",
        ])
        self.visual_mode_combo.setCurrentText("Chon node")
        self.visual_mode_combo.currentIndexChanged.connect(self._on_visual_mode_changed)

        self.visual_selected_label = QLabel("Node dang chon: chua co")
        self.visual_selected_label.setWordWrap(True)
        self.visual_selected_label.setStyleSheet("color: #1A73E8; font-weight: bold;")

        form = QFormLayout()
        self.visual_node_id_edit = QLineEdit()
        self.visual_node_id_edit.setPlaceholderText("Tu dong neu de trong")
        self.visual_node_name_edit = QLineEdit()
        self.visual_node_name_edit.setPlaceholderText("Ten hien thi")
        self.visual_x_label = QLabel("-")
        self.visual_y_label = QLabel("-")
        form.addRow("ID node moi", self.visual_node_id_edit)
        form.addRow("Ten node", self.visual_node_name_edit)
        form.addRow("X click", self.visual_x_label)
        form.addRow("Y click", self.visual_y_label)

        btn_rename = QPushButton("Doi ten node dang chon")
        btn_rename.clicked.connect(self._rename_selected_from_visual)
        btn_clear_name = QPushButton("An ten node dang chon")
        btn_clear_name.clicked.connect(self._clear_selected_node_name)
        btn_recenter = QPushButton("Fit lai ban do")
        btn_recenter.clicked.connect(self.editor_map.zoom_reset)

        hint = QLabel(
            "Chon mode roi thao tac tren ban do. "
            "Co the giu chuot phai hoac chuot giua de keo ban do o moi che do. "
            "Them/xoa canh dung 2 lan click vao 2 node. "
            "Di chuyen node: chon node truoc, sau do click vi tri moi."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #70757A;")

        side_layout.addWidget(QLabel("Che do"))
        side_layout.addWidget(self.visual_mode_combo)
        side_layout.addWidget(self.visual_selected_label)
        side_layout.addLayout(form)
        side_layout.addWidget(btn_rename)
        side_layout.addWidget(btn_clear_name)
        side_layout.addWidget(btn_recenter)
        side_layout.addWidget(hint)
        side_layout.addStretch()

        layout.addWidget(self.editor_map, 1)
        layout.addWidget(side)
        return tab

    def _create_nodes_tab(self) -> QWidget:
        tab = QWidget()
        layout = QHBoxLayout(tab)

        self.node_table = QTableWidget(0, 4)
        self.node_table.setHorizontalHeaderLabels(["ID", "Ten", "X", "Y"])
        self.node_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.node_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.node_table.itemSelectionChanged.connect(self._on_node_selected)
        self.node_table.horizontalHeader().setStretchLastSection(True)

        form_box = QGroupBox("Thong tin node")
        form_layout = QVBoxLayout(form_box)
        fields = QFormLayout()

        self.node_id_edit = QLineEdit()
        self.node_name_edit = QLineEdit()
        self.node_x_spin = QSpinBox()
        self.node_x_spin.setRange(0, max(20000, self._graph.image_size[0] or 20000))
        self.node_y_spin = QSpinBox()
        self.node_y_spin.setRange(0, max(20000, self._graph.image_size[1] or 20000))

        fields.addRow("ID", self.node_id_edit)
        fields.addRow("Ten hien thi", self.node_name_edit)
        fields.addRow("X", self.node_x_spin)
        fields.addRow("Y", self.node_y_spin)

        btn_row_1 = QHBoxLayout()
        btn_new = QPushButton("Nhap node moi")
        btn_new.clicked.connect(self._clear_node_form)
        btn_add = QPushButton("Them node")
        btn_add.clicked.connect(self._add_node)
        btn_row_1.addWidget(btn_new)
        btn_row_1.addWidget(btn_add)

        btn_row_2 = QHBoxLayout()
        btn_update = QPushButton("Cap nhat node")
        btn_update.clicked.connect(self._update_node)
        btn_delete = QPushButton("Xoa node")
        btn_delete.clicked.connect(self._delete_node)
        btn_row_2.addWidget(btn_update)
        btn_row_2.addWidget(btn_delete)

        note = QLabel("Xoa node se xoa tat ca canh lien quan.")
        note.setWordWrap(True)
        note.setStyleSheet("color: #70757A;")

        form_layout.addLayout(fields)
        form_layout.addLayout(btn_row_1)
        form_layout.addLayout(btn_row_2)
        form_layout.addWidget(note)
        form_layout.addStretch()

        layout.addWidget(self.node_table, 2)
        layout.addWidget(form_box, 1)
        return tab

    def _create_edges_tab(self) -> QWidget:
        tab = QWidget()
        layout = QHBoxLayout(tab)

        self.edge_table = QTableWidget(0, 3)
        self.edge_table.setHorizontalHeaderLabels(["Tu", "Den", "Trong so"])
        self.edge_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.edge_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.edge_table.itemSelectionChanged.connect(self._on_edge_selected)
        self.edge_table.horizontalHeader().setStretchLastSection(True)

        form_box = QGroupBox("Thong tin canh")
        form_layout = QVBoxLayout(form_box)
        fields = QFormLayout()

        self.edge_source_combo = QComboBox()
        self.edge_target_combo = QComboBox()
        self.edge_weight_spin = QDoubleSpinBox()
        self.edge_weight_spin.setRange(0.01, 100000.0)
        self.edge_weight_spin.setDecimals(2)
        self.edge_weight_spin.setSingleStep(5.0)
        self.edge_auto_weight = QCheckBox("Tu tinh theo khoang cach 2 node")
        self.edge_auto_weight.setChecked(True)
        self.edge_auto_weight.stateChanged.connect(self._update_auto_weight)
        self.edge_source_combo.currentIndexChanged.connect(self._update_auto_weight)
        self.edge_target_combo.currentIndexChanged.connect(self._update_auto_weight)

        fields.addRow("Node dau", self.edge_source_combo)
        fields.addRow("Node cuoi", self.edge_target_combo)
        fields.addRow("Trong so", self.edge_weight_spin)
        fields.addRow("", self.edge_auto_weight)

        btn_add = QPushButton("Them canh")
        btn_add.clicked.connect(self._add_edge)
        btn_update = QPushButton("Cap nhat trong so")
        btn_update.clicked.connect(self._update_edge)
        btn_delete = QPushButton("Xoa canh")
        btn_delete.clicked.connect(self._delete_edge)

        form_layout.addLayout(fields)
        form_layout.addWidget(btn_add)
        form_layout.addWidget(btn_update)
        form_layout.addWidget(btn_delete)
        form_layout.addStretch()

        layout.addWidget(self.edge_table, 2)
        layout.addWidget(form_box, 1)
        return tab

    def _create_display_tab(self, edge_visible: bool, edge_width: float, edge_opacity: int) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        box = QGroupBox("Cach hien thi canh tren ban do")
        grid = QGridLayout(box)

        self.show_edges_check = QCheckBox("Hien thi canh")
        self.show_edges_check.setChecked(edge_visible)

        self.edge_width_spin = QDoubleSpinBox()
        self.edge_width_spin.setRange(0.5, 12.0)
        self.edge_width_spin.setSingleStep(0.5)
        self.edge_width_spin.setValue(edge_width)

        self.edge_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.edge_opacity_slider.setRange(20, 255)
        self.edge_opacity_slider.setValue(edge_opacity)
        self.edge_opacity_label = QLabel(str(edge_opacity))
        self.edge_opacity_slider.valueChanged.connect(
            lambda value: self.edge_opacity_label.setText(str(value))
        )

        btn_apply = QPushButton("Ap dung hien thi")
        btn_apply.clicked.connect(self._apply_edge_display)

        grid.addWidget(self.show_edges_check, 0, 0, 1, 2)
        grid.addWidget(QLabel("Do day"), 1, 0)
        grid.addWidget(self.edge_width_spin, 1, 1)
        grid.addWidget(QLabel("Do mo"), 2, 0)
        grid.addWidget(self.edge_opacity_slider, 2, 1)
        grid.addWidget(self.edge_opacity_label, 2, 2)
        grid.addWidget(btn_apply, 3, 0, 1, 3)

        layout.addWidget(box)
        return tab

    def _reload_all(self):
        self._reload_node_table()
        self._reload_edge_table()
        self._reload_edge_combos()
        self._refresh_editor_map()

    def _reload_node_table(self):
        self.node_table.blockSignals(True)
        self.node_table.setRowCount(0)
        for row, node_id in enumerate(self._graph.get_all_node_ids()):
            node = self._graph.nodes[node_id]
            self.node_table.insertRow(row)
            for col, value in enumerate([node.id, node.name, str(node.x), str(node.y)]):
                self.node_table.setItem(row, col, QTableWidgetItem(value))
        self.node_table.blockSignals(False)

    def _reload_edge_table(self):
        self.edge_table.blockSignals(True)
        self.edge_table.setRowCount(0)
        for row, edge in enumerate(self._graph.edges):
            self.edge_table.insertRow(row)
            values = [edge.source, edge.target, f"{edge.weight:.2f}"]
            for col, value in enumerate(values):
                self.edge_table.setItem(row, col, QTableWidgetItem(value))
        self.edge_table.blockSignals(False)

    def _reload_edge_combos(self):
        current_source = self.edge_source_combo.currentData()
        current_target = self.edge_target_combo.currentData()
        self.edge_source_combo.blockSignals(True)
        self.edge_target_combo.blockSignals(True)
        self.edge_source_combo.clear()
        self.edge_target_combo.clear()
        for node_id in self._graph.get_all_node_ids():
            node = self._graph.nodes[node_id]
            display_name = node.name if node.name else "(khong co ten)"
            display = f"{display_name} ({node_id})"
            self.edge_source_combo.addItem(display, node_id)
            self.edge_target_combo.addItem(display, node_id)
        self._set_combo_data(self.edge_source_combo, current_source)
        self._set_combo_data(self.edge_target_combo, current_target)
        self.edge_source_combo.blockSignals(False)
        self.edge_target_combo.blockSignals(False)
        self._update_auto_weight()

    def _on_node_selected(self):
        row = self.node_table.currentRow()
        if row < 0:
            return
        node_id = self.node_table.item(row, 0).text()
        node = self._graph.get_node(node_id)
        if node is None:
            return
        self._selected_node_id = node_id
        self.node_id_edit.setText(node.id)
        self.node_id_edit.setEnabled(False)
        self.node_name_edit.setText(node.name)
        self.node_x_spin.setValue(int(node.x))
        self.node_y_spin.setValue(int(node.y))
        if hasattr(self, "visual_selected_label"):
            display_name = node.name if node.name else "(khong co ten)"
            self.visual_selected_label.setText(f"Node dang chon: {display_name} ({node.id})")
            self.visual_node_name_edit.setText(node.name)
            self.visual_x_label.setText(str(node.x))
            self.visual_y_label.setText(str(node.y))
            self._highlight_selected_node(node_id)

    def _on_edge_selected(self):
        row = self.edge_table.currentRow()
        if row < 0:
            return
        source = self.edge_table.item(row, 0).text()
        target = self.edge_table.item(row, 1).text()
        weight = float(self.edge_table.item(row, 2).text())
        self._selected_edge = (source, target)
        self._set_combo_data(self.edge_source_combo, source)
        self._set_combo_data(self.edge_target_combo, target)
        self.edge_weight_spin.setValue(weight)

    def _on_visual_node_clicked(self, node_id: str):
        mode = self.visual_mode_combo.currentText()
        self._select_node(node_id)

        if mode == "Them canh bang 2 click":
            self._pick_visual_edge(node_id, create=True)
        elif mode == "Xoa canh bang 2 click":
            self._pick_visual_edge(node_id, create=False)
        elif mode == "Xoa node duoc click":
            self._delete_node()
        elif mode == "Di chuyen node da chon":
            self._status_label.setText("Da chon node. Click vi tri moi tren ban do de di chuyen.")
        elif mode == "Them node tai vi tri click":
            self._status_label.setText("Vi tri nay da co node. Click vung trong de them node moi.")
        else:
            self._status_label.setText(f"Da chon node {node_id}")

    def _on_visual_map_clicked(self, x: float, y: float):
        x_i = max(0, int(round(x)))
        y_i = max(0, int(round(y)))
        self.visual_x_label.setText(str(x_i))
        self.visual_y_label.setText(str(y_i))

        mode = self.visual_mode_combo.currentText()
        if mode == "Them node tai vi tri click":
            self._add_node_from_visual(x_i, y_i)
        elif mode == "Di chuyen node da chon":
            self._move_selected_node_from_visual(x_i, y_i)
        else:
            self._status_label.setText(f"Vi tri click: x={x_i}, y={y_i}")

    def _add_node_from_visual(self, x: int, y: int):
        node_id = self.visual_node_id_edit.text().strip() or self._suggest_node_id()
        name = self.visual_node_name_edit.text().strip() or node_id
        try:
            self._graph.add_node(node_id, x, y, name)
            self._selected_node_id = node_id
            self.visual_node_id_edit.clear()
            self.visual_node_name_edit.clear()
            self._after_graph_changed(f"Da them node {node_id} tai ({x}, {y})")
            self._select_node(node_id)
        except Exception as exc:
            self._show_error(exc)

    def _move_selected_node_from_visual(self, x: int, y: int):
        if not self._selected_node_id:
            QMessageBox.warning(self, "Thieu lua chon", "Hay chon node truoc khi di chuyen.")
            return
        node = self._graph.get_node(self._selected_node_id)
        if node is None:
            return
        try:
            self._graph.update_node(self._selected_node_id, x, y, node.name)
            self._after_graph_changed(f"Da di chuyen node {self._selected_node_id} den ({x}, {y})")
            self._select_node(self._selected_node_id)
        except Exception as exc:
            self._show_error(exc)

    def _rename_selected_from_visual(self):
        if not self._selected_node_id:
            QMessageBox.warning(self, "Thieu lua chon", "Hay chon node can doi ten.")
            return
        node = self._graph.get_node(self._selected_node_id)
        if node is None:
            return
        new_name = self.visual_node_name_edit.text().strip()
        if not new_name:
            QMessageBox.warning(self, "Thieu ten", "Nhap ten hien thi moi cho node.")
            return
        try:
            self._graph.update_node(self._selected_node_id, node.x, node.y, new_name)
            self._after_graph_changed(f"Da doi ten node {self._selected_node_id}")
            self._select_node(self._selected_node_id)
        except Exception as exc:
            self._show_error(exc)

    def _clear_selected_node_name(self):
        if not self._selected_node_id:
            QMessageBox.warning(self, "Thieu lua chon", "Hay chon node can an ten.")
            return
        node = self._graph.get_node(self._selected_node_id)
        if node is None:
            return
        try:
            self._graph.update_node(self._selected_node_id, node.x, node.y, "")
            self._after_graph_changed(f"Da an ten node {self._selected_node_id}")
            self._select_node(self._selected_node_id)
        except Exception as exc:
            self._show_error(exc)

    def _pick_visual_edge(self, node_id: str, create: bool):
        if self._visual_edge_first is None:
            self._visual_edge_first = node_id
            self._highlight_selected_node(node_id)
            action = "them" if create else "xoa"
            self._status_label.setText(f"Da chon node dau {node_id}. Click node thu hai de {action} canh.")
            return

        source = self._visual_edge_first
        target = node_id
        self._visual_edge_first = None
        if source == target:
            self._status_label.setText("Hai dau canh khong duoc trung nhau.")
            return

        try:
            if create:
                self._graph.add_edge(source, target)
                self._after_graph_changed(f"Da them canh {source} - {target}")
            else:
                self._graph.delete_edge(source, target)
                self._after_graph_changed(f"Da xoa canh {source} - {target}")
        except Exception as exc:
            self._show_error(exc)

    def _select_node(self, node_id: str):
        node = self._graph.get_node(node_id)
        if node is None:
            return
        self._selected_node_id = node_id
        display_name = node.name if node.name else "(khong co ten)"
        self.visual_selected_label.setText(f"Node dang chon: {display_name} ({node.id})")
        self.visual_node_name_edit.setText(node.name)
        self.visual_x_label.setText(str(node.x))
        self.visual_y_label.setText(str(node.y))

        self.node_id_edit.setText(node.id)
        self.node_id_edit.setEnabled(False)
        self.node_name_edit.setText(node.name)
        self.node_x_spin.setValue(int(node.x))
        self.node_y_spin.setValue(int(node.y))

        self._select_node_table_row(node_id)
        self._highlight_selected_node(node_id)

    def _select_node_table_row(self, node_id: str):
        self.node_table.blockSignals(True)
        self.node_table.clearSelection()
        for row in range(self.node_table.rowCount()):
            item = self.node_table.item(row, 0)
            if item and item.text() == node_id:
                self.node_table.selectRow(row)
                break
        self.node_table.blockSignals(False)

    def _highlight_selected_node(self, node_id: str):
        if not hasattr(self, "editor_map"):
            return
        self.editor_map.reset_all_nodes()
        self.editor_map.highlight_current(node_id)

    def _reset_visual_edge_pick(self):
        self._visual_edge_first = None
        if self._selected_node_id:
            self._highlight_selected_node(self._selected_node_id)

    def _on_visual_mode_changed(self):
        self._reset_visual_edge_pick()
        self.editor_map.set_left_drag_pan(
            self.visual_mode_combo.currentText() == "Di chuyen ban do"
        )

    def _refresh_editor_map(self):
        if not hasattr(self, "editor_map"):
            return
        self.editor_map.setup_map(self._graph, self._map_path)
        self.editor_map.set_edge_display(self._edge_visible, self._edge_width, self._edge_opacity)
        if self._selected_node_id and self._graph.node_exists(self._selected_node_id):
            self._highlight_selected_node(self._selected_node_id)

    def _suggest_node_id(self) -> str:
        used = set(self._graph.nodes.keys())
        index = 1
        while True:
            candidate = f"N{index:02d}"
            if candidate not in used:
                return candidate
            index += 1

    def _clear_node_form(self):
        self._selected_node_id = None
        self.node_table.clearSelection()
        self.node_id_edit.setEnabled(True)
        self.node_id_edit.clear()
        self.node_name_edit.clear()
        self.node_x_spin.setValue(0)
        self.node_y_spin.setValue(0)
        if hasattr(self, "visual_selected_label"):
            self.visual_selected_label.setText("Node dang chon: chua co")

    def _add_node(self):
        try:
            self._graph.add_node(
                self.node_id_edit.text(),
                self.node_x_spin.value(),
                self.node_y_spin.value(),
                self.node_name_edit.text(),
            )
            self._after_graph_changed("Da them node")
        except Exception as exc:
            self._show_error(exc)

    def _update_node(self):
        if not self._selected_node_id:
            QMessageBox.warning(self, "Thieu lua chon", "Hay chon node can cap nhat.")
            return
        try:
            self._graph.update_node(
                self._selected_node_id,
                self.node_x_spin.value(),
                self.node_y_spin.value(),
                self.node_name_edit.text(),
            )
            self._after_graph_changed("Da cap nhat node")
        except Exception as exc:
            self._show_error(exc)

    def _delete_node(self):
        if not self._selected_node_id:
            QMessageBox.warning(self, "Thieu lua chon", "Hay chon node can xoa.")
            return
        answer = QMessageBox.question(
            self,
            "Xoa node",
            f"Xoa node {self._selected_node_id} va cac canh lien quan?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self._graph.delete_node(self._selected_node_id)
            self._clear_node_form()
            self._after_graph_changed("Da xoa node")
        except Exception as exc:
            self._show_error(exc)

    def _add_edge(self):
        try:
            source, target = self._current_edge_nodes()
            weight = None if self.edge_auto_weight.isChecked() else self.edge_weight_spin.value()
            self._graph.add_edge(source, target, weight)
            self._after_graph_changed("Da them canh")
        except Exception as exc:
            self._show_error(exc)

    def _update_edge(self):
        try:
            source, target = self._current_edge_nodes()
            self._graph.update_edge(source, target, self.edge_weight_spin.value())
            self._after_graph_changed("Da cap nhat canh")
        except Exception as exc:
            self._show_error(exc)

    def _delete_edge(self):
        if not self._selected_edge:
            QMessageBox.warning(self, "Thieu lua chon", "Hay chon canh can xoa.")
            return
        source, target = self._selected_edge
        answer = QMessageBox.question(self, "Xoa canh", f"Xoa canh {source} - {target}?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self._graph.delete_edge(source, target)
            self._selected_edge = None
            self._after_graph_changed("Da xoa canh")
        except Exception as exc:
            self._show_error(exc)

    def _apply_edge_display(self):
        visible = self.show_edges_check.isChecked()
        width = self.edge_width_spin.value()
        opacity = self.edge_opacity_slider.value()
        self._edge_visible = visible
        self._edge_width = width
        self._edge_opacity = opacity
        if hasattr(self, "editor_map"):
            self.editor_map.set_edge_display(visible, width, opacity)
        self.edge_display_changed.emit(visible, width, opacity)
        self._status_label.setText("Da ap dung hien thi canh")

    def _save(self):
        try:
            self._graph.save_to_json(self._json_path)
            self._modified = False
            self._status_label.setText(f"Da luu: {self._json_path}")
        except Exception as exc:
            self._show_error(exc)

    def _after_graph_changed(self, message: str):
        self._modified = True
        self._selected_edge = None
        self._reload_all()
        self.graph_changed.emit()
        self._status_label.setText(f"{message}. Chua luu JSON.")

    def _update_auto_weight(self):
        if not hasattr(self, "edge_auto_weight") or not self.edge_auto_weight.isChecked():
            return
        source = self.edge_source_combo.currentData()
        target = self.edge_target_combo.currentData()
        if not source or not target or source == target:
            return
        try:
            self.edge_weight_spin.setValue(self._graph.calculate_euclidean_weight(source, target))
        except Exception:
            pass

    def _current_edge_nodes(self) -> tuple[str, str]:
        source = self.edge_source_combo.currentData()
        target = self.edge_target_combo.currentData()
        if not source or not target:
            raise ValueError("Hay chon du 2 node cho canh")
        return source, target

    @staticmethod
    def _set_combo_data(combo: QComboBox, value: Optional[str]):
        if not value:
            return
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _show_error(self, exc: Exception):
        QMessageBox.warning(self, "Loi chinh sua", str(exc))

    def closeEvent(self, event):
        if self._modified:
            answer = QMessageBox.question(
                self,
                "Chua luu JSON",
                "Ban do da thay doi nhung chua luu JSON. Dong cua so?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        super().closeEvent(event)
