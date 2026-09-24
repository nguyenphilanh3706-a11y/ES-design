import paho.mqtt.client as mqtt
import time
import json
import random

# CẤU HÌNH TRÙNG KHỚP VỚI MAIN.PY (HIVEMQ CLOUD)
BROKER = "491d98aeee1043adad1fd8414b04c1e5.s1.eu.hivemq.cloud"
PORT = 8883
TOPIC = "plant/sensor/data"

client = mqtt.Client(client_id="python_publisher_cloud")
client.tls_set() # Bắt buộc bật TLS cho cổng 8883

# ĐÃ ĐIỀN TÀI KHOẢN HIVEMQ CLOUD CHÍNH CHỦ CỦA BẠN VÀO ĐÂY:
client.username_pw_set("esp_iot", "ESPIOT@123") 

client.connect(BROKER, PORT, 60)
client.loop_start()

device_id = "device_01"

print("Đang gửi dữ liệu lên HiveMQ Cloud...")

try:
    while True:
        # Tạo dữ liệu ngẫu nhiên
        temperature = round(random.uniform(28.0, 35.0), 1)
        humidity = round(random.uniform(50.0, 80.0), 1)
        soil_moisture = round(random.uniform(30.0, 70.0), 1)
        light = round(random.uniform(10000, 15000), 0)
        vpd = round(random.uniform(0.8, 1.8), 2)

        # Đóng gói thành JSON
        payload = {
            "device_id": device_id,
            "temperature": temperature,
            "humidity": humidity,
            "soilMoisture": soil_moisture,
            "light": light,
            "vpd": vpd
        }
        
        msg_str = json.dumps(payload)
        client.publish(TOPIC, msg_str)
        print(f"Đã gửi: {msg_str}")
        
        time.sleep(3) # Gửi mỗi 3 giây
except KeyboardInterrupt:
    print("Ngừng gửi dữ liệu.")
    client.loop_stop()
    client.disconnect()