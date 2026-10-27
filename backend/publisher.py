"""
Thiết bị giả lập cho backend AIoT.

- Gửi dữ liệu mỗi 2 giây khi MQTT sẵn sàng.
- Client ID riêng cho mỗi lần chạy.
- Ghi rõ nguyên nhân mất kết nối.
- Nhận lệnh AUTO/MANUAL và tưới có thời lượng.
- Tự tắt bơm, có thời gian nghỉ.
- Chống thực hiện lặp lại cùng một lệnh.
- Không điều khiển phần cứng và không chạy LSTM thật.
"""

import json
import math
import os
import queue
import random
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import paho.mqtt.client as mqtt
from dotenv import load_dotenv


# =========================================================
# 1. ĐỌC CẤU HÌNH
# =========================================================

load_dotenv(Path(__file__).with_name(".env"))

HOST = os.environ["MQTT_HOST"]
PORT = int(os.getenv("MQTT_PORT", "8883"))
USERNAME = os.environ["MQTT_USERNAME"]
PASSWORD = os.environ["MQTT_PASSWORD"]
TLS = os.getenv("MQTT_TLS", "true").lower() == "true"

PREFIX = os.getenv("MQTT_PREFIX", "plant/v2").strip("/")
DEVICE_ID = os.getenv("DEVICE_ID", "esp32_v1")

TELEMETRY_TOPIC = f"{PREFIX}/{DEVICE_ID}/telemetry"
COMMAND_TOPIC = f"{PREFIX}/{DEVICE_ID}/command"
ACK_TOPIC = f"{PREFIX}/{DEVICE_ID}/ack"

# Client ID kết nối khác DEVICE_ID của dữ liệu.
# DEVICE_ID giữ nguyên để backend tìm đúng thiết bị.
CLIENT_ID = f"plant-simulator-{DEVICE_ID}-{uuid4().hex[:8]}"

commands = queue.Queue(maxsize=100)
processed = OrderedDict()

ready = threading.Event()
stopping = threading.Event()


# =========================================================
# 2. TRẠNG THÁI GIẢ LẬP
# =========================================================

mode = "AUTO"
pump = "OFF"
soil = 45.0
water_available = True
fault = None

pump_until = 0.0
cooldown_until = 0.0
active_cooldown = 15.0
active_command = None


# =========================================================
# 3. MQTT
# =========================================================

client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    client_id=CLIENT_ID,
)

client.username_pw_set(USERNAME, PASSWORD)
client.reconnect_delay_set(min_delay=2, max_delay=30)
client.max_queued_messages_set(100)
client.max_inflight_messages_set(10)

if TLS:
    client.tls_set()


def utcnow():
    return datetime.now(timezone.utc)


def on_connect(client, userdata, flags, reason_code, properties):
    ready.clear()

    if reason_code.is_failure:
        print(
            f"[MQTT] Kết nối bị từ chối: {reason_code}",
            flush=True,
        )
        return

    result, _ = client.subscribe(COMMAND_TOPIC, qos=1)

    if result != mqtt.MQTT_ERR_SUCCESS:
        print(
            f"[MQTT] Không gửi được yêu cầu đăng ký topic: {result}",
            flush=True,
        )
        return

    print(
        f"[MQTT] Đã kết nối: {DEVICE_ID}. Đang đăng ký nhận lệnh...",
        flush=True,
    )


def on_subscribe(client, userdata, mid, reason_codes, properties):
    if reason_codes and all(
        not code.is_failure for code in reason_codes
    ):
        ready.set()
        print(
            "[MQTT] Đã đăng ký nhận lệnh. "
            "Bắt đầu gửi dữ liệu mỗi 2 giây.",
            flush=True,
        )
    else:
        ready.clear()
        print(
            f"[MQTT] Broker từ chối đăng ký topic: {reason_codes}",
            flush=True,
        )


def on_disconnect(client, userdata, flags, reason_code, properties):
    ready.clear()

    if stopping.is_set():
        print(
            "[MQTT] Đã ngắt kết nối theo yêu cầu dừng.",
            flush=True,
        )
        return

    print(
        f"[MQTT] Mất kết nối: {reason_code}; "
        f"broker gửi thông báo ngắt="
        f"{flags.is_disconnect_packet_from_server}. "
        "Chương trình sẽ tự thử kết nối lại.",
        flush=True,
    )


def on_connect_fail(client, userdata):
    ready.clear()
    print(
        "[MQTT] Không mở được kết nối. "
        "Kiểm tra mạng, host và cổng trong .env.",
        flush=True,
    )


def on_message(client, userdata, message):
    # Không thực hiện lệnh retained để tránh chạy lại lệnh cũ.
    if message.retain or len(message.payload) > 8192:
        return

    try:
        value = json.loads(message.payload.decode("utf-8"))

        if isinstance(value, dict):
            commands.put_nowait(value)

    except (ValueError, UnicodeError, queue.Full):
        print(
            "[GIẢ LẬP] Bỏ qua lệnh không hợp lệ hoặc hàng đợi đầy",
            flush=True,
        )


client.on_connect = on_connect
client.on_subscribe = on_subscribe
client.on_disconnect = on_disconnect
client.on_connect_fail = on_connect_fail
client.on_message = on_message


# =========================================================
# 4. XÁC NHẬN LỆNH VÀ ĐIỀU KHIỂN BƠM GIẢ LẬP
# =========================================================

def ack(command_id, status, message):
    payload = {
        "command_id": command_id,
        "device_id": DEVICE_ID,
        "status": status,
        "message": message,
        "pump": pump,
        "mode": mode,
        "simulated": True,
    }

    processed[command_id] = payload
    processed.move_to_end(command_id)

    while len(processed) > 500:
        processed.popitem(last=False)

    client.publish(
        ACK_TOPIC,
        json.dumps(payload),
        qos=1,
        retain=False,
    )


def stop_pump(message):
    global pump, pump_until, cooldown_until, active_command

    was_running = pump == "ON"
    previous_command = active_command

    pump = "OFF"
    pump_until = 0.0
    active_command = None

    if was_running:
        cooldown_until = time.monotonic() + active_cooldown

    if previous_command:
        ack(previous_command, "completed", message)


def handle(command):
    global mode, pump, pump_until, active_command, active_cooldown

    try:
        command_id = str(UUID(str(command.get("command_id"))))
    except (ValueError, TypeError, AttributeError):
        return

    if command.get("device_id") != DEVICE_ID:
        return

    if command_id in processed:
        # MQTT có thể chuyển lại một bản tin.
        # Gửi lại xác nhận nhưng không thực hiện lệnh lần nữa.
        client.publish(
            ACK_TOPIC,
            json.dumps(processed[command_id]),
            qos=1,
            retain=False,
        )
        return

    try:
        expires = datetime.fromisoformat(command["expires_at"])

        if expires.tzinfo is None:
            raise ValueError("Thiếu múi giờ")

    except (KeyError, TypeError, ValueError):
        ack(command_id, "rejected", "Thời hạn lệnh không hợp lệ")
        return

    if utcnow() > expires:
        ack(command_id, "rejected", "Lệnh đã hết hạn")
        return

    if command.get("type") == "mode":
        requested_mode = command.get("mode")

        if requested_mode not in ("AUTO", "MANUAL"):
            ack(command_id, "rejected", "Chế độ không hợp lệ")
            return

        if requested_mode != mode:
            stop_pump("Dừng tưới do đổi chế độ")
            mode = requested_mode

        ack(command_id, "applied", f"Đã chuyển sang {mode}")
        return

    if command.get("type") != "pump":
        ack(command_id, "rejected", "Loại lệnh không hỗ trợ")
        return

    if command.get("state") == "OFF":
        stop_pump("Đã dừng bởi lệnh OFF")
        ack(command_id, "applied", "Bơm đã tắt")
        return

    duration = command.get("duration_ms")

    if (
        command.get("state") != "ON"
        or type(duration) is not int
        or not 100 <= duration <= 5000
    ):
        ack(
            command_id,
            "rejected",
            "Lệnh hoặc thời lượng không hợp lệ",
        )
        return

    if mode != "MANUAL":
        ack(command_id, "rejected", "Cần chuyển sang MANUAL")
        return

    if fault or not water_available:
        ack(command_id, "rejected", "Đang lỗi hoặc hết nước")
        return

    if soil >= 60:
        ack(command_id, "rejected", "Đất đã đủ ẩm")
        return

    if pump == "ON" or time.monotonic() < cooldown_until:
        ack(
            command_id,
            "rejected",
            "Đang bơm hoặc đang chờ nước ngấm",
        )
        return

    active_command = command_id
    active_cooldown = 15.0
    pump = "ON"
    pump_until = time.monotonic() + duration / 1000.0

    ack(command_id, "applied", "Bơm giả lập đã bật")


# =========================================================
# 5. TẠO DỮ LIỆU GIẢ LẬP
# =========================================================

def environment():
    # Giờ UTC+7.
    hour = ((time.time() + 7 * 3600) % 86400) / 3600

    sun = (
        max(0.0, math.sin(math.pi * (hour - 6) / 12))
        if 6 <= hour <= 18
        else 0.0
    )

    temperature = 26 + 7 * sun + random.uniform(-0.2, 0.2)
    humidity = 80 - 20 * sun + random.uniform(-0.5, 0.5)
    light = max(
        0.0,
        65000 * sun + random.uniform(-200, 200),
    )

    saturation = 0.61078 * math.exp(
        17.27 * temperature / (temperature + 237.3)
    )
    vpd = saturation * (1 - humidity / 100)

    # Dự báo giả để thử giao diện, không phải kết quả LSTM.
    predicted_soil = max(0.0, soil - 3 - 4 * sun)
    predicted_light = min(150000.0, light * 1.05)

    return (
        temperature,
        humidity,
        vpd,
        light,
        predicted_soil,
        predicted_light,
    )


def publish_telemetry(values):
    temperature, humidity, vpd, light, pred_soil, pred_light = values
    now = time.monotonic()

    if fault or not water_available:
        fsm = "FAULT"
    elif pump == "ON":
        fsm = "PUMPING"
    elif now < cooldown_until:
        fsm = "COOLDOWN"
    else:
        fsm = "IDLE"

    payload = {
        "sample_id": str(uuid4()),
        "device_id": DEVICE_ID,
        "sampled_at": utcnow().isoformat(),
        "temperature": round(temperature, 2),
        "humidity": round(humidity, 2),
        "vpd": round(vpd, 3),
        "light": round(light, 1),
        "soilMoisture": round(soil, 2),
        "predictedSoil": round(pred_soil, 2),
        "predictedLight": round(pred_light, 1),
        "predictionHorizonMinutes": 60,
        "aiReady": True,
        "pump": pump,
        "mode": mode,
        "fsm": fsm,
        "waterAvailable": water_available,
        "fault": fault,
        "simulated": True,
    }

    result = client.publish(
        TELEMETRY_TOPIC,
        json.dumps(payload),
        qos=1,
        retain=False,
    )

    if result.rc != mqtt.MQTT_ERR_SUCCESS:
        print(
            f"[MQTT] Chưa gửi được mẫu dữ liệu, mã lỗi={result.rc}",
            flush=True,
        )
        return

    # Đã vào hàng đợi gửi, chưa chứng minh backend đã lưu.
    print(
        f"[GIẢ LẬP] Đã xếp hàng gửi | Đất={soil:.1f}% "
        f"Mode={mode} Pump={pump} FSM={fsm}",
        flush=True,
    )


# =========================================================
# 6. VÒNG LẶP CHÍNH
# =========================================================

def run():
    global soil, pump, pump_until, active_cooldown

    print(
        f"[MQTT] Client ID phiên này: {CLIENT_ID}",
        flush=True,
    )
    print(
        "[GIẢ LẬP] Không điều khiển phần cứng "
        "và không chạy LSTM thật.",
        flush=True,
    )
    print(
        "[GIẢ LẬP] Chương trình chạy liên tục. "
        "Chỉ nhấn Ctrl+C khi muốn dừng.",
        flush=True,
    )

    client.connect_async(HOST, PORT, keepalive=30)
    client.loop_start()

    previous = time.monotonic()
    last_publish = 0.0
    last_environment = 0.0
    values = environment()

    try:
        while True:
            now = time.monotonic()
            elapsed = min(now - previous, 1.0)
            previous = now

            if pump == "ON":
                soil = min(100.0, soil + 1.5 * elapsed)

                if (
                    now >= pump_until
                    or soil >= 60
                    or fault
                    or not water_available
                ):
                    stop_pump("Đã kết thúc tưới và tắt bơm")
            else:
                soil = max(0.0, soil - 0.015 * elapsed)

            # Xử lý lệnh trên cùng luồng với trạng thái bơm.
            for _ in range(20):
                try:
                    command = commands.get_nowait()
                except queue.Empty:
                    break

                handle(command)

            now = time.monotonic()

            if now - last_environment >= 2:
                last_environment = now
                values = environment()

            _, _, vpd, light, pred_soil, pred_light = values

            pulse_mode = vpd > 1.6 and light > 20000
            proactive = pred_light > 60000 and pred_soil < 45

            should_water = (
                soil < 30
                or proactive
                or (pulse_mode and soil < 60)
            )

            if (
                mode == "AUTO"
                and pump == "OFF"
                and now >= cooldown_until
                and water_available
                and not fault
                and soil < 60
                and should_water
            ):
                pulse = pulse_mode or proactive
                active_cooldown = 25.0 if pulse else 15.0
                pump_until = now + (1.5 if pulse else 3.5)
                pump = "ON"

            if (
                ready.is_set()
                and client.is_connected()
                and now - last_publish >= 5
            ):
                last_publish = now
                publish_telemetry(values)

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n[GIẢ LẬP] Đang dừng...", flush=True)

    finally:
        stopping.set()
        stop_pump("Bộ giả lập đã dừng")
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    run()