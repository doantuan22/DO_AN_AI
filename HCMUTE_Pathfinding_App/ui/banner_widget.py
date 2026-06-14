# Banner độc lập hiển thị phía trên bảng điều khiển chính

import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout


class BannerWidget(QFrame):
    def __init__(self, base_dir: str, parent=None):
        super().__init__(parent)
        self.setObjectName("bannerFrame")
        self.setFixedWidth(434)
        self.setStyleSheet("""
            QFrame#bannerFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0057E7, stop:1 #1A73E8);
                border-radius: 12px;
                border: none;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.banner_label = QLabel()
        self.banner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.banner_label.setStyleSheet("border-radius: 12px; background: transparent;")

        banner_path = os.path.join(base_dir, "assets", "banner.png")
        if os.path.exists(banner_path):
            banner_pixmap = QPixmap(banner_path)
            scaled = banner_pixmap.scaledToWidth(
                434,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.banner_label.setPixmap(scaled)
            self.banner_label.setFixedHeight(scaled.height())
        else:
            self.banner_label.setText("HCMUTE Pathfinding")
            self.banner_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
            self.banner_label.setStyleSheet("""
                color: white;
                padding: 18px;
                font-size: 16px;
                font-weight: bold;
                background: transparent;
            """)
            self.banner_label.setFixedHeight(80)

        layout.addWidget(self.banner_label)
