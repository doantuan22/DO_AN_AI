# BÁO CÁO Ý CHÍNH PROJECT ỨNG DỤNG TÌM ĐƯỜNG HCMUTE

> **Nhận xét từ codebase:** Tài liệu này được phân tích và tổng hợp trực tiếp từ mã nguồn thực tế của dự án. Mọi nhận xét, tính năng và luồng hoạt động đều bám sát các file code hiện có.

---

## Chương 1: Mở đầu

### 1.1 Mục tiêu đề tài
Dựa trên codebase (đặc biệt là file `main.py` và `core/algorithms.py`), dự án hướng đến xây dựng **ứng dụng desktop tìm đường đi tối ưu trong khuôn viên Trường Đại học Sư phạm Kỹ thuật TP.HCM (HCMUTE)**. Hệ thống giúp mô hình hóa bản đồ khuôn viên thành đồ thị và áp dụng 5 thuật toán tìm kiếm phổ biến (BFS, DFS, UCS, Greedy, A*) để tìm đường giữa hai địa điểm. Ứng dụng cũng trực quan hóa quá trình tìm kiếm từng bước trên giao diện đồ họa.

### 1.2 Đối tượng nghiên cứu và phục vụ
- **Đối tượng nghiên cứu:** Bản đồ khuôn viên HCMUTE (được trừu tượng hóa thành đồ thị với các node và edge), 5 thuật toán tìm kiếm (có sử dụng khoảng cách Euclidean và Manhattan làm heuristic), thư viện giao diện PyQt6, và SQLite lưu trữ lịch sử.
- **Đối tượng phục vụ:** Sinh viên, giảng viên, nhân viên và khách đến thăm trường cần tìm lộ trình di chuyển giữa các tòa nhà, khu vực trong khuôn viên HCMUTE.

### 1.3 Phạm vi đề tài
Phạm vi hiện tại của dự án:
- Ứng dụng chạy trên nền tảng **Desktop** (Python + PyQt6).
- Sử dụng **bản đồ 2D tĩnh** (`assets/map.png`).
- Tìm đường giữa 65 điểm nút có sẵn (được định nghĩa trong file JSON), không sử dụng GPS thực tế.
- Hỗ trợ mô phỏng thuật toán qua animation.
- Có tính năng chỉnh sửa đồ thị cơ bản trên UI và lưu lại vào JSON.
- Có lưu lịch sử các lần tìm đường vào cơ sở dữ liệu SQLite.

### 1.4 Dự kiến nội dung đạt được
- Xây dựng bản đồ HCMUTE dạng 2D: ✅ Đã triển khai (`assets/map.png`).
- Mô hình hóa bản đồ thành đồ thị: ✅ Đã triển khai (`core/graph.py` và `data/hcmute_graph_nodes_edges.json`).
- Cài đặt các thuật toán BFS, DFS, UCS, Greedy, A*: ✅ Đã triển khai (`core/algorithms.py`).
- Hiển thị đường đi trên giao diện: ✅ Đã triển khai (`ui/map_widget.py`).
- Mô phỏng quá trình tìm kiếm: ✅ Đã triển khai (Sử dụng Generator và `QTimer` trong `ui/main_window.py`).
- Chỉnh sửa node/cạnh: ✅ Đã triển khai (`ui/graph_editor_dialog.py`).
- Lưu lịch sử tìm đường: ✅ Đã triển khai (`core/history_store.py` và `ui/history_dialog.py`).

---

## Chương 2: Cơ sở lý thuyết

### 2.1 Tổng quan về bài toán tìm đường đi trên bản đồ
Bài toán tìm đường trong khuôn viên HCMUTE nhận **đầu vào** là một điểm xuất phát (node) và một điểm đích (node) trên đồ thị bản đồ. **Đầu ra** là một chuỗi các đỉnh liên tiếp tạo thành lộ trình từ điểm bắt đầu đến điểm đích. Tùy thuộc vào thuật toán sử dụng, lộ trình này có thể là đường đi ngắn nhất (tối ưu) hoặc một đường đi bất kỳ tìm thấy được.

### 2.2 Cơ sở lý thuyết về đồ thị

#### 2.2.1 Khái niệm đồ thị
Đồ thị gồm tập đỉnh (V) và tập cạnh (E). Trong dự án, mỗi địa điểm hoặc giao lộ trong trường (ví dụ: Cổng chính, Khối A, Thư viện) là một Node. Mỗi đoạn đường di chuyển nội bộ nối giữa hai Node là một Edge.

#### 2.2.2 Đồ thị vô hướng có trọng số
Kiểm tra trong `core/graph.py`, khi thêm cạnh, mã nguồn nối hai chiều:
```python
self.adjacency[source].append((target, weight))
self.adjacency[target].append((source, weight))
```
Do đó, đồ thị là **vô hướng**. Thuộc tính `weight` của cạnh đại diện cho **trọng số** (khoảng cách Euclidean bằng pixel giữa hai node).

#### 2.2.3 Biểu diễn đồ thị bằng danh sách kề
Project sử dụng **danh sách kề (Adjacency List)** để biểu diễn đồ thị. Trong class `Graph` (`core/graph.py`), biến `self.adjacency` là một Dictionary ánh xạ từ ID của node (kiểu string) sang một danh sách các tuple `(neighbor_id, weight)`.

#### 2.2.4 Node, Edge và trọng số cạnh trong bản đồ
- **Node:** Được định nghĩa bởi class `Node` gồm: `id` (Mã định danh), `x`, `y` (Tọa độ pixel), `name` (Tên hiển thị, nếu trống sẽ ẩn tên).
- **Edge:** Class `Edge` gồm `source` (Node bắt đầu), `target` (Node kết thúc), và `weight` (Trọng số). Trọng số được lấy trực tiếp từ file JSON, hoặc tính tự động dựa trên khoảng cách Euclidean (Pixel) trong giao diện Editor.

### 2.3 Mô hình hóa bản đồ HCMUTE thành đồ thị
Hệ thống sử dụng ảnh `assets/map.png` làm bản đồ nền. Tọa độ của các địa điểm trên ảnh được trích xuất thủ công hoặc qua Editor, tạo thành 65 node và 80 cạnh lưu trong `data/hcmute_graph_nodes_edges.json`. Khi khởi động, hàm `Graph.load_from_json()` sẽ nạp file này để xây dựng cấu trúc đồ thị.

### 2.4 Cơ sở lý thuyết về các thuật toán tìm kiếm
Tất cả 5 thuật toán trong `core/algorithms.py` đều được thiết kế dưới dạng **Generator** (`yield` trạng thái) để phục vụ cho tính năng mô phỏng trực quan.

#### 2.4.1 Thuật toán BFS
Cài đặt bằng hàng đợi FIFO (`collections.deque`). Thuật toán duyệt qua các đỉnh kề theo từng mức, không xét đến trọng số. Thích hợp để tìm đường đi đi qua ít đoạn đường nhất, nhưng không phải khoảng cách ngắn nhất.

#### 2.4.2 Thuật toán DFS
Cài đặt bằng ngăn xếp LIFO (`list.pop()`). Thuật toán đi sâu xuống từng nhánh cho đến khi hết đường hoặc gặp đích. Không đảm bảo tìm được đường đi ngắn nhất.

#### 2.4.3 Thuật toán UCS
Cài đặt bằng hàng đợi ưu tiên Min-Heap (`heapq`). Node được mở rộng dựa trên chi phí tích lũy `g(n)` nhỏ nhất. Đảm bảo tìm được đường đi ngắn nhất về mặt trọng số.

#### 2.4.4 Thuật toán A*
Sử dụng hàm đánh giá `f(n) = g(n) + h(n)` kết hợp Min-Heap. `g(n)` là chi phí thực từ điểm bắt đầu, `h(n)` là hàm ước lượng heuristic đến đích. Đảm bảo tìm đường ngắn nhất đồng thời giảm thiểu số node phải duyệt.

#### 2.4.5 Thuật toán Greedy
Sử dụng Min-Heap nhưng chỉ đánh giá dựa trên `h(n)` (Heuristic). Thuật toán chọn hướng đi có vẻ gần đích nhất. Tốc độ rất nhanh nhưng không đảm bảo đường đi tìm được là ngắn nhất.

### 2.5 Hàm heuristic trong bài toán tìm đường
Được định nghĩa tại `core/heuristic.py`. Hệ thống có 2 hàm:
1. **Euclidean distance:** Khoảng cách đường chim bay `sqrt(dx^2 + dy^2)`. (Là hàm mặc định cho Greedy và A*).
2. **Manhattan distance:** Khoảng cách lưới vuông góc `|dx| + |dy|`.

### 2.6 Cơ sở lý thuyết về giao diện và database

#### 2.6.1 Tổng quan về PyQt6
PyQt6 là framework chính điều khiển toàn bộ giao diện desktop.
- `QMainWindow` tạo cửa sổ chính.
- `QGraphicsView` / `QGraphicsScene` hiển thị bản đồ, node, cạnh, hỗ trợ zoom/pan.
- `QTimer` tạo animation mô phỏng.
- Các widget cơ bản: `QPushButton`, `QComboBox`, `QTableWidget` cho thao tác điều khiển.

#### 2.6.2 Tổng quan về SQLite
Hệ thống sử dụng thư viện `sqlite3` có sẵn của Python (`core/history_store.py`) để lưu trữ dữ liệu các lần tìm đường vào file `data/path_history.sqlite3`. Dữ liệu lưu gồm thuật toán, điểm bắt đầu/đích, tổng khoảng cách, thời gian xử lý và mảng lộ trình.

---

## Chương 3: Thiết kế và cài đặt

### 3.1 Tổng quan hệ thống
Hệ thống được chia thành 3 lớp rõ rệt:
1. **Lớp Dữ liệu:** Quản lý JSON đồ thị và SQLite lịch sử.
2. **Lớp Xử lý lõi (Core):** Cấu trúc đồ thị, logic tính toán 5 thuật toán, lưu/đọc CSDL.
3. **Lớp Giao diện (UI):** Render bản đồ PyQt6, nhận tương tác người dùng, điều khiển animation qua QTimer.

### 3.2 Sơ đồ tổng quát hệ thống
**Luồng hệ thống cơ bản:**
Người dùng chọn cấu hình (Bắt đầu, Kết thúc, Thuật toán) trên `ControlPanel` → Giao diện phát tín hiệu tới `MainWindow` → Gọi logic thuật toán trong `algorithms.py` cùng dữ liệu từ `Graph` → Hàm trả về `Generator` → `MainWindow` dùng `QTimer` duyệt qua Generator → Gọi `MapWidget` cập nhật màu sắc UI (mô phỏng) → Khi hoàn tất, ghi kết quả xuống `HistoryStore` (SQLite).

### 3.3 Thiết kế chức năng ứng dụng

#### 3.3.1 Chức năng hiển thị bản đồ
- Sử dụng `MapWidget` để render. Nền là ảnh trường.
- Các cạnh hiển thị là đường line xám. Các node hiển thị là hình tròn xanh. Nhãn tên (Google maps style) hiển thị cạnh node.
- Có nút Tạm ẩn/Hiện lớp đồ thị (nút biểu tượng con mắt) để người dùng xem rõ nền bản đồ thực khi cần.

#### 3.3.2 Chức năng tìm đường đi
1. Người dùng chọn điểm Bắt đầu và Kết thúc trên bản đồ (nhấp chuột phải/trái) hoặc dùng ComboBox.
2. Bấm nút "Bắt đầu".
3. UI gọi thuật toán dưới dạng Generator.
4. Mỗi tick của `QTimer` thay đổi màu sắc node: Cam (Đang duyệt), Vàng (Biên), Tím (Đã duyệt).
5. Khi tới đích, đường đi được highlight màu xanh ngọc.
6. Kết quả (chi phí, thời gian, số node) hiện ra trên bảng thông báo. Có tính năng "Đi mẫu" chạy icon avatar mô phỏng theo đường đã tìm.

#### 3.3.3 Chức năng chỉnh sửa đồ thị
- `GraphEditorDialog` cho phép mở giao diện phụ chỉnh sửa bản đồ trực tiếp.
- Chức năng: Click thêm node, 2 click thêm/xóa cạnh, đổi tên, kéo thả di chuyển node. Lưu lại đè file JSON.

#### 3.3.4 Chức năng lưu lịch sử tìm đường
- Tự động lưu sau khi tìm đường thành công qua `HistoryStore.add_route()`.
- Giao diện `HistoryDialog` hiển thị dạng bảng (TableWidget). Có thể xóa lịch sử hoặc xóa tất cả.

### 3.4 Thiết kế dữ liệu

#### 3.4.1 Thiết kế dữ liệu đồ thị
Được lưu tại RAM qua class `Graph`. Biến `nodes` (dict của class `Node`), `edges` (danh sách `Edge`), `adjacency` (dict danh sách kề).

#### 3.4.2 Thiết kế file JSON lưu bản đồ
File `data/hcmute_graph_nodes_edges.json` gồm hai mảng chính:
- `nodes`: Chứa `id`, `x`, `y`, `name`.
- `edges`: Chứa `from`, `to`, `weight`.

#### 3.4.3 Thiết kế cơ sở dữ liệu SQLite
Schema (`data/path_history_schema.sql`) gồm bảng `path_history` với các trường: `id`, `created_at`, `algorithm`, `start_node_id`, `start_node_name`, `goal_node_id`, `goal_node_name`, `distance_m`, `path_node_ids`, `path_names`, `visited_count`, `elapsed_ms`.

### 3.5 Thiết kế giao diện người dùng

#### 3.5.1 Thiết kế giao diện loading app
Màn hình chào mừng (`WelcomeScreen`) xuất hiện khi khởi chạy, hiển thị logo `assets/logo.png`, tên ứng dụng và thanh tiến trình `QProgressBar` load giả lập, tạo cảm giác chuyên nghiệp.

#### 3.5.2 Thiết kế giao diện chính
Chia làm 2 vùng:
- 75% bên trái là bản đồ tương tác (`MapWidget`).
- 25% bên phải là Bảng điều khiển (`ControlPanel`) với màu sắc và nút bấm bo góc hiện đại.

#### 3.5.3 Hiển thị bản đồ HCMUTE
Tích hợp widget nổi trên góc (Floating widgets): Nút zoom in/out/reset góc phải, bảng chú thích màu sắc góc trái, nút xem lịch sử, cài đặt góc dưới. Tooltip ghim vị trí "BẮT ĐẦU" / "ĐÍCH" rất nổi bật.

#### 3.5.4 Bảng điều khiển ControlPanel
Gồm: Combobox chọn điểm, Combobox thuật toán, Combobox heuristic (nếu chọn A*/Greedy), Thanh hiển thị tốc độ, Khung Log quá trình duyệt dạng văn bản, nút Start, Pause/Resume, Stop.

#### 3.5.5 Giao diện chỉnh sửa đồ thị
Là một cửa sổ `QDialog` có TabWidget. Gồm Tab bản đồ trực quan để click và Tab bảng (Table) để nhập liệu X, Y thủ công.

#### 3.5.6 Giao diện lịch sử tìm đường
Cửa sổ `QDialog` hiển thị lưới dữ liệu `QTableWidget` gồm cột thời gian, thuật toán, khoảng cách, thời gian tính toán. Có hộp văn bản bên dưới hiện lộ trình chi tiết.

### 3.6 Thiết kế luồng hoạt động của hệ thống

#### 3.6.1 Luồng khởi động ứng dụng
Chạy `main.py` → Khởi tạo `QApplication` → Mở `WelcomeScreen` → Nạp JSON vào đối tượng `Graph` → Tắt Welcome Screen → Khởi tạo và hiển thị `MainWindow`.

#### 3.6.2 Luồng hoạt động tìm đường đi
Chọn Start/Goal → Click Bắt đầu → `MainWindow._start_algorithm()` → Lấy generator từ `ALGORITHM_MAP` → Khởi động `QTimer` (`_execute_step`) → Gọi `MapWidget.update_step()` đổi màu node → Cập nhật UI Log → Nhận kết quả cuối → Lưu DB → Vẽ đường đi.

#### 3.6.3 Luồng chỉnh sửa đồ thị
Mở Editor → Thao tác trên biến tạm của đồ thị → Nhấn Lưu JSON → Cập nhật file `hcmute_graph_nodes_edges.json` → Reload lại `MapWidget` ở cửa sổ chính.

### 3.7 Các module chính sử dụng
- `main.py`: Khởi chạy ứng dụng và Splash screen.
- `ui/main_window.py`: Quản lý cửa sổ chính, kết nối điều khiển và bản đồ.
- `ui/map_widget.py`: Render bản đồ và node, xử lý sự kiện click.
- `core/algorithms.py`: Triển khai 5 thuật toán.
- `core/graph.py`: Đọc/Lưu JSON và xử lý truy xuất đỉnh/cạnh.
- `core/history_store.py`: Tương tác với SQLite database.
- `ui/graph_editor_dialog.py`: Quản lý giao diện chỉnh sửa đồ thị.

### 3.8 Các công nghệ sử dụng
- Python 3.x
- Thư viện PyQt6 (Xây dựng Desktop GUI)
- Thư viện SQLite3 (Cơ sở dữ liệu)
- JSON (Lưu trữ cấu trúc bản đồ)
- Mypy (Gợi ý kiểm tra kiểu dữ liệu tĩnh trong code)

---

## Chương 4: Kết quả thực hiện và kết luận

### 4.1 Kết quả tổng quan của hệ thống

#### 4.1.1 Các chức năng đã hoàn thành
- Hiển thị bản đồ overlay với chức năng pan/zoom không vỡ hình.
- Tìm đường bằng 5 thuật toán (BFS, DFS, UCS, Greedy, A*).
- Mô phỏng từng bước của thuật toán (có tốc độ nhanh, vừa, chậm).
- Tùy chỉnh heuristic.
- Lịch sử tìm kiếm lưu vào database.
- Map Editor tích hợp với giao diện thêm/sửa/xóa trực quan.

#### 4.1.2 Mức độ hoàn thiện
- Hiển thị bản đồ: **Rất Tốt** (Có ghim tooltip đẹp, hover effect, pulse animation).
- Tìm đường: **Hoàn chỉnh** (Log chi tiết các bước, trả về đúng số mét và path).
- Mô phỏng: **Hoàn chỉnh** (Flow animation và Avatar đi bộ).
- Chỉnh sửa đồ thị: **Hoàn chỉnh** (Đồng bộ trực tiếp JSON).
- Lưu lịch sử: **Hoàn chỉnh** (Database ổn định).

### 4.2 Kết quả chạy chương trình
*(Gợi ý các kịch bản thực tế dựa trên logic đã lập trình)*
- **Kịch bản 1:** Tìm đường từ `Cổng chính` đến `Thư viện` bằng BFS. Ứng dụng mô phỏng lan tỏa nhanh nhưng đường đi tìm được không phải là con đường ngắn nhất.
- **Kịch bản 2:** Tìm đường từ `Khối A` đến `Căn tin` bằng A* (dùng Euclidean). Ứng dụng nhắm thẳng hướng đích, chỉ mở rộng vài node và trả về đúng đường ngắn nhất.
- **Kịch bản 3:** So sánh UCS và Greedy. Trên cùng một lộ trình, UCS duyệt số lượng node gấp nhiều lần Greedy nhưng đảm bảo đường ngắn nhất. Greedy duyệt ít nhưng có thể đi vòng vèo nếu gặp vật cản.

### 4.3 So sánh số liệu giữa các thuật toán
*(Bảng gợi ý để người viết báo cáo điền số liệu thực nghiệm sau khi chạy app)*

| Thuật toán | Điểm bắt đầu | Điểm đích | Chi phí (Pixel) | Số node đã duyệt | Thời gian xử lý | Nhận xét |
|---|---|---|---|---|---|---|
| BFS | N01 | N91 | - | - | - | Nhanh nhưng không tối ưu quãng đường |
| DFS | N01 | N91 | - | - | - | Đi sâu, kết quả không lường trước được |
| UCS | N01 | N91 | - | - | - | Quãng đường tối ưu nhất, duyệt nhiều node |
| Greedy | N01 | N91 | - | - | - | Duyệt ít node, tốc độ nhanh, có thể không tối ưu |
| A* | N01 | N91 | - | - | - | Cân bằng tốt nhất giữa số node duyệt và tính tối ưu |

> **Nhận xét từ codebase:** Thuật toán đo và ghi nhận chính xác các thông số trên và hiển thị ra phần Log cũng như lưu vào bảng `path_history`.

### 4.4 Kết luận
Dự án đã xây dựng thành công phần mềm desktop hoàn chỉnh giúp tìm kiếm và mô phỏng đường đi trong khuôn viên HCMUTE. Hệ thống mô hình hóa xuất sắc bản đồ thành đồ thị vô hướng, áp dụng chuẩn xác 5 thuật toán tìm kiếm kinh điển và cung cấp một giao diện UI/UX rất trực quan bằng PyQt6.

**Hạn chế:**
- Tọa độ và cạnh đồ thị vẫn phải nhập hoặc chỉnh sửa thủ công trên ảnh bản đồ tĩnh, chưa tự động hóa hoặc tích hợp GPS.
- Chưa xét đến vật cản vật lý linh hoạt, đường một chiều hoặc yếu tố thời gian/kẹt xe thực tế.

**Hướng phát triển:**
- Chuyển hướng lên bản đồ động (Mapbox, Google Maps API) thay vì ảnh tĩnh.
- Triển khai thuật toán theo thời gian thực (Real-time pathfinding) nếu bản đồ có mật độ giao thông thay đổi.
- Đưa ứng dụng lên nền tảng Mobile để tiếp cận rộng rãi hơn với đối tượng sinh viên.
