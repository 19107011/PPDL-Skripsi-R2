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
Baseline Comparison Models

Version: 1.0.1
Created: December 2025
"""

import numpy as np
import pandas as pd


class NaivePredictor:
	"""Baseline Naive: y_hat(t) = y(t-1)."""

	@staticmethod
	def predict(train_series: pd.Series, test_series: pd.Series) -> list[float]:
		if test_series is None or len(test_series) == 0:
			return []
		prev = float(train_series.iloc[-1]) if train_series is not None and len(train_series) > 0 else float(test_series.iloc[0])
		preds: list[float] = []
		for idx, val in enumerate(test_series.values):
			if idx == 0:
				preds.append(float(np.nan))
			else:
				preds.append(float(prev))
			prev = val
		return preds


class MovingAveragePredictor:
	"""Baseline Moving Average: rata-rata N terakhir."""

	@staticmethod
	def predict(train_series: pd.Series, test_series: pd.Series, window: int = 3) -> list[float]:
		if test_series is None or len(test_series) == 0:
			return []
		window = max(1, int(window))
		history = [] if train_series is None else [float(v) for v in train_series.values]
		preds: list[float] = []
		for idx, val in enumerate(test_series.values):
			if idx == 0:
				preds.append(float(np.nan))
			else:
				if len(history) < window:
					preds.append(float(np.nan))
				else:
					window_vals = history[-window:]
					preds.append(float(np.mean(window_vals)))
			history.append(float(val))
		return preds
