import threading
import paho.mqtt.client as mqtt
import psycopg2
import requests
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # <-- THƯ VIỆN CORS
from pydantic import BaseModel

app = FastAPI()

# ===== BỔ SUNG CẤU HÌNH CORS NÀY VÀO main.py =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép tất cả các nguồn gọi API vào
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# CẤU HÌNH HIVEMQ CLOUD (THAY CHO LOCAL)
# ==========================================
BROKER_CLOUD = "491d98aeee1043adad1fd8414b04c1e5.s1.eu.hivemq.cloud"
PORT_CLOUD = 8883

mqtt_client = mqtt.Client(client_id="fastapi_backend_cloud")
mqtt_client.tls_set()  # Bật bảo mật TLS cho cổng 8883

# ĐÃ ĐIỀN TÀI KHOẢN HIVEMQ CLOUD CHÍNH CHỦ CỦA BẠN VÀO ĐÂY:
mqtt_client.username_pw_set("esp_iot", "ESPIOT@123")

# ==========================================
# CẤU HÌNH WEBHOOK DISCORD
# ==========================================
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1549998464925048962/RZy58PdKZ0wwBIYFdzQLBIjyFX1mciRGtcOU2txwYN3CiEyby_FjwiE5lewf1YIwobDV"

def send_discord_alert(message: str):
    if not DISCORD_WEBHOOK_URL:
        return
    data = {"content": message}
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=data)
        print("-> Đã đẩy cảnh báo lên Discord!")
    except Exception as e:
        print(f"Lỗi gửi Discord: {e}")

# ==========================================
# CẤU HÌNH DATABASE (CLOUD AIVEN)
# ==========================================
DATABASE_URL = "postgresql://avnadmin:AVNS_4NVhjrkWUR3w2RyW836@pg-2c8553bc-lecongquoca-1be9.l.aivencloud.com:21438/defaultdb?sslmode=require"

def get_db_connection():
    # Sử dụng chuỗi kết nối trực tiếp đến Aiven Cloud
    return psycopg2.connect(DATABASE_URL)

# Khởi tạo bảng lưu dữ liệu cảm biến đầy đủ cột
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 1. Xóa bảng cũ bị thiếu cột (nếu có) để làm mới
    cur.execute("DROP TABLE IF EXISTS sensor_data CASCADE;")
    
    # 2. Tạo lại bảng mới với đầy đủ 7 cột
    cur.execute("""
        CREATE TABLE sensor_data (
            time TIMESTAMPTZ NOT NULL,
            device_id VARCHAR(50),
            temperature FLOAT,
            humidity FLOAT,
            soil_moisture FLOAT,
            light FLOAT,
            vpd FLOAT
        );
    """)
    # Bỏ create_hypertable vì Aiven bản Free có thể không cài sẵn extension TimescaleDB, 
    # dùng PostgreSQL chuẩn vẫn dư sức chạy đồ án mượt mà.
    conn.commit()
    cur.close()
    conn.close()

init_db()

# BÁO CÁO TRẠNG THÁI KẾT NỐI (MỚI THÊM)
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Backend đã KẾT NỐI THÀNH CÔNG với HiveMQ Cloud!")
        client.subscribe("plant/sensor/data")
    else:
        print(f"❌ LỖI KẾT NỐI HiveMQ! Mã lỗi (rc): {rc}")

# Xử lý khi nhận được message từ MQTT Cloud Broker
def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8")
    print(f"Nhận dữ liệu từ topic {msg.topic}: {payload}")
    try:
        if payload.startswith("{"):
            data = json.loads(payload)
            device_id = data.get("device_id", "device_01")
            temp = float(data.get("temperature", 30.0))
            hum = float(data.get("humidity", 70.0))
            soil_moisture = float(data.get("soilMoisture", hum))
            light = float(data.get("light", 12000.0))
            vpd = float(data.get("vpd", 1.2))
        else:
            parts = payload.split(",")
            device_id = parts[0]
            temp = float(parts[1])
            hum = float(parts[2])
            soil_moisture = hum
            light = 12000.0
            vpd = 1.2

        # 1. Lưu vào Database Aiven
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO sensor_data (time, device_id, temperature, humidity, soil_moisture, light, vpd) VALUES (NOW(), %s, %s, %s, %s, %s, %s)",
            (device_id, temp, hum, soil_moisture, light, vpd),
        )
        conn.commit()
        cur.close()
        conn.close()
        print("-> Đã lưu vào Aiven Database thành công!")

        # 2. KIỂM TRA ĐỘ ẨM VÀ BẮN CẢNH BÁO DISCORD
        if hum < 30.0:
            alert_msg = f"🚨 **CẢNH BÁO IoT:** Độ ẩm tại trạm `{device_id}` đang ở mức nguy hiểm ({hum}%). Hệ thống AI đề xuất bật máy bơm ngay!"
            send_discord_alert(alert_msg)

    except Exception as e:
        print(f"Lỗi xử lý dữ liệu: {e}")

# Cấu hình MQTT Subscriber chạy ngầm kết nối Cloud (ĐÃ CẬP NHẬT)
def start_mqtt():
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    try:
        mqtt_client.connect(BROKER_CLOUD, PORT_CLOUD, 60)
        mqtt_client.loop_start()
    except Exception as e:
        print(f"Lỗi khởi động ngầm MQTT: {e}")

@app.on_event("startup")
def startup_event():
    threading.Thread(target=start_mqtt, daemon=True).start()
    print("MQTT Cloud Client background service started.")

# ==========================================
# KHAI BÁO MODEL DỮ LIỆU CHO API POST
# ==========================================
class PumpCommand(BaseModel):
    state: str  # Gửi "ON" hoặc "OFF"

class SystemConfig(BaseModel):
    temp_threshold: float
    hum_threshold: float

# ==========================================
# CÁC ENDPOINT API ĐẦY ĐỦ
# ==========================================

@app.get("/")
def read_root():
    return {"message": "IoT Backend Cloud Server is running!"}

# 1. Lấy thông số môi trường mới nhất (Đảm bảo dùng ORDER BY time DESC LIMIT 1)
@app.get("/api/telemetry/latest")
def get_latest_telemetry():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT time, device_id, temperature, humidity, soil_moisture, light, vpd FROM sensor_data ORDER BY time DESC LIMIT 1"
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row:
            return {
                "status": "success", 
                "data": {
                    "time": row[0], 
                    "device_id": row[1], 
                    "temperature": row[2], 
                    "humidity": row[3],
                    "soilMoisture": row[4],
                    "light": row[5],
                    "vpd": row[6]
                }
            }
        return {"status": "success", "data": None, "message": "Chưa có dữ liệu cảm biến"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# 2. Lấy dữ liệu lịch sử
@app.get("/api/telemetry/history")
def get_telemetry_history(hours: int = 24):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query = f"SELECT time, device_id, temperature, humidity, soil_moisture, light, vpd FROM sensor_data WHERE time >= NOW() - INTERVAL '{hours} hours' ORDER BY time DESC"
        cur.execute(query)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        result = [{
            "time": r[0], 
            "device_id": r[1], 
            "temperature": r[2], 
            "humidity": r[3],
            "soilMoisture": r[4],
            "light": r[5],
            "vpd": r[6]
        } for r in rows]
        return {"status": "success", "count": len(result), "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# 3. Gửi lệnh điều khiển bơm
@app.post("/api/control/pump")
def control_pump(cmd: PumpCommand):
    if cmd.state not in ["ON", "OFF"]:
        return {"status": "error", "message": "Lệnh không hợp lệ. Chỉ chấp nhận 'ON' hoặc 'OFF'"}
    
    mqtt_client.publish("plant/control/pump", cmd.state)
    return {"status": "success", "message": f"Đã gửi lệnh {cmd.state} tới máy bơm qua Cloud!"}

# 4. Cấu hình hệ thống
@app.post("/api/config")
def update_config(config: SystemConfig):
    payload = f"{config.temp_threshold},{config.hum_threshold}"
    mqtt_client.publish("plant/control/config", payload)
    
    return {
        "status": "success", 
        "message": "Đã cập nhật ngưỡng cấu hình",
        "new_config": config.dict()
    }

# 5. API TEST NHANH DISCORD
@app.post("/api/test-discord")
def test_discord():
    send_discord_alert("**Test Bot:** Hệ thống Backend Cloud đã kết nối và gửi tin nhắn thành công lên Discord!")
    return {"status": "success", "message": "Đã gửi test lên Discord!"}