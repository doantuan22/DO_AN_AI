# Dialog xem bản đồ chi tiết và chọn tầng

from PyQt6.QtWidgets import QComboBox, QDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout

from services.sub_map_store import SubMapStore
from widgets.sub_map_widget import SubMapWidget


class SubMapViewerDialog(QDialog):
    def __init__(self, main_node_id: str, store: SubMapStore, parent=None):
        super().__init__(parent)
        self.store = store
        self.maps = store.list_for_node(main_node_id)
        self.setWindowTitle("Bản đồ tòa chi tiết")
        self.resize(1100, 760)
        root = QVBoxLayout(self)
        top = QHBoxLayout()
        title = QLabel("Bản đồ chi tiết")
        title.setStyleSheet("font-size:20px;font-weight:800;color:#0B63E5")
        self.floor_combo = QComboBox()
        for item in self.maps:
            self.floor_combo.addItem(f"Tầng {item.floor} — {item.name}", item.id)
        self.floor_combo.currentIndexChanged.connect(self._load_selected)
        top.addWidget(title); top.addStretch(); top.addWidget(QLabel("Chọn tầng:")); top.addWidget(self.floor_combo)
        self.map_widget = SubMapWidget(editable=False)
        close = QPushButton("Quay lại bản đồ chính"); close.clicked.connect(self.accept)
        root.addLayout(top); root.addWidget(self.map_widget, 1); root.addWidget(close)
        self._load_selected()

    def _load_selected(self):
        sub_map_id = self.floor_combo.currentData()
        if not sub_map_id:
            return
        try:
            item = self.store.get(str(sub_map_id))
            self.map_widget.load_map(
                self.store.absolute_path(item.image), self.store.load_graph(item), rotation=item.rotation
            )
        except Exception as exc:
            QMessageBox.warning(self, "Không thể mở bản đồ", str(exc))
