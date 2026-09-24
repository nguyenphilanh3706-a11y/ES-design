## TÀI LIỆU ĐẶC TẢ TRÍ TUỆ NHÂN TẠO VÀ PHẦN MỀM (AI & SOFTWARE SPECIFICATION)

**Dự án:** Hệ thống tưới cây tự động thích ứng AIoT Node (ESP32-S3 + TinyML LSTM)
**Giai đoạn:** Tuần 1 - Phân tích yêu cầu & Đặc tả hệ thống

### 1. Bài toán mô hình hóa (Evapotranspiration Modeling)
* **Mục tiêu:** Xây dựng mô hình học sâu để dự đoán tốc độ bốc thoát hơi nước của đất dựa trên các biến số vi khí hậu.
### 2. Định dạng Cấu trúc Dữ liệu (Tensor Specifications)
**Input Tensor (Đầu vào mô hình):**
* **Shape:** [Batch_size, 24, 4] (Cửa sổ trượt 24 bước thời gian tương ứng 24 giờ lấy mẫu liên tục).
* **Đặc trưng (Features):** 
  1. Nhiệt độ môi trường (T)
  2. Độ ẩm không khí (RH)
  3. Cường độ ánh sáng (Lux)
  4. Độ ẩm đất hiện tại (SM)
* **Tiền xử lý:** Chuẩn hóa toàn bộ biến số về dải [0, 1] (MinMax Scaling) để phù hợp với định dạng số nguyên INT8.

**Output Tensor (Đầu ra mô hình):**
* **Shape:** [Batch_size, 1]
* **Đại lượng dự báo:** Độ ẩm đất dự kiến sau 6h, 12h hoặc 24h tiếp theo.

### 3. Chỉ số Hiệu năng & Ràng buộc Tài nguyên (KPIs & Constraints)
* **Sai số dự đoán:** Sai số tuyệt đối trung bình (MAE) < 5% so với dữ liệu thực tế.
* **Môi trường triển khai:** TensorFlow Lite for Microcontrollers (TFLM) trên chip ESP32-S3.
* **Lượng tử hóa (Quantization):** Áp dụng Post-Training Quantization (Full INT8) để tối ưu hóa.
* **Giới hạn bộ nhớ vi điều khiển:**
  * Kích thước file mô hình (Flash memory): <= 80 KB.
  * Dung lượng cấp phát tĩnh (Tensor Arena RAM): <= 30 KB.

### 4. Thuật toán Ra quyết định (Away Mode Strategy)
* **Điều kiện kích hoạt:** Hệ thống ở trạng thái "Vắng nhà dài ngày" (7-14 ngày), yêu cầu bảo toàn lượng nước dự trữ tối đa.
* **Quy tắc tưới thích ứng:**
  * **Tránh bốc hơi:** Nếu LSTM dự báo tốc độ bốc hơi cao trong 12h tới (nhiệt độ và ánh sáng đạt đỉnh), tuyệt đối không kích hoạt bơm tưới đẫm vào giữa trưa.
  * **Tưới vi liều (Micro-dosing):** Bơm một lượng nước nhỏ vào sáng sớm hoặc chiều mát nhằm duy trì độ ẩm đất nhỉnh hơn ngưỡng héo rũ (wilting point ~30-35%), đảm bảo trạng thái cân bằng sinh học (homeostasis) cho cây.