# ĐẶC TẢ HỆ THỐNG (SYSTEM SPECIFICATION)

## 1. Tổng quan hệ thống
Hệ thống IoT kết hợp AI giúp thu thập dữ liệu từ cảm biến/camera tại biên (Edge), xử lý thông minh bằng mô hình AI, đồng bộ dữ liệu thời gian thực lên Server và hiển thị trực quan trên giao diện Web Dashboard.

## 2. Kiến trúc tổng thể
Hệ thống bao gồm 4 tầng chính:
1. **Tầng Phần cứng & Firmware (Edge Layer - Phụ trách: Nguyễn Phi Lanh)**
   - Vi điều khiển trung tâm: ESP32-S3 / ESP32-WROOM.
   - Cảm biến: Nhiệt độ/Độ ẩm (DHT22/SHT30), Cảm biến khí gas/chất lượng không khí (MQ135), Camera module (ESP32-CAM / RTSP).
   - Cơ cấu chấp hành: Relay điều khiển thiết bị, Còi báo động (Buzzer), LED trạng thái.
   - Giao thức truyền thông: MQTT (qua Wi-Fi) và HTTP/REST cho OTA hoặc gửi ảnh.

2. **Tầng Xử lý AI (AI Engine Layer - Phụ trách: Nguyễn Phi Lanh)**
   - Mô hình phát hiện bất thường từ dữ liệu cảm biến (Anomaly Detection) và/hoặc Nhận diện hình ảnh (YOLO/MobileNet).
   - Nhận luồng dữ liệu từ thiết bị hoặc MQTT, thực hiện suy luận (Inference) và đẩy kết quả cảnh báo về Backend.

3. **Tầng Backend & Cơ sở dữ liệu (Server Layer - Phụ trách: Lê Công Quốc Anh)**
   - Ngôn ngữ/Framework: Node.js (Express) tích hợp Socket.IO & MQTT Client.
   - Cơ sở dữ liệu: MongoDB / PostgreSQL lưu trữ lịch sử cảm biến, nhật ký cảnh báo AI và thông tin người dùng.
   - Bảo mật: Xác thực JWT (JSON Web Token), phân quyền Admin/User.

4. **Tầng Giao diện Web (Frontend Layer - Phụ trách: Lê Công Quốc Anh)**
   - Framework: React.js + TailwindCSS + Chart.js.
   - Tính năng:
     - Biểu đồ thời gian thực (Real-time charts) hiển thị thông số môi trường.
     - Bảng điều khiển (Control Panel) bật/tắt thiết bị từ xa độ trễ thấp.
     - Trung tâm cảnh báo AI kèm hình ảnh/log chi tiết.

## 3. Luồng dữ liệu (Data Flow)
1. **Luồng Telemetry**: `Sensors -> ESP32 Firmware -> MQTT Broker (Topic: iot/telemetry) -> Backend -> Database & WebSocket -> Web Frontend`.
2. **Luồng AI Inference**: `Device/Stream -> AI Engine -> MQTT/HTTP (Topic: iot/ai_alert) -> Backend -> WebSocket -> Web Frontend`.
3. **Luồng Điều khiển (Control)**: `Web Frontend -> REST API / WebSocket -> Backend -> MQTT Broker (Topic: iot/control) -> ESP32 Firmware -> Relay/Actuator`.

## 4. Yêu cầu phi chức năng
- **Độ trễ (Latency)**: Thời gian phản hồi điều khiển thiết bị < 500ms; Thời gian suy luận AI < 200ms/frame.
- **Độ tin cậy**: Firmware hỗ trợ Watchdog Timer và cơ chế tự động kết nối lại (Auto-reconnect) khi mất Wi-Fi/MQTT.
- **Khả năng mở rộng**: Thiết kế theo chuẩn Docker hóa, dễ dàng thêm node cảm biến mới.
