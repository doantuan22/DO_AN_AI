# Điểm khởi chạy ứng dụng tìm đường HCMUTE
# Khởi tạo QApplication, hiển thị WelcomeScreen rồi vào MainWindow

import sys

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

from ui.welcome_screen import WelcomeScreen


# Hàm main: cấu hình app và khởi động giao diện
def main():
    app = QApplication(sys.argv)
    
    default_font = QFont("Segoe UI", 10)
    app.setFont(default_font)
    app.setStyle("Fusion")
    
    # Hiển thị WelcomeScreen, sau đó nó sẽ tự mở MainWindow
    window = WelcomeScreen()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
