import threading
import paho.mqtt.client as mqtt
import psycopg2
import requests  # <-- THÊM THƯ VIỆN NÀY ĐỂ GỌI DISCORD
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# Khai báo MQTT Client ở mức toàn cục để các API có thể dùng nó gửi lệnh (Publish)
mqtt_client = mqtt.Client()

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
# CẤU HÌNH DATABASE
# ==========================================
DB_HOST = "127.0.0.1"
DB_PORT = "5432"
DB_NAME = "nlant_iot"
DB_USER = "postgres"
DB_PASSWORD = "password123"

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
    )

# Khởi tạo bảng lưu dữ liệu cảm biến nếu chưa có
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sensor_data (
            time TIMESTAMPTZ NOT NULL,
            device_id VARCHAR(50),
            temperature FLOAT,
            humidity FLOAT
        );
    """)
    cur.execute("""
        SELECT create_hypertable('sensor_data', 'time', if_not_exists => TRUE);
    """)
    conn.commit()
    cur.close()
    conn.close()

init_db()

# Xử lý khi nhận được message từ MQTT Broker
def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8")
    print(f"Nhận dữ liệu từ topic {msg.topic}: {payload}")
    try:
        parts = payload.split(",")
        device_id = parts[0]
        temp = float(parts[1])
        hum = float(parts[2])

        # 1. Lưu vào Database
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO sensor_data (time, device_id, temperature, humidity) VALUES (NOW(), %s, %s, %s)",
            (device_id, temp, hum),
        )
        conn.commit()
        cur.close()
        conn.close()
        print("-> Đã lưu vào TimescaleDB thành công!")

        # 2. KIỂM TRA ĐỘ ẨM VÀ BẮN CẢNH BÁO DISCORD
        if hum < 20.0:
            alert_msg = f"🚨 **CẢNH BÁO IoT:** Độ ẩm đất tại trạm `{device_id}` đang ở mức nguy hiểm ({hum}%). Hệ thống AI đề xuất bật máy bơm ngay!"
            send_discord_alert(alert_msg)

    except Exception as e:
        print(f"Lỗi xử lý dữ liệu: {e}")

# Cấu hình MQTT Subscriber chạy ngầm
def start_mqtt():
    mqtt_client.on_message = on_message
    mqtt_client.connect("localhost", 1883, 60)
    mqtt_client.subscribe("sensor/data")
    mqtt_client.loop_start()

@app.on_event("startup")
def startup_event():
    threading.Thread(target=start_mqtt, daemon=True).start()
    print("MQTT Client background service started.")

# ==========================================
# KHAI BÁO MODEL DỮ LIỆU CHO API POST
# ==========================================
class PumpCommand(BaseModel):
    state: str  # Gửi "ON" hoặc "OFF"

class SystemConfig(BaseModel):
    temp_threshold: float
    hum_threshold: float

# ==========================================
# CÁC ENDPOINT API THEO CHECKLIST ĐỒ ÁN
# ==========================================

@app.get("/")
def read_root():
    return {"message": "IoT Backend Server is running!"}

# 1. Lấy thông số môi trường mới nhất
@app.get("/api/telemetry/latest")
def get_latest_telemetry():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT time, device_id, temperature, humidity FROM sensor_data ORDER BY time DESC LIMIT 1"
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row:
            return {
                "status": "success", 
                "data": {"time": row[0], "device_id": row[1], "temperature": row[2], "humidity": row[3]}
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
        # Lấy dữ liệu trong vòng N giờ qua
        query = f"SELECT time, device_id, temperature, humidity FROM sensor_data WHERE time >= NOW() - INTERVAL '{hours} hours' ORDER BY time DESC"
        cur.execute(query)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        result = [{"time": r[0], "device_id": r[1], "temperature": r[2], "humidity": r[3]} for r in rows]
        return {"status": "success", "count": len(result), "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# 3. Gửi lệnh điều khiển bơm
@app.post("/api/control/pump")
def control_pump(cmd: PumpCommand):
    if cmd.state not in ["ON", "OFF"]:
        return {"status": "error", "message": "Lệnh không hợp lệ. Chỉ chấp nhận 'ON' hoặc 'OFF'"}
    
    # Bắn tin nhắn xuống MQTT Broker với topic cmd/pump
    mqtt_client.publish("cmd/pump", cmd.state)
    return {"status": "success", "message": f"Đã gửi lệnh {cmd.state} tới máy bơm!"}

# 4. Cấu hình hệ thống
@app.post("/api/config")
def update_config(config: SystemConfig):
    # Gửi cấu hình xuống ESP32 qua MQTT
    payload = f"{config.temp_threshold},{config.hum_threshold}"
    mqtt_client.publish("cmd/config", payload)
    
    return {
        "status": "success", 
        "message": "Đã cập nhật ngưỡng cấu hình",
        "new_config": config.dict()
    }

# 5. API ĐỂ BẠN TEST NHANH DISCORD TRÊN TRÌNH DUYỆT
@app.post("/api/test-discord")
def test_discord():
    send_discord_alert("**Test Bot:** Nếu bạn thấy tin nhắn này, hệ thống Backend đã gửi thành công dữ liệu lên Discord!")
    return {"status": "success", "message": "Đã gửi test lên Discord, bạn mở app lên xem nhé!"}