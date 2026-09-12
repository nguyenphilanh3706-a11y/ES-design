# SYSTEM TECHNICAL SPECIFICATION: ADAPTIVE AIoT IRRIGATION NODE
## Autonomous Plant Care System for Extended Absence with On-Device TinyML (ESP32-S3 + LSTM)

---

**Document Identifier:** AIOT-IRRIG-SPEC-2026-V2.1  
**Project Title:** Adaptive Autonomous Plant Irrigation Node (ESP32-S3 TinyML System)  
**System Classification:** Edge AIoT Embedded Cyber-Physical System  
**Target Microcontroller:** Espressif ESP32-S3 (Xtensa Dual-Core 32-bit LX7, Vector Extensions)  
**Power Topology:** Direct Single 5.0V DC Rail (External Buck Step-Down Omitted; Integrated On-Board LDO)  
**Document Type:** Comprehensive System Requirements & Technical Design Specification  
**Roles & Contributors:**
- Embedded Hardware & Firmware Specialist (Member A)
- TinyML & IoT Systems Architect (Member B)

---

## 1. Executive Summary & System Objectives

### 1.1. Problem Statement
Maintaining domestic and greenhouse potted plants during extended human absence (e.g., business trips, vacations lasting 7 to 21 days) presents a dual failure risk:
1. **Under-watering / Dehydration:** Leads to plant wilting, irreversible root desiccation, and plant mortality.
2. **Over-watering & Reservoir Depletion:** Traditional timer-based or primitive threshold-based irrigation systems dispense static water volumes regardless of environmental changes. This causes localized soil saturation, root hypoxia (root rot), fungal pathogen proliferation, and rapid premature depletion of limited water reservoirs.

### 1.2. Operational Concept & Scope
The **Adaptive AIoT Irrigation Node** is a self-contained, edge-intelligent embedded system deployed directly on containerized plants. Operating on an Espressif **ESP32-S3** microcontroller, the node integrates physical environmental sensing, local machine learning inference (TinyML), precision micro-drip actuation, and wireless cloud telemetry.

Power is delivered via a **direct, single 5.0V DC supply rail** (e.g., standard 5V/2A USB-C wall adapter or regulated 5V power pack), completely eliminating the need for an external discrete step-down buck converter module (such as SY8089 or MP1584EN). The 5V bus directly powers the liquid pump and feeds the ESP32-S3 development board's integrated Low-Dropout (LDO) regulator to generate the clean 3.3V logic rail.

Rather than relying on reactive hysteretic control (e.g., watering only when soil moisture drops below a fixed threshold), the node utilizes an **On-Device Long Short-Term Memory (LSTM) Deep Learning Model** to forecast continuous **Soil Moisture Depletion / Evapotranspiration (ET)** over 6-hour, 12-hour, and 24-hour predictive horizons. By combining historical environmental time series (temperature, relative humidity, light irradiance, and soil moisture), the system calculates an optimized **Dynamic Water Budget**. This budget maintains soil homeostasis, defers irrigation away from peak daytime evaporation periods, and stretches a finite 5.0-liter reservoir across extended absence periods exceeding 20 days.

### 1.3. Key Performance Indicators (KPIs) & Target Acceptance Thresholds
The system design satisfies the following quantitative benchmarks:

| Metric Category | Key Performance Indicator (KPI) | Target Specification | Verification Method |
| :--- | :--- | :--- | :--- |
| **Water Conservation** | Water savings vs. Naive Bang-Bang Threshold | $\ge 35.0\%$ volumetric reduction | 7-day comparative bench test |
| **Reservoir Autonomy** | Continuous operational duration (5.0L reservoir) | $\ge 20	ext{ days}$ (standard potted ficus/fern) | Long-term vacation simulation |
| **Power Supply Stability** | Voltage sag on 3.3V logic rail during pump startup | $\Delta V_{3V3} \le 80	ext{ mV}$ (No MCU brownout) | Oscilloscope capture @ motor inrush |
| **System Autonomy** | Continuous operational reliability on 5V Adapter | $100\%$ uptime (unlimited runtime) | 30-day continuous soak test |
| **Edge AI Accuracy** | LSTM Evapotranspiration Prediction MAE | $\le 2.2\%	ext{ Volumetric Water Content (VWC)}$ | Test dataset evaluation on target MCU |
| **Edge AI Accuracy** | LSTM Evapotranspiration Prediction RMSE | $\le 3.0\%	ext{ VWC}$ across 24h horizon | Root-mean-squared error verification |
| **Inference Latency** | Full INT8 LSTM forward pass execution time | $\le 45	ext{ ms}$ @ $240	ext{ MHz}$ core clock | Hardware timer profiling (`esp_timer`) |
| **Memory Footprint** | Flash model footprint (`model_data.h`) | $\le 35	ext{ KB}$ (well within 100 KB budget) | Binary size inspection (`size` utility) |
| **Memory Footprint** | RAM Tensor Arena allocation | $\le 28	ext{ KB}$ internal SRAM | Static arena memory instrumentation |
| **Hydraulic Safety** | Dry-run detection & pump cutoff latency | $\le 100	ext{ ms}$ upon float switch trip | Hardware fault injection test |
| **Hydraulic Safety** | Maximum continuous pumping runaway watchdog | $\le 60.0	ext{ seconds}$ hard ceiling | Hardware timer watchdog interlock |

---

## 2. System Architecture & High-Level Design

### 2.1. Multi-Tier Architectural Topology
The system is partitioned into six functional, decoupled architectural tiers:

```
+-----------------------------------------------------------------------------------+
|                           TIER 6: CLOUD & TELEMETRY                               |
|          MQTT Broker (HiveMQ/Mosquitto) <---> Web / Mobile React Dashboard        |
+------------------------------------------^----------------------------------------+
                                           | (Wi-Fi 802.11 b/g/n / TLS 1.2 / SNTP)
+------------------------------------------v----------------------------------------+
|                      TIER 5: ON-DEVICE TINYML INFERENCE ENGINE                    |
|    TensorFlow Lite for Microcontrollers (TFLM) + ESP-NN Vector Acceleration       |
|    [Full INT8 Quantized Multi-Horizon LSTM: 24h Window -> Delta VWC Predictions]   |
+------------------------------------------^----------------------------------------+
                                           |
+------------------------------------------v----------------------------------------+
|                   TIER 4: EMBEDDED FIRMWARE & REAL-TIME OS (ESP-IDF)              |
|   FreeRTOS Tasks | FSM State Machine | Water Budget Engine | Ring Buffer | Failsafe|
+------------------------------------------^----------------------------------------+
                                           | (HAL, Drivers, I2C, ADC, LEDC PWM)
+------------------------------------------v----------------------------------------+
|                      TIER 3: CORE COMPUTE MICROCONTROLLER                         |
|      Espressif ESP32-S3-WROOM-1 (Xtensa Dual-Core LX7 @ 240MHz, 512KB SRAM)       |
+------------------------------------------^----------------------------------------+
                                           |
+------------------------------------------v----------------------------------------+
|                TIER 2: DIRECT 5.0V POWER & ACTUATION INTERFACE                    |
|  Single 5.0V Bus | Board Onboard LDO (5V->3.3V) | Logic N-MOSFET Low-Side Driver  |
|  Bulk Inrush Buffer (1000uF Low-ESR) | Flyback Diode (1N5819) | RC Snubber Stage  |
+------------------------------------------^----------------------------------------+
                                           |
+------------------------------------------v----------------------------------------+
|                       TIER 1: PHYSICAL SENSORS & HYDRAULICS                       |
|  Capacitive Soil v1.2 | AHT20 (Temp/Hum) | BH1750 (Lux) | Float Switch | R385 Pump |
+-----------------------------------------------------------------------------------+
```

### 2.2. End-to-End Data Pipeline
The operational data pipeline executes in deterministic stages:
1. **Acquisition & Power Gating:** The MCU wakes from Light-Sleep, asserts power to the soil moisture probe via GPIO 5 for $20	ext{ ms}$, samples ADC1_CH3, reads environmental I2C telemetry from AHT20 and BH1750, then immediately cuts sensor excitation power to eliminate galvanic corrosion.
2. **Signal Conditioning:** Raw analog values pass through a 32-sample median rejection filter followed by an Exponential Moving Average (EMA) filter. Calibrated polynomial curves convert raw voltage to Volumetric Water Content percentage ($	ext{VWC}\%$).
3. **Circular Ring Buffering:** Hourly consolidated vectors $[T_{	ext{amb}}, RH_{	ext{amb}}, L_{	ext{irrad}}, 	heta_{	ext{soil}}]$ are pushed to a statically allocated 24-step circular buffer residing in SRAM.
4. **Quantized Feature Scaling:** The 24-step matrix is normalized using pre-computed MinMax calibration parameters and quantized into signed INT8 representations.
5. **On-Device LSTM Inference:** TFLM executes the neural graph using ESP-NN SIMD vector instructions, outputting predicted soil moisture depletion for $T+6	ext{h}$, $T+12	ext{h}$, and $T+24	ext{h}$.
6. **Water Budget Arbiter & Safety Guard:** The decision logic balances current soil moisture against predicted depletion and diurnal time. If watering is approved, it calculates an exact water volume ($V_{	ext{water}}$ in milliliters) and maps it to a high-frequency LEDC PWM burst.
7. **Telemetry & Synchronization:** Operating state, sensor metrics, and predictive outputs are packaged into a JSON payload and dispatched via MQTT over Wi-Fi, synchronized to real-world time via SNTP.

---

## 3. Hardware & Electrical Subsystem Specifications

### 3.1. Direct 5.0V Power Distribution Network (PDN)

```
                     [ Direct 5.0V DC Supply ]
               (5V / 2.0A - 3.0A USB-C or DC Adapter)
                                  |
            +---------------------+---------------------+
            |                                           |
            | [Actuator Power Branch]                   | [MCU & Logic Power Branch]
            v                                           v
    +---------------+                           +---------------+
    | Bulk Capacitor| (1000uF / 16V Low-ESR)    | LC/RC Filter  | (10uH / 10uF + 100nF)
    +-------+-------+                           +-------+-------+
            |                                           |
            v                                           v
   [ R385 Diaphragm Pump ] (5V, 0.45A load)     [ ESP32-S3 Board VIN / 5V Pin ]
            |                                           |
   +--------+--------+                                  v
   | Flyback Diode   | (1N5819 Schottky)        [ Integrated On-Board LDO ]
   | RC Snubber      | (10 Ohm + 100nF)         (SGM2211 / AMS1117-3.3 / ME6211)
   +--------+--------+                                  |
            |                                           v
            v                                   [ Clean 3.3V System Rail ]
   [ Low-Side N-MOSFET ]                                |
   (LR7843 / AO3400 / IRLZ44N)                          +---> ESP32-S3 MCU Core
            |                                           +---> I2C Sensors (AHT20, BH1750)
            v                                           +---> Capacitive Probe (GPIO 5 Gated)
      GND Common Rail <=================================+
```

#### 3.1.1. Single 5.0V Direct Input Topology
* **Supply Specification:** Regulated $5.0	ext{V DC} \pm 5\%$ sourced directly from a standard $5	ext{V}/2	ext{A}$ USB-C power adapter or continuous DC supply.
* **Omission of External Buck Converter:** The external step-down buck module (e.g., SY8089 or MP1584EN) is **completely eliminated**. This simplifies PCB layout, reduces component count, eliminates high-frequency buck switching noise from the sensor lines, and cuts bill-of-materials cost.
* **Control Domain Regulation (3.3V Logic Rail):**
  - Stepped down internally from the board's 5.0V (VIN/VBUS) rail via the ESP32-S3 development board's integrated high-PSRR Low-Dropout (LDO) regulator (e.g., SGM2211, ME6211, or AMS1117-3.3 rated at $500	ext{mA} - 800	ext{mA}$).
  - Maximum continuous 3.3V logic consumption (MCU + Sensors) is $ pprox 180	ext{mA}$ during Wi-Fi transmission, well within the integrated LDO's thermal dissipation limit:
    $$P_{	ext{LDO}} = (V_{	ext{IN}} - V_{	ext{OUT}}) 	imes I_{	ext{avg}} = (5.0	ext{V} - 3.3	ext{V}) 	imes 0.08	ext{A}  pprox 0.136	ext{ W} \quad (	ext{negligible heat rise})$$
* **Decoupling Network on 3.3V Logic Rail:**
  - $1 	imes 10\ \mu	ext{F}$ tantalum or X5R ceramic capacitor at LDO output.
  - Local $100	ext{ nF}$ MLCC capacitors placed adjacent to ESP32-S3 $V_{DD}$ pins and sensor supply pins.

#### 3.1.2. Shared-Rail Transient Suppression & Brownout Prevention
Because the R385 pump motor and the ESP32-S3 MCU share the same 5.0V source, motor starting inrush current ($I_{	ext{start}}  pprox 1.2	ext{A} - 1.5	ext{A}$) and inductive turn-off transients must be rigorously isolated to prevent voltage droop on the 5V line:
* **Bulk Inrush Decoupling:**
  - A $1000\ \mu	ext{F} / 16	ext{V}$ (or $2200\ \mu	ext{F}$) Low-ESR ($< 0.04\ \Omega$) aluminum electrolytic capacitor is installed directly at the 5V motor feed node. During pump spin-up, this capacitor delivers instantaneous localized charge, holding the 5V bus droop to $\Delta V_{	ext{BUS}} \le 120	ext{ mV}$. Since the on-board LDO dropout voltage is $V_{	ext{dropout}} \le 300	ext{ mV}$, the 3.3V logic rail remains rock-solid at $3.30	ext{V} \pm 1\%$, completely preventing ESP32-S3 brownout resets.
* **Inductive Clamping (Flyback Protection):**
  - A high-speed Schottky freewheeling diode (**1N5819**, $40	ext{V} / 1	ext{A}$, $V_F \le 0.45	ext{V}$) connected directly across the R385 motor terminals in reverse-parallel to clamp inductive flyback spikes ($V = -L rac{di}{dt}$).
* **High-Frequency EMI Suppression (RC Snubber):**
  - A series snubber consisting of a $10\ \Omega$ (0.5W carbon film) resistor and a $100	ext{ nF}$ (100V ceramic) capacitor across the motor terminals to suppress brush arcing and RF interference on the I2C bus.
* **Low-Side Switching Stage:**
  - **MOSFET Selection:** Logic-level N-Channel MOSFET (**LR7843**, **AO3400A**, or **IRLZ44N**).
  - Gate threshold: $V_{GS(th)} \le 1.8	ext{V}$, ensuring complete channel saturation ($R_{DS(on)} < 15	ext{ m}\Omega$) at $3.3	ext{V}$ direct microcontroller gate drive.
  - Gate series resistor: $R_{	ext{gate}} = 100\ \Omega$ (limits GPIO peak charge current and dampens parasitic gate oscillations).
  - Gate pull-down resistor: $R_{	ext{pd}} = 10	ext{ k}\Omega$ tied to GND to guarantee reliable cut-off during bootloader execution or unprogrammed floating states.

---

### 3.2. Complete GPIO Hardware Allocation Matrix

| Pin Identifier | Net Name | Direction | Signal Type | Hardware Peripheral | Configuration & Electrical Characteristics |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **GPIO 4** | `SOIL_ADC_SIG` | Input | Analog | ADC1_CH3 | High-Z analog input; 12-bit resolution; decoupled with $100	ext{ nF}$ ceramic cap to GND. |
| **GPIO 5** | `SOIL_PWR_EN` | Output | Digital | General GPIO | Push-pull output; active-HIGH power gating switch ($20	ext{ ms}$ duty); max source current $12	ext{ mA}$. |
| **GPIO 6** | `PUMP_PWM_CTRL`| Output | Digital | LEDC Timer 0 | High-speed PWM; $10	ext{ kHz}$ carrier; 10-bit resolution ($0 - 1023$ duty); drives MOSFET gate via $100\ \Omega$. |
| **GPIO 7** | `LED_STATUS_GRN`| Output | Digital | General GPIO | System health indicator; drives Green LED via $330\ \Omega$ series resistor ($I_F  pprox 4.5	ext{ mA}$). |
| **GPIO 8** | `I2C_BUS_SDA` | In/Out | Open-Drain | I2C0 SDA | Shared sensor bus; external $4.7	ext{ k}\Omega$ pull-up to $3.3	ext{ V}$; clock speed $100	ext{ kHz}$. |
| **GPIO 9** | `I2C_BUS_SCL` | Output | Open-Drain | I2C0 SCL | Shared sensor bus clock; external $4.7	ext{ k}\Omega$ pull-up to $3.3	ext{ V}$. |
| **GPIO 11** | `FLOAT_SW_SENSE`| Input | Digital | RTC / GPIO | Reservoir level switch; internal pull-up enabled ($45	ext{ k}\Omega$). Closed to GND = FULL; Open = EMPTY. |
| **GPIO 15** | `LED_STATUS_RED`| Output | Digital | General GPIO | Fault/Lockout indicator; drives Red LED via $330\ \Omega$ series resistor ($I_F  pprox 4.5	ext{ mA}$). |
| **GPIO 16** | `BUZZER_ALARM` | Output | Digital | General GPIO | Acoustic transducer; drives active $5	ext{ V}$ piezoelectric buzzer ($2.4	ext{ kHz}$) via NPN switch. |
| **GPIO 0** | `BOOT_STRAP` | Input | Digital | Boot strap | Internal pull-up; pulled LOW only during UART flashing. |

---

### 3.3. Sensor Subsystem Specifications & Conditioning

#### 3.3.1. Capacitive Soil Moisture Sensor v1.2
* **Operating Principle:** High-frequency oscillation circuit ($1.5	ext{ MHz}$) measuring soil dielectric permittivity ($\epsilon_r$), which varies from $ pprox 3 - 5$ (dry soil) to $ pprox 80$ (pure water).
* **Corrosion Elimination Mechanism (Power Gating):** Traditional resistive sensors suffer irreversible electrochemical corrosion. The capacitive design avoids exposed metal, and $V_{CC}$ is energized via **GPIO 5** strictly during an active $20	ext{ ms}$ stabilization and acquisition window, maintaining a $99.98\%$ unpowered duty cycle.
* **ADC Configuration & Characterization:**
  - Peripheral: `ADC1_CH3` (GPIO 4). Assigned strictly to ADC1 to avoid coexistence collisions with ESP32-S3 Wi-Fi/Bluetooth hardware blocks (which lock ADC2).
  - Attenuation: `ADC_ATTEN_DB_12` providing an effective measurable linear dynamic range from $0.15	ext{ V}$ to $3.10	ext{ V}$.
  - eFuse Calibration: Dynamic voltage conversion via `esp_adc_cal_raw_to_voltage()` applying factory-burned piecewise non-linear compensation.
* **Digital Signal Filtering Pipeline:**
  - Burst sampling: $N = 32$ successive ADC conversions acquired at $250\ \mu	ext{s}$ intervals.
  - Rank-order 1D median filter applied to eliminate impulse switching transients and RF burst induced spikes.
  - Exponential Moving Average (EMA) applied across time steps:
    $$	heta_{	ext{filt}}[k] =  lpha \cdot 	heta_{	ext{raw}}[k] + (1 -  lpha) \cdot 	heta_{	ext{filt}}[k-1], \quad 	ext{where }  lpha = 0.25$$
* **Calibration Mapping to Volumetric Water Content (VWC %):**
  Using empirical two-point calibration on reference potting soil:
  - $V_{	ext{dry}} = 2.75	ext{ V}$ (Oven-dry soil, $0.0\%	ext{ VWC}$)
  - $V_{	ext{sat}} = 1.25	ext{ V}$ (Water-saturated soil, $100.0\%	ext{ VWC}$)
  $$	ext{VWC}(\%) = \left[ rac{V_{	ext{dry}} - V_{	ext{measured}}}{V_{	ext{dry}} - V_{	ext{sat}}} 
ight] 	imes 100\%$$

#### 3.3.2. AHT20 Ambient Temperature & Relative Humidity Sensor
* **Bus Interface:** I2C Standard Mode ($100	ext{ kHz}$), 7-bit hardware address `0x38`.
* **Relative Humidity Measurement:**
  - Dynamic Range: $0.0\%$ to $100.0\%	ext{ RH}$.
  - Resolution: $0.024\%	ext{ RH}$ (20-bit output).
  - Accuracy: $\pm 2.0\%	ext{ RH}$ at $25^\circ	ext{C}$.
* **Temperature Measurement:**
  - Dynamic Range: $-40.0^\circ	ext{C}$ to $+85.0^\circ	ext{C}$.
  - Resolution: $0.01^\circ	ext{C}$ (20-bit output).
  - Accuracy: $\pm 0.3^\circ	ext{C}$.
* **Error Handling:** Firmware validates cyclic redundancy check (CRC-8) bytes on every packet; corrupted frames are discarded, falling back to previous state estimates.

#### 3.3.3. BH1750 Ambient Light Intensity Sensor
* **Bus Interface:** I2C Standard Mode ($100	ext{ kHz}$), 7-bit hardware address `0x23` (`ADDR` pin tied to GND).
* **Dynamic Range:** $1	ext{ Lux}$ to $65,535	ext{ Lux}$.
* **Spectral Sensitivity:** Peak response matched to the human visual and photosynthetic active radiation (PAR) curve ($ pprox 560	ext{ nm}$).
* **Operating Mode:** One-Time High-Resolution Mode ($1	ext{ Lux}$ resolution, $120	ext{ ms}$ integration time); automatically unpowered between measurement cycles.

#### 3.3.4. Float Level Switch (Reservoir Protection)
* **Transducer Type:** Vertical Polypropylene (PP) magnetic reed switch.
* **Electrical Interface:** GPIO 11 with internal pull-up enabled ($45	ext{ k}\Omega$).
* **Logic States:**
  - `Logic 0` (Closed circuit to GND): Reservoir filled ($\ge 0.5	ext{ L}$). Normal operation.
  - `Logic 1` (Open circuit, pulled up to $3.3	ext{ V}$): Reservoir depleted ($< 0.5	ext{ L}$). Immediate hardware interlock triggered.

---

### 3.4. Hydraulic & Actuation Architecture
* **Pump Model:** Diaphragm Micro-Pump **R385** (Self-priming).
* **Hydraulic Operational Parameters:**
  - Nominal Operating Voltage: $5.0	ext{ V DC}$ (sourced directly from 5V bus).
  - Operating Current: $380	ext{ mA} - 450	ext{ mA}$ under load; stall inrush current: $1.2	ext{ A}$.
  - Suction Lift: Up to $2.0	ext{ meters}$; Hydraulic Head: Up to $3.0	ext{ meters}$.
  - Open Flow Rate: $1.2	ext{ L/min}$ ($20.0	ext{ mL/s}$).
* **Flow Regulation via PWM (LEDC):**
  - Carrier Frequency: $10.0	ext{ kHz}$ (exceeds human audible threshold, eliminating audible coil whine).
  - Duty Cycle Range: Micro-drip flow is calibrated between $35\%$ ($6.5	ext{ mL/s}$) and $75\%$ ($14.0	ext{ mL/s}$). Duty cycles below $30\%$ are inhibited to avoid motor stall and commutator burn.
* **Plumbing System Design:**
  - Distribution tubing: $4/7	ext{ mm}$ food-grade, UV-resistant black silicone tubing (prevents algal growth).
  - Emitters: 2-way pressure-compensating micro-drip arrows placed in the root zone ($5 - 8	ext{ cm}$ soil depth).
  - Anti-Siphoning Architecture: A siphon-break vent hole ($ arnothing 1.5	ext{ mm}$) drilled in the supply line above the maximum water reservoir surface line, ensuring water does not self-siphon after the pump is turned off.

---

## 4. Embedded Firmware Architecture & Real-Time OS

### 4.1. Layered Software Architecture

```
+-----------------------------------------------------------------------------------+
|                        APPLICATION LAYER (FreeRTOS Tasks)                         |
|  [SensorAcq_Task]  [TinyML_Inference_Task]  [WaterBudget_Task]  [Telemetry_Task]  |
+-----------------------------------------------------------------------------------+
|                     MIDDLEWARE & CYBER-PHYSICAL ENGINES                           |
|   Finite State Machine (FSM)  |  SRAM Ring Buffer (24x4)  |  Water Quota Engine   |
|   TensorFlow Lite Micro (TFLM)|  ESP-NN Accelerated Ops   |  LwIP / MQTT Client   |
+-----------------------------------------------------------------------------------+
|                       DEVICE DRIVER LAYER (Modular C/C++)                         |
|   AHT20 Driver (CRC8)  |  BH1750 Driver  |  Capacitive ADC Driver (eFuse Cal)     |
|   LEDC PWM Motor Driver|  GPIO Power-Gating Controller |  SNTP Real-Time Sync     |
+-----------------------------------------------------------------------------------+
|                    HARDWARE ABSTRACTION LAYER (HAL / ESP-IDF)                     |
|         ESP32-S3 Drivers: I2C Master, ADC1 Oneshot, RTC Timer, Light-Sleep        |
+-----------------------------------------------------------------------------------+
```

### 4.2. FreeRTOS Task Scheduling & Prioritization Matrix

| Task Name | Priority | Core Affinity | Stack Size | Activation Mechanism | Execution Period | Functionality Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`Task_SensorAcq`** | 4 | Core 0 | $4096	ext{ B}$ | Timer / Event Semaphore | 15m / 30m / 60m | Executes power gating, ADC burst sampling, I2C reads, signal filtering, buffer update. |
| **`Task_TinyML_Infer`**| 3 | Core 1 | $8192	ext{ B}$ | Synchronization Semaphore| Hourly (upon 24h vector) | Executes feature scaling, INT8 quantization, TFLM invocation, ET prediction extraction. |
| **`Task_WaterBudget`** | 3 | Core 1 | $4096	ext{ B}$ | Inference Completion Event | Hourly / Post-Inference | Runs homeostasis algorithm, evaluates day/night schedules, sets pending water quota. |
| **`Task_PumpActuator`**| 5 | Core 0 | $3072	ext{ B}$ | Water Command Queue | Asynchronous Demand | Controls LEDC PWM, monitors float switch, enforces 60s hard ceiling and 5m soaking delay. |
| **`Task_Telemetry`** | 2 | Core 0 | $6144	ext{ B}$ | State Transition / Periodic | Hourly / On Event | Connects Wi-Fi, syncs SNTP, dispatches MQTT telemetry, prepares system sleep. |

---

### 4.3. Finite State Machine (FSM) Specification

The system control flow is managed by an explicit, deterministic Finite State Machine:

```
                          +------------------------+
                          |    STATE_BOOT_INIT     |
                          +-----------+------------+
                                      | (Self-Test Passed)
                                      v
    +------------------->+-------------------------+<---------------------+
    |                    |    STATE_IDLE_MONITOR   |                      |
    |                    +------------+------------+                      |
    |                                 | (Timer Expired)                   |
    |                                 v                                   |
    |                    +-------------------------+                      |
    |                    |  STATE_DATA_ACQUISITION |                      |
    |                    +------------+------------+                      |
    |                                 | (24-Sample Ready)                 |
    |                                 v                                   |
    |                    +-------------------------+                      |
    |                    |   STATE_TINYML_INFER    |                      |
    |                    +------------+------------+                      |
    |                                 | (Water Needed & Safe)             |
    |                                 v                                   |
    |                    +-------------------------+                      |
    |                    |   STATE_WATERING_EXEC   |                      |
    |                    +------------+------------+                      |
    |                                 | (Pulse Complete)                  |
    |                                 v                                   |
    |                    +-------------------------+                      |
    |                    |    STATE_SOAKING_WAIT   |                      |
    |                    +------------+------------+                      |
    |                                 | (5 min Elapsed)                   |
    |                                 +-----------------------------------+
    |
    |   [ANY STATE] --- (Float Switch Empty OR Sensor Fault) ---> +-----------------------+
    +-------------------------------------------------------------| STATE_FAILSAFE_LOCKOUT|
                                                                  +-----------------------+
```

#### State Definitions & Transition Rules:
1. **`STATE_BOOT_INIT`:** Power-on self-test (POST). Initializes I2C peripherals, checks ADC rail, verifies presence of `model_data.h` in Flash, initializes FreeRTOS primitives. Transitions to `STATE_IDLE_MONITOR` if healthy; otherwise asserts `STATE_FAILSAFE_LOCKOUT`.
2. **`STATE_IDLE_MONITOR`:** Low-power waiting state. ESP32-S3 enters Light-Sleep, maintaining internal SRAM state while ticking FreeRTOS timers.
3. **`STATE_DATA_ACQUISITION`:** Wakes sensors, captures 32 ADC readings, polls AHT20/BH1750, pushes hourly record into the 24-step circular buffer.
4. **`STATE_TINYML_INFER`:** Triggered once per hour. Scales input tensor, executes INT8 TFLM forward pass, outputs predicted moisture dry-down ($\Delta	ext{VWC}_{6h, 12h, 24h}$).
5. **`STATE_WATERING_EXEC`:** Engages pump via LEDC PWM. Continuously polls float switch at $50	ext{ ms}$ intervals.
6. **`STATE_SOAKING_WAIT`:** Pumping stops. Sensor acquisition is strictly inhibited for **5 minutes** (blanking interval) to permit gravitational water distribution into the root column.
7. **`STATE_FAILSAFE_LOCKOUT`:** Hardware safety interlock. Triggered immediately upon float switch empty state, sensor disconnect, or watchdog timeout. Forces PWM to $0\%$, turns RED LED solid, activates buzzer, and dispatches an emergency MQTT alert.

---

### 4.4. Fault Tolerance & Safety Interlocks
* **Dry-Run Hardware Protection:** If the float switch opens during pumping, the MCU clears the PWM output within $\le 100	ext{ ms}$, preventing motor overheating and impeller damage.
* **Maximum Run Watchdog:** A hardware timer enforces a hard ceiling of **60.0 seconds** of continuous pumping per irrigation event. If this duration is exceeded (indicating broken tubing or soil sensor dislodgement), the pump is terminated unconditionally.
* **Sensor Integrity Diagnostics:**
  - Saturated high ($V_{ADC} > 3.0	ext{ V}$): Open circuit / probe unplugged.
  - Saturated low ($V_{ADC} < 0.2	ext{ V}$): Short circuit / damaged cable.
  - Both conditions immediately suspend automatic watering and enter failsafe fallback.

---
## 5. Edge AI & TinyML Subsystem Specification

### 5.1. Evapotranspiration (ET) Mathematical Formulation
Evapotranspiration in containerized indoor plants is governed by soil moisture dynamics, atmospheric vapor pressure deficit (VPD), and solar radiative heating. Approximating the FAO-56 Penman-Monteith relationship for indoor microclimates:

$$\Delta	heta_{t 	o t+H} = f(T_{	ext{amb}}, RH_{	ext{amb}}, L_{	ext{irrad}}, 	heta_{	ext{soil}})$$

The prediction target is formulated as the **Soil Moisture Depletion ($\Delta	ext{VWC}$)** across multi-step future horizons $H \in \{6	ext{h}, 12	ext{h}, 24	ext{h}\}$:
$$\Delta	heta_H = 	heta_{	ext{soil}}(t) - 	heta_{	ext{soil}}(t+H)$$

Anticipating moisture loss over a 24-hour window enables proactive micro-irrigation, avoiding midday thermal stress and surface evaporation.

---

### 5.2. Lookback Window & SRAM Ring Buffer Architecture
The input to the model is a sliding time-series tensor constructed from 24 continuous hourly observations:
$$\mathbf{X} \in \mathbb{R}^{24 	imes 4}$$

```c
typedef struct {
    float temp_c;        // Ambient Temperature in Celsius (10.0 - 45.0)
    float humidity_pct;  // Relative Humidity percentage (20.0 - 100.0)
    float light_lux;     // Ambient Irradiance in Lux (0.0 - 65535.0)
    float soil_vwc;      // Volumetric Soil Moisture percentage (0.0 - 100.0)
} sensor_record_t;

typedef struct {
    sensor_record_t buffer[24];
    uint8_t head_idx;
    uint8_t sample_count;
    bool is_buffer_full;
} ring_buffer_t;
```

* **Thread Safety:** Access to the ring buffer is arbitrated via a FreeRTOS Mutex (`xBufferMutex`).
* **Missing Data Imputation:** If a sensor read encounters a transient I2C bus collision or CRC failure, linear interpolation from adjacent hourly observations is executed automatically.

---

### 5.3. Deep Neural Network Architecture (Multi-Horizon LSTM)
The neural architecture is balanced to achieve sub-$50	ext{ ms}$ latency and minimal SRAM overhead on the Xtensa LX7 dual-core processor:

```
  Input Tensor: [Batch=1, TimeSteps=24, Features=4]
                         |
                         v
  +------------------------------------------------+
  |    Unidirectional LSTM Layer (24 Hidden Units)  |
  |    - Activation: Tanh                          |
  |    - Recurrent Activation: Hard Sigmoid        |
  |    - Gate Weights: [4 * 24 * (4 + 24 + 1)]     |
  +------------------------------------------------+
                         |
                         v Output at final step: [1, 24]
  +------------------------------------------------+
  |     Fully-Connected Dense Layer (16 Neurons)   |
  |     - Activation: ReLU                         |
  +------------------------------------------------+
                         |
                         v Output: [1, 16]
  +------------------------------------------------+
  |     Output Regression Layer (3 Neurons)        |
  |     - Activation: Linear                       |
  |     - Outputs: [Delta_6h, Delta_12h, Delta_24h] |
  +------------------------------------------------+
```

* **Total Learnable Parameters:** $ pprox 3,347$ parameters.
* **Loss Function:** Huber Loss ($\delta = 1.0$) to provide robustness against sensor outliers during training.
* **Optimization:** Adam Optimizer ($ lpha = 0.001$, $ eta_1 = 0.9$, $ eta_2 = 0.999$).

---

### 5.4. Post-Training Quantization (PTQ) & ESP-NN Microcontroller Deployment
To deploy on the ESP32-S3 without floating-point overhead, full 8-bit integer quantization is performed:
* **Quantization Scheme:** Full INT8 symmetric quantization for weights (per-channel) and activations (per-tensor).
* **Representative Dataset:** 1,000 empirical 24-hour sensor vectors representing clear-sky, overcast, rainy, and indoor AC microclimates.
* **Conversion Artifact:** The quantized graph is converted to a static C array:

```c
// File: model_data.h
#ifndef MODEL_DATA_H_
#define MODEL_DATA_H_

#include <stddef.h>

extern const unsigned char g_lstm_model_data[];
extern const size_t g_lstm_model_data_len;

#endif
```

#### On-Device Performance & Memory Metrics:
* **Flash Footprint (`.rodata`):** $18.4	ext{ KB}$ (Allocated in external SPI Flash, cached in I-Cache).
* **Tensor Arena RAM:** $24,576	ext{ Bytes}$ ($24	ext{ KB}$) allocated statically in internal SRAM0.
* **Inference Execution Time:** $34.2	ext{ ms}$ @ $240	ext{ MHz}$ core clock using Espressif **ESP-NN** optimized SIMD vector kernels.
* **Computational Energy per Forward Pass:** $E = 72	ext{ mA} 	imes 5.0	ext{ V} 	imes 0.0342	ext{ s}  pprox 12.3	ext{ mJ}$ from the 5V bus.