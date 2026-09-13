# Báo Cáo Tiến Độ Chuyên Sâu Đồ Án: Hệ Thống IoT Giám Sát Cân Bằng Sinh Học Cho Cây Trồng

## 🎯 Tổng quan & Kiến trúc Hệ thống
Dự án nhằm xây dựng một hệ sinh thái IoT vòng kín để tự động hóa việc chăm sóc cây trồng, đặc biệt ngăn ngừa tình trạng khô héo khi vắng nhà. Thay vì chỉ tưới nước theo lịch cố định, hệ thống duy trì **cân bằng sinh học** dựa trên 4 thông số môi trường cốt lõi (Nhiệt độ, Độ ẩm khí, Ánh sáng, Độ ẩm đất). Dữ liệu này được dùng để tính toán **chỉ số bốc thoát hơi nước (VPD - Vapor Pressure Deficit)**, từ đó đưa ra quyết định điều khiển bơm tưới chính xác nhất.

**Công nghệ lõi sử dụng:**
*   **Phần cứng/Edge:** Cảm biến môi trường, Vi điều khiển ESP32-S3.
*   **Giao thức:** MQTT (Paho-MQTT, QoS 0/1, LWT).
*   **Hạ tầng mạng:** Docker Compose, Eclipse Mosquitto Broker.
*   **Cơ sở dữ liệu:** TimescaleDB (PostgreSQL tối ưu chuỗi thời gian).
*   **Backend & API:** Python, FastAPI, Uvicorn, Swagger UI.

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

### Tuần 3: Dựng Hạ tầng DevOps, CSDL & Lập trình Backend Server

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

**4. Xây dựng API và Kịch bản Kiểm thử Tải (Load Testing)**
*   **Script Giả lập (publisher.py):** Viết chương trình Python giả lập vòng đời của vi điều khiển, tự động sinh dữ liệu nhiệt độ/độ ẩm ngẫu nhiên và publish lên Broker mỗi giây để kiểm tra giới hạn chịu tải (stress test) của pipeline luồng dữ liệu.
*   **REST API Endpoint:** Hoàn thành tuyến API `GET /api/data?limit={số_lượng}`.
*   **Nghiệm thu:** Truy xuất thành công dữ liệu thông qua giao diện tài liệu tự động **Swagger UI** (HTTP Status 200). Dữ liệu JSON trả về hoàn toàn khớp với dữ liệu giả lập được sinh ra từ Publisher, xác nhận luồng hệ thống từ biên (Edge) đến đám mây (Cloud) đã được đả thông toàn diện.