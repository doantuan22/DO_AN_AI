"""Dialog showing saved pathfinding history."""

from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from core.history_store import HistoryStore, PathHistoryRecord


HISTORY_DIALOG_STYLE = """
    QDialog {
        background-color: #F7FAFF;
    }
    QLabel#title {
        color: #0B63E5;
        font-family: 'Segoe UI';
        font-size: 22px;
        font-weight: 900;
    }
    QLabel#summary {
        color: #475569;
        font-family: 'Segoe UI';
        font-size: 12px;
        font-weight: 700;
    }
    QTableWidget {
        background-color: #FFFFFF;
        border: 1px solid #DDE7F5;
        border-radius: 8px;
        gridline-color: #E6EDF7;
        color: #0F172A;
        font-family: 'Segoe UI';
        font-size: 12px;
        selection-background-color: #E8F0FE;
        selection-color: #0B63E5;
    }
    QHeaderView::section {
        background-color: #EEF5FF;
        color: #15346F;
        border: none;
        border-right: 1px solid #DDE7F5;
        padding: 8px;
        font-family: 'Segoe UI';
        font-size: 12px;
        font-weight: 800;
    }
    QTextEdit {
        background-color: #FFFFFF;
        border: 1px solid #DDE7F5;
        border-radius: 8px;
        color: #0F172A;
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 12px;
        padding: 8px;
    }
    QPushButton {
        border: 1px solid transparent;
        border-radius: 8px;
        min-height: 36px;
        padding: 7px 14px;
        font-family: 'Segoe UI';
        font-size: 13px;
        font-weight: 800;
    }
    QPushButton#primary {
        background-color: #0B74FF;
        color: #FFFFFF;
    }
    QPushButton#primary:hover {
        background-color: #006DFF;
        border: 1px solid #005BD6;
    }
    QPushButton#primary:pressed {
        background-color: #075BCC;
        padding-top: 9px;
        padding-bottom: 5px;
    }
    QPushButton#secondary {
        background-color: #EEF5FF;
        color: #0B63E5;
    }
    QPushButton#secondary:hover {
        background-color: #DCEBFF;
        border: 1px solid #9CC7FF;
    }
    QPushButton#secondary:pressed {
        background-color: #C7DDFF;
        padding-top: 9px;
        padding-bottom: 5px;
    }
    QPushButton#danger {
        background-color: #FDE9E7;
        color: #D93025;
    }
    QPushButton#danger:hover {
        background-color: #FAD2CF;
        border: 1px solid #F28B82;
    }
    QPushButton#danger:pressed {
        background-color: #F6B8B2;
        padding-top: 9px;
        padding-bottom: 5px;
    }
    QPushButton:focus {
        outline: none;
        border: 1px solid #0B74FF;
    }
"""


class HistoryDialog(QDialog):
    """Table view for routes saved in SQLite."""

    def __init__(self, store: HistoryStore, parent=None):
        super().__init__(parent)
        self._store = store
        self._records: List[PathHistoryRecord] = []

        self.setWindowTitle("Lịch sử đường đi")
        self.setMinimumSize(980, 640)
        self.resize(1120, 720)
        self.setStyleSheet(HISTORY_DIALOG_STYLE)

        self._setup_ui()
        self._load_records()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Lịch sử đường đi")
        title.setObjectName("title")
        self.summary_label = QLabel()
        self.summary_label.setObjectName("summary")
        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.summary_label)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "Thời gian",
            "Thuật toán",
            "Điểm bắt đầu",
            "Điểm đích",
            "Số mét",
            "Node duyệt",
            "Thời gian xử lý",
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._show_selected_details)
        header_view = self.table.horizontalHeader()
        if header_view is not None:
            header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
            header_view.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
            header_view.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
            header_view.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)

        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setMinimumHeight(150)

        buttons = QHBoxLayout()
        btn_refresh = QPushButton("Tải lại")
        btn_refresh.setObjectName("secondary")
        btn_refresh.clicked.connect(self._load_records)
        btn_delete = QPushButton("Xóa dòng chọn")
        btn_delete.setObjectName("danger")
        btn_delete.clicked.connect(self._delete_selected)
        btn_clear = QPushButton("Xóa tất cả")
        btn_clear.setObjectName("danger")
        btn_clear.clicked.connect(self._clear_all)
        btn_close = QPushButton("Đóng")
        btn_close.setObjectName("primary")
        btn_close.clicked.connect(self.close)
        for button in (btn_refresh, btn_delete, btn_clear, btn_close):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
        buttons.addWidget(btn_refresh)
        buttons.addWidget(btn_delete)
        buttons.addWidget(btn_clear)
        buttons.addStretch()
        buttons.addWidget(btn_close)

        root.addLayout(header)
        root.addWidget(self.table, 1)
        root.addWidget(self.details)
        root.addLayout(buttons)

    def _load_records(self) -> None:
        self._records = self._store.list_routes()
        self.table.setRowCount(0)
        for row, record in enumerate(self._records):
            self.table.insertRow(row)
            values = [
                record.created_at.replace("T", " "),
                record.algorithm,
                f"{record.start_node_name} ({record.start_node_id})",
                f"{record.goal_node_name} ({record.goal_node_id})",
                f"{record.distance_m:.1f} m",
                str(record.visited_count),
                f"{record.elapsed_ms:.2f} ms",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, record.id)
                self.table.setItem(row, col, item)

        self.summary_label.setText(f"{len(self._records)} lượt tìm đường đã lưu")
        if self._records:
            self.table.selectRow(0)
        else:
            self.details.setPlainText("Chưa có lịch sử. Hãy chạy thuật toán tìm đường thành công để lưu bản ghi đầu tiên.")

    def _selected_record(self) -> Optional[PathHistoryRecord]:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._records):
            return None
        return self._records[row]

    def _show_selected_details(self) -> None:
        record = self._selected_record()
        if record is None:
            return
        self.details.setPlainText(
            "\n".join([
                f"ID: {record.id}",
                f"Thời gian: {record.created_at.replace('T', ' ')}",
                f"Thuật toán: {record.algorithm}",
                f"Điểm bắt đầu: {record.start_node_name} ({record.start_node_id})",
                f"Điểm đích: {record.goal_node_name} ({record.goal_node_id})",
                f"Tổng quãng đường: {record.distance_m:.1f} m",
                f"Số node đã duyệt: {record.visited_count}",
                f"Thời gian xử lý: {record.elapsed_ms:.2f} ms",
                "",
                "Lộ trình:",
                record.route_text,
            ])
        )

    def _delete_selected(self) -> None:
        record = self._selected_record()
        if record is None:
            return
        answer = QMessageBox.question(
            self,
            "Xóa lịch sử",
            f"Xóa bản ghi lịch sử #{record.id}?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._store.delete_route(record.id)
        self._load_records()

    def _clear_all(self) -> None:
        if not self._records:
            return
        answer = QMessageBox.question(
            self,
            "Xóa tất cả lịch sử",
            "Xóa toàn bộ lịch sử đường đi đã lưu?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._store.clear()
        self._load_records()
