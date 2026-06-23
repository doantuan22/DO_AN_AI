import os
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QPushButton, QHBoxLayout
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import Qt

class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hướng dẫn sử dụng")
        self.resize(720, 560)
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
            }
            QTextBrowser {
                border: 1px solid #DDE6F2;
                border-radius: 8px;
                padding: 10px;
                background-color: #F8FAFC;
                font-family: 'Segoe UI';
                font-size: 14px;
                color: #1E293B;
                line-height: 1.6;
            }
            QPushButton {
                background-color: #0B74FF;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-family: 'Segoe UI';
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1A85FF;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setHtml(self._get_help_content())
        layout.addWidget(self.browser)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Đóng")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _get_help_content(self) -> str:
        return """
        <h2 style='color: #0B63E5;'>Hướng dẫn sử dụng HCMUTE Pathfinding</h2>
        
        <h3 style='color: #15346F;'>1. Trạng thái hiển thị bản đồ</h3>
        <ul>
            <li><b>Chế độ ẩn đồ thị:</b> Bản đồ hiển thị gọn gàng, không bị rối bởi các điểm và đường nối. Chỉ các điểm <i>Bắt đầu</i> và <i>Đích</i> đang được chọn mới được ghim lên bản đồ. Đây là chế độ thích hợp để xem tổng quan.</li>
            <li><b>Chế độ hiện đồ thị:</b> Nhấn nút <b>◉</b> ở góc dưới bên trái màn hình bản đồ để hiện toàn bộ các điểm (node) và đường đi (edge). Ở chế độ này, bạn có thể thấy rõ cấu trúc các con đường nội bộ trong trường.</li>
        </ul>

        <h3 style='color: #15346F;'>2. Cách chọn điểm trên bản đồ</h3>
        <ul>
            <li><b>Cách 1 - Dùng danh sách:</b> Chọn điểm thông qua danh sách thả xuống ở bảng điều khiển bên phải.</li>
            <li><b>Cách 2 - Chọn trực tiếp trên bản đồ:</b>
                <ul>
                    <li>Khi <i>hiện</i> đồ thị: Bấm <b>chuột trái</b> trực tiếp vào các điểm (node).</li>
                    <li>Khi <i>ẩn</i> đồ thị: Bấm <b>chuột phải</b> vào khu vực bản đồ nơi bạn muốn đi/đến, hệ thống sẽ tự động bắt điểm gần nhất. <i>(Mẹo này cũng dùng được khi hiện đồ thị để nhấp chọn nhanh mà không cần phải trúng tâm điểm).</i></li>
                </ul>
            </li>
            <li><i>Thứ tự chọn:</i> Lần 1 ghim <b>Điểm bắt đầu</b>, lần 2 ghim <b>Điểm đích</b>. Bấm lại vào một điểm đã chọn sẽ hủy ghim điểm đó.</li>
        </ul>

        <h3 style='color: #15346F;'>3. Bản đồ chi tiết các tòa nhà (Bản đồ con)</h3>
        <p>Ứng dụng hỗ trợ xem chi tiết bên trong các tòa nhà, bao gồm sơ đồ từng tầng.</p>
        <ul>
            <li><b>Các khu vực có bản đồ con:</b> Các cụm tòa nhà như Khu A (Tòa trung tâm, A2-3, A4-5), Khu B, Khu C, Khu D, Khu E1, Khu E4 đều có bản đồ tầng chi tiết.</li>
            <li><b>Cách vào bản đồ con:</b> Sau khi bạn nhấp chọn một trong các tòa nhà này làm <b>Điểm đích</b>, một nút <b style="color: #0B74FF;">"Bản đồ chi tiết ⬇"</b> sẽ nổi lên ngay trên đỉnh tòa nhà đó. Nhấn vào nút này để mở bản đồ các tầng.</li>
            <li><b>Bên trong bản đồ con:</b> 
                <ul>
                    <li>Sử dụng hộp thoại <b>"Chuyển tầng"</b> ở thanh công cụ phía trên để chuyển đổi qua lại giữa các tầng của tòa nhà.</li>
                    <li>Có thể chọn trực tiếp các phòng cụ thể (như phòng học, phòng thực hành) làm điểm đích cuối cùng.</li>
                    <li>Nhấn <b>"⮌ Quay lại bản đồ chính"</b> để thoát ra ngoài khuôn viên.</li>
                </ul>
            </li>
        </ul>

        <h3 style='color: #15346F;'>4. Mô phỏng tìm đường</h3>
        <ul>
            <li>Sau khi chọn xong điểm xuất phát và đích, hãy chọn thuật toán (A*, BFS, DFS, Dijkstra/UCS, Greedy) và nhấn nút <b>Bắt đầu</b>.</li>
            <li>Sử dụng nút <b>⏱</b> (góc dưới bên trái) để tùy chỉnh tốc độ chạy thuật toán (Chậm/Trung bình/Nhanh).</li>
            <li>Sau khi tìm thấy đường đi tối ưu, bạn có thể nhấn nút <b>▶</b> (Đi mẫu) để xem nhân vật (avatar) di chuyển dọc theo lộ trình.</li>
            <li>Bạn có thể xem lại lịch sử các lần tìm đường đã lưu bằng cách nhấn nút <b>H</b> (Lịch sử).</li>
        </ul>

        <h3 style='color: #15346F;'>5. Lưu ý về thời gian xử lý</h3>
        <ul>
            <li><b>Ở chế độ không hiển thị đồ thị:</b> Vòng lặp thuật toán chạy liên tục không ngắt quãng. Dữ liệu luôn sẵn sàng trong CPU Cache giúp thuật toán chạy với tốc độ tối đa.</li>
            <li><b>Ở chế độ hiển thị đồ thị:</b> Lệnh thuật toán chạy ngắt quãng theo nhịp của QTimer. Sự hao hụt thời gian do chuyển đổi ngữ cảnh Hệ điều hành (Context Switching) và trễ bộ nhớ đệm (Cache Miss) sau mỗi nhịp nghỉ sẽ khiến thời gian đo đạc CPU bị độn lên thêm một chút.</li>
        </ul>
        """
