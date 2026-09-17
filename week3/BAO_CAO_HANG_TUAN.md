# Báo Cáo Tiến Độ Chuyên Sâu Đồ Án: Hệ Thống IoT Giám Sát Cân Bằng Sinh Học Cho Cây Trồng

## 🎯 Tổng quan & Kiến trúc Hệ thống
Dự án nhằm xây dựng một hệ sinh thái IoT vòng kín để tự động hóa việc chăm sóc cây trồng, đặc biệt ngăn ngừa tình trạng khô héo khi vắng nhà. Thay vì chỉ tưới nước theo lịch cố định, hệ thống duy trì **cân bằng sinh học** dựa trên 4 thông số môi trường cốt lõi (Nhiệt độ, Độ ẩm khí, Ánh sáng, Độ ẩm đất). Dữ liệu này được dùng để tính toán **chỉ số bốc thoát hơi nước (VPD - Vapor Pressure Deficit)**, từ đó đưa ra quyết định điều khiển bơm tưới chính xác nhất.

**Công nghệ lõi sử dụng:**
*   **Phần cứng/Edge:** Cảm biến môi trường, Vi điều khiển ESP32-S3.
*   **Giao thức:** MQTT (Paho-MQTT, QoS 0/1, LWT).
*   **Hạ tầng mạng:** Docker Compose, Eclipse Mosquitto Broker.
*   **Cơ sở dữ liệu:** TimescaleDB (PostgreSQL tối ưu chuỗi thời gian).
*   **Backend & API:** Python, FastAPI, Uvicorn, Swagger UI.
*   **AI/TinyML:** LSTM, TensorFlow Lite, C++ Header (Lượng tử hóa Full INT8).

---

## 🚀 Tiến độ Chi tiết & Kết quả Đạt được (Tuần 1 - Tuần 3)

### Tuần 1 & 2: Thiết kế Giao thức Mạng (MQTT Specification) & Quy hoạch Dữ liệu

**1. Xây dựng Cấu trúc Gói tin (JSON Payload)**
Để đảm bảo đường truyền nhẹ và dễ dàng bóc tách tại Backend, gói tin telemetry được chuẩn hóa dưới định dạng JSON. Cấu trúc mô phỏng bao gồm định danh thiết bị, mốc thời gian tuyệt đối và các thông số đo lường thực tế:
    ```json
    {
      "device_id": "device_01",
      "timestamp": 1726154521,
      "temperature": 26.56,
      "humidity": 68.15,
      "vpd": 0.85,
      "pump_status": 0
    }
    ```

**2. Quy hoạch Cây Chủ đề (MQTT Topic Tree)**
Hệ thống sử dụng mô hình Publish/Subscribe với các topic được phân cấp logic, giúp dễ dàng mở rộng khi có nhiều chậu cây (nodes):
*   `plant/node_01/telemetry`: Node ESP32-S3 publish dữ liệu cảm biến định kỳ.
*   `plant/node_01/status`: Topic chuyên biệt để ghi nhận trạng thái kết nối mạng của thiết bị.
*   `plant/node_01/cmd/pump`: Broker/Backend publish lệnh điều khiển (Bật/Tắt) xuống rơ-le máy bơm.

**3. Cấu hình Độ tin cậy (QoS) & Di chúc mạng (LWT)**
*   **QoS (Quality of Service):** Áp dụng linh hoạt hai chuẩn. **QoS 0** (At most once) cho topic `telemetry` vì dữ liệu cảm biến gửi liên tục, mất 1-2 gói tin không ảnh hưởng đến hệ thống, giúp tối ưu băng thông. **QoS 1** (At least once) được cài đặt bắt buộc cho `cmd/pump` nhằm đảm bảo lệnh tưới nước phải được xác nhận giao đến nơi.
*   **LWT (Last Will and Testament):** Đã thiết lập cấu hình an toàn cho phần cứng. Nếu ESP32-S3 sập nguồn hoặc rớt Wi-Fi đột ngột mà không kịp gửi lệnh ngắt kết nối (`DISCONNECT`), Mosquitto Broker sẽ tự động publish payload `{"status": "offline"}` vào topic `plant/node_01/status`.

---

### Tuần 3: Dựng Hạ tầng DevOps, CSDL, AI & Lập trình Backend Server

**1. Khởi tạo Hạ tầng máy chủ với Docker Compose**
Hệ thống backend được container hóa (Dockerized) để cô lập môi trường và dễ dàng khởi chạy đồng bộ:
*   **Eclipse Mosquitto:** Chạy tại port `1883` (giao tiếp thiết bị qua TCP) và `9001` (hỗ trợ WebSockets). Cấu hình `mosquitto.conf` cho phép kết nối ẩn danh (phục vụ môi trường dev) và ghi nhận toàn bộ log giao tiếp.
*   **TimescaleDB:** Mở cổng `5432`. CSDL được chọn để thay thế các SQL truyền thống vì khả năng xử lý dữ liệu chuỗi thời gian vượt trội.

**2. Thiết kế Lược đồ Cơ sở dữ liệu (Database Schema)**
Khởi tạo bảng `sensor_data` và chuyển đổi thành **Hypertable** trong TimescaleDB để tự động phân mảnh dữ liệu (partitioning) theo thời gian.
*   **Cấu trúc bảng:** `time` (TIMESTAMPTZ), `device_id` (VARCHAR), `temperature` (FLOAT), `humidity` (FLOAT).

**3. Lập trình Backend xử lý bất đồng bộ (FastAPI & Paho-MQTT)**
*   **Kiến trúc Đa luồng:** Tích hợp `paho-mqtt` chạy trên một luồng nền (background thread) bên trong FastAPI. Điều này giúp tiến trình lắng nghe MQTT (Subscriber) hoạt động liên tục `loop_forever()` mà không gây đứng (blocking) luồng web server Uvicorn.
*   **Data Pipeline:** Mỗi khi có tin nhắn bắn vào topic `telemetry`, hàm callback `on_message` tự động bóc tách JSON và thực thi lệnh `INSERT` vào TimescaleDB qua thư viện `psycopg2`.

**4. Huấn luyện & Lượng tử hóa Mô hình AI (TinyML)**
*   **Kiến trúc mô hình:** Sử dụng mạng LSTM (Long Short-Term Memory) để phân tích dữ liệu chuỗi thời gian, thực hiện bài toán dự đoán đa khung thời gian (Multi-horizon prediction) cho 6 giờ và 12 giờ tới.
*   **Lượng tử hóa (Quantization):** Để mô hình có thể chạy mượt mà trên phần cứng hạn chế tài nguyên như ESP32-S3, tiến hành kỹ thuật lượng tử hóa Full INT8 (`TFLiteConverter`). 
*   **Đóng gói C/C++:** Xuất mô hình thành công dưới dạng chuỗi mảng Hex `const unsigned char` vào tệp tin `model_data.h`. Kích thước mô hình được tối ưu hóa thành công xuống mức **121.98 KB**, hoàn toàn tương thích với dung lượng Flash/PSRAM của vi điều khiển.

**5. Hoàn thiện REST API & Hệ thống Cảnh báo Discord**
*   **Các Endpoints cấu hình bằng Pydantic:**
    *   `GET /api/telemetry/latest`: Truy xuất realtime dữ liệu cảm biến mới nhất.
    *   `GET /api/telemetry/history`: Truy xuất mảng dữ liệu lịch sử để vẽ biểu đồ.
    *   `POST /api/control/pump`: Cấp lệnh rơ-le bơm nước từ xa qua MQTT.
    *   `POST /api/config`: Cấu hình động các ngưỡng môi trường.
*   **Hệ thống Cảnh báo Chủ động (Discord Webhook):** Thay vì sử dụng Bot truyền thống, backend tích hợp cơ chế Webhook nhằm tối ưu hiệu năng. Hệ thống liên tục giám sát payload MQTT, nếu phát hiện độ ẩm đất thấp (ví dụ: < 20%), server tự động thực thi HTTP POST qua thư viện `requests`, lập tức gửi thông báo khẩn cấp đến kênh Discord của ban quản trị dự án nhằm kịp thời đưa ra hành động can thiệp.
*   **Nghiệm thu:** Toàn bộ luồng dữ liệu (Edge -> MQTT Broker -> Database -> FastAPI -> Discord) đã được kiểm thử độ trễ, vượt qua bài test giả lập và hiển thị tài liệu hóa chuyên nghiệp trên **Swagger UI**.