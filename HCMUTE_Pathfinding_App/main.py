"""
main.py - Điểm khởi chạy ứng dụng
====================================
Hệ thống tìm đường trong khuôn viên HCMUTE
Sử dụng các thuật toán: BFS, DFS, UCS, Greedy, A*

Tác giả: Sinh viên HCMUTE
Đồ án: AI cuối kỳ
"""

import sys

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

from ui.welcome_screen import WelcomeScreen


def main():
    """Khởi chạy ứng dụng."""
    # Tạo QApplication
    app = QApplication(sys.argv)
    
    # Cấu hình font mặc định
    default_font = QFont("Segoe UI", 10)
    app.setFont(default_font)
    
    # Cấu hình High DPI
    app.setStyle("Fusion")
    
    # Hiển thị màn hình welcome trước, sau đó WelcomeScreen sẽ tự mở MainWindow.
    window = WelcomeScreen()
    window.show()
    
    # Chạy event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
