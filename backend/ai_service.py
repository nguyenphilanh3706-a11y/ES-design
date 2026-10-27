import json
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

log = logging.getLogger("plant-ai")

BASE = Path(__file__).resolve().parent / "models"


class PlantAI:
    def __init__(self):
        self.lock = threading.Lock()
        self.model = None
        self.config = None
        self.cache = {}
        self.load_retry_at = 0.0

    def load(self):
        if self.model is not None:
            return

        # Nếu tải lỗi, không thử lại liên tục mỗi lần web gọi.
        if time.monotonic() < self.load_retry_at:
            raise RuntimeError("Đang chờ tải lại mô hình")

        self.load_retry_at = time.monotonic() + 60

        import tensorflow as tf

        config = json.loads(
            (BASE / "inference_config.json").read_text(
                encoding="utf-8"
            )
        )

        expected = ["TEMP", "HUM", "VPD", "LUX", "SOIL_PCT"]

        if (
            config["features"] != expected
            or config["lookback_steps"] != 60
            or config["sample_seconds"] != 30
            or config["forecast_minutes"] != 60
        ):
            raise ValueError("Cấu hình mô hình không khớp")

        model = tf.keras.models.load_model(
            BASE / "best_lstm_csv_huber.keras",
            compile=False,
        )

        if tuple(model.input_shape[1:]) != (60, 5):
            raise ValueError("Mô hình phải nhận 60 mẫu × 5 thông số")

        self.config = config
        self.model = model
        log.info("Đã tải LSTM Huber cho backend")

    @staticmethod
    def empty(message):
        return {
            "aiReady": False,
            "predictedSoil": None,
            "predictedLight": None,
            "predictionHorizonMinutes": 60,
            "aiMessage": message,
            "soilPredictionSource": "lstm_csv_huber",
            "lightPredictionSource": "persistence",
            "predictionInputAt": None,
            "predictionTargetAt": None,
        }

    def enrich(self, payload, db):
        result = dict(payload)

        # Luôn thay dự báo từ publisher bằng trạng thái AI backend.
        result.update(self.empty("Đang chuẩn bị dữ liệu AI"))

        if not payload.get("online"):
            result["aiMessage"] = "Thiết bị chưa trực tuyến"
            return result

        device_id = payload["device_id"]

        with self.lock:
            # Không trả dự đoán cũ khi thiết bị đang tưới hoặc lỗi.
            if (
                payload.get("pump") == "ON"
                or payload.get("fsm") in ("PUMPING", "COOLDOWN", "FAULT")
                or payload.get("fault")
            ):
                self.cache.pop(device_id, None)
                result["aiMessage"] = "Tạm dừng dự đoán khi tưới hoặc lỗi"
                return result

            now = time.monotonic()
            source = bool(payload["simulated"])
            cached = self.cache.get(device_id)

            if (
                cached
                and now - cached["created"] < 30
                and cached["simulated"] == source
            ):
                result.update(cached["value"])
                return result

            try:
                self.load()
                prediction = self.calculate(payload, db)
            except Exception:
                log.exception("Không tính được dự đoán AI")
                prediction = self.empty(
                    "AI tạm thời chưa sẵn sàng; xem log backend"
                )

            # Giới hạn số thiết bị lưu trong bộ nhớ.
            if len(self.cache) >= 100 and device_id not in self.cache:
                self.cache.pop(next(iter(self.cache)))

            self.cache[device_id] = {
                "created": time.monotonic(),
                "simulated": source,
                "value": prediction,
            }

            result.update(prediction)
            return result

    def calculate(self, payload, db):
        rows = db(
            """
            SELECT payload
            FROM telemetry_v2
            WHERE device_id = %s
              AND received_at >= NOW() - INTERVAL '40 minutes'
            ORDER BY received_at DESC, id DESC
            LIMIT 5000
            """,
            (payload["device_id"],),
            fetch="all",
        )

        latest_time = datetime.fromisoformat(
            payload["sampled_at"]
        ).timestamp()

        # Chỉ dùng mẫu có cùng nguồn thật/mô phỏng.
        # Sau khi đổi nguồn hoặc tưới, bắt đầu một chuỗi mới.
        ordered = []
        for row in rows:
            item = row["payload"]
            timestamp = datetime.fromisoformat(
                item["sampled_at"]
            ).timestamp()

            if timestamp <= latest_time:
                ordered.append((timestamp, item))

        ordered.sort(key=lambda pair: pair[0])

        points = {}
        for timestamp, item in ordered:
            invalid = (
                item.get("simulated") != payload["simulated"]
                or item.get("pump") == "ON"
                or item.get("fsm") in (
                    "PUMPING", "COOLDOWN", "FAULT"
                )
                or item.get("fault")
            )

            if invalid:
                points.clear()
                continue

            values = [
                item["temperature"],
                item["humidity"],
                item["vpd"],
                item["light"],
                item["soilMoisture"],
            ]

            if not np.isfinite(values).all():
                points.clear()
                continue

            points[timestamp] = values

        if len(points) < 60:
            return self.empty(
                "Đang thu thập khoảng 30 phút dữ liệu liên tục"
            )

        times = np.asarray(sorted(points), dtype=np.float64)
        values = np.asarray(
            [points[t] for t in times],
            dtype=np.float32,
        )

        # 60 điểm cách nhau đúng 30 giây.
        # Nội suy từ telemetry gửi thường xuyên hơn.
        grid = latest_time - np.arange(59, -1, -1) * 30.0

        if times[0] > grid[0] or times[-1] < grid[-1]:
            return self.empty(
                "Chưa đủ khoảng 30 phút dữ liệu liên tục"
            )

        left = max(0, np.searchsorted(times, grid[0]) - 1)
        relevant_times = times[left:]

        # Không nội suy qua khoảng mất dữ liệu dài.
        if np.any(np.diff(relevant_times) > 45):
            return self.empty(
                "Dữ liệu bị gián đoạn; đang chờ chuỗi mới"
            )

        history = np.column_stack([
            np.interp(grid, times, values[:, column])
            for column in range(5)
        ]).astype(np.float32)
                # Kiểm tra toàn bộ 60 mẫu trước khi chạy LSTM.
        train_min = np.asarray(
            self.config["train_min"], dtype=np.float32
        )
        train_max = np.asarray(
            self.config["train_max"], dtype=np.float32
        )

        outside = np.any(
            (history < train_min - 1e-6)
            | (history > train_max + 1e-6),
            axis=0,
        )

        if np.any(outside):
            labels = [
                "nhiệt độ",
                "độ ẩm không khí",
                "VPD",
                "ánh sáng",
                "độ ẩm đất",
            ]

            affected = [
                labels[i]
                for i in range(len(labels))
                if outside[i]
            ]

            return self.empty(
                "Dữ liệu ngoài phạm vi huấn luyện: "
                + ", ".join(affected)
                + ". Tạm không đưa ra dự đoán."
            )
        scale = np.asarray(
            self.config["input_scale"], dtype=np.float32
        )
        offset = np.asarray(
            self.config["input_offset"], dtype=np.float32
        )

        normalized = history * scale + offset

        outputs = self.model(
            normalized[np.newaxis, ...],
            training=False,
        )

        delta = float(
            outputs[self.config["soil_output"]]
            .numpy().reshape(-1)[0]
        )

        predicted_soil = (
            float(history[-1, 4])
            + delta * self.config["soil_delta_unit"]
        )

        # Không âm thầm kẹp một dự đoán không hợp lệ.
        if (
            not np.isfinite(predicted_soil)
            or not 0 <= predicted_soil <= 100
        ):
            return self.empty(
                "Dự đoán độ ẩm ngoài giới hạn; tạm không sử dụng"
            )

        input_time = datetime.fromisoformat(payload["sampled_at"])

        return {
            "aiReady": True,
            "predictedSoil": round(predicted_soil, 2),

            # Baseline, không phải đầu ra LSTM ánh sáng.
            "predictedLight": round(float(history[-1, 3]), 1),

            "predictionHorizonMinutes": 60,
            "soilPredictionSource": "lstm_csv_huber",
            "lightPredictionSource": "persistence",
            "predictionInputAt": input_time.isoformat(),
            "predictionTargetAt": (
                input_time + timedelta(minutes=60)
            ).isoformat(),
            "aiMessage": (
                "Độ ẩm: LSTM thử nghiệm. "
                "Ánh sáng: giữ nguyên giá trị tại thời điểm dự báo."
            ),
        }


plant_ai = PlantAI()