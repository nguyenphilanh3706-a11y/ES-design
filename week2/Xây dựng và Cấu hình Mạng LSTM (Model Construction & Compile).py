

#Khối 1: Xây dựng Kiến trúc Mạng LSTM
import tensorflow as tf
from tensorflow.keras import layers,models

model = models.Sequential([
    layers.Input(shape=(24,4)),
    layers.LSTM(32, return_sequences= False, unroll = True),
    layers.Dense(16,activation = 'relu'),
    layers.Dense(1)
])

# train cho con AI
#Khối 2: Cấu hình và Huấn luyện Mô hình với EarlyStopping
model.compile(optimizer = 'adam', loss = 'mse', metrics = ['mae'])
model.summary()
early_stop = tf.keras.callbacks.EarlyStopping(monitor = 'val_loss',patience = 5)
history = model.fit(
    X_train, y_train,
    epochs = 40,
    batch_size = 16,
    validation_data= (X_test, y_test),
    callbacks =[early_stop]
)
#Khối 3: Chuyển đổi và Lượng tử hóa TFLite INT8
def representative_data_gen():
    for i in range(min(100, len(X_train))):
      yield [X_train[i:i+1].astype(np.float32)]
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.representative_dataset = representative_data_gen
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
converter.inference_input_type = tf.int8
converter.inference_output_type = tf.int8

tflite_model = converter.convert()

with open('model.tflite', 'wb') as f:
    f.write(tflite_model)
print("Data Min:", scaler.data_min_)
print("Data Max:", scaler.data_max_)
#Khối 4: Khởi tạo Interpreter và Trích xuất Tham số Lượng tử hóa
interpreter = tf.lite.Interpreter(model_content=tflite_model)
interpreter.allocate_tensors()
in_det = interpreter.get_input_details()[0]
out_det = interpreter.get_output_details()[0]

print("Input Scale/Zero:", in_det['quantization'])
print("Output Scale/Zero:", out_det['quantization'])

