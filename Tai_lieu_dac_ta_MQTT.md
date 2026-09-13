# TÀI LIỆU ĐẶC TẢ GIAO THỨC MQTT - HỆ THỐNG IoT CHẬU CÂY THÔNG MINH

## 1. Phân tích bài toán bốc thoát hơi nước (Evapotranspiration)
- **Lập luận đầu vào:** Hệ thống bắt buộc phải thu thập đồng thời 4 đặc trưng cốt lõi gồm Nhiệt độ, Độ ẩm không khí, Ánh sáng (Lux) và Lịch sử độ ẩm đất 24h vì chúng tác động trực tiếp và liên tục đến tốc độ bốc hơi nước của bề mặt đất và hiện tượng thoát hơi nước qua khí khổng của thực vật.
- **Kịch bản Homeostasis (Cân bằng sinh học):** Thay vì chờ cảm biến báo đất khô cạn mới kích hoạt máy bơm, hệ thống sử dụng dữ liệu 4 thông số trên để mô hình AI dự báo trước tốc độ mất nước của môi trường, từ đó ra quyết định tưới bù sớm nhằm duy trì độ ẩm ổn định, bảo vệ cây trồng không bị khô héo khi vắng nhà.

## 2. Quy hoạch Cây MQTT Topic
| Topic MQTT | Người gửi (Publisher) | Người nhận (Subscriber) | Chức năng cốt lõi |
| :--- | :--- | :--- | :--- |
| `plant/node_01/telemetry` | Vi điều khiển ESP32 | Backend Server / Web | Gửi định kỳ dữ liệu 4 cảm biến, chỉ số VPD và độ ẩm dự báo từ AI. |
| `plant/node_01/status` | ESP32 / Broker | Backend Server / Web | Báo cáo trạng thái hoạt động (online) hoặc mất kết nối đột ngột (offline qua LWT). |
| `plant/node_01/cmd/pump` | Web Dashboard / Backend | Vi điều khiển ESP32 | Truyền lệnh điều khiển cưỡng chế thủ công (Bật/Tắt máy bơm). |
| `plant/node_01/actuator/pump` | Vi điều khiển ESP32 | Backend Server / Web | ESP32 xác nhận ngược lại trạng thái thực tế của máy bơm. |
| `plant/node_01/config` | Web Dashboard / Backend | Vi điều khiển ESP32 | Truyền thông số cài đặt mới từ xa (ngưỡng tưới, cấu hình). |

## 3. Định dạng Cấu trúc JSON Payload
Mẫu cấu trúc dữ liệu JSON truyền tải qua giao thức MQTT:
- `device_id`: node_01
- `timestamp`: 1789011009000
- `sensors`: temperature_c (32.5), humidity_percent (65.0), light_lux (450.2), soil_moisture_percent (45.3)
- `indicators`: vpd_kpa (1.67)
- `actuators`: pump_status (ON)
z
## 4. Cơ chế Độ tin cậy (QoS & LWT)
- **Chất lượng dịch vụ (QoS):**
  - **Telemetry (Cảm biến định kỳ):** Sử dụng `QoS 0` (Fire and forget) cho luồng dữ liệu gửi lên liên tục nhằm tiết kiệm băng thông và tài nguyên mạng, chấp nhận thất lạc nhỏ vì dữ liệu sẽ được cập nhật liên tục ở các chu kỳ sau.
  - **Command (Lệnh điều khiển bơm):** Sử dụng `QoS 1` (At least once) cho các bản tin ra lệnh đóng cắt máy bơm từ xa để bắt buộc hệ thống bảo đảm gói tin đến được đích, tránh việc lệnh bị thất lạc.
- **Cơ chế Di chúc mạng (LWT - Last Will and Testament):**
  - **Cấu hình:** Đăng ký thông điệp gắn liền với phiên kết nối của ESP32-S3 tại topic `plant/node_01/status`.
  - **Nội dung payload:** `{"status": "offline"}` kèm theo cờ `Retain = true`.
  - **Hành vi hệ thống:** Nếu thiết bị phần cứng đột ngột mất nguồn hoặc đứt kết nối Internet mà không kịp gửi tín hiệu ngắt kết nối, Mosquitto Broker sẽ tự động phát tán thông điệp di chúc này để Dashboard nhận biết ngay lập tức tình trạng sự cố của chậu cây.