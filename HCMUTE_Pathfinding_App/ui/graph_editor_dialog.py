# Dialog chỉnh sửa node/cạnh của bản đồ

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
    # MapWidget có click vùng trống để chỉnh sửa trực quan

    map_clicked = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._left_drag_pan = False
        self._is_panning = False
        self._last_pan_pos = None

    def set_left_drag_pan(self, enabled: bool):
        # Bật/tắt kéo bản đồ bằng chuột trái
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
            h_bar = self.horizontalScrollBar()
            v_bar = self.verticalScrollBar()
            if h_bar and v_bar:
                h_bar.setValue(h_bar.value() - delta.x())
                v_bar.setValue(v_bar.value() - delta.y())
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
    # Công cụ thêm/sửa/xóa node, cạnh và hiển thị

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

        self.setWindowTitle("Chỉnh sửa bản đồ")
        self.setMinimumSize(980, 680)
        self.resize(1180, 760)

        self._setup_ui(edge_visible, edge_width, edge_opacity)
        self._reload_all()

    def _setup_ui(self, edge_visible: bool, edge_width: float, edge_opacity: int):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        self._status_label = QLabel("Chưa có thay đổi")
        self._status_label.setStyleSheet("color: #5F6368;")

        tabs = QTabWidget()
        tabs.addTab(self._create_visual_tab(), "Bản đồ trực quan")
        tabs.addTab(self._create_nodes_tab(), "Nút")
        tabs.addTab(self._create_edges_tab(), "Cạnh")
        tabs.addTab(self._create_display_tab(edge_visible, edge_width, edge_opacity), "Cài đặt")

        bottom = QHBoxLayout()
        self.btn_save = QPushButton("Lưu JSON")
        self.btn_save.clicked.connect(self._save)
        btn_close = QPushButton("Đóng")
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

        side = QGroupBox("Thao tác trực tiếp")
        side.setFixedWidth(310)
        side_layout = QVBoxLayout(side)
        side_layout.setSpacing(8)

        self.visual_mode_combo = QComboBox()
        self.visual_mode_combo.addItems([
            "Di chuyển bản đồ",
            "Chọn nút",
            "Thêm nút tại vị trí nhấp",
            "Di chuyển nút đã chọn",
            "Thêm cạnh bằng 2 lần nhấp",
            "Xóa cạnh bằng 2 lần nhấp",
            "Xóa nút được nhấp",
        ])
        self.visual_mode_combo.setCurrentText("Chọn nút")
        self.visual_mode_combo.currentIndexChanged.connect(self._on_visual_mode_changed)

        self.visual_selected_label = QLabel("Nút đang chọn: chưa có")
        self.visual_selected_label.setWordWrap(True)
        self.visual_selected_label.setStyleSheet("color: #1A73E8; font-weight: bold;")

        form = QFormLayout()
        self.visual_node_id_edit = QLineEdit()
        self.visual_node_id_edit.setPlaceholderText("Tự động nếu để trống")
        self.visual_node_name_edit = QLineEdit()
        self.visual_node_name_edit.setPlaceholderText("Tên hiển thị")
        self.visual_x_label = QLabel("-")
        self.visual_y_label = QLabel("-")
        form.addRow("ID nút mới", self.visual_node_id_edit)
        form.addRow("Tên nút", self.visual_node_name_edit)
        form.addRow("Tọa độ X", self.visual_x_label)
        form.addRow("Tọa độ Y", self.visual_y_label)

        btn_rename = QPushButton("Đổi tên nút đang chọn")
        btn_rename.clicked.connect(self._rename_selected_from_visual)
        btn_clear_name = QPushButton("Ẩn tên nút đang chọn")
        btn_clear_name.clicked.connect(self._clear_selected_node_name)
        btn_recenter = QPushButton("Căn vừa bản đồ")
        btn_recenter.clicked.connect(self.editor_map.zoom_reset)

        hint = QLabel(
            "Chọn chế độ rồi thao tác trên bản đồ. "
            "Có thể giữ chuột phải hoặc chuột giữa để kéo bản đồ ở mọi chế độ. "
            "Thêm hoặc xóa cạnh bằng cách nhấp lần lượt vào hai nút. "
            "Để di chuyển nút, hãy chọn nút trước rồi nhấp vào vị trí mới."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #70757A;")

        side_layout.addWidget(QLabel("Chế độ"))
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
        self.node_table.setHorizontalHeaderLabels(["ID", "Tên", "X", "Y"])
        self.node_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.node_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.node_table.itemSelectionChanged.connect(self._on_node_selected)
        header = self.node_table.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(True)

        form_box = QGroupBox("Thông tin nút")
        form_layout = QVBoxLayout(form_box)
        fields = QFormLayout()

        self.node_id_edit = QLineEdit()
        self.node_name_edit = QLineEdit()
        self.node_x_spin = QSpinBox()
        self.node_x_spin.setRange(0, max(20000, self._graph.image_size[0] or 20000))
        self.node_y_spin = QSpinBox()
        self.node_y_spin.setRange(0, max(20000, self._graph.image_size[1] or 20000))

        fields.addRow("ID", self.node_id_edit)
        fields.addRow("Tên hiển thị", self.node_name_edit)
        fields.addRow("X", self.node_x_spin)
        fields.addRow("Y", self.node_y_spin)

        btn_row_1 = QHBoxLayout()
        btn_new = QPushButton("Nhập nút mới")
        btn_new.clicked.connect(self._clear_node_form)
        btn_add = QPushButton("Thêm nút")
        btn_add.clicked.connect(self._add_node)
        btn_row_1.addWidget(btn_new)
        btn_row_1.addWidget(btn_add)

        btn_row_2 = QHBoxLayout()
        btn_update = QPushButton("Cập nhật nút")
        btn_update.clicked.connect(self._update_node)
        btn_delete = QPushButton("Xóa nút")
        btn_delete.clicked.connect(self._delete_node)
        btn_row_2.addWidget(btn_update)
        btn_row_2.addWidget(btn_delete)

        note = QLabel("Xóa nút sẽ xóa tất cả cạnh liên quan.")
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
        self.edge_table.setHorizontalHeaderLabels(["Từ", "Đến", "Trọng số"])
        self.edge_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.edge_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.edge_table.itemSelectionChanged.connect(self._on_edge_selected)
        header_edge = self.edge_table.horizontalHeader()
        if header_edge is not None:
            header_edge.setStretchLastSection(True)

        form_box = QGroupBox("Thông tin cạnh")
        form_layout = QVBoxLayout(form_box)
        fields = QFormLayout()

        self.edge_source_combo = QComboBox()
        self.edge_target_combo = QComboBox()
        self.edge_weight_spin = QDoubleSpinBox()
        self.edge_weight_spin.setRange(0.01, 100000.0)
        self.edge_weight_spin.setDecimals(2)
        self.edge_weight_spin.setSingleStep(5.0)
        self.edge_auto_weight = QCheckBox("Tự tính theo khoảng cách giữa hai nút")
        self.edge_auto_weight.setChecked(True)
        self.edge_auto_weight.stateChanged.connect(self._update_auto_weight)
        self.edge_source_combo.currentIndexChanged.connect(self._update_auto_weight)
        self.edge_target_combo.currentIndexChanged.connect(self._update_auto_weight)

        fields.addRow("Nút đầu", self.edge_source_combo)
        fields.addRow("Nút cuối", self.edge_target_combo)
        fields.addRow("Trọng số", self.edge_weight_spin)
        fields.addRow("", self.edge_auto_weight)

        btn_add = QPushButton("Thêm cạnh")
        btn_add.clicked.connect(self._add_edge)
        btn_update = QPushButton("Cập nhật trọng số")
        btn_update.clicked.connect(self._update_edge)
        btn_delete = QPushButton("Xóa cạnh")
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

        box = QGroupBox("Cách hiển thị cạnh trên bản đồ")
        grid = QGridLayout(box)

        self.show_edges_check = QCheckBox("Hiển thị cạnh")
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

        btn_apply = QPushButton("Áp dụng hiển thị")
        btn_apply.clicked.connect(self._apply_edge_display)

        grid.addWidget(self.show_edges_check, 0, 0, 1, 2)
        grid.addWidget(QLabel("Độ dày"), 1, 0)
        grid.addWidget(self.edge_width_spin, 1, 1)
        grid.addWidget(QLabel("Độ mờ"), 2, 0)
        grid.addWidget(self.edge_opacity_slider, 2, 1)
        grid.addWidget(self.edge_opacity_label, 2, 2)
        grid.addWidget(btn_apply, 3, 0, 1, 3)

        layout.addWidget(box)

        node_box = QGroupBox("Cài đặt tên nút")
        node_layout = QVBoxLayout(node_box)

        btn_hide_all_names = QPushButton("Ẩn toàn bộ tên nút")
        btn_hide_all_names.clicked.connect(self._clear_all_node_names)

        note = QLabel(
            "Chức năng này sẽ xóa tên hiển thị của tất cả nút. "
            "Trong nhật ký và hộp chọn, nút không có tên sẽ hiển thị ID gốc như N11, N22."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #70757A;")

        node_layout.addWidget(btn_hide_all_names)
        node_layout.addWidget(note)

        layout.addWidget(node_box)
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
            display_name = node.name if node.name else "(không có tên)"
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
        item = self.node_table.item(row, 0)
        if item is None:
            return
        node_id = item.text()
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
            display_name = node.name if node.name else "(không có tên)"
            self.visual_selected_label.setText(f"Nút đang chọn: {display_name} ({node.id})")
            self.visual_node_name_edit.setText(node.name)
            self.visual_x_label.setText(str(node.x))
            self.visual_y_label.setText(str(node.y))
            self._highlight_selected_node(node_id)

    def _on_edge_selected(self):
        row = self.edge_table.currentRow()
        if row < 0:
            return
        
        item0 = self.edge_table.item(row, 0)
        item1 = self.edge_table.item(row, 1)
        item2 = self.edge_table.item(row, 2)
        if not (item0 and item1 and item2):
            return
            
        source = item0.text()
        target = item1.text()
        weight = float(item2.text())
        self._selected_edge = (source, target)
        self._set_combo_data(self.edge_source_combo, source)
        self._set_combo_data(self.edge_target_combo, target)
        self.edge_weight_spin.setValue(weight)

    def _on_visual_node_clicked(self, node_id: str):
        mode = self.visual_mode_combo.currentText()
        self._select_node(node_id)

        if mode == "Thêm cạnh bằng 2 lần nhấp":
            self._pick_visual_edge(node_id, create=True)
        elif mode == "Xóa cạnh bằng 2 lần nhấp":
            self._pick_visual_edge(node_id, create=False)
        elif mode == "Xóa nút được nhấp":
            self._delete_node()
        elif mode == "Di chuyển nút đã chọn":
            self._status_label.setText("Đã chọn nút. Hãy nhấp vị trí mới trên bản đồ để di chuyển.")
        elif mode == "Thêm nút tại vị trí nhấp":
            self._status_label.setText("Vị trí này đã có nút. Hãy nhấp vùng trống để thêm nút mới.")
        else:
            self._status_label.setText(f"Đã chọn nút {node_id}")

    def _on_visual_map_clicked(self, x: float, y: float):
        x_i = max(0, int(round(x)))
        y_i = max(0, int(round(y)))
        self.visual_x_label.setText(str(x_i))
        self.visual_y_label.setText(str(y_i))

        mode = self.visual_mode_combo.currentText()
        if mode == "Thêm nút tại vị trí nhấp":
            self._add_node_from_visual(x_i, y_i)
        elif mode == "Di chuyển nút đã chọn":
            self._move_selected_node_from_visual(x_i, y_i)
        else:
            self._status_label.setText(f"Vị trí nhấp: x={x_i}, y={y_i}")

    def _add_node_from_visual(self, x: int, y: int):
        node_id = self.visual_node_id_edit.text().strip() or self._suggest_node_id()
        name = self.visual_node_name_edit.text().strip() or node_id
        try:
            self._graph.add_node(node_id, x, y, name)
            self._selected_node_id = node_id
            self.visual_node_id_edit.clear()
            self.visual_node_name_edit.clear()
            self._after_graph_changed(f"Đã thêm nút {node_id} tại ({x}, {y})")
            self._select_node(node_id)
        except Exception as exc:
            self._show_error(exc)

    def _move_selected_node_from_visual(self, x: int, y: int):
        if not self._selected_node_id:
            QMessageBox.warning(self, "Thiếu lựa chọn", "Hãy chọn nút trước khi di chuyển.")
            return
        node = self._graph.get_node(self._selected_node_id)
        if node is None:
            return
        try:
            self._graph.update_node(self._selected_node_id, x, y, node.name)
            self._after_graph_changed(f"Đã di chuyển nút {self._selected_node_id} đến ({x}, {y})")
            self._select_node(self._selected_node_id)
        except Exception as exc:
            self._show_error(exc)

    def _rename_selected_from_visual(self):
        if not self._selected_node_id:
            QMessageBox.warning(self, "Thiếu lựa chọn", "Hãy chọn nút cần đổi tên.")
            return
        node = self._graph.get_node(self._selected_node_id)
        if node is None:
            return
        new_name = self.visual_node_name_edit.text().strip()
        if not new_name:
            QMessageBox.warning(self, "Thiếu tên", "Hãy nhập tên hiển thị mới cho nút.")
            return
        try:
            self._graph.update_node(self._selected_node_id, node.x, node.y, new_name)
            self._after_graph_changed(f"Đã đổi tên nút {self._selected_node_id}")
            self._select_node(self._selected_node_id)
        except Exception as exc:
            self._show_error(exc)

    def _clear_selected_node_name(self):
        if not self._selected_node_id:
            QMessageBox.warning(self, "Thiếu lựa chọn", "Hãy chọn nút cần ẩn tên.")
            return
        node = self._graph.get_node(self._selected_node_id)
        if node is None:
            return
        try:
            self._graph.update_node(self._selected_node_id, node.x, node.y, "")
            self._after_graph_changed(f"Đã ẩn tên nút {self._selected_node_id}")
            self._select_node(self._selected_node_id)
        except Exception as exc:
            self._show_error(exc)

    def _clear_all_node_names(self):
        # Xóa tên hiển thị của tất cả node trên graph
        named_count = sum(1 for node in self._graph.nodes.values() if node.name)
        if named_count == 0:
            self._status_label.setText("Tất cả nút hiện đã không có tên hiển thị.")
            return

        answer = QMessageBox.question(
            self,
            "Ẩn toàn bộ tên nút",
            f"Xóa tên hiển thị của {named_count} nút? Bạn vẫn cần bấm Lưu JSON để ghi vào file.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        for node in self._graph.nodes.values():
            node.name = ""

        self._after_graph_changed(f"Đã ẩn tên hiển thị của {named_count} nút")

    def _pick_visual_edge(self, node_id: str, create: bool):
        if self._visual_edge_first is None:
            self._visual_edge_first = node_id
            self._highlight_selected_node(node_id)
            action = "thêm" if create else "xóa"
            self._status_label.setText(
                f"Đã chọn nút đầu {node_id}. Hãy nhấp nút thứ hai để {action} cạnh."
            )
            return

        source = self._visual_edge_first
        target = node_id
        self._visual_edge_first = None
        if source == target:
            self._status_label.setText("Hai đầu cạnh không được trùng nhau.")
            return

        try:
            if create:
                self._graph.add_edge(source, target)
                self._after_graph_changed(f"Đã thêm cạnh {source} - {target}")
            else:
                self._graph.delete_edge(source, target)
                self._after_graph_changed(f"Đã xóa cạnh {source} - {target}")
        except Exception as exc:
            self._show_error(exc)

    def _select_node(self, node_id: str):
        node = self._graph.get_node(node_id)
        if node is None:
            return
        self._selected_node_id = node_id
        display_name = node.name if node.name else "(không có tên)"
        self.visual_selected_label.setText(f"Nút đang chọn: {display_name} ({node.id})")
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
            self.visual_mode_combo.currentText() == "Di chuyển bản đồ"
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
            self.visual_selected_label.setText("Nút đang chọn: chưa có")

    def _add_node(self):
        try:
            self._graph.add_node(
                self.node_id_edit.text(),
                self.node_x_spin.value(),
                self.node_y_spin.value(),
                self.node_name_edit.text(),
            )
            self._after_graph_changed("Đã thêm nút")
        except Exception as exc:
            self._show_error(exc)

    def _update_node(self):
        if not self._selected_node_id:
            QMessageBox.warning(self, "Thiếu lựa chọn", "Hãy chọn nút cần cập nhật.")
            return
        try:
            self._graph.update_node(
                self._selected_node_id,
                self.node_x_spin.value(),
                self.node_y_spin.value(),
                self.node_name_edit.text(),
            )
            self._after_graph_changed("Đã cập nhật nút")
        except Exception as exc:
            self._show_error(exc)

    def _delete_node(self):
        if not self._selected_node_id:
            QMessageBox.warning(self, "Thiếu lựa chọn", "Hãy chọn nút cần xóa.")
            return
        answer = QMessageBox.question(
            self,
            "Xóa nút",
            f"Xóa nút {self._selected_node_id} và các cạnh liên quan?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self._graph.delete_node(self._selected_node_id)
            self._clear_node_form()
            self._after_graph_changed("Đã xóa nút")
        except Exception as exc:
            self._show_error(exc)

    def _add_edge(self):
        try:
            source, target = self._current_edge_nodes()
            weight = None if self.edge_auto_weight.isChecked() else self.edge_weight_spin.value()
            self._graph.add_edge(source, target, weight)
            self._after_graph_changed("Đã thêm cạnh")
        except Exception as exc:
            self._show_error(exc)

    def _update_edge(self):
        try:
            source, target = self._current_edge_nodes()
            self._graph.update_edge(source, target, self.edge_weight_spin.value())
            self._after_graph_changed("Đã cập nhật cạnh")
        except Exception as exc:
            self._show_error(exc)

    def _delete_edge(self):
        if not self._selected_edge:
            QMessageBox.warning(self, "Thiếu lựa chọn", "Hãy chọn cạnh cần xóa.")
            return
        source, target = self._selected_edge
        answer = QMessageBox.question(self, "Xóa cạnh", f"Xóa cạnh {source} - {target}?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self._graph.delete_edge(source, target)
            self._selected_edge = None
            self._after_graph_changed("Đã xóa cạnh")
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
        self._status_label.setText("Đã áp dụng cách hiển thị cạnh")

    def _save(self):
        try:
            self._graph.save_to_json(self._json_path)
            self._modified = False
            self._status_label.setText(f"Đã lưu: {self._json_path}")
        except Exception as exc:
            self._show_error(exc)

    def _after_graph_changed(self, message: str):
        self._modified = True
        self._selected_edge = None
        self._reload_all()
        self.graph_changed.emit()
        self._status_label.setText(f"{message}. Chưa lưu JSON.")

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
            raise ValueError("Hãy chọn đủ hai nút cho cạnh")
        return source, target

    @staticmethod
    def _set_combo_data(combo: QComboBox, value: Optional[str]):
        if not value:
            return
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _show_error(self, exc: Exception):
        QMessageBox.warning(self, "Lỗi chỉnh sửa", str(exc))

    def closeEvent(self, a0):
        if self._modified:
            answer = QMessageBox.question(
                self,
                "Chưa lưu JSON",
                "Bản đồ đã thay đổi. Bạn muốn lưu trước khi đóng?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer == QMessageBox.StandardButton.Save:
                try:
                    self._graph.save_to_json(self._json_path)
                    self._modified = False
                except Exception as exc:
                    self._show_error(exc)
                    if a0 is not None:
                        a0.ignore()
                    return
            elif answer == QMessageBox.StandardButton.Discard:
                try:
                    self._graph.load_from_json(self._json_path)
                    self._modified = False
                    self.graph_changed.emit()
                except Exception as exc:
                    self._show_error(exc)
                    if a0 is not None:
                        a0.ignore()
                    return
            else:
                if a0 is not None:
                    a0.ignore()
                return
        super().closeEvent(a0)
