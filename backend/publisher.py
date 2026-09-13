import time
import random
import paho.mqtt.client as mqtt

# Kết nối tới Mosquitto Broker chạy trên Docker
broker_address = "localhost"
port = 1883
topic = "sensor/data"

client = mqtt.Client()
client.connect(broker_address, port)

print("Đang khởi động thiết bị giả lập gửi dữ liệu MQTT...")

try:
  while True:
    # Giả lập dữ liệu cảm biến: device_id, temperature, humidity
    device_id = "device_01"
    temperature = round(random.uniform(20.0, 35.0), 2)
    humidity = round(random.uniform(40.0, 80.0), 2)

    payload = f"{device_id},{temperature},{humidity}"

    # Gửi bản tin lên MQTT Broker
    client.publish(topic, payload)
    print(f"Đã gửi lên topic '{topic}': {payload}")

    # Gửi định kỳ mỗi 3 giây
    time.sleep(3)
except KeyboardInterrupt:
  print("Đã dừng chương trình giả lập.")
  client.disconnect()