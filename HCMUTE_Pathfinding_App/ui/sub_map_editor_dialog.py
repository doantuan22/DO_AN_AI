"""Trình chỉnh sửa graph, marker và góc xoay của một bản đồ con.

Hỗ trợ thao tác trực quan trên bản đồ (click thêm node, click 2 node để
thêm/xóa cạnh, ...) giống GraphEditorDialog của bản đồ chính.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.sub_map_store import SubMapStore
from widgets.sub_map_widget import SubMapWidget


# ──────────────────────────────────────────────────────────────
# Mapping chế độ hiển thị → interaction mode nội bộ
# ──────────────────────────────────────────────────────────────

_MODE_LABELS = [
    "Di chuyển bản đồ",
    "Chọn nút (kéo di chuyển)",
    "Thêm nút tại vị trí nhấp",
    "Di chuyển nút đã chọn",
    "Thêm cạnh bằng 2 lần nhấp",
    "Xóa cạnh bằng 2 lần nhấp",
    "Xóa nút được nhấp",
]

_MODE_KEYS = [
    "pan",
    "select",
    "add_node",
    "move_node",
    "add_edge",
    "delete_edge",
    "delete_node",
]


class SubMapEditorDialog(QDialog):
    """Dialog chỉnh sửa bản đồ con với thao tác trực quan trên bản đồ."""

    def __init__(self, sub_map_id: str, store: SubMapStore, parent=None):
        super().__init__(parent)
        self.store = store
        self.item = store.get(sub_map_id)
        self.graph: Dict[str, Any] = store.load_graph(self.item)
        self.entry: Dict[str, float] = dict(
            self.item.entry_position or {"x": 0, "y": 0}
        )
        # Đảm bảo __entry__ tồn tại trong đồ thị
        entry_node = self._find_node("__entry__")
        if not entry_node:
            self.graph.setdefault("nodes", []).append({
                "id": "__entry__",
                "name": "Cổng vào",
                "x": self.entry.get("x", 0.0),
                "y": self.entry.get("y", 0.0)
            })
        else:
            self.entry["x"] = float(entry_node.get("x", 0))
            self.entry["y"] = float(entry_node.get("y", 0))

        # Trạng thái editor
        self._selected_node_id: Optional[str] = None
        self._edge_pick_first: Optional[str] = None

        self.setWindowTitle(f"Chỉnh sửa — {self.item.name}")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)
        self.resize(1320, 820)

        self._setup_ui()
        self._reload_all()

    # ──────────────────────────────────────────────────
    # Setup UI
    # ──────────────────────────────────────────────────

    def _setup_ui(self):
        root = QHBoxLayout(self)

        # Bản đồ con (trái)
        self.map_widget = SubMapWidget(editable=True)
        self.map_widget.node_moved.connect(self._on_node_dragged)
        self.map_widget.node_clicked.connect(self._on_visual_node_clicked)
        self.map_widget.map_clicked.connect(self._on_visual_map_clicked)
        root.addWidget(self.map_widget, 1)

        # Panel phải
        panel = QWidget()
        panel.setFixedWidth(450)
        side = QVBoxLayout(panel)
        side.setSpacing(8)

        # Tiêu đề
        title = QLabel(f"{self.item.name} · Tầng {self.item.floor}")
        title.setWordWrap(True)
        title.setStyleSheet(
            "font-size: 18px; font-weight: 800; color: #0B63E5;"
        )
        side.addWidget(title)

        # ── Thao tác trực quan ──
        visual_box = QGroupBox("Thao tác trực tiếp trên bản đồ")
        visual_layout = QVBoxLayout(visual_box)
        visual_layout.setSpacing(8)

        # Combo chế độ
        visual_layout.addWidget(QLabel("Chế độ"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(_MODE_LABELS)
        self.mode_combo.setCurrentIndex(1)  # "Chọn nút"
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        visual_layout.addWidget(self.mode_combo)

        # Thông tin node đang chọn
        self.selected_label = QLabel("Nút đang chọn: chưa có")
        self.selected_label.setWordWrap(True)
        self.selected_label.setStyleSheet(
            "color: #1A73E8; font-weight: bold; margin-top: 4px;"
        )
        visual_layout.addWidget(self.selected_label)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #5F6368;")
        visual_layout.addWidget(self.status_label)

        # Form thông tin node (cho thêm/sửa)
        form = QFormLayout()
        self.visual_id_edit = QLineEdit()
        self.visual_id_edit.setPlaceholderText("Tự động nếu để trống")
        self.visual_name_edit = QLineEdit()
        self.visual_name_edit.setPlaceholderText("Tên hiển thị")
        self.visual_x_label = QLabel("—")
        self.visual_y_label = QLabel("—")
        form.addRow("ID nút mới:", self.visual_id_edit)
        form.addRow("Tên nút:", self.visual_name_edit)
        form.addRow("Tọa độ X:", self.visual_x_label)
        form.addRow("Tọa độ Y:", self.visual_y_label)
        visual_layout.addLayout(form)

        # Nút đổi tên
        btn_rename = QPushButton("Đổi tên nút đang chọn")
        btn_rename.clicked.connect(self._rename_selected_node)
        visual_layout.addWidget(btn_rename)

        btn_recenter = QPushButton("Căn vừa bản đồ")
        btn_recenter.clicked.connect(self.map_widget.reset_view)
        visual_layout.addWidget(btn_recenter)

        # Hướng dẫn
        hint = QLabel(
            "Chọn chế độ rồi thao tác trên bản đồ. "
            "Ở chế độ 'Chọn nút' có thể kéo node để di chuyển. "
            "Thêm/xóa cạnh bằng cách nhấp lần lượt vào hai nút."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #70757A; font-size: 11px;")
        visual_layout.addWidget(hint)

        side.addWidget(visual_box)

        # ── Tabs: Node table, Edge table ──
        tabs = QTabWidget()
        tabs.addTab(self._create_nodes_tab(), "Node")
        tabs.addTab(self._create_edges_tab(), "Cạnh")
        side.addWidget(tabs, 1)

        # ── Transform panel (xoay, marker) ──
        side.addWidget(self._create_transform_panel())

        # ── Nút Lưu / Đóng ──
        buttons = QHBoxLayout()
        save = QPushButton("Lưu thay đổi")
        save.setStyleSheet(
            "background-color: #0B73F6; color: white; "
            "font-weight: 700; border: none; border-radius: 8px; "
            "padding: 10px 20px; font-size: 14px;"
        )
        save.clicked.connect(self._save)
        close = QPushButton("Đóng")
        close.setStyleSheet(
            "background-color: #F1F3F4; color: #3C4043; "
            "font-weight: 600; border: none; border-radius: 8px; "
            "padding: 10px 20px; font-size: 14px;"
        )
        close.clicked.connect(self.reject)
        buttons.addWidget(save)
        buttons.addWidget(close)
        side.addLayout(buttons)

        root.addWidget(panel)

    def _create_nodes_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.node_table = QTableWidget(0, 4)
        self.node_table.setHorizontalHeaderLabels(["ID", "Tên", "X", "Y"])
        self.node_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.node_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.node_table.itemSelectionChanged.connect(
            self._on_node_table_selected
        )
        header = self.node_table.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(True)
        layout.addWidget(self.node_table)
        return tab

    def _create_edges_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self.edge_table = QTableWidget(0, 3)
        self.edge_table.setHorizontalHeaderLabels(["Từ", "Đến", "Trọng số"])
        self.edge_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.edge_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.edge_table.itemSelectionChanged.connect(
            self._on_edge_table_selected
        )
        header = self.edge_table.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(True)
        layout.addWidget(self.edge_table)
        return tab

    def _create_transform_panel(self) -> QWidget:
        box = QGroupBox("Xoay bản đồ và vị trí hiện tại")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 8, 8, 8)

        note = QLabel(
            "Marker đỏ là vị trí hiện tại trên bản đồ con. "
            "Có thể kéo marker hoặc nhập tọa độ X/Y."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #5F6368;")
        layout.addWidget(note)

        rotation_row = QHBoxLayout()
        for text, delta in (
            ("↶ 90°", -90),
            ("↷ 90°", 90),
            ("180°", 180),
            ("Reset", None),
        ):
            button = QPushButton(text)
            button.clicked.connect(
                lambda checked=False, d=delta: self._quick_rotate(d)
            )
            rotation_row.addWidget(button)
        layout.addLayout(rotation_row)

        self.rotation_spin = QDoubleSpinBox()
        self.rotation_spin.setRange(-3600, 3600)
        self.rotation_spin.setSuffix("°")
        self.rotation_spin.setValue(self.item.rotation)
        self.rotation_spin.valueChanged.connect(self.map_widget.set_rotation)
        layout.addWidget(self.rotation_spin)

        position = QHBoxLayout()
        self.entry_x = QDoubleSpinBox()
        self.entry_y = QDoubleSpinBox()
        for spin in (self.entry_x, self.entry_y):
            spin.setRange(-100000, 100000)
            spin.setDecimals(1)
        self.entry_x.setValue(float(self.entry.get("x", 0)))
        self.entry_y.setValue(float(self.entry.get("y", 0)))
        self.entry_x.valueChanged.connect(self._entry_spin_changed)
        self.entry_y.valueChanged.connect(self._entry_spin_changed)
        position.addWidget(QLabel("X:"))
        position.addWidget(self.entry_x)
        position.addWidget(QLabel("Y:"))
        position.addWidget(self.entry_y)
        layout.addLayout(position)

        return box

    # ──────────────────────────────────────────────────
    # Reload dữ liệu
    # ──────────────────────────────────────────────────

    def _reload_all(self):
        """Tải lại table, bản đồ và đồng bộ trạng thái."""
        self._reload_node_table()
        self._reload_edge_table()
        self.map_widget.load_map(
            self.store.absolute_path(self.item.image),
            self.graph,
            rotation=self.rotation_spin.value(),
        )
        self._apply_current_mode()
        if self._selected_node_id:
            self.map_widget.highlight_node(self._selected_node_id)

    def _reload_node_table(self):
        self.node_table.blockSignals(True)
        self.node_table.setRowCount(0)
        for row, node in enumerate(self.graph.get("nodes", [])):
            self.node_table.insertRow(row)
            for col, value in enumerate(
                (
                    node.get("id"),
                    node.get("name", ""),
                    node.get("x", 0),
                    node.get("y", 0),
                )
            ):
                self.node_table.setItem(
                    row, col, QTableWidgetItem(str(value))
                )
        self.node_table.blockSignals(False)

    def _reload_edge_table(self):
        self.edge_table.blockSignals(True)
        self.edge_table.setRowCount(0)
        for row, edge in enumerate(self.graph.get("edges", [])):
            self.edge_table.insertRow(row)
            for col, value in enumerate(
                (edge.get("from"), edge.get("to"), edge.get("weight", 1))
            ):
                self.edge_table.setItem(
                    row, col, QTableWidgetItem(str(value))
                )
        self.edge_table.blockSignals(False)

    # ──────────────────────────────────────────────────
    # Chế độ thao tác
    # ──────────────────────────────────────────────────

    def _on_mode_changed(self, index: int):
        self._edge_pick_first = None
        self._apply_current_mode()
        self.status_label.setText("")

    def _apply_current_mode(self):
        index = self.mode_combo.currentIndex()
        if 0 <= index < len(_MODE_KEYS):
            self.map_widget.set_interaction_mode(_MODE_KEYS[index])

    def _current_mode_key(self) -> str:
        index = self.mode_combo.currentIndex()
        if 0 <= index < len(_MODE_KEYS):
            return _MODE_KEYS[index]
        return "select"

    # ──────────────────────────────────────────────────
    # Click trên bản đồ — xử lý theo mode
    # ──────────────────────────────────────────────────

    def _on_visual_node_clicked(self, node_id: str):
        """Xử lý click vào node trên bản đồ theo chế độ hiện tại."""
        mode = self._current_mode_key()

        if mode == "add_edge":
            self._pick_edge_node(node_id, create=True)
        elif mode == "delete_edge":
            self._pick_edge_node(node_id, create=False)
        elif mode == "delete_node":
            self._delete_node_by_id(node_id)
        elif mode == "move_node":
            # Click node trong mode move → chọn node đó
            self._select_node(node_id)
            self.status_label.setText(
                f"Đã chọn nút {node_id}. Nhấp vị trí mới trên bản đồ để di chuyển."
            )
        elif mode == "add_node":
            self.status_label.setText(
                "Vị trí này đã có nút. Hãy nhấp vùng trống để thêm nút mới."
            )
            self._select_node(node_id)
        else:
            # select mode
            self._select_node(node_id)

    def _on_visual_map_clicked(self, x: float, y: float):
        """Xử lý click vùng trống trên bản đồ theo chế độ hiện tại."""
        x_r = round(x, 1)
        y_r = round(y, 1)
        self.visual_x_label.setText(str(x_r))
        self.visual_y_label.setText(str(y_r))

        mode = self._current_mode_key()

        if mode == "add_node":
            self._add_node_at(x_r, y_r)
        elif mode == "move_node":
            self._move_selected_node_to(x_r, y_r)
        else:
            self.status_label.setText(f"Vị trí nhấp: x={x_r}, y={y_r}")

    # ──────────────────────────────────────────────────
    # Node kéo (drag) trên bản đồ
    # ──────────────────────────────────────────────────

    def _on_node_dragged(self, node_id: str, x: float, y: float):
        """Cập nhật tọa độ node khi kéo (mode select)."""
        for node in self.graph.get("nodes", []):
            if node.get("id") == node_id:
                node["x"] = round(x, 2)
                node["y"] = round(y, 2)
                if node_id == "__entry__":
                    self.entry = {"x": node["x"], "y": node["y"]}
                    if hasattr(self, "entry_x") and hasattr(self, "entry_y"):
                        self.entry_x.blockSignals(True)
                        self.entry_y.blockSignals(True)
                        self.entry_x.setValue(node["x"])
                        self.entry_y.setValue(node["y"])
                        self.entry_x.blockSignals(False)
                        self.entry_y.blockSignals(False)
                break
        # Cập nhật UI nếu đang chọn node này
        if self._selected_node_id == node_id:
            self.visual_x_label.setText(str(round(x, 1)))
            self.visual_y_label.setText(str(round(y, 1)))

    # ──────────────────────────────────────────────────
    # Chọn node
    # ──────────────────────────────────────────────────

    def _select_node(self, node_id: str):
        """Chọn một node và cập nhật tất cả UI liên quan."""
        node = self._find_node(node_id)
        if node is None:
            return
        self._selected_node_id = node_id
        name = node.get("name", "") or "(không có tên)"
        self.selected_label.setText(f"Nút đang chọn: {name} ({node_id})")
        if self._current_mode_key() != "add_node":
            self.visual_name_edit.setText(node.get("name", ""))
        self.visual_x_label.setText(str(node.get("x", 0)))
        self.visual_y_label.setText(str(node.get("y", 0)))
        self.map_widget.highlight_node(node_id)

        # Đồng bộ node table
        self.node_table.blockSignals(True)
        self.node_table.clearSelection()
        for row in range(self.node_table.rowCount()):
            item = self.node_table.item(row, 0)
            if item and item.text() == node_id:
                self.node_table.selectRow(row)
                break
        self.node_table.blockSignals(False)

    def _clear_selection(self):
        self._selected_node_id = None
        self.selected_label.setText("Nút đang chọn: chưa có")
        self.visual_name_edit.clear()
        self.visual_x_label.setText("—")
        self.visual_y_label.setText("—")

    # ──────────────────────────────────────────────────
    # Thao tác thêm node
    # ──────────────────────────────────────────────────

    def _add_node_at(self, x: float, y: float):
        """Thêm node mới tại tọa độ (x, y) từ click bản đồ."""
        node_id = self.visual_id_edit.text().strip() or self._suggest_node_id()
        name = self.visual_name_edit.text().strip() or node_id

        # Kiểm tra trùng ID
        if any(n.get("id") == node_id for n in self.graph.get("nodes", [])):
            QMessageBox.warning(
                self, "Trùng ID", f"Node '{node_id}' đã tồn tại."
            )
            return

        self.graph.setdefault("nodes", []).append(
            {"id": node_id, "name": name, "x": x, "y": y}
        )
        self.visual_id_edit.clear()
        self.visual_name_edit.clear()
        self.status_label.setText(
            f"Đã thêm nút {node_id} tại ({x}, {y})"
        )
        self._reload_all()
        self._select_node(node_id)

    def _suggest_node_id(self) -> str:
        """Tạo ID node tự động (S01, S02, ...)."""
        used = {n.get("id") for n in self.graph.get("nodes", [])}
        index = 1
        while True:
            candidate = f"S{index:02d}"
            if candidate not in used:
                return candidate
            index += 1

    # ──────────────────────────────────────────────────
    # Thao tác di chuyển node
    # ──────────────────────────────────────────────────

    def _move_selected_node_to(self, x: float, y: float):
        """Di chuyển node đã chọn đến vị trí mới."""
        if not self._selected_node_id:
            QMessageBox.warning(
                self, "Thiếu lựa chọn",
                "Hãy chọn nút trước khi di chuyển."
            )
            return
        node = self._find_node(self._selected_node_id)
        if node is None:
            return
        node["x"] = x
        node["y"] = y
        
        if self._selected_node_id == "__entry__":
            self.entry = {"x": x, "y": y}
            if hasattr(self, "entry_x") and hasattr(self, "entry_y"):
                self.entry_x.blockSignals(True)
                self.entry_y.blockSignals(True)
                self.entry_x.setValue(x)
                self.entry_y.setValue(y)
                self.entry_x.blockSignals(False)
                self.entry_y.blockSignals(False)
                
        self.status_label.setText(
            f"Đã di chuyển nút {self._selected_node_id} đến ({x}, {y})"
        )
        self._reload_all()
        self._select_node(self._selected_node_id)

    # ──────────────────────────────────────────────────
    # Thao tác đổi tên node
    # ──────────────────────────────────────────────────

    def _rename_selected_node(self):
        if not self._selected_node_id:
            QMessageBox.warning(
                self, "Thiếu lựa chọn", "Hãy chọn nút cần đổi tên."
            )
            return
        node = self._find_node(self._selected_node_id)
        if node is None:
            return
        new_name = self.visual_name_edit.text().strip()
        if not new_name:
            QMessageBox.warning(
                self, "Thiếu tên", "Hãy nhập tên hiển thị mới cho nút."
            )
            return
        node["name"] = new_name
        self.status_label.setText(
            f"Đã đổi tên nút {self._selected_node_id} → {new_name}"
        )
        self._reload_all()
        self._select_node(self._selected_node_id)

    # ──────────────────────────────────────────────────
    # Thao tác xóa node
    # ──────────────────────────────────────────────────

    def _delete_node_by_id(self, node_id: str):
        """Xóa node và tất cả cạnh liên quan."""
        if node_id == "__entry__":
            QMessageBox.warning(self, "Không thể xóa", "Không thể xóa điểm liên kết (Cổng vào).")
            return
            
        answer = QMessageBox.question(
            self,
            "Xóa nút",
            f"Xóa nút {node_id} và các cạnh liên quan?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.graph["nodes"] = [
            n for n in self.graph.get("nodes", [])
            if n.get("id") != node_id
        ]
        self.graph["edges"] = [
            e for e in self.graph.get("edges", [])
            if node_id not in (e.get("from"), e.get("to"))
        ]
        if self._selected_node_id == node_id:
            self._clear_selection()
        self.status_label.setText(f"Đã xóa nút {node_id}")
        self._reload_all()

    # ──────────────────────────────────────────────────
    # Thao tác thêm/xóa cạnh bằng 2 lần nhấp
    # ──────────────────────────────────────────────────

    def _pick_edge_node(self, node_id: str, create: bool):
        """Chọn lần lượt 2 node để thêm hoặc xóa cạnh."""
        if self._edge_pick_first is None:
            self._edge_pick_first = node_id
            self._select_node(node_id)
            action = "thêm" if create else "xóa"
            self.status_label.setText(
                f"Đã chọn nút đầu: {node_id}. Nhấp nút thứ hai để {action} cạnh."
            )
            return

        source = self._edge_pick_first
        target = node_id
        self._edge_pick_first = None

        if source == target:
            self.status_label.setText("Hai đầu cạnh không được trùng nhau.")
            return

        if create:
            if self._find_edge(source, target):
                QMessageBox.warning(
                    self, "Trùng cạnh", "Cạnh này đã tồn tại."
                )
                return
            weight = self._distance(source, target)
            self.graph.setdefault("edges", []).append(
                {"from": source, "to": target, "weight": round(weight, 2)}
            )
            self.status_label.setText(
                f"Đã thêm cạnh {source} — {target}"
            )
        else:
            edge = self._find_edge(source, target)
            if not edge:
                QMessageBox.warning(
                    self, "Không tìm thấy",
                    f"Cạnh {source} — {target} không tồn tại."
                )
                return
            self.graph["edges"].remove(edge)
            self.status_label.setText(
                f"Đã xóa cạnh {source} — {target}"
            )

        self._reload_all()

    # ──────────────────────────────────────────────────
    # Table selection → đồng bộ
    # ──────────────────────────────────────────────────

    def _on_node_table_selected(self):
        row = self.node_table.currentRow()
        nodes = self.graph.get("nodes", [])
        if 0 <= row < len(nodes):
            node_id = nodes[row].get("id")
            if node_id:
                self._select_node(str(node_id))

    def _on_edge_table_selected(self):
        row = self.edge_table.currentRow()
        edges = self.graph.get("edges", [])
        if 0 <= row < len(edges):
            edge = edges[row]
            source = str(edge.get("from", ""))
            target = str(edge.get("to", ""))
            self.status_label.setText(
                f"Cạnh đã chọn: {source} — {target} "
                f"(trọng số: {edge.get('weight', '?')})"
            )

    # ──────────────────────────────────────────────────
    # Transform (xoay, entry position)
    # ──────────────────────────────────────────────────

    def _quick_rotate(self, delta):
        self.rotation_spin.setValue(
            0 if delta is None else self.rotation_spin.value() + delta
        )

    def _entry_spin_changed(self):
        self.entry = {"x": self.entry_x.value(), "y": self.entry_y.value()}
        entry_node = self._find_node("__entry__")
        if entry_node:
            entry_node["x"] = self.entry["x"]
            entry_node["y"] = self.entry["y"]
            self.map_widget.refresh_graph(self.graph)

    # ──────────────────────────────────────────────────
    # Lưu
    # ──────────────────────────────────────────────────

    def _save(self):
        try:
            self.store.save_graph(self.item, self.graph)
            self.item = self.store.update(
                self.item.id,
                rotation=self.rotation_spin.value(),
                entry_position=self.entry,
            )
            QMessageBox.information(
                self, "Đã lưu",
                "Đã lưu bản đồ con, node, cạnh và vị trí marker."
            )
        except Exception as exc:
            QMessageBox.warning(self, "Không thể lưu", str(exc))

    # ──────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────

    def _find_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        for node in self.graph.get("nodes", []):
            if node.get("id") == node_id:
                return node
        return None

    def _find_edge(self, source: str, target: str) -> Optional[Dict[str, Any]]:
        return next(
            (
                e
                for e in self.graph.get("edges", [])
                if {e.get("from"), e.get("to")} == {source, target}
            ),
            None,
        )

    def _distance(self, source: str, target: str) -> float:
        nodes = {n["id"]: n for n in self.graph.get("nodes", [])}
        a, b = nodes.get(source), nodes.get(target)
        if not a or not b:
            return 1.0
        return math.hypot(
            float(a["x"]) - float(b["x"]),
            float(a["y"]) - float(b["y"]),
        )
