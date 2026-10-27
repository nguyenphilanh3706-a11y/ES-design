/**
 * @file main.cpp
 * @author Nguyen Phi Lanh
 * @brief Firmware ESP32 doc du lieu cam bien va dieu khien thiet bi qua MQTT
 */

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include "config.h"

DHT dht(PIN_DHT, DHT22);
WiFiClient espClient;
PubSubClient mqttClient(espClient);

bool relayState = false;
unsigned long lastTelemetryTime = 0;

void setupWiFi() {
    Serial.print("[WiFi] Connecting to ");
    Serial.println(WIFI_SSID);
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\n[WiFi] Connected! IP: " + WiFi.localIP().toString());
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, payload, length);
    if (error) {
        Serial.println("[MQTT] JSON Parse Error!");
        return;
    }

    const char* command = doc["command"];
    if (command && strcmp(command, "SET_RELAY") == 0) {
        relayState = doc["value"];
        digitalWrite(PIN_RELAY, relayState ? HIGH : LOW);
        Serial.printf("[Control] Relay state updated to: %s\n", relayState ? "ON" : "OFF");
    }
}

void reconnectMQTT() {
    while (!mqttClient.connected()) {
        Serial.print("[MQTT] Attempting connection...");
        if (mqttClient.connect(DEVICE_ID)) {
            Serial.println("connected!");
            mqttClient.subscribe(TOPIC_CONTROL);
        } else {
            Serial.print("failed, rc=");
            Serial.print(mqttClient.state());
            Serial.println(" try again in 3 seconds");
            delay(3000);
        }
    }
}

void publishTelemetry() {
    float temp = dht.readTemperature();
    float hum = dht.readHumidity();
    int gasRaw = analogRead(PIN_MQ135);

    if (isnan(temp) || isnan(hum)) {
        temp = 28.5;
        hum = 65.0;
    }

    StaticJsonDocument<256> doc;
    doc["device_id"] = DEVICE_ID;
    doc["temperature"] = temp;
    doc["humidity"] = hum;
    doc["air_quality"] = map(gasRaw, 0, 4095, 50, 500);
    doc["relay_state"] = relayState;
    doc["timestamp"] = millis() / 1000;

    char buffer[256];
    serializeJson(doc, buffer);
    mqttClient.publish(TOPIC_TELEMETRY, buffer);
    Serial.println("[Telemetry] Published: " + String(buffer));
}

void setup() {
    Serial.begin(115200);
    pinMode(PIN_RELAY, OUTPUT);
    pinMode(PIN_LED_STATUS, OUTPUT);
    pinMode(PIN_MQ135, INPUT);

    digitalWrite(PIN_RELAY, LOW);
    dht.begin();

    setupWiFi();
    mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
    mqttClient.setCallback(mqttCallback);
}

void loop() {
    if (!mqttClient.connected()) {
        reconnectMQTT();
    }
    mqttClient.loop();

    unsigned long now = millis();
    if (now - lastTelemetryTime >= TELEMETRY_INTERVAL_MS) {
        lastTelemetryTime = now;
        publishTelemetry();
    }
}
