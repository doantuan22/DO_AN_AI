# 🗺️ Hệ thống tìm đường trong khuôn viên Trường Đại học Sư phạm Kỹ thuật TP.HCM (HCMUTE)

## 📋 Mục lục
- [Giới thiệu](#giới-thiệu)
- [Mục tiêu](#mục-tiêu)
- [Công nghệ sử dụng](#công-nghệ-sử-dụng)
- [Cấu trúc thư mục](#cấu-trúc-thư-mục)
- [Cài đặt](#cài-đặt)
- [Hướng dẫn chạy](#hướng-dẫn-chạy)
- [Hướng dẫn sử dụng](#hướng-dẫn-sử-dụng)
- [Các thuật toán](#các-thuật-toán)
- [Dữ liệu đồ thị](#dữ-liệu-đồ-thị)
- [Hướng phát triển](#hướng-phát-triển)

---

## 🎯 Giới thiệu

**Đề tài:** Thiết kế và xây dựng ứng dụng tìm đường đi giữa các địa điểm trong khuôn viên Trường Đại học Sư phạm Kỹ thuật TP.HCM – HCMUTE.

Ứng dụng desktop được xây dựng bằng Python và PyQt6, cho phép người dùng:
- Xem bản đồ 2D mô phỏng khuôn viên trường HCMUTE
- Chọn điểm bắt đầu và điểm đích trên bản đồ
- Chạy các thuật toán tìm đường đi trên đồ thị
- Quan sát quá trình mô phỏng từng bước của thuật toán
- So sánh hiệu quả giữa các thuật toán khác nhau

## 🎯 Mục tiêu

1. Áp dụng kiến thức về **thuật toán tìm kiếm trên đồ thị** vào bài toán thực tế
2. Xây dựng ứng dụng có **giao diện trực quan**, dễ sử dụng
3. **Mô phỏng** quá trình hoạt động của các thuật toán để hiểu rõ cách chúng làm việc
4. **So sánh** hiệu quả giữa các thuật toán: BFS, DFS, UCS, Greedy, A*

## 🛠️ Công nghệ sử dụng

| Thành phần | Công nghệ |
|---|---|
| Ngôn ngữ | Python 3.8+ |
| GUI Framework | PyQt6 |
| Thuật toán | BFS, DFS, UCS, Greedy Search, A* Search |
| Dữ liệu | JSON |
| Đồ họa | QGraphicsView, QGraphicsScene |

## 📁 Cấu trúc thư mục

```
HCMUTE_Pathfinding_App/
│
├── main.py                      # File khởi chạy ứng dụng
├── requirements.txt             # Thư viện cần cài đặt
├── README.md                    # Hướng dẫn sử dụng
│
├── assets/                      # Tài nguyên ảnh
│   ├── map.png                  # Ảnh bản đồ HCMUTE
│   └── UI_demo.png              # Ảnh giao diện mẫu
│
├── data/                        # Dữ liệu đồ thị
│   └── hcmute_graph_nodes_edges.json
│
├── core/                        # Module xử lý logic
│   ├── __init__.py
│   ├── graph.py                 # Xử lý đồ thị (đọc JSON, adjacency list)
│   ├── algorithms.py            # 5 thuật toán tìm kiếm
│   ├── heuristic.py             # Hàm heuristic (Euclidean, Manhattan)
│   └── utils.py                 # Tiện ích (format, timer)
│
├── ui/                          # Module giao diện
│   ├── __init__.py
│   ├── main_window.py           # Cửa sổ chính
│   ├── map_widget.py            # Widget hiển thị bản đồ
│   └── control_panel.py         # Panel điều khiển
│
└── tests/                       # Kiểm thử
    ├── __init__.py
    └── test_algorithms.py       # Unit test các thuật toán
```

## ⚙️ Cài đặt

### Yêu cầu hệ thống
- Python 3.8 trở lên
- Hệ điều hành: Windows / macOS / Linux

### Bước 1: Clone hoặc tải project

```bash
cd HCMUTE_Pathfinding_App
```

### Bước 2: Cài đặt thư viện

```bash
pip install -r requirements.txt
```

## 🚀 Hướng dẫn chạy

### Chạy ứng dụng

```bash
python main.py
```

### Chạy kiểm thử

```bash
python -m pytest tests/ -v
```

Hoặc:

```bash
python tests/test_algorithms.py
```

## 📖 Hướng dẫn sử dụng

### Bước 1: Khởi động
Chạy `python main.py`, ứng dụng sẽ tự động tải bản đồ HCMUTE và hiển thị các node trên bản đồ.

### Bước 2: Chọn thuật toán
Trên panel bên phải, chọn thuật toán muốn sử dụng:
- **BFS** - Tìm kiếm theo chiều rộng
- **DFS** - Tìm kiếm theo chiều sâu
- **UCS** - Tìm kiếm chi phí đồng nhất
- **Greedy** - Tìm kiếm tham lam
- **A*** - Tìm kiếm A*

### Bước 3: Chọn heuristic (nếu cần)
Nếu chọn Greedy hoặc A*, cần chọn hàm heuristic:
- **Euclidean** - Khoảng cách đường thẳng
- **Manhattan** - Khoảng cách theo trục

### Bước 4: Chọn điểm bắt đầu và điểm đích
- **Click lần 1** vào node trên bản đồ → chọn điểm bắt đầu (xanh lá)
- **Click lần 2** vào node khác → chọn điểm đích (đỏ)
- Hoặc sử dụng combo box trên panel để chọn

### Bước 5: Chạy thuật toán
- Nhấn **▶ Bắt đầu** để chạy thuật toán
- Quan sát quá trình mô phỏng trên bản đồ
- Sử dụng **⏸ Tạm dừng** / **▶ Tiếp tục** để điều khiển
- Nhấn **⏹ Dừng** để hủy
- Nhấn **↻ Reset** để bắt đầu lại

### Bước 6: Xem kết quả
- Đường đi kết quả được highlight bằng màu xanh lá đậm
- Bảng log hiển thị chi tiết từng bước
- Thống kê: tổng quãng đường, số node duyệt, thời gian

## 🧮 Các thuật toán

### 1. BFS (Breadth-First Search)
- **Cấu trúc dữ liệu:** Hàng đợi (Queue - FIFO)
- **Đặc điểm:** Duyệt theo chiều rộng, mở rộng tất cả node cùng mức trước
- **Tối ưu:** Tìm đường đi ít cạnh nhất, **không** tối ưu theo trọng số
- **Độ phức tạp:** O(V + E)

### 2. DFS (Depth-First Search)
- **Cấu trúc dữ liệu:** Ngăn xếp (Stack - LIFO)
- **Đặc điểm:** Duyệt theo chiều sâu, ưu tiên đi sâu trước khi quay lui
- **Tối ưu:** **Không** đảm bảo đường đi ngắn nhất
- **Độ phức tạp:** O(V + E)

### 3. UCS (Uniform-Cost Search)
- **Cấu trúc dữ liệu:** Hàng đợi ưu tiên (Priority Queue / Min-Heap)
- **Hàm ưu tiên:** g(n) - chi phí tích lũy từ start đến node hiện tại
- **Tối ưu:** ✅ Đảm bảo tìm đường đi có tổng trọng số nhỏ nhất
- **Độ phức tạp:** O((V + E) log V)

### 4. Greedy Best-First Search
- **Cấu trúc dữ liệu:** Hàng đợi ưu tiên (Priority Queue / Min-Heap)
- **Hàm ưu tiên:** h(n) - heuristic ước lượng khoảng cách đến đích
- **Tối ưu:** **Không** đảm bảo tối ưu (có thể lao vào ngõ cụt)
- **Độ phức tạp:** O((V + E) log V)

### 5. A* Search
- **Cấu trúc dữ liệu:** Hàng đợi ưu tiên (Priority Queue / Min-Heap)
- **Hàm ưu tiên:** f(n) = g(n) + h(n)
  - g(n): chi phí thực tế từ start đến node hiện tại
  - h(n): heuristic ước lượng từ node hiện tại đến goal
- **Tối ưu:** ✅ Nếu h(n) admissible (không bao giờ ước lượng quá)
- **Độ phức tạp:** O((V + E) log V)

### Bảng so sánh

| Thuật toán | Tối ưu | Dùng trọng số | Dùng heuristic | Tốc độ |
|---|---|---|---|---|
| BFS | Theo số cạnh | ❌ | ❌ | Trung bình |
| DFS | ❌ | ❌ | ❌ | Nhanh |
| UCS | ✅ | ✅ | ❌ | Chậm |
| Greedy | ❌ | ❌ | ✅ | Nhanh |
| A* | ✅ | ✅ | ✅ | Nhanh nhất |

## 📊 Dữ liệu đồ thị

File `data/hcmute_graph_nodes_edges.json` chứa dữ liệu đồ thị bản đồ HCMUTE:

```json
{
  "coordinate_system": "pixel coordinates, origin at top-left",
  "image_size": { "width": 1122, "height": 1402 },
  "nodes": [
    { "id": "N01", "x": 404, "y": 169 },
    ...
  ],
  "edges": [
    { "from": "N01", "to": "N02", "weight": 104.02 },
    ...
  ]
}
```

- **Nodes:** 57 node đại diện cho các địa điểm và giao lộ
- **Edges:** 63 cạnh nối các node, trọng số tính bằng khoảng cách pixel
- **Đồ thị:** Vô hướng (đi được cả hai chiều)

## 🔮 Hướng phát triển

1. **Thêm thuật toán:** IDA*, Bidirectional Search, Dijkstra
2. **Tối ưu giao diện:** Zoom mượt hơn, animation đường đi
3. **Thêm chức năng:** So sánh nhiều thuật toán cùng lúc
4. **Mở rộng bản đồ:** Hỗ trợ tải bản đồ khác, tự tạo đồ thị
5. **Tích hợp GPS:** Kết nối với bản đồ thực tế
6. **Thêm thông tin:** Hiển thị thông tin chi tiết về từng tòa nhà
7. **Export kết quả:** Xuất báo cáo so sánh thuật toán ra PDF

---

**Đồ án AI cuối kỳ - Trường Đại học Sư phạm Kỹ thuật TP.HCM (HCMUTE)**
