"""
AI Anomaly Detection & Smart Inference Service
Author: Nguyen Phi Lanh
Description: Lang nghe luong du lieu cam bien qua MQTT, phat hien bat thuong bang mo hinh AI
va day canh bao thoi gian thuc ve MQTT Broker / Backend Server.
"""

import json
import time
import numpy as np
import paho.mqtt.client as mqtt
from sklearn.ensemble import IsolationForest

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
TOPIC_TELEMETRY = "iot/device/telemetry"
TOPIC_AI_ALERT = "iot/ai/alert"

class SmartAnomalyDetector:
    def __init__(self):
        # Khoi tao va huan luyen mo hinh Isolation Forest voi du lieu moi truong binh thuong
        rng = np.random.RandomState(42)
        normal_temp = rng.normal(loc=28.0, scale=3.0, size=(500, 1))
        normal_hum = rng.normal(loc=65.0, scale=8.0, size=(500, 1))
        normal_aq = rng.normal(loc=110.0, scale=25.0, size=(500, 1))
        X_train = np.hstack([normal_temp, normal_hum, normal_aq])

        self.model = IsolationForest(contamination=0.05, random_state=42)
        self.model.fit(X_train)

    def predict(self, temperature: float, humidity: float, air_quality: float) -> dict:
        features = np.array([[temperature, humidity, air_quality]])
        pred = self.model.predict(features)[0]  # -1: Anomaly, 1: Normal
        score = float(self.model.decision_function(features)[0])

        is_anomaly = (pred == -1) or (temperature > 42.0) or (air_quality > 300)
        label = "NORMAL"
        message = "He thong hoat dong binh thuong."

        if is_anomaly:
            if temperature > 42.0 and air_quality > 250:
                label = "FIRE_RISK_HIGH"
                message = "Canh bao nguy co chay cao: Nhiet do va khi gas vuot nguong an toan!"
            elif air_quality > 300:
                label = "GAS_LEAK_DETECTED"
                message = "Canh bao chat luong khong khi xau / Ro ri khi gas!"
            else:
                label = "ENV_ANOMALY"
                message = "Phat hien bat thuong thong so moi truong tu mo hinh AI!"

        return {
            "anomaly_detected": bool(is_anomaly),
            "confidence": round(min(max(abs(score) + 0.75, 0.5), 0.99), 2),
            "label": label,
            "message": message
        }

detector = SmartAnomalyDetector()

def on_connect(client, userdata, flags, rc):
    print(f"[AI Engine] Connected to MQTT Broker (rc={rc})")
    client.subscribe(TOPIC_TELEMETRY)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        temp = float(payload.get("temperature", 28.0))
        hum = float(payload.get("humidity", 65.0))
        aq = float(payload.get("air_quality", 100.0))

        result = detector.predict(temp, hum, aq)
        if result["anomaly_detected"]:
            alert_payload = {
                "device_id": payload.get("device_id", "ESP32_NODE_01"),
                **result,
                "timestamp": int(time.time())
            }
            client.publish(TOPIC_AI_ALERT, json.dumps(alert_payload))
            print(f"[AI Alert] Published: {alert_payload}")
    except Exception as e:
        print(f"[AI Engine] Error processing message: {e}")

if __name__ == "__main__":
    print("[AI Engine] Starting Smart Anomaly Detector...")
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("[AI Engine] Stopped.")
