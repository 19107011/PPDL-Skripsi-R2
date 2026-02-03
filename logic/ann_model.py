"""

PPDL - Prediksi Pemakaian Daya Listrik
PPDL - Electrical Power Consumption Prediction

Academic Project Title:
Prediksi Pemakaian Daya Listrik Pada Rumah Tangga di Jakarta Berbasis IoT
dengan Menggunakan Metode Fuzzy Time Series

Prediction of Household Electrical Power Consumption in Jakarta
Using the Fuzzy Time Series Method

Property of:
Universitas Trilogi | Teknik Informatika | Program Sarjana (Strata 1)
Trilogi University | Informatics Engineering | Bachelor Degree

Author:
Alma Zannuba Arifah | 19107011

Supervisors:
Ir. Yaddarabulah, M.Kom., Ph.D.
Opitasari, S.Si., M.Kom.

Module:
Artificial Neural Network Model

Version: 1.0.1
Created: December 2025
"""

import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import Callback


class TrainingCallback(Callback):
	"""Callback untuk menghubungkan proses training ANN dengan UI.

	Jika `signal_callback` diberikan, akan dipanggil setiap akhir epoch
	dengan parameter (percent, message).
	"""

	def __init__(self, total_epochs: int, signal_callback=None) -> None:
		super().__init__()
		self.total_epochs = int(total_epochs)
		self.signal_callback = signal_callback

	def on_epoch_end(self, epoch, logs=None):  # type: ignore[override]
		logs = logs or {}
		if not self.signal_callback:
			return
		percent = int(((epoch + 1) / self.total_epochs) * 100)
		loss = logs.get("loss", 0.0)
		msg = f"Epoch {epoch+1}/{self.total_epochs} - Loss: {loss:.4f}"
		self.signal_callback(percent, msg)


class ANNModel:
	"""Glass Box Implementation of MLP Regressor untuk PPDL V1.0."""

	def __init__(self) -> None:
		self.model: Sequential | None = None
		self.scaler = MinMaxScaler(feature_range=(0, 1))

	def _build_model(self, input_dim: int, config: dict) -> Sequential:
		"""Menyusun arsitektur jaringan sesuai konfigurasi user."""

		model = Sequential()

		neurons = int(config.get("neuron", 10))
		layers = int(config.get("layers", 1))
		activation = "relu"
		learning_rate = float(config.get("lr", 0.01))

		# Input + first hidden layer
		model.add(Dense(neurons, input_dim=input_dim, activation=activation))

		# Additional hidden layers
		for _ in range(layers - 1):
			model.add(Dense(neurons, activation=activation))

		# Output layer (regresi)
		model.add(Dense(1, activation="linear"))

		optimizer = Adam(learning_rate=learning_rate)
		model.compile(loss="mse", optimizer=optimizer)
		return model

	def _create_dataset(self, dataset: np.ndarray, look_back: int = 1):
		"""Mengubah deret waktu menjadi pasangan (X, y) dengan lag tertentu."""

		dataX, dataY = [], []
		for i in range(len(dataset) - look_back):
			a = dataset[i : (i + look_back), 0]
			dataX.append(a)
			dataY.append(dataset[i + look_back, 0])
		return np.array(dataX), np.array(dataY)

	def train_predict(
		self,
		train_data: pd.Series,
		test_data: pd.Series,
		config: dict,
		progress_callback=None,
	) -> dict:
		"""Main pipeline: Normalisasi -> Training -> Prediksi -> Inverse transform.

		Mengembalikan dict dengan kunci:
		- "forecast": list float
		- "artifacts": dict (loss_history, final_loss, model_summary, epochs_run, config_used)
		"""

		# 1. Siapkan data & normalisasi
		train_val = train_data.values.reshape(-1, 1).astype(float)
		test_val = test_data.values.reshape(-1, 1).astype(float)

		self.scaler.fit(train_val)
		train_scaled = self.scaler.transform(train_val)
		test_scaled = self.scaler.transform(test_val)

		look_back = 1

		X_train, y_train = self._create_dataset(train_scaled, look_back)

		# Untuk test, gunakan titik terakhir train sebagai konteks awal
		last_train = train_scaled[-look_back:]
		test_input = np.concatenate((last_train, test_scaled))
		X_test, y_test = self._create_dataset(test_input, look_back)

		# 2. Build model
		self.model = self._build_model(input_dim=look_back, config=config)

		# 3. Training
		epochs = int(config.get("epoch", 200))
		batch_size = 32

		cb = TrainingCallback(epochs, progress_callback)

		history = self.model.fit(
			X_train,
			y_train,
			epochs=epochs,
			batch_size=batch_size,
			verbose=0,
			callbacks=[cb],
		)

		# 4. Prediksi
		train_pred_scaled = self.model.predict(X_train, verbose=0)
		test_pred_scaled = self.model.predict(X_test, verbose=0)

		# 5. Inverse transform
		train_pred = self.scaler.inverse_transform(train_pred_scaled)
		test_pred = self.scaler.inverse_transform(test_pred_scaled)
		forecast_list = test_pred.flatten().tolist()

		# 6. Artifacts
		loss_history = [float(x) for x in history.history.get("loss", [])]
		final_loss = float(loss_history[-1]) if loss_history else 0.0

		stringlist: list[str] = []
		self.model.summary(print_fn=lambda x: stringlist.append(x))
		model_summary = "\n".join(stringlist)

		return {
			"forecast": forecast_list,
			"artifacts": {
				"loss_history": loss_history,
				"final_loss": final_loss,
				"model_summary": model_summary,
				"epochs_run": epochs,
				"config_used": config,
				"scaler_min": float(self.scaler.data_min_[0]),
				"scaler_max": float(self.scaler.data_max_[0]),
			},
		}
