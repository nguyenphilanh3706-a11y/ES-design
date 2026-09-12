# HARDWARE SPECIFICATION & PIN ALLOCATION MATRIX
## Microcontroller Pin Multiplexing, Bus Topology & Peripheral Interfacing (ESP32-S3)

---

**Document Identifier:** AIOT-GPIO-MATRIX-2026-V1.0  
**Project:** Adaptive Autonomous Plant Irrigation Node (ESP32-S3 + On-Device TinyML)  
**Author / Subsystem:** Embedded Hardware & Firmware Core (Member A)  
**Target Microcontroller:** Espressif ESP32-S3-WROOM-1 / ESP32-S3-DevKitC-1 (Xtensa LX7 Dual-Core)  
**System Voltage Rails:** 5.0V DC Actuator Bus | 3.3V DC Regulated Logic Rail  
**Document Status:** Production Hardware Interface Specification  

---

## 1. Executive Summary & Architecture Overview

This document specifies the exact **General-Purpose Input/Output (GPIO) Pin Allocation Matrix** for the ESP32-S3 AIoT Irrigation Node. The peripheral routing is optimized to eliminate silicon-level resource contention, prevent analog-to-digital converter (ADC) lockouts during 2.4 GHz Wi-Fi / BLE RF transactions, ensure multi-drop bus integrity across heterogeneous I2C peripherals, and provide safe, glitch-free gate switching for the high-current liquid pump.

### 1.1. Core Pin Assignment Summary
* **GPIO 1 (`ADC1_CH0`):** Dedicated high-impedance analog input for the **Capacitive Soil Moisture Sensor v1.2**.
* **GPIO 2 (`I2C_SDA`):** Shared bidirectional serial data line for the high-density sensor and display bus.
* **GPIO 42 (`I2C_SCL`):** Shared serial clock line for the high-density sensor and display bus.
  - *Shared I2C Peripherals:* **AHT20 / SHT30** (Ambient Temperature & Relative Humidity), **BH1750** (Ambient Light / PAR Irradiance), and **OLED 1.3-inch** (SH1106 / SSD1306 128x64 Graphical Display).
* **GPIO 4 (`LEDC_PWM`):** High-speed hardware pulse-width modulated (PWM) digital output driving the **Low-Side N-Channel MOSFET Module** for inductive liquid pump actuation.

---

## 2. Master GPIO Pin Allocation Matrix

The table below details the hardware pin multiplexing, operating voltage levels, internal/external termination resistors, and peripheral controller assignments:

| Pin | Net / Signal Name | I/O Direction | Electrical Domain | Silicon Peripheral | Connected Peripheral Device | Termination / Conditioning | Operational Description & Constraints |
| :---: | :--- | :---: | :---: | :---: | :--- | :--- | :--- |
| **GPIO 1** | `SOIL_MOIST_ADC` | Input | 3.3V Analog | **ADC1_CH0** (SAR ADC 1) | Capacitive Soil Moisture Sensor v1.2 | External RC Anti-Aliasing:<br>- Series: $1\text{ k}\Omega$ (1%)<br>- Shunt: $100\text{ nF}$ MLCC to AGND | High-impedance analog measurement ($0.15\text{V} - 3.10\text{V}$). Assigned strictly to **ADC1** to prevent RF coexistence lockout with Wi-Fi/BT transceiver. |
| **GPIO 2** | `I2C_BUS_SDA` | In / Out | 3.3V Digital (Open-Drain) | **I2C0 Master** (Data) | - AHT20 / SHT30<br>- BH1750 FVI<br>- 1.3" OLED (SH1106/SSD1306) | External Pull-Up:<br>- $4.7\text{ k}\Omega \pm 1\%$ tied to 3.3V Rail | Shared multi-drop serial data line. Slew rate controlled by open-drain driver; internal weak pull-up disabled (`GPIO_PULLUP_DISABLE`). |
| **GPIO 42** | `I2C_BUS_SCL` | Output | 3.3V Digital (Open-Drain) | **I2C0 Master** (Clock) | - AHT20 / SHT30<br>- BH1750 FVI<br>- 1.3" OLED (SH1106/SSD1306) | External Pull-Up:<br>- $4.7\text{ k}\Omega \pm 1\%$ tied to 3.3V Rail | Shared multi-drop serial clock line ($100\text{ kHz}$ Standard Mode). Configured as open-drain to support multi-master clock stretching if asserted by slaves. |
| **GPIO 4** | `PUMP_GATE_CTRL` | Output | 3.3V Digital (Push-Pull) | **LEDC Timer 0, Channel 0** | Discrete / Modular N-Channel MOSFET Gate | Gate Network:<br>- Series: $100\ \Omega$ damping<br>- Pulldown: $10\text{ k}\Omega$ to GND | High-frequency hardware PWM ($10\text{ kHz}$, 10-bit resolution). Guarantees $V_{\text{GS}} = 0\text{V}$ during power-up, reset, or bootloader execution. |

---

## 3. Subsystem Interface Engineering & Signal Conditioning

### 3.1. Analog Subsystem: Soil Moisture Sensing (GPIO 1 / ADC1_CH0)

```
 [ Capacitive Soil Probe v1.2 ]
   (Analog Signal: 1.2V - 2.8V)
               |
               v
         [ R_series: 1 kOhm ]
               |
               +---------------------> ESP32-S3 GPIO 1 (ADC1_CH0)
               |
             ===== C_shunt: 100nF MLCC
               |
           Analog GND
```

#### 3.1.1. Silicon-Level ADC Justification
* **Wi-Fi / RF Isolation:** The ESP32-S3 features two SAR ADCs (ADC1 and ADC2). The Wi-Fi and Bluetooth wireless subsystem forcefully arbitrates and locks ADC2 during radio frequency transmission events. By binding the soil moisture sensor exclusively to **ADC1_CH0 (GPIO 1)**, continuous unhindered ADC sampling is guaranteed even during sustained MQTT/TLS cloud telemetry streaming.
* **Input Voltage Dynamic Range:**
  * Sensor output dynamic range: $V_{\text{out}} \approx 1.25\text{V}$ (100% saturation / pure water) to $V_{\text{out}} \approx 2.75\text{V}$ (0% moisture / oven-dry soil).
  * The ADC input is configured with **$12\text{ dB}$ Attenuation (`ADC_ATTEN_DB_12`)**, yielding an effective full-scale measurable range of $0.15\text{V}$ to $3.10\text{V}$. This spans the entire sensor output profile with $> 350\text{ mV}$ of headroom below the $3.3\text{V}$ rail.
* **Hardware Signal Conditioning (Anti-Aliasing Filter):**
  * A passive first-order low-pass RC network ($R_{\text{series}} = 1\text{ k}\Omega \pm 1\%$, $C_{\text{shunt}} = 100\text{ nF}$ X7R ceramic) is placed adjacent to the MCU pin.
  * Filter cut-off frequency:
    $$f_c = \frac{1}{2\pi R C} = \frac{1}{2\pi \times 10^3\ \Omega \times 100 \times 10^{-9}\text{ F}} \approx 1.59\text{ kHz}$$
  * This filter eliminates high-frequency RF ingress picked up along the $30\text{ cm}$ sensor wiring leads, rejects $10\text{ kHz}$ PWM switching ripple from the nearby pump, and stabilizes the sample-and-hold internal capacitor charging current.
* **Factory eFuse Calibration:** Raw 12-bit quantization values ($0 - 4095$) are linearized using the Espressif `esp_adc_cal_raw_to_voltage()` API, which references factory-burned bandgap characterization trim bits stored in chip eFuses.

---

### 3.2. Shared Multi-Drop I2C Bus Subsystem (GPIO 2 & GPIO 42)

The system implements a high-density, heterogeneous I2C bus operating at **Standard Mode ($100\text{ kHz}$)**. It accommodates environmental telemetry and a local graphical diagnostic display on a single two-wire bus.

```
                  3.3V System Logic Rail
                            |
           +----------------+----------------+
           |                                 |
         [ 4.7 kOhm ]                      [ 4.7 kOhm ]
           |                                 |
           +---------------------------------+------------------------+
           | I2C_SDA (GPIO 2)                | I2C_SCL (GPIO 42)      |
           |                                 |                        |
    +------+------+                   +------+------+                 |
    |   AHT20 /   | (Addr: 0x38       |   BH1750    | (Addr: 0x23     |
    |    SHT30    |  or 0x44)         | Irradiance  |  ADDR=GND)      |
    +------+------+                   +------+------+                 |
           |                                 |                        |
           +---------------------------------+                        |
           |                                                          |
    +------+------+                                                   |
    |  OLED 1.3"  | (Addr: 0x3C, SH1106 Controller)                   |
    | Display Module                                                  |
    +-------------+---------------------------------------------------+
```

#### 3.2.1. 7-Bit Addressing & Collision Prevention Matrix
To verify that no address overlap occurs on the shared bus, the hardware addressing configuration is mapped below:

| Peripheral Device | Primary Function | Fixed / Configurable | Hardware Address (7-Bit Hex) | Binary Address (`[A6:A0]`) | Pin Strapping / Hardware Configuration |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **AHT20** *(Option 1)* | Ambient Temp & Humidity | Fixed | `0x38` | `011 1000b` | Factory hardwired internal ASIC address. |
| **SHT30** *(Option 2)* | Ambient Temp & Humidity | Configurable | `0x44` | `100 0100b` | Pin `ADDR` tied to `GND`. (Alternative: `0x45` if `ADDR` to $3.3\text{V}$). |
| **BH1750FVI** | Ambient Light / Lux | Configurable | `0x23` | `010 0011b` | Pin `ADDR` tied to `GND`. (Alternative: `0x5C` if `ADDR` to $3.3\text{V}$). |
| **1.3" Monochrome OLED**| Real-Time System Dashboard| Configurable | `0x3C` | `011 1100b` | On-board address jumper set to `0x78` write mode ($7\text{-bit} = \texttt{0x3C}$). |

**Address Conflict Verdict:** **ZERO CONFLICTS.** The hardware addresses (`0x38`/`0x44`, `0x23`, `0x3C`) are mutually orthogonal and operate seamlessly on the single I2C bus.

#### 3.2.2. Electrical Pull-Up Resistor & Capacitive Bus Loading Analysis
The I2C specification (UM10204) defines a maximum total capacitive bus loading of $C_b \le 400\text{ pF}$ for Standard Mode ($100\text{ kbps}$) and sets maximum allowable rise time to $t_r \le 1000\text{ ns}$.

* **Cumulative Bus Capacitance Estimation ($C_b$):**
  $$C_b = C_{\text{trace}} + C_{\text{MCU}} + C_{\text{AHT20}} + C_{\text{BH1750}} + C_{\text{OLED}}$$
  - Microcontroller pin capacitance ($C_{\text{MCU}}$): $\approx 7\text{ pF}$
  - AHT20 input capacitance: $\approx 5\text{ pF}$
  - BH1750 input capacitance: $\approx 5\text{ pF}$
  - 1.3" OLED breakout board (including on-module filtering): $\approx 25\text{ pF}$
  - PCB interconnect traces & $20\text{ cm}$ ribbon wiring harness: $\approx 35\text{ pF}$
  - **Total Worst-Case Bus Capacitance:** $C_b \approx \mathbf{77\text{ pF}} \ll 400\text{ pF}$ (Safe margin $> 80\%$).

* **Optimal Pull-Up Resistor Calculation ($R_p$):**
  - Maximum allowable pull-up resistance to satisfy rise time ($t_r \le 1000\text{ ns}$):
    $$R_{p(\text{max})} = \frac{t_r}{0.8473 \times C_b} = \frac{1000 \times 10^{-9}\text{ s}}{0.8473 \times 77 \times 10^{-12}\text{ F}} \approx 15.3\text{ k}\Omega$$
  - Minimum pull-up resistance to limit sink current through slave open-drain drivers ($I_{OL} \le 3.0\text{ mA}$ at $V_{OL} = 0.4\text{V}$):
    $$R_{p(\text{min})} = \frac{V_{DD} - V_{OL}}{I_{OL}} = \frac{3.3\text{V} - 0.4\text{V}}{3.0\text{ mA}} \approx 967\ \Omega$$
  - **Selected Value:** $R_p = \mathbf{4.7\text{ k}\Omega \pm 1\%}$.
    $$t_r = 0.8473 \times 4.7\times 10^3\ \Omega \times 77\times 10^{-12}\text{ F} \approx \mathbf{306\text{ ns}} \le 1000\text{ ns}$$
    The $306\text{ ns}$ rise time guarantees crisp square-wave transitions and exceptional noise immunity.

#### 3.2.3. Silicon Pin Characteristics: GPIO 42 & GPIO 2
* **GPIO 42 Strapping & JTAG Considerations:** On the ESP32-S3, GPIO 42 defaults to JTAG `MTMS` functionality during factory testing. However, the ESP32-S3 integrates an internal USB-to-JTAG/Serial converter. In user applications, standard software configuration disables hardware boundary scan on GPIO 42 and binds it cleanly to the I2C0 peripheral clock (`I2C0_SCL`) without any conflict.
* **GPIO 2 Open-Drain Integrity:** GPIO 2 is an RTC and general-purpose digital pin. When assigned to `I2C0_SDA`, the internal pull-up and pull-down transistors are disabled, allowing the external $4.7\text{ k}\Omega$ pull-up to pull the net to the $3.3\text{V}$ rail cleanly.

---

### 3.3. Actuator Output Subsystem: MOSFET Gate Driving (GPIO 4)

GPIO 4 is assigned to control the low-side N-channel power MOSFET switching stage for the 5V liquid pump.

```
 ESP32-S3 Core
 +-------------------+
 | GPIO 4 (LEDC PWM) |-----[ R_gate: 100 Ohm ]----+----> MOSFET Gate
 +-------------------+                         |
                                         [ R_pd: 10k Ohm ]
                                               |
                                          Common GND
```

#### 3.3.1. Drive Characteristics & Failsafe Network
* **Peripheral Mapping:** Driven by **LEDC (LED Control) Hardware Peripheral (Timer 0, Channel 0)**.
* **PWM Modulation Frequency:** $f_{\text{PWM}} = 10.0\text{ kHz}$. This frequency is well above the human audio perception band ($20\text{ Hz} - 20\text{ kHz}$ acoustic cutoff for micro-diaphragm pumps), eliminating audible coil whine while avoiding excessive dynamic switching losses ($P_{\text{sw}} = \frac{1}{2} C_{\text{iss}} V^2 f$).
* **Series Damping Resistor ($R_{\text{gate}} = 100\ \Omega$):**
  - Dampens parasitic LC high-frequency ringing formed by PCB trace inductance and the MOSFET gate-to-source input capacitance ($C_{\text{iss}} \approx 400 - 800\text{ pF}$).
  - Clamps peak MCU transient source current to:
    $$I_{\text{peak}} = \frac{3.3\text{V}}{100\ \Omega} = 33\text{ mA} \quad (\text{Transient for } < 50\text{ ns})$$
* **Gate Pull-Down Resistor ($R_{\text{pd}} = 10\text{ k}\Omega$):**
  - Connects directly from Gate to Source (GND).
  - During MCU power-on reset (POR), firmware flashing, or tri-state bootloader execution, GPIO 4 is high-impedance (floating). The pull-down resistor forces $V_{\text{GS}} = 0\text{V}$, preventing spurious, uncommanded pump activation that could cause vessel flooding.

---

## 4. Hardware Connection & Wiring Schematics

The complete interconnect topology between the ESP32-S3 and the external transducers is presented below:

```
===================================================================================================
                                      INTERCONNECT TOPOLOGY
===================================================================================================

    +-----------------------------------------------------------------------+
    |                          ESP32-S3 CONTROLLER                          |
    |                                                                       |
    |  [ GPIO 1  ] --------------------+                                    |
    |  [ GPIO 2  ] ----------+         |                                    |
    |  [ GPIO 42 ] -----+    |         |                                    |
    |  [ GPIO 4  ] -+   |    |         |                                    |
    +---------------+---+----+---------+------------------------------------+
                    |   |    |         |
                    |   |    |         +------[ 1 kOhm ]--+---> [ SOIL SENSOR PIN AOUT ]
                    |   |    |                            |
                    |   |    |                          [100nF]
                    |   |    |                            |
                    |   |    |                           GND
                    |   |    |
                    |   |    +--+------------------+--------------------+---> [ AHT20/SHT30 SDA ]
                    |   |       |                  |                    |---> [ BH1750 SDA      ]
                    |   |   [4.7k Pullup]          |                    +---> [ OLED 1.3" SDA   ]
                    |   |       |                  |
                    |   +-------+--[4.7k Pullup]---+--------------------+---> [ AHT20/SHT30 SCL ]
                    |           |                  |                    |---> [ BH1750 SCL      ]
                    |         +3.3V              +3.3V                  +---> [ OLED 1.3" SCL   ]
                    |
                    +--[ 100 Ohm ]---+---> [ MOSFET MODULE GATE (SIG) ]
                                     |
                                 [10k Ohm]
                                     |
                                    GND
===================================================================================================
```

---

## 5. Production Firmware Driver Implementation (ESP-IDF C Framework)

The following production C implementation configures the assigned pins according to this hardware specification using native ESP-IDF v5.x APIs.

```c
/**
 * @file gpio_matrix_init.c
 * @brief Production Hardware Initialization for ESP32-S3 AIoT Node
 */

#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "driver/gpio.h"
#include "driver/i2c.h"
#include "driver/ledc.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_log.h"
#include "esp_err.h"

static const char *TAG = "HW_INIT";

/* Pin Definitions */
#define PIN_SOIL_ADC           ADC_CHANNEL_0      // GPIO 1 on ADC1
#define PIN_I2C_SDA            GPIO_NUM_2         // GPIO 2
#define PIN_I2C_SCL            GPIO_NUM_42        // GPIO 42
#define PIN_PUMP_GATE          GPIO_NUM_4         // GPIO 4

/* I2C Configuration */
#define I2C_MASTER_PORT        I2C_NUM_0
#define I2C_MASTER_FREQ_HZ     100000             // 100 kHz Standard Mode
#define I2C_MASTER_TX_BUF_DIS  0
#define I2C_MASTER_RX_BUF_DIS  0

/* LEDC PWM Configuration */
#define PUMP_LEDC_TIMER        LEDC_TIMER_0
#define PUMP_LEDC_MODE         LEDC_LOW_SPEED_MODE
#define PUMP_LEDC_CHANNEL      LEDC_CHANNEL_0
#define PUMP_LEDC_DUTY_RES     LEDC_TIMER_10_BIT  // Resolution: 0 - 1023
#define PUMP_LEDC_FREQ_HZ      10000              // 10 kHz Carrier

/* Mutex for Shared I2C Bus Arbitration */
static SemaphoreHandle_t s_i2c_mutex = NULL;
static adc_oneshot_unit_handle_t s_adc1_handle = NULL;
static adc_cali_handle_t s_adc1_cali_handle = NULL;

/**
 * @brief Initialize ADC1 Channel 0 on GPIO 1
 */
static esp_err_t init_soil_moisture_adc(void) {
    adc_oneshot_unit_init_cfg_t init_config = {
        .unit_id = ADC_UNIT_1,
        .ulp_mode = ADC_ULP_MODE_DISABLE,
    };
    ESP_ERROR_CHECK(adc_oneshot_new_unit(&init_config, &s_adc1_handle));

    adc_oneshot_chan_cfg_t config = {
        .bitwidth = ADC_BITWIDTH_12,
        .atten = ADC_ATTEN_DB_12,
    };
    ESP_ERROR_CHECK(adc_oneshot_config_channel(s_adc1_handle, PIN_SOIL_ADC, &config));

    // Initialize calibration scheme
    adc_cali_curve_fitting_config_t cali_config = {
        .unit_id = ADC_UNIT_1,
        .chan = PIN_SOIL_ADC,
        .atten = ADC_ATTEN_DB_12,
        .bitwidth = ADC_BITWIDTH_12,
    };
    esp_err_t ret = adc_cali_create_scheme_curve_fitting(&cali_config, &s_adc1_cali_handle);
    if (ret == ESP_OK) {
        ESP_LOGI(TAG, "ADC1 calibrated using eFuse Curve Fitting.");
    } else {
        ESP_LOGW(TAG, "eFuse calibration not supported; raw values will be used.");
    }

    ESP_LOGI(TAG, "GPIO 1 configured: ADC1_CH0 (12-bit, 12dB attenuation).");
    return ESP_OK;
}

/**
 * @brief Initialize Shared I2C Bus on GPIO 2 (SDA) and GPIO 42 (SCL)
 */
static esp_err_t init_shared_i2c_bus(void) {
    s_i2c_mutex = xSemaphoreCreateMutex();
    if (s_i2c_mutex == NULL) {
        ESP_LOGE(TAG, "Failed to create I2C bus mutex!");
        return ESP_ERR_NO_MEM;
    }

    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = PIN_I2C_SDA,
        .scl_io_num = PIN_I2C_SCL,
        .sda_pullup_en = GPIO_PULLUP_DISABLE, // Rely on external 4.7k resistors
        .scl_pullup_en = GPIO_PULLUP_DISABLE,
        .master.clk_speed = I2C_MASTER_FREQ_HZ,
        .clk_flags = 0,
    };
    ESP_ERROR_CHECK(i2c_param_config(I2C_MASTER_PORT, &conf));
    ESP_ERROR_CHECK(i2c_driver_install(I2C_MASTER_PORT, conf.mode, 
                                       I2C_MASTER_RX_BUF_DIS, 
                                       I2C_MASTER_TX_BUF_DIS, 0));

    ESP_LOGI(TAG, "Shared I2C initialized: SDA=GPIO2, SCL=GPIO42 @ 100kHz.");
    return ESP_OK;
}

/**
 * @brief Initialize Pump Gate Drive PWM on GPIO 4
 */
static esp_err_t init_pump_pwm(void) {
    ledc_timer_config_t ledc_timer = {
        .speed_mode       = PUMP_LEDC_MODE,
        .timer_num        = PUMP_LEDC_TIMER,
        .duty_resolution  = PUMP_LEDC_DUTY_RES,
        .freq_hz          = PUMP_LEDC_FREQ_HZ,
        .clk_cfg          = LEDC_AUTO_CLK
    };
    ESP_ERROR_CHECK(ledc_timer_config(&ledc_timer));

    ledc_channel_config_t ledc_channel = {
        .speed_mode     = PUMP_LEDC_MODE,
        .channel        = PUMP_LEDC_CHANNEL,
        .timer_sel      = PUMP_LEDC_TIMER,
        .intr_type      = LEDC_INTR_DISABLE,
        .gpio_num       = PIN_PUMP_GATE,
        .duty           = 0, // Initially OFF (0V gate)
        .hpoint         = 0
    };
    ESP_ERROR_CHECK(ledc_channel_config(&ledc_channel));

    ESP_LOGI(TAG, "GPIO 4 configured: LEDC PWM Output (10kHz, 10-bit). State: LOW.");
    return ESP_OK;
}

/**
 * @brief Master Hardware Initialization Function
 */
esp_err_t bsp_hardware_init(void) {
    ESP_LOGI(TAG, "Starting Master GPIO Subsystem Initialization...");
    ESP_ERROR_CHECK(init_soil_moisture_adc());
    ESP_ERROR_CHECK(init_shared_i2c_bus());
    ESP_ERROR_CHECK(init_pump_pwm());
    ESP_LOGI(TAG, "Master GPIO Subsystem initialized successfully.");
    return ESP_OK;
}
```

---

## 6. Real-Time Bus Arbitration & Multi-Threading Safety

Because the 1.3" OLED display (SH1106) transfers large graphical framebuffers ($128 \times 64 / 8 = 1024\text{ Bytes}$) over the same two wires used by time-critical sensors (AHT20/SHT30, BH1750), **bus contention and priority inversion** must be prevented.

### 6.1. Mutex Locking Protocol
All FreeRTOS tasks interacting with the I2C bus must obtain the `s_i2c_mutex` token before asserting a START condition:

```c
esp_err_t i2c_bus_read_sensor(uint8_t dev_addr, uint8_t *data, size_t len) {
    if (xSemaphoreTake(s_i2c_mutex, pdMS_TO_TICKS(50)) == pdTRUE) {
        esp_err_t err = i2c_master_read_from_device(I2C_MASTER_PORT, dev_addr, 
                                                    data, len, pdMS_TO_TICKS(20));
        xSemaphoreGive(s_i2c_mutex);
        return err;
    }
    ESP_LOGW("I2C_BUS", "Bus busy; failed to acquire mutex for device 0x%02X", dev_addr);
    return ESP_ERR_TIMEOUT;
}
```

### 6.2. Frame Slice Transmission for Display Updates
* Sending an entire 1024-byte framebuffer in one transaction locks the bus for $\approx 105\text{ ms}$ at $100\text{ kHz}$, preventing environmental reads.
* **Solution:** The display driver transmits the framebuffer in **8 separate page chunks (128 bytes per page)**. Between each page transmission, the display task yields the CPU and gives up the mutex for $2\text{ ms}$, allowing sensor polling tasks to execute without latency spikes.

---

## 7. Verification & Oscilloscope Acceptance Protocol

| Test ID | Test Category | Target Interface | Verification Procedure | Pass / Fail Acceptance Criteria |
| :--- | :--- | :--- | :--- | :--- |
| **TEST-PIN-01** | Analog Linearity & Noise | GPIO 1 (`ADC1_CH0`) | Inject calibrated DC voltages ($1.20\text{V} - 2.80\text{V}$) via bench calibrator; measure peak-to-peak noise with oscilloscope. | Noise floor $V_{p-p} \le 15\text{ mV}$; ADC conversion error $\le \pm 1.5\%$. |
| **TEST-PIN-02** | I2C Signal Rise Time | GPIO 2 (`SDA`) & GPIO 42 (`SCL`) | Probe lines with $500\text{ MHz}$ active probe with all 3 slaves connected. Measure rise time ($10\% \to 90\%$). | Rise time $t_r \le 400\text{ ns}$ (well below $1000\text{ ns}$ specification limit). |
| **TEST-PIN-03** | Multi-Drop Bus Arbitration | GPIO 2 & GPIO 42 | Trigger OLED page refresh simultaneously with periodic sensor reading tasks. | Zero `ESP_ERR_TIMEOUT` or bus collisions across 1,000 consecutive cycles. |
| **TEST-PIN-04** | PWM Gate Drive Waveform | GPIO 4 (`LEDC_PWM`) | Probe MOSFET gate during $10\text{ kHz}$ switching at $0\%$, $50\%$, and $100\%$ duty cycles. | Rise time $t_r \le 80\text{ ns}$; fall time $t_f \le 80\text{ ns}$; overshoot $\le 0.3\text{V}$. |
| **TEST-PIN-05** | Bootloader Failsafe State | GPIO 4 (`LEDC_PWM`) | Monitor GPIO 4 with logic analyzer during chip reset, UART bootloading, and hard power cycles. | Voltage strictly maintains $0.00\text{V} \pm 0.05\text{V}$; pump never flinches. |

---