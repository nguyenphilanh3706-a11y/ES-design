"""
Train LSTM du bao 60 phut toi:
[do am dat se THAY DOI bao nhieu %, anh sang (lux)]

Dau vao:
60 buoc x 5 dac trung
(moi buoc 30 giay = 30 phut lich su)

Khac ban cu:
  - Scaler CO DINH (khong fit theo du lieu)
    -> hang so trong firmware khong bao gio lech.
  - Muc tieu do am dat =
    (dat sau 1h - dat hien tai) / 20,
    KHONG phai gia tri tuyet doi.
  - LSTM unroll=True ngay luc train
    (tuong thich TFLite Micro).
  - Danh gia tren cac NGAY chua tung thay
    + so voi baseline "giu nguyen hien tai".
"""

import json

import joblib
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler


# =========================================================
# 1. CAU HINH
# =========================================================

CSV = "sensor_data_v2_28days.csv"

FEATURES = [
    "TEMP",
    "HUM",
    "VPD",
    "LUX",
    "SOIL_PCT",
]

# 60 buoc * 30 giay = 30 phut lich su
LOOKBACK = 60

# 120 buoc * 30 giay = 60 phut
PREDICT_AHEAD = 120

STRIDE = 3

# output[0] * 20 = so % dat thay doi sau 1 gio
SOIL_DELTA_SCALE = 20.0


# =========================================================
# 2. SCALER CO DINH
# =========================================================
# Phai trung voi SCALER_MIN / SCALER_MAX trong main.cpp

SCALER_MIN = np.array([
    15.0,       # TEMP
    20.0,       # HUM
    0.0,        # VPD
    0.0,        # LUX
    0.0,        # SOIL_PCT
])

SCALER_MAX = np.array([
    45.0,       # TEMP
    100.0,      # HUM
    5.0,        # VPD
    120000.0,   # LUX
    100.0,      # SOIL_PCT
])


# =========================================================
# 3. DOC DU LIEU
# =========================================================

print(f"[INFO] Dang doc du lieu tu: {CSV}")

df = pd.read_csv(CSV)

raw = df[FEATURES].values.astype(np.float64)

# Chuan hoa ve khoang 0 -> 1 bang scaler co dinh
X_all = np.clip(
    (raw - SCALER_MIN) / (SCALER_MAX - SCALER_MIN),
    0.0,
    1.0
)

soil = df["SOIL_PCT"].values.astype(np.float64)

# LUX da chuan hoa
lux_n = X_all[:, 3]

episode = df["EPISODE"].values

n = len(df)

print(f"[INFO] Tong so mau: {n}")


# =========================================================
# 4. LUU SCALER
# =========================================================

# Luu scaler dang .pkl de cac script khac van dung duoc
sc = MinMaxScaler().fit(
    np.vstack([
        SCALER_MIN,
        SCALER_MAX
    ])
)

joblib.dump(
    sc,
    "scaler.pkl"
)

# Luu them scaler dang JSON
with open("scaler_ranges.json", "w") as f:
    json.dump(
        {
            "min": SCALER_MIN.tolist(),
            "max": SCALER_MAX.tolist(),
            "soil_delta_scale": SOIL_DELTA_SCALE,
        },
        f,
        indent=1,
    )

print("[OK] Da luu scaler.pkl")
print("[OK] Da luu scaler_ranges.json")


# =========================================================
# 5. TAO CUA SO TRUOT
# =========================================================
#
# Moi cua so gom:
#
#   X:
#       i - LOOKBACK ... i - 1
#
# Mau hien tai:
#       i - 1
#
# Mau can du doan:
#       target = i - 1 + PREDICT_AHEAD
#
# Vi:
#       PREDICT_AHEAD = 120
#
# va moi mau cach nhau 30 giay:
#
#       120 * 30 giay = 3600 giay = 60 phut
#
# Nhu vay target cach CHINH XAC 60 phut
# so voi mau cuoi cua cua so input.
#
# =========================================================

idx_end = []
X = []
y = []

for i in range(
    LOOKBACK,
    n - PREDICT_AHEAD + 1,
    STRIDE
):

    # Mau dich cach mau hien tai dung 120 buoc
    target = i - 1 + PREDICT_AHEAD

    # Khong cho cua so / target cat ngang episode
    if episode[i - LOOKBACK] != episode[target]:
        continue

    # 60 mau lich su
    X.append(
        X_all[i - LOOKBACK:i]
    )

    # -----------------------------------------------------
    # Output 0:
    # Do thay doi do am dat sau 60 phut
    #
    # Output 1:
    # Lux sau 60 phut (da normalize)
    # -----------------------------------------------------

    y.append([
        (
            soil[target] - soil[i - 1]
        ) / SOIL_DELTA_SCALE,

        lux_n[target],
    ])

    # i la vi tri ngay SAU mau cuoi cua input
    idx_end.append(i)


# Chuyen sang NumPy
X = np.array(
    X,
    dtype=np.float32
)

y = np.array(
    y,
    dtype=np.float32
)

idx_end = np.array(idx_end)


print("\n=== WINDOW INFORMATION ===")
print("X shape:", X.shape)
print("y shape:", y.shape)
print("idx_end shape:", idx_end.shape)


# =========================================================
# 6. CHIA TRAIN / VALIDATION THEO NGAY
# =========================================================
#
# Du lieu co 28 ngay
# 5 ngay cuoi lam validation
#
# 1 ngay:
#   24 * 60 * 60 / 30 = 2880 mau
#
# =========================================================

val_start = (28 - 5) * 2880


# ---------------------------------------------------------
# Validation:
#
# Dau cua cua so input phai nam trong validation.
# Nhờ đó toàn bộ input + target đều thuộc vùng validation.
# ---------------------------------------------------------

is_val = (
    idx_end - LOOKBACK
) >= val_start


# ---------------------------------------------------------
# Training:
#
# TARGET cua training phai nam truoc val_start.
#
# target =
#     idx_end - 1 + PREDICT_AHEAD
#
# ---------------------------------------------------------

is_tr = (
    idx_end - 1 + PREDICT_AHEAD
) < val_start


Xtr = X[is_tr]
ytr = y[is_tr]

Xva = X[is_val]
yva = y[is_val]


print(
    f"\nTrain: {len(Xtr)} cua so"
    f" | Validation: {len(Xva)} cua so"
    f" (5 ngay chua tung thay)"
)


# =========================================================
# 7. TAO MO HINH LSTM
# =========================================================

tf.keras.utils.set_random_seed(7)


model = tf.keras.Sequential([

    tf.keras.layers.Input(
        shape=(
            LOOKBACK,
            len(FEATURES)
        )
    ),

    # LSTM 1
    tf.keras.layers.LSTM(
        64,
        return_sequences=True,
        unroll=True
    ),

    tf.keras.layers.Dropout(
        0.1
    ),

    # LSTM 2
    tf.keras.layers.LSTM(
        32,
        return_sequences=False,
        unroll=True
    ),

    tf.keras.layers.Dropout(
        0.1
    ),

    tf.keras.layers.Dense(
        16,
        activation="relu"
    ),

    # Output:
    # [soil_delta, lux_normalized]
    tf.keras.layers.Dense(
        2,
        activation="linear"
    ),
])


# =========================================================
# 8. COMPILE
# =========================================================

model.compile(

    optimizer=tf.keras.optimizers.Adam(
        learning_rate=1e-3
    ),

    loss="mse",

    metrics=[
        "mae"
    ],
)


model.summary()


# =========================================================
# 9. TRAIN
# =========================================================

print("\n=== BAT DAU TRAIN ===")


model.fit(

    Xtr,
    ytr,

    validation_data=(
        Xva,
        yva
    ),

    epochs=40,

    batch_size=128,

    verbose=2,

    callbacks=[

        tf.keras.callbacks.EarlyStopping(

            monitor="val_loss",

            patience=6,

            restore_best_weights=True,
        )
    ]
)


# =========================================================
# 10. LUU MODEL
# =========================================================

model.save(
    "lstm_proactive_model.h5"
)

print(
    "\n[OK] Da luu lstm_proactive_model.h5"
)


# =========================================================
# 11. DANH GIA TREN VALIDATION
# =========================================================

print(
    "\n[INFO] Dang danh gia model..."
)


p = model.predict(

    Xva,

    batch_size=256,

    verbose=0
)


# =========================================================
# 12. CHUYEN OUTPUT VE DON VI THAT
# =========================================================

# Do am dat hien tai
soil_cur_va = (
    X[is_val][:, -1, 4]
    * (
        SCALER_MAX[4]
        - SCALER_MIN[4]
    )
    + SCALER_MIN[4]
)


# Do thay doi do am dat that
d_true = (
    yva[:, 0]
    * SOIL_DELTA_SCALE
)


# Do thay doi do am dat model du doan
d_pred = (
    p[:, 0]
    * SOIL_DELTA_SCALE
)


# Lux that
lux_true = (
    yva[:, 1]
    * (
        SCALER_MAX[3]
        - SCALER_MIN[3]
    )
    + SCALER_MIN[3]
)


# Lux model du doan
lux_pred = (
    p[:, 1]
    * (
        SCALER_MAX[3]
        - SCALER_MIN[3]
    )
    + SCALER_MIN[3]
)


# Lux hien tai
lux_now = (
    X[is_val][:, -1, 3]
    * (
        SCALER_MAX[3]
        - SCALER_MIN[3]
    )
    + SCALER_MIN[3]
)


# =========================================================
# 13. TINH MAE
# =========================================================

soil_mae_model = np.mean(
    np.abs(
        d_pred - d_true
    )
)

soil_mae_baseline = np.mean(
    np.abs(
        d_true
    )
)


lux_mae_model = np.mean(
    np.abs(
        lux_pred - lux_true
    )
)

lux_mae_baseline = np.mean(
    np.abs(
        lux_now - lux_true
    )
)


# =========================================================
# 14. IN KET QUA
# =========================================================

print(
    "\n=== KET QUA TREN NGAY CHUA TUNG THAY ==="
)


print(
    f"Dat  : "
    f"MAE model = {soil_mae_model:.2f}%"
    f"   | baseline 'giu nguyen' = "
    f"{soil_mae_baseline:.2f}%"
)


print(
    f"Lux  : "
    f"MAE model = {lux_mae_model:.0f}"
    f"   | baseline 'giu nguyen' = "
    f"{lux_mae_baseline:.0f}"
)


# =========================================================
# 15. KIEM TRA TRUONG HOP NANG GAT + DAT KHO
# =========================================================

sunny = (
    lux_true > 60000
)

dry = (
    soil_cur_va + d_true
) < 45


print(
    f"Cua so nang gat (>60000 lux): "
    f"{int(sunny.sum())}"
    f" | trong do dat <45% sau 1h: "
    f"{int((sunny & dry).sum())}"
)


print("\n=== HOAN TAT TRAIN AI ===")