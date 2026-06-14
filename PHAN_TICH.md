# Phân Tích Hiệu Suất Các Thuật Toán Tìm Đường

Báo cáo này phân tích kết quả thực thi của 5 thuật toán tìm kiếm đường đi (BFS, DFS, UCS, Greedy, A*) từ điểm xuất phát **N91 (Cổng chính)** đến điểm đích **N04 (Ký túc xá)** trong khuôn viên HCMUTE.

## 1. Kết Quả Thực Thi

Các thuật toán được chạy và đo đạc với các thông số: độ dài đường đi (cost), số lượng node đã duyệt (visited nodes) và thời gian thực thi (ms).

| Thuật toán | Chi phí đường đi (m) | Số node đã duyệt | Thời gian chạy (ms) | Lộ trình |
|:---:|:---:|:---:|:---:|---|
| **DFS** | 1614.34 | 18 | 0.1008 | N91 → N23 → N86 → N27 → N76 → N74 → N71 → N60 → N56 → N37 → N31 → N11 → N07 → N01 → N02 → N03 → N04 |
| **Greedy**| **1325.54** | **14** | 0.1187 | N91 → N25 → N24 → N87 → N79 → N65 → N54 → N21 → N39 → N30 → N20 → N17 → N09 → N04 |
| **A\*** | **1325.54** | 25 | 0.1900 | N91 → N25 → N24 → N87 → N79 → N65 → N54 → N21 → N39 → N30 → N20 → N17 → N09 → N04 |
| **BFS** | **1325.54** | 65 | 0.2398 | N91 → N25 → N24 → N87 → N79 → N65 → N54 → N21 → N39 → N30 → N20 → N17 → N09 → N04 |
| **UCS** | **1325.54** | 64 | 0.2935 | N91 → N25 → N24 → N87 → N79 → N65 → N54 → N21 → N39 → N30 → N20 → N17 → N09 → N04 |

*(Thời gian đo có thể chênh lệch rất nhỏ qua các lần chạy khác nhau, nhưng tỷ lệ tương quan vẫn giữ nguyên).*

## 2. Phân Tích & Đánh Giá

### 2.1. Về tính tối ưu của đường đi (Độ dài quãng đường)
- **BFS, UCS, Greedy và A\*** đều tìm ra được lộ trình ngắn nhất với tổng chi phí là **1325.54m**. Mặc dù Greedy Search không đảm bảo luôn luôn tìm ra đường đi tối ưu theo lý thuyết, nhưng đối với bài toán này nhờ có heuristic tốt (khoảng cách Euclidean), nó cũng tìm ra kết quả tốt nhất.
- **DFS** tìm ra một đường đi khá vòng vèo (lên tới 1614.34m). Lý do là DFS đi sâu vào một nhánh ngẫu nhiên cho đến khi đụng đích thay vì mở rộng dần đều quanh điểm xuất phát.

### 2.2. Về số lượng node đã duyệt
- **Greedy** duyệt ít node nhất (**14 nodes**). Thuật toán này luôn ưu tiên mở rộng node gần đích nhất (theo đường chim bay), do đó nó tiến thẳng một mạch tới N04 mà không cần đi qua các hướng khác.
- **DFS** cũng duyệt rất ít node (**18 nodes**). Khi DFS vừa may mắn chọc đúng nhánh dẫn đến N04, nó dừng lại ngay.
- **A\*** duyệt **25 nodes**, nhỉnh hơn Greedy một chút vì A* phải cân đối cả "quãng đường đã đi" và "khoảng cách ước lượng đến đích" để đảm bảo tính tối ưu tuyệt đối.
- **BFS** và **UCS** duyệt số node cực kỳ lớn (**65** và **64 nodes**). Các thuật toán mù này buộc phải loan rộng ra mọi hướng để chắc chắn không bỏ sót con đường ngắn nhất, làm lãng phí nhiều tài nguyên tính toán.

### 2.3. Về thời gian thực thi
- Thời gian chạy tỉ lệ thuận trực tiếp với số lượng node đã duyệt và độ phức tạp của cấu trúc dữ liệu lưu trữ.
- **DFS** (0.1008 ms) và **Greedy** (0.1187 ms) chạy nhanh nhất do không phải đưa nhiều node vào frontier. 
- **A\*** chạy cực kỳ ổn định và nhanh chóng ở mức **0.1900 ms**.
- **BFS** (0.2398 ms) và **UCS** (0.2935 ms) chậm nhất do chi phí lấy node ra/vào hàng đợi và duyệt quá nhiều hướng sai lầm.

## 3. Kết Luận
- **A\* (A-Star)** là sự lựa chọn hoàn hảo và thực tiễn nhất. Thuật toán này chứng minh sự hiệu quả khi kết hợp được tốc độ xử lý nhanh gọn (nhờ heuristic) và chất lượng đầu ra tuyệt đối tối ưu (luôn tìm ra đường đi ngắn nhất).
- **Greedy Search** chạy siêu nhanh và phù hợp nếu chấp nhận sai số (trong test-case này nó cho ra kết quả hoàn hảo nhưng có thể gặp rủi ro ở các cặp điểm khác).
- **DFS, BFS, UCS** không thích hợp cho bài toán tìm đường thực tế (GPS, game) do tính chất lan truyền quá rộng (BFS, UCS) hoặc tìm đường quá xa (DFS).
