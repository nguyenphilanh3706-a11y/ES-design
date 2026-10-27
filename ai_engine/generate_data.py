"""
Tao du lieu mo phong 28 ngay (moi 30 giay/mau) cho model du bao.

Khac ban cu (generate_data.py 7 ngay):
  - Thoi tiet moi ngay LAY NGAU NHIEN (nang / nong / mat / u am / mua), co may troi bien thien.
  - Do am dat khoi dau NGAU NHIEN va khoi dong lai moi 7 ngay (cot EPISODE) -> co du mau
    dat 25-60% luc nang gat, de model hoc duoc "dat se kho di bao nhieu trong 1 gio".
  - Cac lan tuoi/mua KHONG con gan cung vao gio co dinh nhu ban cu
    (ban cu: tuoi dung 8h15 ngay 2, 8h30 ngay 6 -> model hoc thuoc "sang som => dat tang").
    Gio day: tuoi bu khi dat < 30% (giong FSM tren ESP32), mua ngau nhien, tuoi tay ngau nhien.
  - Quy doi ADC <-> % dung 3 moc thuc nghiem 1770 / 980 / 822 (khop firmware moi).
"""
import math
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# ---- Moc ADC thuc nghiem (PHAI giong firmware) ----
ADC_DRY_REAL = 1770   # dat kho (0%)
ADC_HALF_REAL = 980   # 50%
ADC_WET_REAL = 822    # bao hoa (100%)

INTERVAL_SEC = 30
SAMPLES_PER_DAY = 2880
TOTAL_DAYS = 28
EPISODE_DAYS = 7
START_TIME = datetime(2026, 9, 1, 0, 0, 0)

rng = np.random.default_rng(2026)

DAY_KINDS = {
    #            tmin        tmax        hmax        hmin        lux_peak          cloud(base)
    "sunny":    ((24, 26),   (30, 34),   (80, 88),   (52, 65),   (60000, 80000),   (0.90, 1.00)),
    "hot":      ((26, 28),   (34, 38),   (70, 80),   (38, 48),   (80000, 100000),  (0.95, 1.00)),
    "mild":     ((23, 25),   (28, 31),   (85, 92),   (62, 72),   (45000, 62000),   (0.80, 0.95)),
    "overcast": ((23, 25),   (26, 29),   (90, 96),   (75, 85),   (20000, 35000),   (0.45, 0.70)),
    "rainy":    ((23, 25),   (26, 30),   (92, 97),   (78, 88),   (25000, 45000),   (0.40, 0.65)),
}
KIND_P = [0.30, 0.20, 0.20, 0.15, 0.15]
KIND_NAMES = list(DAY_KINDS.keys())


def u(lohi):
    return rng.uniform(lohi[0], lohi[1])


def adc_from_pct(pct):
    if pct <= 50:
        return ADC_DRY_REAL - (pct / 50.0) * (ADC_DRY_REAL - ADC_HALF_REAL)
    return ADC_HALF_REAL - ((pct - 50.0) / 50.0) * (ADC_HALF_REAL - ADC_WET_REAL)


rows = []
soil = rng.uniform(35, 85)
water_left = 0          # so mau con lai cua dot tuoi dang chay
water_inc = 0.0         # % dat tang moi mau trong dot tuoi
cooldown = 0            # so mau nghi sau dot tuoi
cloud = 1.0

for day in range(TOTAL_DAYS):
    episode = day // EPISODE_DAYS
    if day % EPISODE_DAYS == 0 and day > 0:
        soil = rng.uniform(35, 85)       # chau cay moi / bat dau chu ky moi
        water_left = 0
        cooldown = 0

    kind = rng.choice(KIND_NAMES, p=KIND_P)
    tmin_r, tmax_r, hmax_r, hmin_r, lux_r, cloud_r = DAY_KINDS[kind]
    t_min, t_max = u(tmin_r), u(tmax_r)
    h_max, h_min = u(hmax_r), u(hmin_r)
    lux_peak = u(lux_r)
    cloud_base = u(cloud_r)
    evap_mult = rng.uniform(0.7, 1.6)

    # Mua (chi ngay "rainy"): bat dau 12-17h, keo dai 30-120 phut
    rain_start = rain_end = None
    rain_rate = 0.0
    if kind == "rainy":
        rain_start = rng.uniform(12, 17)
        rain_end = rain_start + rng.uniform(0.5, 2.0)
        rain_rate = rng.uniform(0.15, 0.40)       # % dat tang moi mau trong mua

    # Tuoi tay ngau nhien (xac suat 40%/ngay), gio bat ky 6-20h
    manual_hour = rng.uniform(6, 20) if rng.random() < 0.4 else None
    manual_done = False

    for k in range(SAMPLES_PER_DAY):
        i = day * SAMPLES_PER_DAY + k
        t_now = START_TIME + timedelta(seconds=i * INTERVAL_SEC)
        hour = t_now.hour + t_now.minute / 60.0 + t_now.second / 3600.0
        raining = rain_start is not None and rain_start <= hour <= rain_end

        # May troi: qua trinh tu hoi quy, keo ve cloud_base
        cloud += 0.02 * (cloud_base - cloud) + rng.normal(0, 0.03)
        cloud = float(np.clip(cloud, 0.2, 1.0))
        cloud_eff = cloud * (0.35 if raining else 1.0)

        # Anh sang
        if 6.0 <= hour <= 18.0:
            sun = math.sin((hour - 6.0) / 12.0 * math.pi)
            lux = max(0.0, lux_peak * sun * cloud_eff + rng.normal(0, 700.0))
        else:
            lux = 0.0

        # Nhiet do & do am khong khi
        ang = (hour - 14.0) / 24.0 * 2 * math.pi
        temp = t_min + (t_max - t_min) * (0.5 + 0.5 * math.cos(ang)) + rng.normal(0, 0.08)
        hum = h_max - (h_max - h_min) * (0.5 + 0.5 * math.cos(ang)) + rng.normal(0, 0.25)
        if raining:
            hum = min(100.0, hum + 8.0)
            temp -= 1.5
        hum = float(np.clip(hum, 1.0, 100.0))
        vp_sat = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
        vpd = max(0.0, vp_sat * (1.0 - hum / 100.0))

        # ---- Dong luc hoc do am dat ----
        # Tuoi tay ngau nhien
        if manual_hour is not None and not manual_done and hour >= manual_hour:
            water_left, water_inc = 12, rng.uniform(1.6, 2.4)
            manual_done = True
        # Tuoi bu tu dong khi dat kho (giong FSM tren ESP32: < 30%)
        if water_left == 0 and cooldown == 0 and soil < 30.0:
            water_left, water_inc = 12, rng.uniform(1.8, 2.3)

        if raining:
            soil = min(98.0, soil + rain_rate)
        elif water_left > 0:
            soil = min(96.0, soil + water_inc)
            water_left -= 1
            if water_left == 0:
                cooldown = 120                    # nghi 1 gio sau dot tuoi
        else:
            if 6.0 <= hour <= 18.0:
                evap = (0.000045 * vpd + 0.000000012 * lux) * INTERVAL_SEC * evap_mult
            else:
                evap = 0.000006 * INTERVAL_SEC
            soil = max(15.0, soil - evap)
        if cooldown > 0 and water_left == 0 and not raining:
            cooldown -= 1

        soil_obs = int(round(np.clip(soil + rng.normal(0, 0.12), 0, 100)))
        raw_adc = adc_from_pct(soil_obs) + rng.normal(0, 2.0)
        raw_adc = int(round(np.clip(raw_adc, ADC_WET_REAL - 15, ADC_DRY_REAL + 15)))

        rows.append({
            "PC_TIME": t_now.strftime("%Y-%m-%d %H:%M:%S"),
            "SAMPLE_ID": i + 1,
            "EPISODE": episode,
            "DAY_KIND": kind,
            "TEMP": round(temp, 2),
            "HUM": round(hum, 1),
            "VPD": round(vpd, 3),
            "LUX": round(lux, 1),
            "SOIL_RAW": raw_adc,
            "SOIL_PCT": soil_obs,
        })

df = pd.DataFrame(rows)
df.to_csv("sensor_data_v2_28days.csv", index=False)
print(f"[OK] sensor_data_v2_28days.csv: {len(df)} dong")
print("Loai ngay:", df.groupby('DAY_KIND').size().div(SAMPLES_PER_DAY).astype(int).to_dict())
s = df.SOIL_PCT
print(f"Do am dat: min={s.min()} mean={s.mean():.1f} max={s.max()} | <45%: {100*(s<45).mean():.1f}% mau")
print(f"Lux max={df.LUX.max():.0f}  Temp {df.TEMP.min():.1f}-{df.TEMP.max():.1f}  Hum {df.HUM.min():.1f}-{df.HUM.max():.1f}  VPD max={df.VPD.max():.2f}")