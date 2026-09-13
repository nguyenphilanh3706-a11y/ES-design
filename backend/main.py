import threading
import paho.mqtt.client as mqtt
import psycopg2
from fastapi import FastAPI

app = FastAPI()

# Cấu hình kết nối TimescaleDB (PostgreSQL)
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
  # Chuyển bảng thành Hypertable của TimescaleDB
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

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO sensor_data (time, device_id, temperature, humidity)"
        " VALUES (NOW(), %s, %s, %s)",
        (device_id, temp, hum),
    )
    conn.commit()
    cur.close()
    conn.close()
    print("-> Đã lưu vào TimescaleDB thành công!")
  except Exception as e:
    print(f"Lỗi xử lý dữ liệu: {e}")


# Cấu hình MQTT Subscriber chạy ngầm (phải thẳng hàng với các hàm khác ở ngoài)
def start_mqtt():
  client = mqtt.Client()
  client.on_message = on_message
  client.connect("localhost", 1883, 60)
  client.subscribe("sensor/data")
  client.loop_start()


# Khởi chạy luồng MQTT ngầm khi bật FastAPI
@app.on_event("startup")
def startup_event():
  threading.Thread(target=start_mqtt, daemon=True).start()
  print("MQTT Client background service started.")


@app.get("/")
def read_root():
  return {"message": "IoT Backend Server is running!"}

@app.get("/api/data")
def get_sensor_data(limit: int = 10):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Truy vấn lấy dữ liệu mới nhất, giới hạn số lượng bằng tham số limit
        cur.execute(
            "SELECT time, device_id, temperature, humidity FROM sensor_data ORDER BY time DESC LIMIT %s",
            (limit,)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        # Định dạng dữ liệu trả về dạng JSON
        result = []
        for row in rows:
            result.append({
                "time": row[0],
                "device_id": row[1],
                "temperature": row[2],
                "humidity": row[3]
            })
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}