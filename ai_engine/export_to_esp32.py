"""
Convert lstm_proactive_model.h5 -> model.tflite -> model_data.h cho ESP32 (TFLM).
Khong can train lai: nap trong so cu vao cung kien truc nhung LSTM unroll=True.

Chay:  python export_to_esp32.py
Ket qua: model.tflite, model_data.h  (chep model_data.h vao thu muc src/)
"""
import re
import numpy as np
import tensorflow as tf

H5_PATH   = "lstm_proactive_model.h5"
LOOKBACK  = 60
FEATURES  = 5

# 1. Nap model cu (khong unroll) de lay trong so
old = tf.keras.models.load_model(H5_PATH, compile=False)

# 2. Kien truc GIONG HET train_ai.py, chi them unroll=True va batch_size=1 co dinh.
#    Dropout bo di vi chi co tac dung luc train.
new = tf.keras.Sequential([
    tf.keras.layers.Input(shape=(LOOKBACK, FEATURES), batch_size=1),
    tf.keras.layers.LSTM(64, return_sequences=True, unroll=True),
    tf.keras.layers.LSTM(32, return_sequences=False, unroll=True),
    tf.keras.layers.Dense(16, activation="relu"),
    tf.keras.layers.Dense(2, activation="linear"),
])
# Dropout khong co trong so nen danh sach weights cua hai model giong nhau
new.set_weights(old.get_weights())

# 3. Kiem tra model moi cho ket qua giong model cu
x = np.random.rand(1, LOOKBACK, FEATURES).astype(np.float32)
diff = np.abs(old.predict(x, verbose=0) - new.predict(x, verbose=0)).max()
print("Chenh lech Keras cu vs moi:", diff)
assert diff < 1e-5, "Trong so nap sai!"

# 4. Convert: CHI cho phep op co san, khong SELECT_TF_OPS
converter = tf.lite.TFLiteConverter.from_keras_model(new)
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS]
tflite_model = converter.convert()
open("model.tflite", "wb").write(tflite_model)
print("model.tflite:", len(tflite_model), "bytes")

# 5. Kiem tra khong con Flex/Custom/TensorList
txt = ""
import io, contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    tf.lite.experimental.Analyzer.analyze(model_content=tflite_model)
txt = buf.getvalue()
ops = sorted(set(re.findall(r"Op#\d+ ([A-Z_0-9a-z]+)\(", txt)))
print("Cac op trong model:", ops)
bad = [o for o in ops if re.search(r"FLEX|Flex|CUSTOM|TENSOR_LIST|TensorList|WHILE", o)]
print("OP XAU:", bad if bad else "KHONG CON  -> OK")
assert not bad

# 6. TFLite interpreter phai ra cung ket qua Keras
it = tf.lite.Interpreter(model_content=tflite_model)
it.allocate_tensors()
it.set_tensor(it.get_input_details()[0]["index"], x)
it.invoke()
out = it.get_tensor(it.get_output_details()[0]["index"])
d2 = np.abs(out - new.predict(x, verbose=0)).max()
print("Chenh lech TFLite vs Keras:", d2)
assert d2 < 1e-4

# 7. Xuat model_data.h (cung ten bien g_model / g_model_len nhu main.cpp dang dung)
with open("model_data.h", "w") as f:
    f.write("#ifndef MODEL_DATA_H\n#define MODEL_DATA_H\n\n")
    f.write(f"const unsigned int g_model_len = {len(tflite_model)};\n")
    f.write("const unsigned char g_model[] __attribute__((aligned(16))) = {\n")
    rows = []
    for i in range(0, len(tflite_model), 16):
        rows.append("  " + ", ".join(f"0x{b:02x}" for b in tflite_model[i:i+16]))
    f.write(",\n".join(rows))
    f.write("\n};\n\n#endif // MODEL_DATA_H\n")
print("Da ghi model_data.h")