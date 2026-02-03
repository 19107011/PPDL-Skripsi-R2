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
Calculation Worker Thread

Version: 1.0.1
Created: December 2025
"""

import traceback

import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal

from utils import logging_events as EVT
from utils.logging_spec import CAUSE_SEP, FIELD_SEP, RESULT_SEP, format_route

from logic.preprocessing import Preprocessor
from logic.fts_chen import FTSChen
from logic.ann_model import ANNModel
from logic.arima_model import ARIMAModel
from logic.metrics import Metrics
from logic.baseline import NaivePredictor, MovingAveragePredictor
from logic.sensitivity import run_sensitivity_analysis


class CalculationWorker(QThread):
	"""Worker Thread untuk menjalankan pipeline analisis backend.

	Alur:
	- Preprocessing (resample + split)
	- FTS Chen
	- ANN
	- ARIMA
	- Hitung metrics untuk setiap metode

	Hasil akhir dikirim lewat sinyal `sig_finished` sebagai dict.
	"""

	sig_step_update = pyqtSignal(str, str, int)  # task_id, status, percent
	sig_log = pyqtSignal(str, str)  # level, message
	sig_cancelled = pyqtSignal()
	sig_finished = pyqtSignal(dict)
	sig_error = pyqtSignal(str)

	def __init__(self, raw_data: pd.DataFrame, params: dict):
		super().__init__()
		self.raw_data = raw_data
		self.params = params
		self.is_running = True

	def _emit_event(
		self,
		level: str,
		evt: str,
		*,
		route_actor: str = "MAIN",
		route_to: list[str] | None = None,
		fields: list[str] | None = None,
		cause: str | None = None,
		result: str | None = None,
	) -> None:
		route_targets = route_to if route_to is not None else ["HOME", "RESUME"]
		route = format_route(route_actor, route_targets)
		parts = [f"EVT={evt}", route]
		if fields:
			parts.extend([str(x).strip() for x in fields if str(x).strip()])
		msg = FIELD_SEP.join(parts)
		if cause:
			msg = f"{msg} {CAUSE_SEP} {cause}"
		if result:
			msg = f"{msg} {RESULT_SEP} {result}"
		self.sig_log.emit(level, msg)

	def run(self) -> None:  # type: ignore[override]
		results: dict = {}
		try:
			# AP-01: Worker Thread Target Variable Extraction
			target_variable = self.params.get('global', {}).get('target_variable', 'watt')
			if target_variable not in self.raw_data.columns:
				raise ValueError(f"Target variable '{target_variable}' not found in data columns: {list(self.raw_data.columns)}")
			
			self.sig_log.emit("INFO", f"Analysis starting with target variable: '{target_variable}'")
			
			# LOG-03: Analysis Pipeline Critical Parameters Logging
			forecast_horizon = self.params.get('global', {}).get('forecast_horizon', 1)
			analysis_methods = "FTS+ANN+ARIMA"  # Standard analysis methods
			self.sig_log.emit("INFO", f"🔑 ANALYSIS START: TARGET='{target_variable}' | FORECAST='{forecast_horizon}' | METHODS='{analysis_methods}'")
			
			# E2E-03: Analysis Pipeline Testing Validation  
			self.sig_log.emit("INFO", f"🔍 E2E-03 PIPELINE VALIDATION: Target_extraction='{target_variable}' | Column_exists=TRUE | Pipeline_ready=TRUE")
			
			# AP-02: MODEL_PREP.Target_Selection Implementation
			# Drop rows where target is NaN/Infinite
			original_count = len(self.raw_data)
			clean_data = self.raw_data.copy()
			target_series = clean_data[target_variable]
			
			# Remove NaN and infinite values
			valid_mask = target_series.notna() & target_series.replace([float('inf'), float('-inf')], float('nan')).notna()
			clean_data = clean_data[valid_mask]
			cleaned_count = len(clean_data)
			
			self.sig_log.emit("INFO", f"MODEL_PREP.Target_Selection: {original_count} -> {cleaned_count} rows (removed {original_count - cleaned_count} NaN/Infinite target values)")
			
			# E2E-03: Target Selection Validation
			data_quality_ratio = cleaned_count / original_count if original_count > 0 else 0
			self.sig_log.emit("INFO", f"🔍 E2E-03 TARGET VALIDATION: Original_rows={original_count} | Clean_rows={cleaned_count} | Quality_ratio={data_quality_ratio:.3f} | Target_column='{target_variable}'")
			
			# LOG-04: Critical Parameters for Resume Output
			target_display_mapping = {
				"watt": "W - Daya (Watt)", "voltage": "V - Tegangan (Voltage)", 
				"current": "A - Arus (Current)", "frequency": "F - Frekuensi (Frequency)",
				"energy_kwh": "E - Energi (kWh)", "pf": "PF - Power Factor"
			}
			target_display_name = target_display_mapping.get(target_variable, target_variable)
			self.sig_log.emit("INFO", f"🔑 RESUME HEADER: Analysis Results | Target: {target_display_name} | Horizon: {forecast_horizon} periods")
			
			# Use cleaned data for further processing
			processing_data = clean_data
			
			# STEP 1: PREPROCESSING
			self.sig_step_update.emit("setup", "Resampling Data (5 min)...", 10)

			raw_rows = len(processing_data) if processing_data is not None else 0
			
			resample_method = (
				self.params.get("global", {}).get("resample_method")
				if isinstance(self.params.get("global"), dict)
				else None
			)
			if not resample_method:
				resample_method = "mean"
			
			self._emit_event(
				"INFO",
				EVT.PRE_RESAMPLE,
				fields=[
					"step=1_Time_Index: Convert 'ts' (epoch ms) to DatetimeIndex",
					f"step=2_Resample: rule='5T' (5 minutes), aggregation='{resample_method}'",
					"step=3_Imputation: ffill() -> bfill() -> fillna(0)",
					f"target_column={target_variable}",
					f"🔍 E2E-03: Preprocessing_target='{target_variable}' | Method='{resample_method}' | Status=PROCESSING",
				],
			)
			
			# AP-04: Analysis Pipeline Target Variable Usage
			prep_res = Preprocessor.resample_data(
				processing_data,
				interval_minutes=5,
				resample_method=resample_method,
				target_column=target_variable  # Pass target variable to preprocessing
			)
			series_clean = prep_res["data"]
			artifacts = prep_res.get("artifacts", {})
						
			if artifacts:
				# Log Resample Result as Recipe Outcome
				self._emit_event(
					"GEN",
					EVT.PRE_RESAMPLE,
					fields=[
						f"original_rows={artifacts.get('original_count')}",
						f"resampled_rows={artifacts.get('resampled_count')}",
						f"missing_filled_count={artifacts.get('missing_filled')}",
						"status=OK",
					],
				)

			ratio = float(self.params["global"]["split_ratio"])
			self.sig_step_update.emit(
				"setup",
				f"Splitting Data ({int(ratio*100)}:{int((1-ratio)*100)})...",
				50,
			)

			self._emit_event(
				"INFO",
				EVT.PRE_SPLIT,
				fields=[
					f"ratio={ratio:.2f}",
					"calc_n_train=floor(len(series) * ratio)",
					"train_set=series[0 : n_train]",
					"test_set=series[n_train : end]",
					"constraint=Sequential split (No random shuffle)",
				],
			)

			train_series, test_series = Preprocessor.train_test_split(series_clean, ratio)
			
			self._emit_event(
				"GEN",
				EVT.PRE_SPLIT,
				fields=[
					f"n_total={len(series_clean)}",
					f"n_train={len(train_series)}",
					f"n_test={len(test_series)}",
					"status=OK",
				],
			)

			results["data"] = {
				"train": train_series,
				"test": test_series,
				"full": series_clean,
			}

			self.sig_step_update.emit("setup", "Done", 100)
			if not self.is_running:
				self.sig_log.emit("INFO", "Analysis cancelled by user during preprocessing.")
				self.sig_cancelled.emit()
				return

			# Baseline (Naive & Moving Average)
			try:
				naive_forecast = NaivePredictor.predict(train_series, test_series)
				naive_metrics = Metrics.get_all_metrics(test_series.values, naive_forecast)
				ma_window = max(2, int(self.params.get("fts", {}).get("interval", 3)))
				ma_forecast = MovingAveragePredictor.predict(train_series, test_series, window=ma_window)
				ma_metrics = Metrics.get_all_metrics(test_series.values, ma_forecast)
				results["naive"] = {"metrics": naive_metrics, "forecast": naive_forecast}
				results["ma"] = {"metrics": ma_metrics, "forecast": ma_forecast, "window": ma_window}
				self.sig_log.emit(
					"RESULT",
					(
						f"[baseline] Naive MAE={naive_metrics['mae']:.6f} | "
						f"RMSE={naive_metrics['rmse']:.6f} | "
						f"MAPE={naive_metrics['mape']:.4f}%"
					),
				)
				self.sig_log.emit(
					"RESULT",
					(
						f"[baseline] MA({ma_window}) MAE={ma_metrics['mae']:.6f} | "
						f"RMSE={ma_metrics['rmse']:.6f} | "
						f"MAPE={ma_metrics['mape']:.4f}%"
					),
				)
			except Exception as e:
				self.sig_log.emit("ERROR", f"[baseline] Failed: {e}")

			# STEP 2: FTS CHEN
			if not self.is_running:
				self.sig_log.emit("INFO", "Analysis cancelled by user before FTS stage.")
				self.sig_cancelled.emit()
				return

			self.sig_step_update.emit("fts", "Initializing FTS Chen...", 0)
			fts_params = self.params["fts"]
			partition = fts_params.get("partition")
			method = "equal-width"
			if partition:
				method_key = str(partition).strip().lower()
				if method_key in {"equal frequency", "equal-frequency", "equalfrequency", "equal freq", "equal-freq"}:
					method = "equal-frequency"
				elif method_key in {"equal width", "equal-width", "equalwidth"}:
					method = "equal-width"

			pad_pct = fts_params.get("pad_pct")
			if pad_pct is None:
				pad_pct = fts_params.get("padPct")
			if pad_pct is None:
				pad_pct = 0.05
			try:
				pad_pct = float(pad_pct)
			except (TypeError, ValueError):
				pad_pct = 0.05

			fts_model = FTSChen(
				interval_num=int(fts_params["interval"]),
				method=method,
				pad_pct=pad_pct,
			)

			self.sig_step_update.emit("fts", "Training & Generating FLR/FLRG...", 40)
			fts_model.fit(train_series)

			self.sig_step_update.emit("fts", "Forecasting test data...", 70)
			fts_out = fts_model.predict(test_series)
			fts_forecast = fts_out.get("forecast", [])
			actual_vals = test_series.values
			if len(fts_forecast) == len(actual_vals) and len(actual_vals) > 1:
				fts_metrics = Metrics.get_all_metrics(actual_vals[1:], fts_forecast[1:])
			else:
				fts_metrics = Metrics.get_all_metrics(actual_vals, fts_forecast)
			fts_art = fts_out.get("artifacts", {})
			uod = fts_art.get("uod")
			intervals = fts_art.get("intervals") or []
			flrg = fts_art.get("flrg_table") or {}
			flr_list = fts_art.get("flr_table") or []
			self._emit_event(
				"GEN",
				EVT.FTS_PARTITION,
				fields=[
					f"partition={fts_art.get('partition_method')}",
					f"requested_intervals={fts_art.get('requested_intervals')}",
					f"actual_intervals={fts_art.get('actual_intervals')}",
					f"pad_pct={fts_art.get('pad_pct')}",
				],
			)
			if isinstance(uod, (tuple, list)) and len(uod) == 2:
				span = float(uod[1]) - float(uod[0])
				n_int = int(fts_art.get("actual_intervals", 1))
				len_int = span / n_int if n_int else 0.0

				self._emit_event(
					"GEN",
					EVT.FTS_UOD,
					fields=[
						f"uod_min={uod[0]}", 
						f"uod_max={uod[1]}",
						f"formula_min=min(data)-pad",
						f"formula_max=max(data)+pad"
					],
				)
				self._emit_event(
					"INFO",
					EVT.FTS_UOD,
					fields=[
						f"n_intervals={n_int}",
						f"interval_len={len_int:.4f}",
						f"formula_len=(uod_max-uod_min)/n"
					]
				)

			self._emit_event(
				"GEN",
				EVT.FTS_FLR,
				fields=[
					f"flr_count={len(flr_list)}",
					f"intervals={len(intervals)}",
				],
			)
			if flr_list:
				self._emit_event(
					"DEBUG",
					EVT.FTS_FLR,
					fields=[f"flr_head={flr_list[:3]}"],
				)
			self._emit_event(
				"GEN",
				EVT.FTS_FLRG,
				fields=[f"flrg_groups={len(flrg)}"],
			)
			if flrg:
				flrg_sample = list(flrg.items())[:3]
				self._emit_event(
					"DEBUG",
					EVT.FTS_FLRG,
					fields=[f"flrg_head={flrg_sample}"],
				)

			# Defuzzification Formula
			midpoints = fts_art.get("midpoints", [])
			if midpoints:
				self._emit_event(
					"INFO",
					EVT.FTS_FORECAST,
					fields=[
						"defuzz_method=Weighted_Average",
						"formula=sum(midpoint[i] * support[i])"
					]
				)

			self._emit_event(
				"DEBUG",
				EVT.FTS_FORECAST,
				fields=[f"forecast_head={fts_out.get('forecast', [])[:5]}"],
			)
			self._emit_event(
				"RESULT",
				EVT.FTS_METRICS,
				fields=[
					f"MAE={fts_metrics['mae']:.6f}",
					f"RMSE={fts_metrics['rmse']:.6f}",
					f"MAPE={fts_metrics['mape']:.4f}%",
				],
				result="status=OK",
			)
			self._emit_event(
				"INFO",
				EVT.FTS_METRICS,
				fields=[f"formula_MAE=mean(|y-yhat|)={fts_metrics['mae']:.6f}"],
			)
			self._emit_event(
				"INFO",
				EVT.FTS_METRICS,
				fields=[f"formula_RMSE=sqrt(mean((y-yhat)^2))={fts_metrics['rmse']:.6f}"],
			)
			self._emit_event(
				"INFO",
				EVT.FTS_METRICS,
				fields=[f"formula_MAPE=mean(|(y-yhat)/y|)*100={fts_metrics['mape']:.4f}%"],
			)

			results["fts"] = {
				"metrics": fts_metrics,
				"forecast": fts_out["forecast"],
				"artifacts": fts_out["artifacts"],
			}
			try:
				sens = run_sensitivity_analysis(
					train_series,
					test_series,
					interval_num=int(fts_params["interval"]),
					method=method,
					pad_pct=pad_pct,
					base_mape=float(fts_metrics.get("mape", 0.0)),
				)
				results["sensitivity"] = sens
				self.sig_log.emit(
					"INFO",
					f"[sens] cases={len(sens.get('cases', []))} | best={sens.get('bestCase')}",
				)
			except Exception as e:
				self.sig_log.emit("ERROR", f"[sens] Failed: {e}")
			self.sig_step_update.emit("fts", "Done", 100)
			if not self.is_running:
				self.sig_log.emit("INFO", "Analysis cancelled by user after FTS stage.")
				self.sig_cancelled.emit()
				return

			# STEP 3: ANN
			if not self.is_running:
				self.sig_log.emit("INFO", "Analysis cancelled by user before ANN stage.")
				self.sig_cancelled.emit()
				return

			self.sig_step_update.emit("ann", "Building Neural Network...", 0)
			ann_params = self.params["ann"]
			ann_model = ANNModel()
			self._emit_event(
				"INIT",
				EVT.ANN_TRAIN_START,
				fields=[
					f"epochs={ann_params.get('epoch')}",
					f"neurons={ann_params.get('neuron')}",
					f"layers={ann_params.get('layers')}",
					f"lr={ann_params.get('lr')}",
				],
			)

			def ann_progress(percent: int, msg: str) -> None:
				if not self.is_running:
					# Abaikan update jika proses sudah dibatalkan
					return
				self.sig_step_update.emit("ann", msg, percent)

			ann_out = ann_model.train_predict(
				train_series,
				test_series,
				config=ann_params,
				progress_callback=ann_progress,
			)

			ann_metrics = Metrics.get_all_metrics(test_series.values, ann_out["forecast"])
			ann_art = ann_out.get("artifacts", {})

			# Scaler & Formula Logging (setelah artifacts tersedia)
			s_min = ann_art.get("scaler_min")
			s_max = ann_art.get("scaler_max")
			if s_min is not None and s_max is not None:
				self._emit_event(
					"INFO",
					EVT.ANN_TRAIN_START,
					fields=[
						f"scaler_min={s_min:.4f}",
						f"scaler_max={s_max:.4f}",
						"formula_norm=(x-min)/(max-min)"
					]
				)

			# Architecture Logging
			if "model_summary" in ann_art or True:
				# gunakan konfigurasi untuk rangkuman arsitektur
				n_layers = ann_params.get("layers", 1)
				n_neurons = ann_params.get("neuron", 10)
				self._emit_event(
					"INFO",
					EVT.ANN_TRAIN_START,
					fields=[
						f"layers={n_layers}",
						f"neurons={n_neurons}",
						"activation=relu_then_linear"
					]
				)
			if "final_loss" in ann_art:
				self._emit_event(
					"INFO",
					EVT.ANN_TRAIN_END,
					fields=[
						f"final_loss={ann_art.get('final_loss')}",
						f"epochs_run={ann_art.get('epochs_run')}",
					],
					result="status=OK",
				)
			loss_hist = ann_art.get("loss_history", [])
			if loss_hist:
				self._emit_event(
					"DEBUG",
					EVT.ANN_TRAIN_END,
					fields=[f"loss_head_tail={loss_hist[:3]} ... {loss_hist[-3:]}"],
				)
			self._emit_event(
				"DEBUG",
				EVT.ANN_PREDICT,
				fields=[f"forecast_head={ann_out.get('forecast', [])[:5]}"],
			)
			self._emit_event(
				"RESULT",
				EVT.ANN_METRICS,
				fields=[
					f"MAE={ann_metrics['mae']:.6f}",
					f"RMSE={ann_metrics['rmse']:.6f}",
					f"MAPE={ann_metrics['mape']:.4f}%",
				],
				result="status=OK",
			)
			self._emit_event(
				"INFO",
				EVT.ANN_METRICS,
				fields=[f"formula_MAE=mean(|y-yhat|)={ann_metrics['mae']:.6f}"],
			)
			self._emit_event(
				"INFO",
				EVT.ANN_METRICS,
				fields=[f"formula_RMSE=sqrt(mean((y-yhat)^2))={ann_metrics['rmse']:.6f}"],
			)
			self._emit_event(
				"INFO",
				EVT.ANN_METRICS,
				fields=[f"formula_MAPE=mean(|(y-yhat)/y|)*100={ann_metrics['mape']:.4f}%"],
			)

			results["ann"] = {
				"metrics": ann_metrics,
				"forecast": ann_out["forecast"],
				"artifacts": ann_out["artifacts"],
			}
			self.sig_step_update.emit("ann", "Done", 100)
			if not self.is_running:
				self.sig_log.emit("INFO", "Analysis cancelled by user after ANN stage.")
				self.sig_cancelled.emit()
				return

			# STEP 4: ARIMA
			if not self.is_running:
				self.sig_log.emit("INFO", "Analysis cancelled by user before ARIMA stage.")
				self.sig_cancelled.emit()
				return

			self.sig_step_update.emit("arima", "Configuring ARIMA/SARIMA...", 0)
			arima_params = self.params["arima"]
			arima_model = ARIMAModel()
			arima_mode = "seasonal" if bool(arima_params.get("seasonal", False)) else "nonseasonal"
			self._emit_event(
				"INIT",
				EVT.ARIMA_FIT,
				fields=[
					f"mode={arima_mode}",
					f"order=({arima_params.get('p')},{arima_params.get('d')},{arima_params.get('q')})",
					f"seasonal=({arima_params.get('P')},{arima_params.get('D')},{arima_params.get('Q')},{arima_params.get('s')})",
				],
			)

			self.sig_step_update.emit(
				"arima",
				"Fitting ARIMA model (may take a while)...",
				30,
			)
			arima_out = arima_model.run(train_series, test_series, config=arima_params)

			self.sig_step_update.emit("arima", "Calculating metrics...", 80)
			arima_metrics = Metrics.get_all_metrics(test_series.values, arima_out["forecast"])
			arima_art = arima_out.get("artifacts", {})
			if "error" in arima_art:
				self._emit_event(
					"FAIL",
					EVT.ARIMA_DIAG,
					fields=[f"error={arima_art.get('error')}"],
					cause="model_failed",
					result="status=FALLBACK",
				)
			else:
				self._emit_event(
					"INFO",
					EVT.ARIMA_DIAG,
					fields=[f"AIC={arima_art.get('aic')}", f"BIC={arima_art.get('bic')}"],
					result="status=OK",
				)
			self._emit_event(
				"DEBUG",
				EVT.ARIMA_FORECAST,
				fields=[f"forecast_head={arima_out.get('forecast', [])[:5]}"],
			)
			self._emit_event(
				"RESULT",
				EVT.ARIMA_METRICS,
				fields=[
					f"MAE={arima_metrics['mae']:.6f}",
					f"RMSE={arima_metrics['rmse']:.6f}",
					f"MAPE={arima_metrics['mape']:.4f}%",
				],
				result="status=OK",
			)
			self._emit_event(
				"INFO",
				EVT.ARIMA_METRICS,
				fields=[f"formula_MAE=mean(|y-yhat|)={arima_metrics['mae']:.6f}"],
			)
			self._emit_event(
				"INFO",
				EVT.ARIMA_METRICS,
				fields=[f"formula_RMSE=sqrt(mean((y-yhat)^2))={arima_metrics['rmse']:.6f}"],
			)
			self._emit_event(
				"INFO",
				EVT.ARIMA_METRICS,
				fields=[f"formula_MAPE=mean(|(y-yhat)/y|)*100={arima_metrics['mape']:.4f}%"],
			)

			results["arima"] = {
				"metrics": arima_metrics,
				"forecast": arima_out["forecast"],
				"artifacts": arima_out["artifacts"],
			}
			self.sig_step_update.emit("arima", "Done", 100)
			if not self.is_running:
				self.sig_log.emit("INFO", "Analysis cancelled by user after ARIMA stage.")
				self.sig_cancelled.emit()
				return

			# FINISH
			self.sig_finished.emit(results)

		except Exception as e:  # pragma: no cover - debug
			traceback.print_exc()
			self.sig_log.emit("ERROR", f"Worker crashed: {e}")
			self.sig_error.emit(str(e))

	def stop(self) -> None:
		"""Menandai worker untuk berhenti secepat aman."""

		self.is_running = False
		self.sig_log.emit("INFO", "Stop requested for analysis worker.")
