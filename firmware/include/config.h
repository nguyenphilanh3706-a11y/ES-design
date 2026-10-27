#ifndef CONFIG_H
#define CONFIG_H

// Cau hinh Wi-Fi & MQTT (Phu trach: Nguyen Phi Lanh)
#define WIFI_SSID       "Smart_IoT_WiFi"
#define WIFI_PASSWORD   "12345678"

#define MQTT_BROKER     "192.168.1.100"
#define MQTT_PORT       1883
#define DEVICE_ID       "ESP32_NODE_01"

// MQTT Topics
#define TOPIC_TELEMETRY "iot/device/telemetry"
#define TOPIC_CONTROL   "iot/device/control"

// Cau hinh chan GPIO
#define PIN_DHT         4
#define PIN_MQ135       34
#define PIN_RELAY       26
#define PIN_LED_STATUS  2

#define TELEMETRY_INTERVAL_MS 3000

#endif
