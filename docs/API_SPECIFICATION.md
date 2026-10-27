# ĐẶC TẢ GIAO THỨC MQTT & RESTful API

## 1. Cấu trúc MQTT Topics
- **Topic gửi dữ liệu cảm biến (ESP32 -> Broker -> Backend)**
  - Topic: `iot/device/telemetry`
  - Payload:
    ```json
    {
      "device_id": "ESP32_NODE_01",
      "temperature": 28.5,
      "humidity": 65.2,
      "air_quality": 120,
      "relay_state": false,
      "timestamp": 1730000000
    }
    ```
- **Topic cảnh báo AI (AI Engine -> Broker -> Backend)**
  - Topic: `iot/ai/alert`
  - Payload:
    ```json
    {
      "device_id": "ESP32_NODE_01",
      "anomaly_detected": true,
      "confidence": 0.94,
      "label": "FIRE_OR_ABNORMAL_TEMP",
      "message": "Phat hien nhiet do va khi gas tang bat thuong!"
    }
    ```
- **Topic điều khiển thiết bị (Backend -> Broker -> ESP32)**
  - Topic: `iot/device/control`
  - Payload:
    ```json
    {
      "device_id": "ESP32_NODE_01",
      "command": "SET_RELAY",
      "value": true
    }
    ```

## 2. RESTful API Endpoints (Backend)
- `GET /api/health` : Kiểm tra trạng thái hoạt động của Server.
- `GET /api/telemetry/latest` : Lấy dữ liệu cảm biến mới nhất.
- `GET /api/telemetry/history?limit=50` : Lấy lịch sử dữ liệu cảm biến.
- `GET /api/alerts` : Lấy danh sách cảnh báo từ AI Engine.
- `POST /api/control` : Gửi lệnh bật/tắt thiết bị xuống mạch phần cứng.
