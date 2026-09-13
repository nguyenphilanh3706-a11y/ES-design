#include <Arduino.h>

// Tạm thời ẩn file model.h để tập trung hoàn thiện khối thu thập dữ liệu cảm biến
// #include "model.h"

float data_min[4] = {18.83561493, 62.00238676, 0.0, -0.80543641};
float data_max[4] = {31.5410926, 98.5877855, 50483.6662, 59.8308899};

#define WINDOW_SIZE 24
#define NUM_FEATURES 4

float ring_buffer[WINDOW_SIZE][NUM_FEATURES];
int current_index = 0;
bool buffer_full = false;

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

void setup() {
    Serial.begin(115200);
    Serial.println("Khoi dong he thong thu thap du lieu...");
}

void loop() {
    float current_temp = 32.5; 
    float current_humid = 65.0;
    float current_light = 12000.0;
    float current_soil = 45.0;

    add_sensor_data(current_temp, current_humid, current_light, current_soil);

    if (buffer_full) {
        Serial.println("Ring Buffer da day (24h). Chuan bi xu ly...");
    }

    delay(3000); 
}