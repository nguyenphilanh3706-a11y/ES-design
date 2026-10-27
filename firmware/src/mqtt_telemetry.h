// ============================================================================
// mqtt_telemetry.h - CHỈ ĐẨY SỐ LIỆU LÊN MQTT (không nhận lệnh, không điều khiển bơm)
// Định dạng bản tin + topic khớp với backend hiện có:
//   topic:  <MQTT_PREFIX>/<DEVICE_ID>/telemetry
//   payload JSON: sample_id, device_id, sampled_at, temperature, humidity, vpd,
//                 light, soilMoisture, fsm, pump, predictedSoil, predictedLight, ...
// ============================================================================
#pragma once
#include <PubSubClient.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include <time.h>
#include <esp_system.h>
#include <strings.h>

// ---------------------------------------------------------------------------
// >>> PHẦN CẦN ĐIỀN / XÁC NHẬN VỚI BẠN LÀM BACKEND <<<
// ---------------------------------------------------------------------------
static const char*    MQTT_HOST   = "491d98aeee1043adad1fd8414b04c1e5.s1.eu.hivemq.cloud";
static const uint16_t MQTT_PORT   = 8883;
static const char*    MQTT_USER   = "esp_iot";
static const char*    MQTT_PASS   = "espiot@123";
static const char*    DEVICE_ID   = "esp32_v1";
static const char*    MQTT_PREFIX = "plant/v2";

// Chu kỳ gửi định kỳ dự phòng (ms)
static const unsigned long MQTT_PUBLISH_MS      = 5000UL;
static const unsigned long MQTT_MAX_BACKOFF_SEC = 10UL;
// Dự đoán AI coi là "cũ" nếu quá 2 phút chưa chạy lại (AI chạy mỗi 30 s)
static const unsigned long MQTT_AI_STALE_MS     = 120000UL;

// Chứng chỉ CA của HiveMQ Cloud (ISRG Root X1)
static const char MQTT_CA[] = R"PEM(
-----BEGIN CERTIFICATE-----
MIIFazCCA1OgAwIBAgIRAIIQz7DSQONZRGPgu2OCiwAwDQYJKoZIhvcNAQELBQAw
TzELMAkGA1UEBhMCVVMxKTAnBgNVBAoTIEludGVybmV0IFNlY3VyaXR5IFJlc2Vh
cmNoIEdyb3VwMRUwEwYDVQQDEwxJU1JHIFJvb3QgWDEwHhcNMTUwNjA0MTEwNDM4
WhcNMzUwNjA0MTEwNDM4WjBPMQswCQYDVQQGEwJVUzEpMCcGA1UEChMgSW50ZXJu
ZXQgU2VjdXJpdHkgUmVzZWFyY2ggR3JvdXAxFTATBgNVBAMTDElTUkcgUm9vdCBY
MTCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBAK3oJHP0FDfzm54rVygc
h77ct984kIxuPOZXoHj3dcKi/vVqbvYATyjb3miGbESTtrFj/RQSa78f0uoxmyF+
0TM8ukj13Xnfs7j/EvEhmkvBioZxaUpmZmyPfjxwv60pIgbz5MDmgK7iS4+3mX6U
A5/TR5d8mUgjU+g4rk8Kb4Mu0UlXjIB0ttov0DiNewNwIRt18jA8+o+u3dpjq+sW
T8KOEUt+zwvo/7V3LvSye0rgTBIlDHCNAymg4VMk7BPZ7hm/ELNKjD+Jo2FR3qyH
B5T0Y3HsLuJvW5iB4YlcNHlsdu87kGJ55tukmi8mxdAQ4Q7e2RCOFvu396j3x+UC
B5iPNgiV5+I3lg02dZ77DnKxHZu8A/lJBdiB3QW0KtZB6awBdpUKD9jf1b0SHzUv
KBds0pjBqAlkd25HN7rOrFleaJ1/ctaJxQZBKT5ZPt0m9STJEadao0xAH0ahmbWn
OlFuhjuefXKnEgV4We0+UXgVCwOPjdAvBbI+e0ocS3MFEvzG6uBQE3xDk3SzynTn
jh8BCNAw1FtxNrQHusEwMFxIt4I7mKZ9YIqioymCzLq9gwQbooMDQaHWBfEbwrbw
qHyGO0aoSCqI3Haadr8faqU9GY/rOPNk3sgrDQoo//fb4hVC1CLQJ13hef4Y53CI
rU7m2Ys6xt0nUW7/vGT1M0NPAgMBAAGjQjBAMA4GA1UdDwEB/wQEAwIBBjAPBgNV
HRMBAf8EBTADAQH/MB0GA1UdDgQWBBR5tFnme7bl5AFzgAiIyBpY9umbbjANBgkq
hkiG9w0BAQsFAAOCAgEAVR9YqbyyqFDQDLHYGmkgJykIrGF1XIpu+ILlaS/V9lZL
ubhzEFnTIZd+50xx+7LSYK05qAvqFyFWhfFQDlnrzuBZ6brJFe+GnY+EgPbk6ZGQ
3BebYhtF8GaV0nxvwuo77x/Py9auJ/GpsMiu/X1+mvoiBOv/2X/qkSsisRcOj/KK
NFtY2PwByVS5uCbMiogziUwthDyC3+6WVwW6LLv3xLfHTjuCvjHIInNzktHCgKQ5
ORAzI4JMPJ+GslWYHb4phowim57iaztXOoJwTdwJx4nLCgdNbOhdjsnvzqvHu7Ur
TkXWStAmzOVyyghqpZXjFaH3pO3JLF+l+/+sKAIuvtd7u+Nxe5AW0wdeRlN8NwdC
jNPElpzVmbUq4JUagEiuTDkHzsxHpFKVK7q4+63SM1N95R1NbdWhscdCb+ZAJzVc
oyi3B43njTOQ5yOf+1CceWxG1bQVs5ZufpsMljq4Ui0/1lvh+wjChP4kqKOJ2qxq
4RgqsahDYVvTH9w7jXbyLeiNdd8XM2w9U/t7y0Ff/9yi0GE44Za4rF2LN9d11TPA
mRGunUHBcnWEvgJBQl9nJEiU0Zsnvgc/ubhPgXRR4Xq37Z0j4r7g1SgEEzwxA57d
emyPxgcYxn/eR44/KJ4EBs+lVDR3veyJm+kXQ99b21/+jh5Xos1AnX5iItreGCc=
-----END CERTIFICATE-----
)PEM";

// Sau bao lâu mất MQTT mà đang MANUAL thì tự về AUTO (để cây không bị bỏ đói)
static const unsigned long MANUAL_FALLBACK_MS = 10UL * 60UL * 1000UL;

// ---- Chế độ điều khiển. Mặc định AUTO sau mỗi lần khởi động (an toàn) ----
volatile bool manualMode    = false;  // false = AUTO (FSM cũ), true = MANUAL
volatile bool manualPumpReq = false;  // lệnh "bơm 1 chu kỳ" đang chờ FSM xử lý

static WiFiClientSecure mqttNet;
static PubSubClient mqttClient(mqttNet);
static char mqttClientId[48];
static char mqttTopicTelemetry[96];
static char mqttTopicCommand[96];
static char mqttTopicAck[96];
static unsigned long lastMqttOkMs = 0;
static bool mqttInited = false;
static unsigned long lastMqttRetry = 0;
static unsigned long mqttBackoffSec = 2;
static unsigned long lastMqttPublish = 0;
static unsigned long netDownSince = 0;   // lúc bắt đầu mất mạng (WiFi hoặc MQTT)
static unsigned long lastWifiKick = 0;
static unsigned long lastMqttKick = 0;
static uint8_t mqttPubFail = 0;          // số lần publish lỗi liên tiếp

static void mqttFormatUtc(time_t v, char* out, size_t len) {
  struct tm t;
  gmtime_r(&v, &t);
  strftime(out, len, "%Y-%m-%dT%H:%M:%SZ", &t);
}

static void mqttUuid(char* out) {
  uint8_t b[16];
  esp_fill_random(b, sizeof(b));
  b[6] = (b[6] & 0x0F) | 0x40;
  b[8] = (b[8] & 0x3F) | 0x80;
  snprintf(out, 37, "%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-%02x%02x%02x%02x%02x%02x",
           b[0], b[1], b[2], b[3], b[4], b[5], b[6], b[7],
           b[8], b[9], b[10], b[11], b[12], b[13], b[14], b[15]);
}

static void publishTelemetry() {
  time_t nowEpoch = time(nullptr);
  static unsigned long lastSkipLog = 0;
  if (nowEpoch < 1700000000) {         // NTP chưa đồng bộ -> chưa gửi
    if (millis() - lastSkipLog > 10000UL) { lastSkipLog = millis(); Serial.println("[MQTT] Bo qua: chua co gio NTP"); }
    return;
  }
  if (!ahtOk && !bhOk) {               // chưa có cảm biến nào hoạt động
    if (millis() - lastSkipLog > 10000UL) { lastSkipLog = millis(); Serial.println("[MQTT] Bo qua: AHT va BH1750 deu khong hoat dong"); }
    return;
  }

  static const char* STATE_NAMES[] = {"IDLE", "PUMPING", "COOLDOWN", "FAULT"};
  unsigned long nowMs = millis();
  bool predReady = aiReady && aiHasPrediction && (nowMs - aiLastRunMs) <= MQTT_AI_STALE_MS
                   && currentState != FAULT;

  char sampleId[37], sampledAt[32], inputAt[32], targetAt[32];
  mqttUuid(sampleId);
  mqttFormatUtc(nowEpoch, sampledAt, sizeof(sampledAt));

  StaticJsonDocument<1024> doc;
  doc["sample_id"]  = sampleId;
  doc["device_id"]  = DEVICE_ID;
  doc["sampled_at"] = sampledAt;
  doc["simulated"]  = false;

  doc["temperature"]  = tempC;
  doc["humidity"]     = humPct;
  doc["vpd"]          = vpdKPa;
  doc["light"]        = lux;
  doc["soilMoisture"] = soilPct;

  doc["mode"]           = manualMode ? "MANUAL" : "AUTO";
  doc["pump"]           = (currentState == PUMPING) ? "ON" : "OFF";
  doc["fsm"]            = STATE_NAMES[(int)currentState];
  doc["waterAvailable"] = waterAvailable;
  if (currentState == FAULT) doc["fault"] = faultReason;
  else                       doc["fault"] = nullptr;

  doc["aiReady"] = predReady;
  doc["predictionHorizonMinutes"] = 60;
  doc["soilPredictionSource"]  = "esp32_week2";
  doc["lightPredictionSource"] = "esp32_week2";

  if (predReady) {
    time_t inEpoch = nowEpoch - (time_t)((nowMs - aiLastRunMs) / 1000UL);
    mqttFormatUtc(inEpoch, inputAt, sizeof(inputAt));
    mqttFormatUtc(inEpoch + 3600, targetAt, sizeof(targetAt));
    doc["predictedSoil"]        = aiPredSoil;
    doc["predictedLight"]       = aiPredLux;
    doc["predictionInputAt"]    = inputAt;
    doc["predictionTargetAt"]   = targetAt;
    doc["aiMessage"]            = aiProactiveTrigger ? "AI de nghi tuoi don" : "AI binh thuong";
  } else {
    doc["predictedSoil"]      = nullptr;
    doc["predictedLight"]     = nullptr;
    doc["predictionInputAt"]  = nullptr;
    doc["predictionTargetAt"] = nullptr;
    doc["aiMessage"] = !aiReady ? "AI chua san sang" : "Dang cho du doan moi";
  }

  if (doc.overflowed()) { Serial.println("[MQTT] JSON vuot dung luong."); return; }

  char payload[1024];
  size_t n = serializeJson(doc, payload, sizeof(payload));
  static unsigned long sentCount = 0;
  if (!mqttClient.publish(mqttTopicTelemetry, (const uint8_t*)payload, n, false)) {
    Serial.printf("[MQTT] Gui telemetry THAT BAI (%u byte, state=%d)\n", (unsigned)n, mqttClient.state());
    if (++mqttPubFail >= 3) {            // kết nối treo (half-open): ép nối lại
      Serial.println("[MQTT] Gui loi 3 lan -> ngat de ket noi lai");
      mqttPubFail = 0;
      mqttClient.disconnect();
      mqttNet.stop();
    }
  } else if ((mqttPubFail = 0, ++sentCount % 5 == 1)) {   // gửi OK -> xóa bộ đếm lỗi
    Serial.printf("[MQTT] Da gui telemetry #%lu (%u byte)\n", sentCount, (unsigned)n);
  }
}


// ---------------------------------------------------------------------------
// NHẬN LỆNH TỪ WEB - đúng giao thức backend (main.py), topic <prefix>/<device>/command (QoS1):
//   {"command_id","device_id","type":"mode","mode":"AUTO|MANUAL","issued_at","expires_at"}
//   {"command_id","device_id","type":"pump","state":"ON|OFF","duration_ms":100..5000,...}
// Trả lời ở <prefix>/<device>/ack:
//   {"command_id","device_id","status":"applied|rejected|completed","message","pump","mode","simulated":false}
// Lệnh hết hạn (expires_at) hoặc thời hạn > 60 s bị từ chối.
// ---------------------------------------------------------------------------
volatile unsigned long manualPumpDurationMs = 2500UL;  // thời gian bơm theo lệnh web
static char pendingPumpCmd[40] = "";    // lệnh bơm đang chạy, chờ gửi ack "completed"
static bool pendingPumpStarted = false;
static unsigned long pendingPumpSince = 0;
static char lastCmdId[40] = "";         // chống xử lý trùng lệnh QoS1
static FsmState lastPublishedFsm = IDLE;

static void mqttSendAck(const char* cmdId, const char* status, const char* message) {
  StaticJsonDocument<512> a;
  a["command_id"] = cmdId;
  a["device_id"]  = DEVICE_ID;
  a["status"]     = status;
  a["message"]    = message;
  a["pump"]       = (currentState == PUMPING) ? "ON" : "OFF";
  a["mode"]       = manualMode ? "MANUAL" : "AUTO";
  a["simulated"]  = false;
  char out[512];
  size_t n = serializeJson(a, out, sizeof(out));
  mqttClient.publish(mqttTopicAck, (const uint8_t*)out, n, false);
  Serial.printf("[MQTT] Ack %s: %s\n", status, message);
}

// "YYYY-MM-DDTHH:MM:SS[.ffffff](+00:00|Z)" -> epoch UTC. Backend luôn gửi UTC.
static bool isoToEpoch(const char* s, time_t* out) {
  int Y, M, D, h, m, sec;
  if (!s || strlen(s) < 20) return false;
  if (sscanf(s, "%d-%d-%dT%d:%d:%d", &Y, &M, &D, &h, &m, &sec) != 6) return false;
  const char* tail = s + 19;
  if (*tail == '.') { tail++; while (*tail >= '0' && *tail <= '9') tail++; }
  if (!(strncmp(tail, "+00:00", 6) == 0 || *tail == 'Z')) return false;
  Y -= (M <= 2);
  long era = (Y >= 0 ? Y : Y - 399) / 400;
  long yoe = Y - era * 400;
  long doy = (153L * (M + (M > 2 ? -3 : 9)) + 2) / 5 + D - 1;
  long doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
  long days = era * 146097L + doe - 719468L;
  *out = (time_t)(days * 86400L + h * 3600L + m * 60L + sec);
  return true;
}

static void mqttOnMessage(char* topic, byte* payload, unsigned int len) {
  if (len == 0 || len > 500) return;
  char buf[501];
  memcpy(buf, payload, len);   // copy trước: PubSubClient dùng chung buffer khi publish ack
  buf[len] = 0;
  Serial.printf("[MQTT] Lenh nhan: %s\n", buf);

  StaticJsonDocument<768> d;
  if (deserializeJson(d, buf)) { Serial.println("[MQTT] Lenh khong phai JSON"); return; }

  const char* cmdId = d["command_id"] | "";
  const char* devId = d["device_id"] | "";
  const char* type  = d["type"] | "";
  if (!cmdId[0] || strlen(cmdId) >= sizeof(lastCmdId)) return;
  if (strcmp(devId, DEVICE_ID) != 0) return;            // lệnh của thiết bị khác
  if (strcmp(cmdId, lastCmdId) == 0) { Serial.println("[MQTT] Bo qua lenh trung"); return; }
  snprintf(lastCmdId, sizeof(lastCmdId), "%s", cmdId);

  // Kiểm tra hạn dùng của lệnh (chống phát lại lệnh cũ)
  time_t nowE = time(nullptr), expE = 0, issE = 0;
  if (nowE < 1700000000) { mqttSendAck(cmdId, "rejected", "Thiet bi chua dong bo gio"); return; }
  if (!isoToEpoch(d["expires_at"] | "", &expE) || !isoToEpoch(d["issued_at"] | "", &issE)) {
    mqttSendAck(cmdId, "rejected", "Thieu hoac sai issued_at/expires_at"); return;
  }
  if (expE - issE > 61 || nowE > expE) {
    mqttSendAck(cmdId, "rejected", "Lenh het han hoac thoi han khong hop le"); return;
  }

  if (strcmp(type, "mode") == 0) {
    const char* mode = d["mode"] | "";
    if (!strcasecmp(mode, "MANUAL"))    { manualMode = true;  manualPumpReq = false; }
    else if (!strcasecmp(mode, "AUTO")) { manualMode = false; manualPumpReq = false; }
    else { mqttSendAck(cmdId, "rejected", "Che do khong hop le"); return; }
    publishTelemetry();   // web thấy chế độ mới trước khi nhận ack
    mqttSendAck(cmdId, "applied", manualMode ? "Da chuyen sang MANUAL" : "Da chuyen sang AUTO");
    return;
  }

  if (strcmp(type, "pump") == 0) {
    const char* state = d["state"] | "";
    long dur = d["duration_ms"] | 2500;

    if (!strcasecmp(state, "OFF")) {
      manualPumpReq = false;
      if (currentState == PUMPING) {
        digitalWrite(PIN_PUMP_TRIG, LOW);
        cooldownStartTime = millis();
        currentState = COOLDOWN;
      }
      publishTelemetry();
      mqttSendAck(cmdId, "completed", "Bom da tat");
      return;
    }
    if (strcasecmp(state, "ON") != 0) { mqttSendAck(cmdId, "rejected", "Trang thai bom khong hop le"); return; }

    char msg[96];
    if (!manualMode)                           { mqttSendAck(cmdId, "rejected", "Chua o che do MANUAL"); return; }
    if (currentState == FAULT) {
      snprintf(msg, sizeof(msg), "Thiet bi dang loi: %s", faultReason);
      mqttSendAck(cmdId, "rejected", msg); return;
    }
    if (currentState != IDLE || pendingPumpCmd[0]) { mqttSendAck(cmdId, "rejected", "Thiet bi chua san sang (dang bom/nghi)"); return; }
    if (soilPct >= SOIL_THRESHOLD_HIGH)        { mqttSendAck(cmdId, "rejected", "Dat da du am"); return; }

    if (dur < 100) dur = 100;
    if (dur > 4500) dur = 4500;          // luôn dưới watchdog 5 s
    manualPumpDurationMs = (unsigned long)dur;
    manualPumpReq = true;                // FSM sẽ bơm; vẫn có watchdog/dừng khi đất đủ ẩm/cooldown
    snprintf(pendingPumpCmd, sizeof(pendingPumpCmd), "%s", cmdId);
    pendingPumpStarted = false;
    pendingPumpSince = millis();
    snprintf(msg, sizeof(msg), "Da nhan lenh, bom %ld ms", dur);
    mqttSendAck(cmdId, "applied", msg);
    return;
  }

  mqttSendAck(cmdId, "rejected", "Loai lenh khong duoc ho tro");
}

// HÀM GỬI TỨC THÌ (Được gọi ngay khi cảm biến đọc xong)
void publishTelemetryImmediate() {
  if (WiFi.status() == WL_CONNECTED && mqttClient.connected()) {
    unsigned long t0 = millis();
    publishTelemetry();
    mqttClient.loop(); // Xả buffer socket ngay lập tức, triệt tiêu độ trễ
    lastMqttPublish = millis();
    unsigned long dt = lastMqttPublish - t0;
    if (dt > 200) Serial.printf("[MQTT] publish mat %lums (cham)\n", dt);
  }
}

void handleMqtt(unsigned long now) {
  if (!mqttInited) {
    mqttInited = true;
    uint64_t mac = ESP.getEfuseMac();
    snprintf(mqttClientId, sizeof(mqttClientId), "%s-%08lX", DEVICE_ID, (unsigned long)(mac & 0xFFFFFFFFULL));
    snprintf(mqttTopicTelemetry, sizeof(mqttTopicTelemetry), "%s/%s/telemetry", MQTT_PREFIX, DEVICE_ID);
    snprintf(mqttTopicCommand, sizeof(mqttTopicCommand), "%s/%s/command", MQTT_PREFIX, DEVICE_ID);
    snprintf(mqttTopicAck, sizeof(mqttTopicAck), "%s/%s/ack", MQTT_PREFIX, DEVICE_ID);
    WiFi.setSleep(false);
    WiFi.setAutoReconnect(true);
    WiFi.persistent(false);   // tắt modem-sleep: giảm trễ gửi/nhận qua WiFi
    mqttNet.setCACert(MQTT_CA);
    mqttNet.setHandshakeTimeout(8);
    mqttClient.setServer(MQTT_HOST, MQTT_PORT);
    mqttClient.setBufferSize(1536);
    mqttClient.setCallback(mqttOnMessage);
    mqttClient.setSocketTimeout(3);
    mqttClient.setKeepAlive(15);
  }

  if (mqttClient.connected()) {
    lastMqttOkMs = now;
  } else if (manualMode && (now - lastMqttOkMs) > MANUAL_FALLBACK_MS) {
    manualMode = false;
    manualPumpReq = false;
    Serial.println("[MODE] Mat MQTT qua lau -> tu dong ve AUTO");
  }

  // Chưa có giờ -> thử lại NTP với nhiều máy chủ khác nhau (hotspot đôi khi chặn pool.ntp.org)
  {
    static unsigned long lastNtpKick = 0;
    static int ntpTry = 0;
    static bool ntpLogged = false;
    bool haveTime = (time(nullptr) >= 1700000000);
    if (haveTime && !ntpLogged) { ntpLogged = true; Serial.println("[NTP] Da dong bo gio"); }
    if (!haveTime && WiFi.status() == WL_CONNECTED && now - lastNtpKick > 15000UL) {
      lastNtpKick = now;
      static const char* NTP_SETS[3][3] = {
        {"time.google.com", "time.cloudflare.com", "pool.ntp.org"},
        {"vn.pool.ntp.org", "time.windows.com", "time.nist.gov"},
        {"time.apple.com", "asia.pool.ntp.org", "pool.ntp.org"}};
      const char** set = NTP_SETS[ntpTry++ % 3];
      configTime(GMT_OFFSET_SEC, DAYLIGHT_OFFSET, set[0], set[1], set[2]);
      Serial.printf("[NTP] Chua co gio, thu: %s, %s, %s\n", set[0], set[1], set[2]);
    }
  }

  // ---- TỰ PHỤC HỒI MẠNG ----
  {
    bool wifiUp = (WiFi.status() == WL_CONNECTED);
    bool mqttUp = wifiUp && mqttClient.connected();
    if (mqttUp) netDownSince = 0;
    else if (netDownSince == 0) netDownSince = now ? now : 1;
    unsigned long down = netDownSince ? (now - netDownSince) : 0;

    // Mất WiFi > 60 s: khởi động lại stack WiFi (mỗi 60 s một lần)
    if (!wifiUp && down > 60000UL && now - lastWifiKick > 60000UL) {
      lastWifiKick = now;
      Serial.println("[NET] Mat WiFi > 60s -> khoi dong lai WiFi");
      WiFi.disconnect(true);
      delay(100);
      WiFi.mode(WIFI_STA);
      WiFi.begin(WIFI_SSID, WIFI_PASS);
    }

    // WiFi còn nhưng MQTT mất > 90 s: hủy phiên TLS cũ để nối lại từ đầu
    if (wifiUp && !mqttUp && down > 90000UL && now - lastMqttKick > 90000UL) {
      lastMqttKick = now;
      Serial.println("[NET] Mat MQTT > 90s -> dat lai ket noi TLS");
      mqttClient.disconnect();
      mqttNet.stop();
      mqttBackoffSec = 2;
    }

    // Mất WiFi > 10 phút (stack WiFi có thể kẹt): khởi động lại ESP32, chỉ khi bơm không chạy
    if (!wifiUp && down > 600000UL && currentState != PUMPING) {
      Serial.println("[NET] Mat WiFi > 10 phut -> khoi dong lai ESP32");
      digitalWrite(PIN_PUMP_TRIG, LOW);
      delay(200);
      ESP.restart();
    }
  }

  if (WiFi.status() != WL_CONNECTED) return;

  if (!mqttClient.connected()) {
    if (currentState == PUMPING) return;
    if (now - lastMqttRetry < mqttBackoffSec * 1000UL) return;
    lastMqttRetry = now;

    if (mqttClient.connect(mqttClientId, MQTT_USER, MQTT_PASS)) {
      Serial.printf("[MQTT] Da ket noi, topic: %s\n", mqttTopicTelemetry);
      mqttBackoffSec = 2;
      lastMqttPublish = 0;
      mqttClient.subscribe(mqttTopicCommand, 1);
    } else {
      Serial.printf("[MQTT] Ket noi that bai (rc=%d), thu lai sau %lus\n", mqttClient.state(), mqttBackoffSec);
      mqttBackoffSec = min(mqttBackoffSec * 2, MQTT_MAX_BACKOFF_SEC);
    }
    return;
  }

  mqttClient.loop();

  // FSM đổi trạng thái (bắt đầu/ngừng bơm, nghỉ...) -> gửi telemetry ngay cho web
  if (currentState != lastPublishedFsm) {
    lastPublishedFsm = currentState;
    publishTelemetry();
    lastMqttPublish = now ? now : 1;
  }

  // Lệnh bơm thủ công: gửi ack "completed" khi bơm đã chạy xong
  if (pendingPumpCmd[0]) {
    if (currentState == PUMPING) pendingPumpStarted = true;
    if (pendingPumpStarted && currentState != PUMPING) {
      mqttSendAck(pendingPumpCmd, "completed", "Bom da hoan tat");
      pendingPumpCmd[0] = 0;
    } else if (!pendingPumpStarted && (now - pendingPumpSince) > 4000UL) {
      manualPumpReq = false;
      mqttSendAck(pendingPumpCmd, "completed", "Bom khong chay (dieu kien an toan chan)");
      pendingPumpCmd[0] = 0;
    }
  }

  // Giữ lại gửi dự phòng định kỳ nếu quá 5s không có gói tin nào
  if (lastMqttPublish == 0 || now - lastMqttPublish >= MQTT_PUBLISH_MS) {
    lastMqttPublish = now ? now : 1;
    publishTelemetry();
  }
}