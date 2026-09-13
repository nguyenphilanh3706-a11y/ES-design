//Khối 1: Khai báo Thư viện, Cấu hình Mạng và Biến Toàn cục
#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include "model.h"
#include <TensorFlowLite_ESP32.h>
#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_error_reporter.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"

// Thông tin Wi-Fi và MQTT Broker 
const char* ssid = "E2_916_5G";
const char* password = "0367565475";
const char* mqtt_server = "broker.hivemq.com"; // Hoặc địa chỉ MQTT broker của bạn

WiFiClient espClient;
PubSubClient client(espClient);

// Khai báo các thành phần cốt lõi của AI
const tflite::Model* tflite_model = nullptr;
tflite::ErrorReporter* error_reporter = nullptr;
tflite::MicroInterpreter* interpreter = nullptr;
TfLiteTensor* input = nullptr;
TfLiteTensor* output = nullptr;

constexpr int kTensorArenaSize = 15 * 1024;
uint8_t tensor_arena[kTensorArenaSize];

float data_min[4] = {18.83561493, 62.00238676, 0.0, -0.80543641};
float data_max[4] = {31.5410926, 98.5877855, 50483.6662, 59.8308899};

#define WINDOW_SIZE 24
#define NUM_FEATURES 4

float ring_buffer[WINDOW_SIZE][NUM_FEATURES];
int current_index = 0;
bool buffer_full = false;

const int PUMP_PIN = 23;
//Khối 2: Hàm Tiền xử lý, Quản lý Kết nối WiFi và MQTT
void setup_wifi() {
    delay(10);
    Serial.println();
    Serial.print("Dang ket noi toi Wi-Fi: ");
    Serial.println(ssid);

    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }

    Serial.println("");
    Serial.println("WiFi đã kết nối thành công!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
}

void reconnect() {
    while (!client.connected()) {
        Serial.print("Dang ket noi MQTT...");
        if (client.connect("ESP32S3WaterClient")) {
            Serial.println("connected");
        } else {
            Serial.print("that bai, rc=");
            Serial.print(client.state());
            Serial.println(" thu lai sau 5 giay");
            delay(5000);
        }
    }
}

float min_max_scale(float value, float min_val, float max_val) {
    float scaled = (value - min_val) / (max_val - min_val);
    if (scaled < 0.0) return 0.0;
    if (scaled > 1.0) return 1.0;
    return scaled;
}

void add_sensor_data(float temp, float humid, float light, float soil) {
    ring_buffer[current_index][0] = min_max_scale(temp, data_min[0], data_max[0]);
    ring_buffer[current_index][1] = min_max_scale(humid, data_min[1], data_max[1]);
    ring_buffer[current_index][2] = min_max_scale(light, data_min[2], data_max[2]);
    ring_buffer[current_index][3] = min_max_scale(soil, data_min[3], data_max[3]);
    
    current_index++; 
    if (current_index >= WINDOW_SIZE) {
        current_index = 0; 
        buffer_full = true; 
    }
}
//Khối 3: Khởi tạo Phần cứng, Tensor Arena và Mô hình AI
void setup() {
    Serial.begin(115200);
    delay(1000);
    
    pinMode(PUMP_PIN, OUTPUT);
    digitalWrite(PUMP_PIN, LOW);

    setup_wifi();
    client.setServer(mqtt_server, 1883);

    Serial.println("Khoi dong he thong AI cho ESP32-S3...");

    tflite_model = tflite::GetModel(model_tflite);
    if (tflite_model->version() != TFLITE_SCHEMA_VERSION) {
        Serial.println("Loi phien ban schema cua mo hinh AI!");
        return;
    }

    static tflite::AllOpsResolver resolver;
    static tflite::MicroInterpreter static_interpreter(
        tflite_model, resolver, tensor_arena, kTensorArenaSize, error_reporter);
    interpreter = &static_interpreter;

    if (interpreter->AllocateTensors() != kTfLiteOk) {
        Serial.println("Cap phat Tensor Arena that bai!");
        return;
    }

    input = interpreter->input(0);
    output = interpreter->output(0);
    Serial.println("Khoi tao AI thanh cong!");
}
//Khối 4: Vòng lặp Thu thập, Suy luận AI và Điều khiển Chấp hành
void loop() {
    if (!client.connected()) {
        reconnect();
    }
    client.loop();

    float current_temp = 32.5; 
    float current_humid = 65.0;
    float current_light = 12000.0;
    float current_soil = 45.0;

    add_sensor_data(current_temp, current_humid, current_light, current_soil);

    if (buffer_full) {
        Serial.println("Ring Buffer da day. Dang chay suy luan AI...");

        int tensor_index = 0;
        for (int i = 0; i < WINDOW_SIZE; i++) {
            int idx = (current_index + i) % WINDOW_SIZE;
            for (int j = 0; j < NUM_FEATURES; j++) {
                input->data.f[tensor_index++] = ring_buffer[idx][j];
            }
        }

        if (interpreter->Invoke() != kTfLiteOk) {
            Serial.println("Loi khi chay suy luan AI!");
            return;
        }

        float predicted_soil_moisture = output->data.f[0];
        Serial.print("Do am dat du bao: ");
        Serial.println(predicted_soil_moisture);

        String pump_status = "OFF";
        if (predicted_soil_moisture < 0.3f) {
            digitalWrite(PUMP_PIN, HIGH);
            pump_status = "ON";
            Serial.println("Canh bao: Dat kho! Da BAT may bom.");
        } else {
            digitalWrite(PUMP_PIN, LOW);
            pump_status = "OFF";
            Serial.println("Do am du. Tat may bom.");
        }

        // Gửi dữ liệu qua MQTT lên Dashboard
        String payload = "{\"predicted_soil\": " + String(predicted_soil_moisture) + ", \"pump\": \"" + pump_status + "\"}";
        client.publish("esp32s3/water_controller/status", payload.c_str());
    }

    delay(3000); 
}