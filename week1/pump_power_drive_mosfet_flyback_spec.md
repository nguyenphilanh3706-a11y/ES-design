# HARDWARE DESIGN SPECIFICATION: PUMP POWER DRIVE CIRCUITRY
## Dual N-MOSFET Low-Side Switching Module (D4184/LR7843) & 1N4007 Inductive Flyback Clamping

---

**Document Identifier:** AIOT-DRV-MOSFET-FLYBACK-2026-V1.0  
**Project:** Adaptive Autonomous Plant Irrigation Node (ESP32-S3 + On-Device TinyML)  
**Subsystem:** Actuator Power Electronics & Hydraulic Driver Core (Member A)  
**Target Microcontroller:** Espressif ESP32-S3 (3.3V CMOS Logic Level, GPIO 4)  
**Actuator Load:** 5.0V DC Mini Micro-Diaphragm Liquid Pump ($I_{\text{run}} \approx 380\text{ mA}$, $I_{\text{inrush}} \approx 750\text{ mA}$)  
**Power Domain:** Centralized 5.0V DC Rail via USB Type-C  
**Document Status:** Production Engineering Release  

---

## 1. Executive Summary & Design Scope

This engineering specification establishes the electrical design, component sizing, and circuit implementation of the **Pump Power Driver Stage** for the ESP32-S3 AIoT Irrigation Node. 

Liquid diaphragm pumps utilize brushed DC electromagnetic motors characterized by significant armature inductance ($L_a$). Switching these high-current inductive loads using digital microcontroller outputs requires a dedicated solid-state switching interface combined with counter-electromotive force (Back-EMF) suppression.

### Key Architectural Provisions:
1. **Low-Side Solid-State Switch:** Implementation of a pre-engineered **Dual N-Channel MOSFET Module** populated with two parallel D4184 (AOD4184A) or LR7843 power transistors.
2. **Fail-Safe Gate Biasing:** Utilization of an integrated **$10\text{ k}\Omega$ internal pull-down resistor** directly across the MOSFET Gate-to-Source terminal to eliminate floating states during MCU power-on reset (POR) and flashing.
3. **Inductive Kickback Suppression:** Reverse-parallel installation of a **1N4007 Flyback Freewheeling Diode** directly across the motor output screw terminals to clamp inductive turn-off voltage spikes ($V = -L \frac{di}{dt}$) and protect the semiconductor switches from avalanche breakdown.

---

## 2. Dual N-MOSFET Module Architecture & Semiconductor Physics

### 2.1. Dual MOSFET Parallel Configuration (D4184 / LR7843)
Commercial driver modules typically utilize two TO-252 (DPAK) N-channel power MOSFETs connected in direct electrical parallel ($Q_{1A} \parallel Q_{1B}$).

```
                             +-------------------+
                             | Drain Terminal    |
                             +----+---------+----+
                                  |         |
                              D1  |         |  D2
                             +----+----+   +----+----+
                             |  Q1A    |   |  Q1B    |
       PWM / Trigger In ---->| Gate    |---| Gate    |
                             |  D4184  |   |  D4184  |
                             | Source  |   | Source  |
                             +----+----+   +----+----+
                                  |         |
                              S1  |         |  S2
                                  +----+----+
                                       |
                             +---------+---------+
                             | Source / GND Bus  |
                             +-------------------+
```

#### Electrical Parameter Comparison:

| Parameter | Symbol | AOD4184A (D4184) | LR7843 (IRLR7843) | Operating Conditions / Target Application |
| :--- | :---: | :---: | :---: | :--- |
| **Drain-Source Voltage Limit** | $V_{\text{DSS}}$ | $40\text{ V}$ | $30\text{ V}$ | Absolute maximum drain breakdown voltage |
| **Continuous Drain Current** | $I_D$ | $50\text{ A}$ | $161\text{ A}$ | @ $T_C = 25^\circ\text{C}$ (Silicon limited) |
| **Gate-to-Source Threshold** | $V_{\text{GS(th)}}$ | $1.7\text{V} - 2.6\text{V}$ | $1.0\text{V} - 3.0\text{V}$ | Logic-level conduction onset ($I_D = 250\ \mu\text{A}$) |
| **On-Resistance @ $V_{\text{GS}} = 4.5\text{V}$**| $R_{\text{DS(on)}}$| $\le 9.5\text{ m}\Omega$ | $\le 3.8\text{ m}\Omega$ | Low gate bias saturation |
| **Estimated $R_{\text{DS(on)}} @ 3.3\text{V}$** | $R_{\text{DS(on)}}$| $\approx 14.0\text{ m}\Omega$ | $\approx 6.5\text{ m}\Omega$ | Direct 3.3V ESP32-S3 logic gate drive |
| **Input Capacitance** | $C_{\text{iss}}$ | $1100\text{ pF}$ | $4380\text{ pF}$ | Gate capacitance per single FET |

### 2.2. Logic-Level Conduction & Conduction Loss Analysis
The ESP32-S3 operates exclusively from a $3.3\text{V}$ CMOS logic domain. When GPIO 4 is asserted HIGH:
$$V_{\text{GS}} = V_{\text{OH}} \approx 3.30\text{ V}$$

Because $V_{\text{GS}} = 3.30\text{V} > V_{\text{GS(th)(max)}} = 2.6\text{V}$, the conduction channel is fully inverted, operating safely in the linear (ohmic) saturation region.

#### Parallel Channel Equivalent Resistance ($R_{\text{eq}}$):
Due to the parallel silicon configuration, the effective static on-resistance is halved:
$$R_{\text{eq}} = R_{\text{DS(on), 1A}} \parallel R_{\text{DS(on), 1B}} = \frac{R_{\text{DS(on)}}}{2}$$
* For D4184: $R_{\text{eq}} \approx \frac{14.0\text{ m}\Omega}{2} = \mathbf{7.0\text{ m}\Omega}$
* For LR7843: $R_{\text{eq}} \approx \frac{6.5\text{ m}\Omega}{2} = \mathbf{3.25\text{ m}\Omega}$

#### Power Dissipation Under Dynamic Loading:
1. **Steady-State Operational Load ($I_{\text{run}} = 380\text{ mA}$):**
   $$P_{\text{cond, ss}} = I_{\text{run}}^2 \times R_{\text{eq}} = (0.380\text{ A})^2 \times 0.007\ \Omega = \mathbf{1.01\text{ mW}}$$
2. **Peak Inrush Window ($I_{\text{inrush}} = 750\text{ mA}$ for $\Delta t \approx 50\text{ ms}$):**
   $$P_{\text{cond, inrush}} = I_{\text{inrush}}^2 \times R_{\text{eq}} = (0.750\text{ A})^2 \times 0.007\ \Omega = \mathbf{3.94\text{ mW}}$$

**Thermal Verdict:** The maximum conduction loss is below **$4.0\text{ mW}$**. The junction-to-ambient thermal resistance of the TO-252 package ($\theta_{\text{JA}} \approx 50^\circ\text{C/W}$) yields a negligible temperature rise:
$$\Delta T = P_{\text{cond}} \times \theta_{\text{JA}} = 0.004\text{ W} \times 50^\circ\text{C/W} = \mathbf{0.20^\circ\text{C}}$$
The module operates essentially at ambient temperature without requiring heat sinks.

---

### 2.3. Integrated $10\text{ k}\Omega$ Internal Pull-Down Resistor ($R_{\text{pd}}$)
The driver module integrates an on-board $10\text{ k}\Omega$ resistor tied directly between the Gate control net and the GND terminal.

```
 ESP32-S3 Core
 +--------------------+
 | GPIO 4 (LEDC PWM)  |----+----------------------------------> Module TRIG Terminal
 +--------------------+    |                                        |
                           |                                   +----+----+
                           |                                   | Gate    |
                     (PCB Stray C)                       [ 10k Ohm ] Q1A/Q1B
                           |                                   | Source  |
                          GND                                  +----+----+
                                                                    |
                                                                Power GND
```

#### Engineering Functions of $R_{\text{pd}}$:
1. **Floating Gate Prevention (High-Z Immunity):** During microcontroller power-on reset, firmware bootloader execution, or serial flashing, all ESP32-S3 GPIO pins enter a high-impedance tri-state mode. Without a pull-down resistor, minute electrostatic charges or capacitive coupling could charge the gate above $V_{\text{GS(th)}}$, causing the pump to run uncontrolled and flood the plant container.
2. **Gate Discharge Dynamics:** When GPIO 4 is driven LOW, $R_{\text{pd}}$ assists the GPIO active pull-down driver in draining the combined input capacitance ($C_{\text{iss, total}} = 2 \times C_{\text{iss}} \approx 2200\text{ pF}$ for D4184).
   $$\tau_{\text{discharge}} = R_{\text{pd}} \times C_{\text{iss, total}} = 10\times 10^3\ \Omega \times 2200\times 10^{-12}\text{ F} = \mathbf{22.0\ \mu\text{s}}$$
   When driven actively by the ESP32-S3 push-pull stage ($R_{\text{driver}} \approx 30\ \Omega$), the turn-off transition is accelerated to $< 80\text{ ns}$.

---

## 3. Inductive Flyback Physics & 1N4007 Diode Suppression

### 3.1. Mathematical Origin of Inductive Turn-Off Spikes
The pump motor consists of electromagnetic coils exhibiting continuous magnetic energy storage. The fundamental differential equation governing the armature winding voltage is:
$$v_L(t) = L_a \frac{di_m(t)}{dt}$$

When the MOSFET abruptly transitions from ON to OFF to throttle or cease pumping:
1. The current forced through the motor winding drops from $I_0 \approx 380\text{ mA}$ to $0\text{ A}$ across the MOSFET turn-off fall time ($t_f \approx 50\text{ ns}$).
2. The instantaneous rate of current change is massively negative:
   $$\frac{di}{dt} = \frac{0 - 0.380\text{ A}}{50 \times 10^{-9}\text{ s}} = -7.6 \times 10^6\text{ A/s}$$
3. According to Lenz's Law, the inductor reverses its terminal polarity to maintain current flow:
   $$V_{\text{spike}} = -L_a \left(-7.6 \times 10^6\text{ A/s}\right) = +L_a \times 7.6 \times 10^6\text{ V}$$
4. For an armature winding inductance of $L_a = 500\ \mu\text{H}$:
   $$V_{\text{spike}} = (500 \times 10^{-6}\text{ H}) \times (7.6 \times 10^6\text{ A/s}) = \mathbf{+3,800\text{ V (Theoretical)}}$$

Without a freewheeling clamp path, the voltage at the MOSFET Drain node rises catastrophically until exceeding the silicon breakdown rating ($V_{\text{DSS}} = 30\text{V} - 40\text{V}$). The MOSFET is forced into avalanche breakdown, leading to permanent gate oxide punch-through, thermal runaway, and destruction.

---

### 3.2. 1N4007 Reverse-Parallel Clamping Mechanics
To prevent overvoltage destruction, a **1N4007 standard silicon rectifier diode** is connected in **reverse-parallel** directly across the motor terminal outputs (`OUT+` and `OUT-`).

```
                    +5.0V DC Actuator Bus
                              |
                              +-----------------------+
                              |                       |
                              | Motor (+)             | Cathode (Band)
                           +-----+                 +-----+
                           |     |                 |     |
                           |  M  | Pump Motor      |  D  | 1N4007 Flyback
                           |     |                 |     |
                           +-----+                 +-----+
                              | Motor (-)             | Anode
                              |                       |
                              +-----------+-----------+
                                          |
                                          v Drain Node (V_Drain)
                                   +--------------+
                                   | D4184/LR7843 |
                                   | Dual MOSFET  |
                                   +------+-------+
                                          | Source
                                          v
                                      Power GND
```

#### Operating State Matrix:

| Operational State | MOSFET Channel | Motor Voltage Polarities | 1N4007 Diode State | Circuit Current Path |
| :--- | :---: | :---: | :---: | :--- |
| **PWM ON Stage** | **Saturated (ON)** | Motor (+) = +5.0V<br>Motor (-) $\approx 0.003\text{V}$ | **REVERSE-BIASED**<br>(Cathode = 5V, Anode = 0V)<br>$I_{\text{leakage}} \le 5\ \mu\text{A}$ | +5V Rail $\to$ Motor Coils $\to$ MOSFET Drain $\to$ Source $\to$ Power GND. |
| **PWM OFF Edge** | **Cut-Off (OFF)** | Terminal polarity flips:<br>Motor (-) climbs $> +5.0\text{V}$ | **FORWARD-BIASED**<br>(Cathode = 5V, Anode $> 5.7\text{V}$)<br>Conduction engages | Motor (-) $\to$ 1N4007 Anode $\to$ Cathode $\to$ Motor (+) terminal. |

#### Maximum Clamped Drain Voltage ($V_{\text{Drain, max}}$):
When the diode enters forward conduction during turn-off, the voltage at the MOSFET Drain terminal is rigorously clamped:
$$V_{\text{Drain, max}} = V_{\text{BUS}} + V_{F(\text{1N4007})}$$
Where $V_F \approx 0.85\text{V} - 1.0\text{V}$ at $I_F = 380\text{ mA}$.
$$V_{\text{Drain, max}} = 5.00\text{ V} + 0.90\text{ V} = \mathbf{5.90\text{ V DC}}$$

The Drain voltage is strictly constrained to **$5.90\text{V}$**, which is vastly below the MOSFET breakdown limit ($V_{\text{DSS}} = 30\text{V} - 40\text{V}$), providing an extraordinary **$> 80\%$ silicon voltage safety margin**.

---

### 3.3. 1N4007 Diode Parameter Sizing & Performance Evaluation

| Parameter | Symbol | 1N4007 Specification | Application Requirement | Compliance Status |
| :--- | :---: | :---: | :---: | :---: |
| **Peak Repetitive Reverse Voltage**| $V_{\text{RRM}}$ | $1000\text{ V}$ | $5.0\text{ V DC}$ | **Exceeds spec by 200x** |
| **Average Forward Current** | $I_{F(\text{AV})}$ | $1.0\text{ A}$ | $0.380\text{ A}$ continuous | **Passed (62% margin)** |
| **Non-Repetitive Peak Surge Current**| $I_{\text{FSM}}$ | $30.0\text{ A}$ ($8.3\text{ ms}$ half-sine) | $0.750\text{ A}$ peak inrush | **Passed (40x surge margin)** |
| **Forward Voltage Drop** | $V_F$ | $1.1\text{ V}$ max @ $1.0\text{ A}$ | $\approx 0.85\text{ V}$ @ $380\text{ mA}$ | **Passed (Damps spike to 5.85V)**|
| **Reverse Recovery Time** | $t_{rr}$ | $\approx 2.0 - 3.0\ \mu\text{s}$ (Typical) | Switching frequency dependent | **Evaluated in Section 3.4** |

#### 3.3.4. Energy Dissipation in the Freewheeling Loop
The magnetic energy stored in the armature coil prior to turn-off is:
$$E_L = \frac{1}{2} L_a I_{\text{run}}^2 = \frac{1}{2} (500 \times 10^{-6}\text{ H}) \times (0.380\text{ A})^2 = \mathbf{36.1\ \mu\text{J}}$$
During freewheeling, this energy circulates in the closed loop comprising the motor winding resistance ($R_a \approx 6.67\ \Omega$) and the forward resistance of the 1N4007 diode. The total decay time constant is:
$$\tau_{\text{decay}} = \frac{L_a}{R_a + R_{\text{diode}}} \approx \frac{500 \times 10^{-6}\text{ H}}{6.67\ \Omega + 1.2\ \Omega} \approx \mathbf{63.5\ \mu\text{s}}$$
The stored magnetic energy is completely dissipated into thermal energy within $5 \times \tau_{\text{decay}} \approx 317\ \mu\text{s}$.

---

## 4. Hardware Connection & Complete Wiring Schematic

The schematic below outlines the exact electrical interconnections between the ESP32-S3 controller board, the Dual MOSFET power module, the 1N4007 flyback diode, and the 5V DC pump:

```
===================================================================================================
                             COMPLETE ACTUATOR DRIVE SCHEMATIC
===================================================================================================

   [ ESP32-S3 Controller ]
   +--------------------+
   | GPIO 4 (LEDC PWM)  |----------[ 100 Ohm ]---------------------+
   |                    |                                          |
   | GND                |------------------------------+           |
   +--------------------+                              |           |
                                                       |           |
                                                       v           v
   +---------------------------------------------------------------------------------------+
   |                       DUAL N-MOSFET MODULE (D4184 / LR7843)                           |
   |                                                                                       |
   |  [ CONTROL TERMINALS ]                                                                |
   |    - GND / Trigger (-)  <-------------------------+                                   |
   |    - PWM / Trigger (+)  <-------------------------------------+                       |
   |                                                               |                       |
   |    (Internal Pull-Down)                                       |                       |
   |    GND ---[ 10 kOhm ]-----------------------------------------+                       |
   |                                                               |                       |
   |  [ POWER TERMINALS ]                                      Gate Pins                   |
   |    - VIN (+) <--------- +5.0V DC Centralized Rail             |                       |
   |    - VIN (-) <--------- Main Power GND                        v                       |
   |                                                         +------------+                |
   |    - VOUT (+) <-------- Shunted internally to VIN (+)   | Q1A // Q1B |                |
   |    - VOUT (-) <-------- Connected to MOSFET Drain Pin --| (Parallel) |                |
   +---------------------------------------------------------+----+-------+----------------+
              |                                                   |
              | VOUT (+)                                          | VOUT (-) (Switched GND)
              |                                                   |
              +-----------------------+                           |
                                      |                           |
                                      |                           |
                                      v Anode                     v Cathode (White Band)
                                  +-----------------------------------+
                                  |   1N4007 REVERSE FLYBACK DIODE    |
                                  |   (Mounted across Screw Terminals)|
                                  +-----------------+-----------------+
                                                    |
                                      +-------------+-------------+
                                      |                           |
                                      v Terminal 1 (+)            v Terminal 2 (-)
                                  +-----------------------------------+
                                  |                                   |
                                  |     5V DC MINI LIQUID PUMP        |
                                  |       (Brushed DC Motor)          |
                                  |                                   |
                                  +-----------------------------------+
===================================================================================================
```

### 4.1. Terminal Connection Table

| Physical Connector | Terminal Label | Connected Net | Electrical Function & Wire Sizing |
| :--- | :---: | :--- | :--- |
| **Module Signal Header** | `PWM / TRIG (+)` | ESP32-S3 GPIO 4 (via $100\ \Omega$) | 3.3V Logic PWM control signal ($26\text{ AWG}$). |
| **Module Signal Header** | `GND / TRIG (-)` | ESP32-S3 System Digital GND | Ground reference return for gate drive ($26\text{ AWG}$). |
| **Module Input Block** | `VIN (+)` | +5.0V DC USB-C VBUS Rail | Main actuator power feed ($20\text{ AWG}$ stranded wire). |
| **Module Input Block** | `VIN (-)` | System Power GND | Main high-current return path ($20\text{ AWG}$ stranded wire). |
| **Module Output Block**| `VOUT (+)` | Motor Positive (+) & 1N4007 Cathode | Positive inductive supply node ($20\text{ AWG}$). |
| **Module Output Block**| `VOUT (-)` | Motor Negative (-) & 1N4007 Anode | Switched low-side return node ($20\text{ AWG}$). |

---

## 5. Firmware Drive Implementation & PWM Tuning

### 5.1. PWM Frequency Trade-Off: 1N4007 vs. Fast Recovery
Standard rectifier diodes like the **1N4007** feature a reverse recovery time of $t_{rr} \approx 2.0 - 3.0\ \mu\text{s}$.
* If modulated at ultra-high PWM frequencies ($> 50\text{ kHz}$), a $2\ \mu\text{s}$ recovery delay would result in cross-conduction shoot-through current when the MOSFET turns on while the diode is still recovering.
* **Firmware Frequency Tuning:**
  The hardware PWM driver on **GPIO 4** is configured to **$10\text{ kHz}$ carrier frequency** ($T = 100\ \mu\text{s}$) or lower.
  At $10\text{ kHz}$, the $2\ \mu\text{s}$ recovery time represents only $2.0\%$ of the cycle period:
  $$\text{Duty Overhead} = \frac{t_{rr}}{T_{\text{PWM}}} = \frac{2.0\ \mu\text{s}}{100\ \mu\text{s}} = 2.0\%$$
  This confirms safe operation without diode overheating.

### 5.2. ESP-IDF C Driver Implementation

```c
/**
 * @file pump_mosfet_driver.c
 * @brief Precision PWM Gate Driver for D4184/LR7843 Module with Failsafe
 */

#include "driver/ledc.h"
#include "driver/gpio.h"
#include "esp_err.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define PUMP_GATE_GPIO         (GPIO_NUM_4)
#define PUMP_LEDC_TIMER        (LEDC_TIMER_0)
#define PUMP_LEDC_MODE         (LEDC_LOW_SPEED_MODE)
#define PUMP_LEDC_CHANNEL      (LEDC_CHANNEL_0)
#define PUMP_PWM_FREQ_HZ       (10000)               // 10 kHz Carrier
#define PUMP_PWM_RESOLUTION    (LEDC_TIMER_10_BIT)   // Resolution: 0 - 1023

static const char *TAG = "MOSFET_DRV";

/**
 * @brief Initialize GPIO 4 and LEDC PWM Timer
 */
esp_err_t pump_driver_init(void) {
    // 1. Configure LEDC Timer
    ledc_timer_config_t timer_cfg = {
        .speed_mode       = PUMP_LEDC_MODE,
        .timer_num        = PUMP_LEDC_TIMER,
        .duty_resolution  = PUMP_PWM_RESOLUTION,
        .freq_hz          = PUMP_PWM_FREQ_HZ,
        .clk_cfg          = LEDC_AUTO_CLK
    };
    ESP_ERROR_CHECK(ledc_timer_config(&timer_cfg));

    // 2. Configure LEDC Channel on GPIO 4
    ledc_channel_config_t ch_cfg = {
        .speed_mode     = PUMP_LEDC_MODE,
        .channel        = PUMP_LEDC_CHANNEL,
        .timer_sel      = PUMP_LEDC_TIMER,
        .intr_type      = LEDC_INTR_DISABLE,
        .gpio_num       = PUMP_GATE_GPIO,
        .duty           = 0, // Explicitly initialize to OFF (0V Gate)
        .hpoint         = 0
    };
    ESP_ERROR_CHECK(ledc_channel_config(&ch_cfg));

    ESP_LOGI(TAG, "Pump MOSFET driver initialized on GPIO 4 (10kHz, 10-bit PWM). State: OFF");
    return ESP_OK;
}

/**
 * @brief Sets pump operating duty cycle with clamping
 * @param duty_percent Float from 0.0% to 100.0%
 */
esp_err_t pump_set_speed(float duty_percent) {
    if (duty_percent < 0.0f) duty_percent = 0.0f;
    if (duty_percent > 85.0f) duty_percent = 85.0f; // Max safe limit to prevent splashing

    // Inhibit motor stall band (< 30% duty)
    if (duty_percent > 0.0f && duty_percent < 30.0f) {
        duty_percent = 30.0f;
    }

    uint32_t duty_raw = (uint32_t)((duty_percent / 100.0f) * 1023.0f);
    ESP_ERROR_CHECK(ledc_set_duty(PUMP_LEDC_MODE, PUMP_LEDC_CHANNEL, duty_raw));
    ESP_ERROR_CHECK(ledc_update_duty(PUMP_LEDC_MODE, PUMP_LEDC_CHANNEL));

    ESP_LOGI(TAG, "Pump duty set to %.1f%% (Raw: %u)", duty_percent, (unsigned int)duty_raw);
    return ESP_OK;
}

/**
 * @brief Emergency shutdown routine (Instant 0V Gate)
 */
void IRAM_ATTR pump_emergency_stop(void) {
    ledc_set_duty(PUMP_LEDC_MODE, PUMP_LEDC_CHANNEL, 0);
    ledc_update_duty(PUMP_LEDC_MODE, PUMP_LEDC_CHANNEL);
}
```

---

## 6. Verification & Oscilloscope Measurement Protocol

To ensure absolute electrical integrity and certify inductive suppression, the assembled driver circuit must undergo physical bench testing:

```
+-----------------------------------------------------------------------------------------------+
|                               OSCILLOSCOPE VALIDATION MATRIX                                  |
+---------+-------------------+-----------------------------------+-----------------------------+
| Test ID | Test Condition    | Oscilloscope Probing Points       | Pass / Fail Criteria        |
+---------+-------------------+-----------------------------------+-----------------------------+
| TEST-M1 | Steady Turn-Off   | CH1: MOSFET Drain Node (`VOUT -`) | Peak voltage spike clamped  |
|         | Inductive Clamp   | CH2: Gate Drive (`GPIO 4`)        | <= 6.50 V DC.               |
|         | (100% to 0% step) | Trigger: GPIO 4 Falling Edge      | Zero avalanche breakdown.   |
+---------+-------------------+-----------------------------------+-----------------------------+
| TEST-M2 | PWM Steady State  | CH1: Motor Terminals Differential | Rise time tr <= 150 ns.     |
|         | (10 kHz, 70% duty)| CH2: 5V System Power Bus          | Flyback ringing damped      |
|         |                   | Timebase: 20 us / division        | within 5 us. Zero bus droop.|
+---------+-------------------+-----------------------------------+-----------------------------+
| TEST-M3 | Gate Failsafe     | Logic Analyzer on GPIO 4          | Gate voltage strictly       |
|         | Resistance Test   | Disconnect MCU or assert RESET    | maintained at 0.0V +/- 0.05V|
|         |                   |                                   | Pump completely unpowered.  |
+---------+-------------------+-----------------------------------+-----------------------------+
| TEST-M4 | Thermal Stress    | FLIR Thermal Imager or K-Type     | MOSFET Case Temp <= 45 deg C|
|         | (60s continuous)  | thermocouple on D4184 & 1N4007    | 1N4007 Diode <= 50 deg C.   |
+---------+-------------------+-----------------------------------+-----------------------------+
```

---