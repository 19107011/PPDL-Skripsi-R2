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
Performance Metrics Calculator

Version: 1.0.1
Created: December 2025
"""

import numpy as np


class Metrics:
	"""Kalkulator Error untuk Evaluasi Model Skripsi.

	Mendukung input berupa list, numpy array, atau pandas Series.
	"""

	@staticmethod
	def _validate_input(y_true, y_pred):
		"""Konversi ke numpy array dan buang nilai non-finite.

		Juga memastikan panjang kedua array sama.
		"""

		y_true = np.asarray(y_true, dtype=float)
		y_pred = np.asarray(y_pred, dtype=float)

		if y_true.shape[0] != y_pred.shape[0]:
			raise ValueError(
				f"Dimensi data tidak sama: True({y_true.shape[0]}) vs Pred({y_pred.shape[0]})"
			)

		mask = np.isfinite(y_true) & np.isfinite(y_pred)
		return y_true[mask], y_pred[mask]

	@staticmethod
	def calculate_mae(y_true, y_pred) -> float:
		"""Mean Absolute Error."""

		y_true, y_pred = Metrics._validate_input(y_true, y_pred)
		if y_true.size == 0:
			return 0.0
		return float(np.mean(np.abs(y_true - y_pred)))

	@staticmethod
	def calculate_rmse(y_true, y_pred) -> float:
		"""Root Mean Square Error."""

		y_true, y_pred = Metrics._validate_input(y_true, y_pred)
		if y_true.size == 0:
			return 0.0
		return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

	@staticmethod
	def _calculate_mape_with_ignored(y_true, y_pred) -> tuple[float, int]:
		"""MAPE dengan skip nilai aktual nol.

		Mengembalikan (mape, ignored_zero_count).
		"""

		y_true, y_pred = Metrics._validate_input(y_true, y_pred)
		if y_true.size == 0:
			return 0.0, 0

		mask = y_true != 0
		ignored_zero_count = int(np.sum(~mask))
		if not np.any(mask):
			return 0.0, ignored_zero_count

		mape_val = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100.0
		return float(mape_val), ignored_zero_count

	@staticmethod
	def calculate_mape(y_true, y_pred) -> float:
		"""Mean Absolute Percentage Error (dalam persen).

		Nilai y_true == 0 di-skip dari perhitungan MAPE.
		"""

		mape_val, _ = Metrics._calculate_mape_with_ignored(y_true, y_pred)
		return float(mape_val)

	@staticmethod
	def get_all_metrics(y_true, y_pred) -> dict:
		"""Mengembalikan MAE, RMSE, dan MAPE sekaligus dalam dict."""

		mape_val, ignored_zero_count = Metrics._calculate_mape_with_ignored(y_true, y_pred)
		return {
			"mae": Metrics.calculate_mae(y_true, y_pred),
			"rmse": Metrics.calculate_rmse(y_true, y_pred),
			"mape": mape_val,
			"ignored_zero_count": ignored_zero_count,
		}
