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
ARIMA Statistical Model

Version: 1.0.1
Created: December 2025
"""

import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.statespace.sarimax import SARIMAX


warnings.filterwarnings("ignore")


class ARIMAModel:
	"""Glass Box Implementation of ARIMA/SARIMAX untuk PPDL V1.0."""

	def run(self, train_data: pd.Series, test_data: pd.Series, config: dict) -> dict:
		"""Menjalankan ARIMA/SARIMA dan mengembalikan forecast + artifacts.

		Config keys:
		- p, d, q
		- seasonal (bool)
		- P, D, Q, s (jika seasonal=True)
		"""

		order = (
			int(config.get("p", 1)),
			int(config.get("d", 1)),
			int(config.get("q", 1)),
		)

		seasonal_order = (0, 0, 0, 0)
		is_seasonal = bool(config.get("seasonal", False))
		if is_seasonal:
			seasonal_order = (
				int(config.get("P", 0)),
				int(config.get("D", 1)),
				int(config.get("Q", 0)),
				int(config.get("s", 12)),
			)

		try:
			model = SARIMAX(
				train_data,
				order=order,
				seasonal_order=seasonal_order if is_seasonal else (0, 0, 0, 0),
				enforce_stationarity=False,
				enforce_invertibility=False,
			)

			model_fit = model.fit(disp=False)

			# Forecast sepanjang test_data
			start = len(train_data)
			end = len(train_data) + len(test_data) - 1
			forecast_series = model_fit.predict(start=start, end=end, dynamic=False)
			forecast_list = forecast_series.values.tolist()

			residuals = model_fit.resid.values.tolist()
			summary_text = str(model_fit.summary())

			return {
				"forecast": forecast_list,
				"artifacts": {
					"aic": float(model_fit.aic),
					"bic": float(model_fit.bic),
					"residuals": residuals,
					"summary_text": summary_text,
					"params_fitted": model_fit.params.to_dict(),
				},
			}

		except Exception as e:  # pragma: no cover - fallback
			print(f"[ERR] ARIMA Failed: {e}")
			return {
				"forecast": [0.0] * len(test_data),
				"artifacts": {
					"error": str(e),
					"aic": 0.0,
					"bic": 0.0,
					"residuals": [],
					"summary_text": "Model Failed to Converge",
				},
			}
