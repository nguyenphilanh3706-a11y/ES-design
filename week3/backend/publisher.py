import paho.mqtt.client as mqtt
import time
import json
import random

# ==========================================
# CẤU HÌNH HIVEMQ CLOUD (Giống hệt Backend)
# ==========================================
BROKER = "491d98aeee1043adad1fd8414b04c1e5.s1.eu.hivemq.cloud"
PORT = 8883
USERNAME = "esp_iot"
PASSWORD = "ESPIOT@123"
TOPIC = "plant/sensor/data"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ [MẠCH ẢO] Đã kết nối HiveMQ Cloud thành công!")
    else:
        print(f"❌ Kết nối thất bại, mã lỗi: {rc}")

# Khởi tạo client MQTT
client = mqtt.Client(client_id="esp32_simulator_01")
client.tls_set() # Bắt buộc phải có để kết nối bảo mật tới Cloud
client.username_pw_set(USERNAME, PASSWORD)
client.on_connect = on_connect

print("Đang kết nối tới HiveMQ Cloud...")
client.connect(BROKER, PORT, 60)
client.loop_start()

print("🚀 Bắt đầu giả lập ESP32 gửi dữ liệu cảm biến (Nhấn Ctrl+C để dừng)...")
print("-" * 50)

try:
    while True:
        # Tạo dữ liệu ngẫu nhiên mô phỏng cảm biến
        temp = round(random.uniform(28.0, 35.0), 1)
        hum = round(random.uniform(40.0, 80.0), 1)
        soil = round(random.uniform(30.0, 70.0), 1)
        light = random.randint(8000, 15000)
        vpd = round(random.uniform(0.8, 1.5), 2)
        
        # Đóng gói dữ liệu thành chuẩn JSON
        payload = {
            "device_id": "esp32_v1",
            "temperature": temp,
            "humidity": hum,
            "soilMoisture": soil,
            "light": light,
            "vpd": vpd
        }
        
        json_payload = json.dumps(payload)
        
        # Gửi lên Cloud
        client.publish(TOPIC, json_payload)
        print(f"Đã gửi -> {json_payload}")
        
        # Chờ 5 giây rồi gửi tiếp
        time.sleep(5)
        
except KeyboardInterrupt:
    print("\n🛑 Đã dừng gửi dữ liệu.")
    client.loop_stop()
    client.disconnect()