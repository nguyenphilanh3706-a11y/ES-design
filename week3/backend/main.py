"""
Plant AIoT Backend — AI chạy trên ESP32 Week 2.

Chức năng:
- Nhận dữ liệu cảm biến, dự đoán AI và ACK qua MQTT.
- Lưu dữ liệu vào PostgreSQL.
- Trả dữ liệu cho frontend.
- Gửi lệnh AUTO/MANUAL và bật/tắt bơm.
- Không chạy TensorFlow hoặc LSTM trên backend.

Các file cần dùng:
BACKEND/
    main.py
    requirements.txt
    .env
"""

import json
import logging
import os
import secrets
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

import paho.mqtt.client as mqtt
import psycopg2
import requests
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from psycopg2.extras import Json, RealDictCursor
from pydantic import BaseModel, ConfigDict, Field, ValidationError


# =========================================================
# 1. CẤU HÌNH
# =========================================================

ENV_PATH = Path(__file__).with_name(".env")
load_dotenv(ENV_PATH, override=False)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("plant-backend")

APP_VERSION = "2.3.0"
AI_SOURCE = "esp32_week2"
PREDICTION_MAX_AGE_SECONDS = 90


def required(name: str) -> str:
    value = os.getenv(name, "").strip()

    if not value:
        raise RuntimeError(f"Thiếu cấu hình {name}")

    return value


def utcnow():
    return datetime.now(timezone.utc)


DATABASE_URL = required("DATABASE_URL")

MQTT_HOST = required("MQTT_HOST")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
MQTT_USERNAME = required("MQTT_USERNAME")
MQTT_PASSWORD = required("MQTT_PASSWORD")
MQTT_TLS = os.getenv("MQTT_TLS", "true").lower() == "true"

PREFIX = os.getenv("MQTT_PREFIX", "plant/v2").strip().strip("/")
DEVICE_ID = os.getenv("DEVICE_ID", "esp32_v1").strip()

CONTROL_KEY = required("CONTROL_API_KEY")
DISCORD_URL = os.getenv("DISCORD_WEBHOOK_URL", "").strip()

DEVICE_TIMEOUT = max(
    5,
    int(os.getenv("DEVICE_TIMEOUT_SECONDS", "20")),
)

# Firmware đã gửi chấp nhận lệnh có thời hạn tối đa 60 giây.
COMMAND_TTL = min(
    60,
    max(5, int(os.getenv("COMMAND_TTL_SECONDS", "15"))),
)

ORIGINS = [
    item.strip().rstrip("/")
    for item in os.getenv("CORS_ORIGINS", "*").split(",")
    if item.strip()
]

TELEMETRY_FILTER = f"{PREFIX}/+/telemetry"
ACK_FILTER = f"{PREFIX}/+/ack"

mqtt_ready = threading.Event()
stopping = threading.Event()

alert_lock = threading.Lock()
last_alert = None


# =========================================================
# 2. DATABASE
# =========================================================

def db(sql, params=(), fetch=None):
    connection = psycopg2.connect(
        DATABASE_URL,
        connect_timeout=5,
        options="-c statement_timeout=5000",
    )

    try:
        with connection:
            with connection.cursor(
                cursor_factory=RealDictCursor
            ) as cursor:
                cursor.execute(sql, params)

                if fetch == "one":
                    row = cursor.fetchone()
                    return dict(row) if row is not None else None

                if fetch == "all":
                    return [dict(row) for row in cursor.fetchall()]

                return cursor.rowcount
    finally:
        connection.close()


def init_db():
    db("""
        CREATE TABLE IF NOT EXISTS telemetry_v2 (
            id BIGSERIAL PRIMARY KEY,
            sample_id UUID NOT NULL UNIQUE,
            device_id VARCHAR(64) NOT NULL,
            received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            payload JSONB NOT NULL
        );

        CREATE INDEX IF NOT EXISTS telemetry_v2_device_time_idx
        ON telemetry_v2 (
            device_id,
            received_at DESC,
            id DESC
        );

        CREATE TABLE IF NOT EXISTS commands_v2 (
            command_id UUID PRIMARY KEY,
            device_id VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            payload JSONB NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'pending',
            message TEXT,
            acknowledged_at TIMESTAMPTZ,
            ack JSONB
        );

        CREATE INDEX IF NOT EXISTS commands_v2_device_time_idx
        ON commands_v2 (
            device_id,
            created_at DESC
        );
    """)

    log.info("Database đã sẵn sàng")


def log_database_error(context, error):
    log.error(
        "%s | loại=%s | SQLSTATE=%s",
        context,
        type(error).__name__,
        getattr(error, "pgcode", None) or "không có",
    )


# =========================================================
# 3. ĐỊNH DẠNG DỮ LIỆU
# =========================================================

class Telemetry(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        allow_inf_nan=False,
    )

    sample_id: UUID

    device_id: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )

    sampled_at: datetime

    temperature: float = Field(ge=-50, le=100)
    humidity: float = Field(ge=0, le=100)
    vpd: float = Field(ge=0, le=20)
    light: float = Field(ge=0, le=200000)
    soilMoisture: float = Field(ge=0, le=100)

    # Kết quả AI do ESP32 gửi.
    predictedSoil: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    predictedLight: float | None = Field(
        default=None,
        ge=0,
        le=200000,
    )

    predictionHorizonMinutes: Literal[60] = 60
    aiReady: bool = Field(default=False, strict=True)

    aiMessage: str | None = Field(
        default=None,
        max_length=500,
    )

    soilPredictionSource: str | None = Field(
        default=None,
        max_length=64,
    )

    lightPredictionSource: str | None = Field(
        default=None,
        max_length=64,
    )

    predictionInputAt: datetime | None = None
    predictionTargetAt: datetime | None = None

    pump: Literal["ON", "OFF"]
    mode: Literal["AUTO", "MANUAL"]
    fsm: Literal["IDLE", "PUMPING", "COOLDOWN", "FAULT"]

    waterAvailable: bool = Field(strict=True)
    fault: str | None = Field(default=None, max_length=200)
    simulated: bool = Field(strict=True)


class Ack(BaseModel):
    model_config = ConfigDict(extra="ignore")

    command_id: UUID

    device_id: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )

    status: Literal["applied", "rejected", "completed"]
    message: str = Field(default="", max_length=300)

    pump: Literal["ON", "OFF"]
    mode: Literal["AUTO", "MANUAL"]
    simulated: bool = Field(strict=True)


class PumpRequest(BaseModel):
    device_id: str = Field(
        default=DEVICE_ID,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )

    state: Literal["ON", "OFF"]

    duration_ms: int = Field(
        default=2500,
        ge=100,
        le=5000,
        strict=True,
    )


class ModeRequest(BaseModel):
    device_id: str = Field(
        default=DEVICE_ID,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )

    mode: Literal["AUTO", "MANUAL"]


# =========================================================
# 4. XỬ LÝ KẾT QUẢ AI TỪ ESP32
# =========================================================

def parse_prediction_time(value):
    if not isinstance(value, str) or not value:
        return None

    try:
        parsed = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return None

    return parsed.astimezone(timezone.utc)


def clear_prediction(payload, message):
    payload.update({
        "aiReady": False,
        "predictedSoil": None,
        "predictedLight": None,
        "predictionInputAt": None,
        "predictionTargetAt": None,
        "aiMessage": message,
    })

    return payload


def normalize_kit_prediction(payload, sampled_at):
    """
    Kiểm tra thông tin dự đoán do kit gửi.

    Không chạy mô hình, không tự tạo dự đoán và không áp dụng
    scaler/phạm vi huấn luyện của mô hình Huber trước đây.
    """

    if payload.get("simulated") is not False:
        return clear_prediction(
            payload,
            "Đang nhận dữ liệu mô phỏng; "
            "chưa xác nhận dự đoán từ kit Week 2.",
        )

    sources_match = (
        payload.get("soilPredictionSource") == AI_SOURCE
        and payload.get("lightPredictionSource") == AI_SOURCE
    )

    if not sources_match:
        return clear_prediction(
            payload,
            "Bản tin chưa có nguồn dự đoán esp32_week2. "
            "Cần dùng firmware Week 2 có tích hợp MQTT đã gửi.",
        )

    if payload.get("fault") or payload.get("fsm") == "FAULT":
        return clear_prediction(
            payload,
            "Thiết bị đang báo lỗi. Tạm không hiển thị dự đoán.",
        )

    if payload.get("aiReady") is not True:
        return clear_prediction(
            payload,
            payload.get("aiMessage")
            or (
                "ESP32 chưa có kết quả AI; "
                "đang chờ kit thu thập dữ liệu và chạy mô hình."
            ),
        )

    soil = payload.get("predictedSoil")
    light = payload.get("predictedLight")

    valid_values = (
        type(soil) in (int, float)
        and type(light) in (int, float)
        and 0 <= soil <= 100
        and 0 <= light <= 200000
    )

    if not valid_values:
        return clear_prediction(
            payload,
            "Kết quả dự đoán từ ESP32 thiếu hoặc không hợp lệ.",
        )

    input_at = parse_prediction_time(
        payload.get("predictionInputAt")
    )

    target_at = parse_prediction_time(
        payload.get("predictionTargetAt")
    )

    if input_at is None or target_at is None:
        return clear_prediction(
            payload,
            "ESP32 chưa gửi đủ thời điểm đầu vào và dự đoán.",
        )

    # Đánh giá dự đoán tại thời điểm bản tin được tạo.
    # Nhờ vậy, API lịch sử vẫn giữ dự đoán hợp lệ trước đây.
    prediction_age = (
        sampled_at - input_at
    ).total_seconds()

    horizon_seconds = (
        target_at - input_at
    ).total_seconds()

    if not -10 <= prediction_age <= PREDICTION_MAX_AGE_SECONDS:
        return clear_prediction(
            payload,
            "Kết quả AI trên ESP32 đã cũ; chờ lần dự đoán mới.",
        )

    if (
        payload.get("predictionHorizonMinutes") != 60
        or abs(horizon_seconds - 3600) > 2
    ):
        return clear_prediction(
            payload,
            "Thời điểm dự đoán từ ESP32 không khớp mốc 60 phút.",
        )

    payload.update({
        "aiReady": True,
        "predictionInputAt": input_at.isoformat(),
        "predictionTargetAt": target_at.isoformat(),
        "aiMessage": "Dự đoán từ mô hình Week 2 chạy trên ESP32.",
    })

    return payload


# =========================================================
# 5. CẢNH BÁO DISCORD
# =========================================================

def send_discord(message):
    if not DISCORD_URL:
        return False

    try:
        response = requests.post(
            DISCORD_URL,
            json={"content": message},
            timeout=5,
        )
        response.raise_for_status()
        return True

    except requests.RequestException:
        log.warning("Không gửi được cảnh báo Discord")
        return False


def maybe_alert(sample):
    global last_alert

    if sample.simulated or not DISCORD_URL:
        return

    problems = []

    if not sample.waterAvailable:
        problems.append("bình hết nước")

    if sample.fault:
        problems.append(f"lỗi: {sample.fault}")

    if sample.soilMoisture < 30:
        problems.append(
            f"độ ẩm đất thấp: {sample.soilMoisture:.1f}%"
        )

    if not problems:
        return

    executor = getattr(app.state, "alert_executor", None)

    if executor is None:
        return

    with alert_lock:
        now = time.monotonic()

        if last_alert is not None and now - last_alert < 300:
            return

        last_alert = now

    executor.submit(
        send_discord,
        f"🌱 Thiết bị {sample.device_id}: "
        + "; ".join(problems),
    )


# =========================================================
# 6. MQTT
# =========================================================

mqtt_client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    client_id=f"plant-backend-{uuid4().hex[:10]}",
)

mqtt_client.username_pw_set(
    MQTT_USERNAME,
    MQTT_PASSWORD,
)

mqtt_client.reconnect_delay_set(
    min_delay=2,
    max_delay=30,
)

mqtt_client.max_queued_messages_set(100)

if MQTT_TLS:
    mqtt_client.tls_set()


def on_connect(client, userdata, flags, reason_code, properties):
    mqtt_ready.clear()

    if reason_code.is_failure:
        log.error("MQTT từ chối kết nối: %s", reason_code)
        return

    result, _ = client.subscribe([
        (TELEMETRY_FILTER, 1),
        (ACK_FILTER, 1),
    ])

    if result != mqtt.MQTT_ERR_SUCCESS:
        log.error(
            "Không gửi được yêu cầu đăng ký MQTT | mã=%s",
            result,
        )
        return

    log.info(
        "Đang đăng ký MQTT | telemetry=%s | ack=%s",
        TELEMETRY_FILTER,
        ACK_FILTER,
    )


def on_subscribe(client, userdata, mid, reason_codes, properties):
    if (
        len(reason_codes) == 2
        and all(not code.is_failure for code in reason_codes)
    ):
        mqtt_ready.set()
        log.info("MQTT đã kết nối và đăng ký đủ hai topic")
    else:
        mqtt_ready.clear()
        log.error(
            "MQTT chưa đăng ký đủ topic | kết quả=%s",
            [str(code) for code in reason_codes],
        )


def on_disconnect(client, userdata, flags, reason_code, properties):
    mqtt_ready.clear()

    if stopping.is_set():
        log.info("MQTT đã ngắt khi dừng backend")
        return

    log.warning(
        "MQTT mất kết nối | lý do=%s | broker gửi ngắt=%s",
        reason_code,
        flags.is_disconnect_packet_from_server,
    )


def on_connect_fail(client, userdata):
    mqtt_ready.clear()

    log.warning(
        "Không mở được kết nối MQTT | host=%s | port=%s",
        MQTT_HOST,
        MQTT_PORT,
    )


def store_ack(device_id, raw):
    ack = Ack.model_validate(raw)

    if ack.device_id != device_id:
        raise ValueError("ACK có device_id không khớp topic")

    updated = db(
        """
        UPDATE commands_v2
        SET status = %s,
            message = %s,
            acknowledged_at = NOW(),
            ack = %s
        WHERE command_id = %s
          AND device_id = %s
          AND (
              (
                  status = 'pending'
                  AND expires_at >= NOW()
              )
              OR (
                  status = 'applied'
                  AND %s = 'completed'
              )
          )
        """,
        (
            ack.status,
            ack.message,
            Json(ack.model_dump(mode="json")),
            str(ack.command_id),
            device_id,
            ack.status,
        ),
    )

    if updated:
        log.info(
            "ĐÃ LƯU ACK | command=%s | status=%s",
            ack.command_id,
            ack.status,
        )
    else:
        log.info(
            "Bỏ qua ACK trùng, muộn hoặc không khớp lệnh "
            "| command=%s",
            ack.command_id,
        )


def on_message(client, userdata, msg):
    log.info(
        "NHẬN MQTT | topic=%s | bytes=%d | retained=%s",
        msg.topic,
        len(msg.payload),
        msg.retain,
    )

    try:
        if msg.retain:
            log.warning(
                "Bỏ qua bản tin retained: %s",
                msg.topic,
            )
            return

        if len(msg.payload) > 16384:
            log.warning("Bỏ qua bản tin quá lớn")
            return

        topic_prefix = PREFIX + "/"

        if not msg.topic.startswith(topic_prefix):
            log.warning(
                "Topic không khớp prefix: %s",
                msg.topic,
            )
            return

        parts = msg.topic[len(topic_prefix):].split("/")

        if len(parts) != 2:
            log.warning(
                "Cấu trúc topic không hợp lệ: %s",
                msg.topic,
            )
            return

        device_id, kind = parts
        raw = json.loads(msg.payload.decode("utf-8"))

        if kind == "ack":
            store_ack(device_id, raw)
            return

        if kind != "telemetry":
            log.warning(
                "Loại bản tin không được hỗ trợ: %s",
                kind,
            )
            return

        sample = Telemetry.model_validate(raw)

        if sample.device_id != device_id:
            raise ValueError(
                "device_id trong dữ liệu không khớp topic"
            )

        if sample.sampled_at.tzinfo is None:
            raise ValueError(
                "sampled_at phải có múi giờ"
            )

        age = (
            utcnow() - sample.sampled_at
        ).total_seconds()

        if age < -10 or age > DEVICE_TIMEOUT:
            log.warning(
                "Bỏ qua dữ liệu lệch thời gian "
                "| age=%.1fs | giới hạn=%ss",
                age,
                DEVICE_TIMEOUT,
            )
            return

        if sample.pump == "ON" and (
            not sample.waterAvailable or sample.fault
        ):
            log.warning(
                "Thiết bị báo bơm ON khi hết nước hoặc đang lỗi"
            )

        # Lưu bản tin đã kiểm tra định dạng, bao gồm metadata AI.
        # Không gọi TensorFlow hoặc ai_service.
        inserted = db(
            """
            INSERT INTO telemetry_v2 (
                sample_id,
                device_id,
                payload
            )
            VALUES (%s, %s, %s)
            ON CONFLICT (sample_id) DO NOTHING
            RETURNING id
            """,
            (
                str(sample.sample_id),
                sample.device_id,
                Json(sample.model_dump(mode="json")),
            ),
            fetch="one",
        )

        if inserted is None:
            log.info(
                "Bỏ qua mẫu trùng | sample=%s",
                sample.sample_id,
            )
            return

        log.info(
            "ĐÃ LƯU DATABASE | id=%s | device=%s "
            "| đất=%.1f%% | kit_ai_ready=%s",
            inserted["id"],
            sample.device_id,
            sample.soilMoisture,
            sample.aiReady,
        )

        maybe_alert(sample)

    except ValidationError as error:
        details = [
            {
                "field": ".".join(
                    str(part) for part in item["loc"]
                ),
                "type": item["type"],
                "message": item["msg"],
            }
            for item in error.errors(
                include_input=False,
                include_url=False,
            )
        ]

        log.warning(
            "Dữ liệu không đúng định dạng: %s",
            details,
        )

    except UnicodeError:
        log.warning("Bản tin không phải chuỗi UTF-8 hợp lệ")

    except json.JSONDecodeError:
        log.warning("Bản tin không phải JSON hợp lệ")

    except ValueError as error:
        log.warning("Bỏ qua dữ liệu: %s", error)

    except psycopg2.Error as error:
        log_database_error(
            "Không lưu được bản tin vào database",
            error,
        )

    except Exception as error:
        log.error(
            "Lỗi xử lý bản tin MQTT | loại=%s",
            type(error).__name__,
        )


mqtt_client.on_connect = on_connect
mqtt_client.on_subscribe = on_subscribe
mqtt_client.on_disconnect = on_disconnect
mqtt_client.on_connect_fail = on_connect_fail
mqtt_client.on_message = on_message


# =========================================================
# 7. KHỞI ĐỘNG / DỪNG BACKEND
# =========================================================

@asynccontextmanager
async def lifespan(app):
    stopping.clear()
    mqtt_ready.clear()

    log.info(
        "File backend: %s",
        Path(__file__).resolve(),
    )

    log.info(
        "BACKEND | version=%s | host=%s | port=%s "
        "| prefix=%s | device=%s | ai=ESP32 Week 2",
        APP_VERSION,
        MQTT_HOST,
        MQTT_PORT,
        PREFIX,
        DEVICE_ID,
    )

    init_db()

    executor = ThreadPoolExecutor(max_workers=1)
    app.state.alert_executor = executor
    loop_started = False

    try:
        mqtt_client.connect_async(
            MQTT_HOST,
            MQTT_PORT,
            keepalive=30,
        )

        result = mqtt_client.loop_start()

        if result != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(
                f"Không khởi động được MQTT loop: {result}"
            )

        loop_started = True
        yield

    finally:
        stopping.set()
        mqtt_ready.clear()

        if loop_started:
            mqtt_client.disconnect()
            mqtt_client.loop_stop()

        executor.shutdown(
            wait=True,
            cancel_futures=True,
        )


app = FastAPI(
    title="Plant AIoT Backend — ESP32 Week 2",
    version=APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
)


@app.exception_handler(psycopg2.Error)
async def database_error(request, error):
    log_database_error(
        "Database không khả dụng",
        error,
    )

    return JSONResponse(
        status_code=503,
        content={
            "status": "error",
            "message": "Database tạm thời không khả dụng",
        },
    )


# =========================================================
# 8. XÁC THỰC VÀ CHUYỂN DỮ LIỆU CHO WEB
# =========================================================

def authorize(
    x_api_key: str | None = Header(default=None),
):
    if not x_api_key or not secrets.compare_digest(
        x_api_key.encode("utf-8"),
        CONTROL_KEY.encode("utf-8"),
    ):
        raise HTTPException(
            status_code=401,
            detail="Thiếu hoặc sai X-API-Key",
        )


def latest_row(device_id):
    return db(
        """
        SELECT id, received_at, payload
        FROM telemetry_v2
        WHERE device_id = %s
        ORDER BY received_at DESC, id DESC
        LIMIT 1
        """,
        (device_id,),
        fetch="one",
    )


def serialize(row):
    payload = dict(row["payload"])

    sampled_at = datetime.fromisoformat(
        payload["sampled_at"].replace("Z", "+00:00")
    )

    age = max(
        0.0,
        (utcnow() - sampled_at).total_seconds(),
    )

    payload.update({
        "time": payload["sampled_at"],
        "receivedAt": row["received_at"].isoformat(),
        "dataAgeSeconds": round(age, 1),
        "online": age <= DEVICE_TIMEOUT,
        "aiExecution": "esp32",
    })

    return normalize_kit_prediction(
        payload,
        sampled_at,
    )


@app.get("/")
def root():
    return {
        "status": "success",
        "message": (
            f"Plant AIoT Backend {APP_VERSION} — ESP32 Week 2"
        ),
        "mqttConnected": mqtt_ready.is_set(),
        "aiExecution": "esp32",
    }


@app.get("/health")
def health():
    result = db(
        "SELECT 1 AS ok",
        fetch="one",
    )

    return {
        "status": "ok",
        "databaseConnected": (
            result is not None and result["ok"] == 1
        ),
        "mqttConnected": mqtt_ready.is_set(),
        "aiExecution": "esp32",
    }


@app.get("/api/telemetry/latest")
def latest(
    device_id: str = Query(
        default=DEVICE_ID,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    ),
):
    row = latest_row(device_id)
    payload = serialize(row) if row is not None else None

    if payload is not None:
        if not payload["online"]:
            clear_prediction(
                payload,
                "Thiết bị offline hoặc dữ liệu đã cũ. "
                "Đang chờ bản tin mới từ ESP32.",
            )

        elif not mqtt_ready.is_set():
            clear_prediction(
                payload,
                "Backend đang mất kết nối MQTT. "
                "Tạm không hiển thị dự đoán trực tiếp.",
            )

        elif payload.get("aiReady"):
            # API latest kiểm tra thêm tuổi dự đoán ở hiện tại.
            input_at = parse_prediction_time(
                payload.get("predictionInputAt")
            )

            if input_at is None:
                clear_prediction(
                    payload,
                    "Chưa có thời điểm đầu vào dự đoán hợp lệ.",
                )
            else:
                age = (
                    utcnow() - input_at
                ).total_seconds()

                if not -10 <= age <= PREDICTION_MAX_AGE_SECONDS:
                    clear_prediction(
                        payload,
                        "Kết quả AI trên ESP32 đã cũ; "
                        "chờ lần dự đoán mới.",
                    )

    return {
        "status": "success",
        "mqttConnected": mqtt_ready.is_set(),
        "data": payload,
    }


@app.get("/api/telemetry/history")
def history(
    device_id: str = Query(
        default=DEVICE_ID,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    ),
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=1000, ge=1, le=5000),
    before_id: int | None = Query(default=None, ge=1),
):
    rows = db(
        """
        SELECT id, received_at, payload
        FROM telemetry_v2
        WHERE device_id = %s
          AND received_at >= NOW() - (%s * INTERVAL '1 hour')
          AND (%s::bigint IS NULL OR id < %s::bigint)
        ORDER BY id DESC
        LIMIT %s
        """,
        (
            device_id,
            hours,
            before_id,
            before_id,
            limit + 1,
        ),
        fetch="all",
    )

    has_more = len(rows) > limit
    rows = rows[:limit]

    return {
        "status": "success",
        "count": len(rows),
        "hasMore": has_more,
        "nextBeforeId": rows[-1]["id"] if has_more else None,
        "data": [
            serialize(row)
            for row in reversed(rows)
        ],
    }


# =========================================================
# 9. GỬI LỆNH ĐIỀU KHIỂN
# =========================================================

def dispatch(device_id, kind, values):
    if not mqtt_ready.is_set():
        raise HTTPException(
            status_code=503,
            detail="Backend chưa kết nối MQTT",
        )

    row = latest_row(device_id)

    if row is None:
        raise HTTPException(
            status_code=409,
            detail="Chưa có dữ liệu thiết bị",
        )

    # Điều khiển dựa trên trạng thái thiết bị.
    # Không yêu cầu AI phải sẵn sàng.
    telemetry = serialize(row)

    if not telemetry["online"]:
        raise HTTPException(
            status_code=409,
            detail="Thiết bị offline hoặc dữ liệu đã cũ",
        )

    if kind == "pump" and values["state"] == "ON":
        if telemetry["mode"] != "MANUAL":
            raise HTTPException(
                status_code=409,
                detail="Chuyển sang MANUAL trước khi tưới",
            )

        if (
            not telemetry["waterAvailable"]
            or telemetry.get("fault")
        ):
            raise HTTPException(
                status_code=409,
                detail="Bình hết nước hoặc thiết bị đang lỗi",
            )

        if telemetry["soilMoisture"] >= 60:
            raise HTTPException(
                status_code=409,
                detail="Đất đã đạt ngưỡng đủ ẩm",
            )

        if (
            telemetry["fsm"] != "IDLE"
            or telemetry["pump"] != "OFF"
        ):
            raise HTTPException(
                status_code=409,
                detail="Thiết bị chưa sẵn sàng cho lần tưới mới",
            )

    command_id = str(uuid4())
    now = utcnow()
    expires_at = now + timedelta(seconds=COMMAND_TTL)

    payload = {
        "command_id": command_id,
        "device_id": device_id,
        "type": kind,
        "issued_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        **values,
    }

    # Lưu trước khi gửi để ACK nhanh vẫn tìm được lệnh.
    db(
        """
        INSERT INTO commands_v2 (
            command_id,
            device_id,
            created_at,
            expires_at,
            payload,
            status
        )
        VALUES (%s, %s, %s, %s, %s, 'pending')
        """,
        (
            command_id,
            device_id,
            now,
            expires_at,
            Json(payload),
        ),
    )

    result = mqtt_client.publish(
        f"{PREFIX}/{device_id}/command",
        json.dumps(payload),
        qos=1,
        retain=False,
    )

    if result.rc != mqtt.MQTT_ERR_SUCCESS:
        db(
            """
            UPDATE commands_v2
            SET status = 'publish_failed',
                message = 'Không gửi được lệnh MQTT'
            WHERE command_id = %s
              AND status = 'pending'
            """,
            (command_id,),
        )

        raise HTTPException(
            status_code=503,
            detail="Không gửi được lệnh MQTT",
        )

    log.info(
        "Đã xếp hàng gửi lệnh | command=%s "
        "| device=%s | type=%s",
        command_id,
        device_id,
        kind,
    )

    return {
        "status": "accepted",
        "command_id": command_id,
        "commandStatus": "pending",
        "simulated": telemetry["simulated"],
        "message": "Đang chờ thiết bị xác nhận",
    }


@app.post(
    "/api/control/pump",
    status_code=202,
    dependencies=[Depends(authorize)],
)
def control_pump(command: PumpRequest):
    return dispatch(
        command.device_id,
        "pump",
        {
            "state": command.state,
            "duration_ms": command.duration_ms,
        },
    )


@app.post(
    "/api/control/mode",
    status_code=202,
    dependencies=[Depends(authorize)],
)
def control_mode(command: ModeRequest):
    return dispatch(
        command.device_id,
        "mode",
        {
            "mode": command.mode,
        },
    )


@app.get("/api/commands/{command_id}")
def command_status(command_id: UUID):
    row = db(
        """
        SELECT
            command_id,
            device_id,
            created_at,
            expires_at,
            status,
            message,
            acknowledged_at,
            ack
        FROM commands_v2
        WHERE command_id = %s
        """,
        (str(command_id),),
        fetch="one",
    )

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy lệnh",
        )

    if (
        row["status"] == "pending"
        and row["expires_at"] < utcnow()
    ):
        row["status"] = "timeout"
        row["message"] = (
            "Chưa nhận được xác nhận trong thời hạn; "
            "không thể kết luận thiết bị đã thực hiện hay chưa"
        )

    return {
        "status": "success",
        "data": row,
    }


# =========================================================
# 10. KIỂM TRA KẾT NỐI DISCORD
# =========================================================

@app.post(
    "/api/test-discord",
    dependencies=[Depends(authorize)],
)
def test_discord():
    if not DISCORD_URL:
        raise HTTPException(
            status_code=503,
            detail="Chưa cấu hình Discord webhook",
        )

    success = send_discord(
        "🌱 Kiểm tra kết nối từ backend AIoT."
    )

    if not success:
        raise HTTPException(
            status_code=502,
            detail="Gửi Discord không thành công",
        )

    return {
        "status": "success",
        "message": "Đã gửi Discord",
    }