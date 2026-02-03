"""Smoke test backend PPDL V1.0 (aligned with latest logic).

Tujuan:
- Validasi pipeline backend end-to-end tanpa UI.
- Cek konsistensi rumus (FTS, baseline, metrics, sensitivity, resample).
- Generate report Markdown di folder smoke.

Cara menjalankan:
    cd ppdl-app
    python -m smoke.smoke_backend
"""

from __future__ import annotations

import os
import sys
import traceback
from datetime import datetime

import numpy as np

from database.db_manager import DBManager
from database.importer import DataImporter
from logic.preprocessing import Preprocessor
from logic.fts_chen import FTSChen
from logic.ann_model import ANNModel
from logic.arima_model import ARIMAModel
from logic.metrics import Metrics
from logic.baseline import NaivePredictor, MovingAveragePredictor
from logic.sensitivity import run_sensitivity_analysis


def _find_sample_json(project_root: str) -> str:
	"""Cari 1 file JSON di folder input_data."""
	sample_dir = os.path.join(project_root, "input_data")
	if not os.path.isdir(sample_dir):
		raise RuntimeError(f"Folder input_data tidak ditemukan: {sample_dir}")

	for name in os.listdir(sample_dir):
		if name.lower().endswith(".json"):
			return os.path.join(sample_dir, name)

	raise RuntimeError(f"Tidak ada file .json di folder: {sample_dir}")


def _record_check(report: dict, name: str, ok: bool, detail: str = "") -> None:
	status = "PASS" if ok else "FAIL"
	report["checks"].append({"status": status, "name": name, "detail": detail})
	if not ok:
		report["has_failures"] = True


def _write_report(report_path: str, report: dict) -> None:
	lines: list[str] = []
	lines.append("# Smoke Backend Report")
	lines.append("")
	lines.append(f"Timestamp: {report.get('timestamp', '-')}")
	lines.append(f"Status: {report.get('status', '-')}")
	lines.append("")
	lines.append("## Summary")
	lines.append(f"- Project root: `{report.get('project_root', '-')}`")
	lines.append(f"- Sample JSON: `{report.get('sample_path', '-')}`")
	lines.append(f"- Raw rows: {report.get('raw_rows', 0)}")
	lines.append(f"- Train size: {report.get('train_size', 0)}")
	lines.append(f"- Test size: {report.get('test_size', 0)}")
	lines.append("")

	resample = report.get("resample", {})
	if resample:
		lines.append("## Preprocess (Resample)")
		lines.append("| Method | Resampled | Missing Filled |")
		lines.append("| --- | --- | --- |")
		for method, info in resample.items():
			lines.append(
				f"| {method} | {info.get('resampled', 0)} | {info.get('missing_filled', 0)} |"
			)
		lines.append("")

	models = report.get("models", {})
	if models:
		lines.append("## Metrics (Test Window)")
		lines.append("| Model | MAE | RMSE | MAPE (%) | Ignored Zero |")
		lines.append("| --- | --- | --- | --- | --- |")
		for name, metrics in models.items():
			lines.append(
				"| {name} | {mae:.4f} | {rmse:.4f} | {mape:.2f} | {ignored} |".format(
					name=name,
					mae=float(metrics.get("mae", 0.0)),
					rmse=float(metrics.get("rmse", 0.0)),
					mape=float(metrics.get("mape", 0.0)),
					ignored=int(metrics.get("ignored_zero_count", 0)),
				)
			)
		lines.append("")

	sensitivity = report.get("sensitivity")
	if sensitivity:
		lines.append("## Sensitivity Analysis")
		lines.append(f"- Baseline MAPE: {float(sensitivity.get('baselineMAPE', 0.0)):.2f}%")
		lines.append(f"- Best case: {sensitivity.get('bestCase', 'N/A')}")
		lines.append(f"- Improvement: {float(sensitivity.get('improvement', 0.0)):.2f}%")
		lines.append("")
		lines.append("| Case | MAPE (%) | Delta (%) |")
		lines.append("| --- | --- | --- |")
		for case in sensitivity.get("cases", []):
			lines.append(
				"| {label} | {mape:.2f} | {delta:.2f} |".format(
					label=case.get("label", "N/A"),
					mape=float(case.get("mape", 0.0)),
					delta=float(case.get("delta", 0.0)),
				)
			)
		lines.append("")

	lines.append("## Checks")
	for item in report.get("checks", []):
		detail = f" - {item['detail']}" if item.get("detail") else ""
		lines.append(f"- {item['status']}: {item['name']}{detail}")

	if report.get("errors"):
		lines.append("")
		lines.append("## Errors")
		lines.append("```")
		for err in report.get("errors", []):
			lines.append(str(err))
		lines.append("```")

	lines.append("")
	lines.append(f"Report file: `{report_path}`")

	with open(report_path, "w", encoding="utf-8") as f:
		f.write("\n".join(lines))


def main() -> int:
	project_root = os.path.dirname(os.path.abspath(os.path.join(__file__, os.pardir)))
	report_path = os.path.join(os.path.dirname(__file__), "Report_SMOKE.md")
	report = {
		"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
		"status": "RUNNING",
		"project_root": project_root,
		"sample_path": None,
		"raw_rows": 0,
		"train_size": 0,
		"test_size": 0,
		"resample": {},
		"models": {},
		"sensitivity": None,
		"checks": [],
		"errors": [],
		"has_failures": False,
	}

	print("=== SMOKE BACKEND: PPDL V1.0 ===")
	print(f"Project root : {project_root}")
	print(f"Report path  : {report_path}")

	try:
		# STEP 1: Import data
		db = DBManager()
		importer = DataImporter(db)

		sample_path = _find_sample_json(project_root)
		report["sample_path"] = sample_path
		print(f"Sample JSON : {sample_path}")

		print("\n[STEP 1] Import JSON -> SQLite ...")
		imp_res = importer.import_from_json(sample_path)
		print(f"Importer result: {imp_res}")

		# STEP 2: Fetch data
		print("\n[STEP 2] Fetch data dari DB ...")
		df_raw = db.fetch_data()
		report["raw_rows"] = len(df_raw)
		print(f"Rows fetched : {len(df_raw)}")
		_record_check(report, "DB fetch non-empty", not df_raw.empty, f"rows={len(df_raw)}")

		if df_raw.empty:
			raise RuntimeError("DataFrame kosong setelah fetch_data().")

		# STEP 3: Preprocessing with multiple methods
		print("\n[STEP 3] Preprocessing (resample + split) ...")
		for method in ["mean", "ffill", "linear"]:
			try:
				prep = Preprocessor.resample_data(
					df_raw,
					interval_minutes=5,
					resample_method=method,
				)
				series_clean = prep["data"]
				artifacts = prep.get("artifacts", {})
				report["resample"][method] = {
					"resampled": len(series_clean),
					"missing_filled": int(artifacts.get("missing_filled", 0)),
				}
				_record_check(
					report,
					f"Resample method {method}",
					len(series_clean) > 0,
					f"resampled={len(series_clean)}",
				)
				print(f"{method} resampled count : {len(series_clean)}")
			except Exception as e:
				report["errors"].append(f"Resample {method} failed: {e}")
				_record_check(report, f"Resample method {method}", False, str(e))

		prep_main = Preprocessor.resample_data(
			df_raw,
			interval_minutes=5,
			resample_method="mean",
		)
		series_clean = prep_main["data"]
		train_series, test_series = Preprocessor.train_test_split(series_clean, ratio=0.8)
		report["train_size"] = len(train_series)
		report["test_size"] = len(test_series)
		print(f"Train size      : {len(train_series)}")
		print(f"Test size       : {len(test_series)}")

		if len(train_series) < 10 or len(test_series) < 5:
			raise RuntimeError("Data terlalu sedikit untuk smoke test model.")

		# STEP 4: FTS Cheng (equal-width)
		print("\n[STEP 4] FTS Cheng (equal-width) ...")
		pad_pct = 0.05
		fts = FTSChen(interval_num=7, method="equal-width", pad_pct=pad_pct)
		fts.fit(train_series)
		fts_out = fts.predict(test_series)
		fts_forecast = fts_out.get("forecast", [])
		actual_vals = test_series.values
		if len(fts_forecast) == len(actual_vals) and len(actual_vals) > 1:
			fts_metrics = Metrics.get_all_metrics(actual_vals[1:], fts_forecast[1:])
		else:
			fts_metrics = Metrics.get_all_metrics(actual_vals, fts_forecast)
		report["models"]["FTS (equal-width)"] = fts_metrics
		print("FTS metrics  :", fts_metrics)

		uod = fts_out.get("artifacts", {}).get("uod")
		train_min = float(train_series.min())
		train_max = float(train_series.max())
		span = train_max - train_min
		expected_min = train_min - (span * pad_pct)
		expected_max = train_max + (span * pad_pct)
		uod_ok = (
			uod
			and abs(uod[0] - expected_min) <= 1e-6
			and abs(uod[1] - expected_max) <= 1e-6
		)
		_record_check(report, "FTS UoD padding span-based", bool(uod_ok), f"uod={uod}")

		alignment_ok = len(fts_forecast) > 0 and fts_forecast[0] is None
		_record_check(report, "FTS alignment (t-1 -> t)", bool(alignment_ok), "forecast[0]=None")

		clamp_ok = True
		if uod and fts_forecast:
			uod_min, uod_max = uod
			for pred in fts_forecast:
				if pred is None or not np.isfinite(pred):
					continue
				if pred < uod_min or pred > uod_max:
					clamp_ok = False
					break
		_record_check(report, "FTS clamp within UoD", clamp_ok)

		flrg_table = fts_out.get("artifacts", {}).get("flrg_table", {})
		support_ok = any("%" in str(v) for v in flrg_table.values()) if flrg_table else False
		_record_check(report, "FTS FLRG support (%)", support_ok)

		# STEP 4b: FTS Cheng (equal-frequency)
		print("\n[STEP 4b] FTS Cheng (equal-frequency) ...")
		fts_freq = FTSChen(interval_num=7, method="equal-frequency", pad_pct=pad_pct)
		fts_freq.fit(train_series)
		fts_freq_out = fts_freq.predict(test_series)
		fts_freq_forecast = fts_freq_out.get("forecast", [])
		if len(fts_freq_forecast) == len(actual_vals) and len(actual_vals) > 1:
			fts_freq_metrics = Metrics.get_all_metrics(actual_vals[1:], fts_freq_forecast[1:])
		else:
			fts_freq_metrics = Metrics.get_all_metrics(actual_vals, fts_freq_forecast)
		report["models"]["FTS (equal-frequency)"] = fts_freq_metrics
		print("FTS eqfreq metrics:", fts_freq_metrics)
		_record_check(
			report,
			"FTS equal-frequency intervals",
			len(fts_freq_out.get("artifacts", {}).get("intervals", [])) >= 3,
			f"intervals={len(fts_freq_out.get('artifacts', {}).get('intervals', []))}",
		)

		# STEP 5: Baselines
		print("\n[STEP 5] Baseline Naive & MA ...")
		naive_forecast = NaivePredictor.predict(train_series, test_series)
		ma_window = max(2, int(7))
		ma_forecast = MovingAveragePredictor.predict(train_series, test_series, window=ma_window)
		naive_metrics = Metrics.get_all_metrics(test_series.values, naive_forecast)
		ma_metrics = Metrics.get_all_metrics(test_series.values, ma_forecast)
		report["models"]["Naive"] = naive_metrics
		report["models"][f"MA(w={ma_window})"] = ma_metrics
		print("Naive metrics:", naive_metrics)
		print("MA metrics   :", ma_metrics)

		naive_nan_ok = len(naive_forecast) > 0 and np.isnan(naive_forecast[0])
		ma_nan_ok = len(ma_forecast) > 0 and np.isnan(ma_forecast[0])
		_record_check(report, "Baseline Naive first NaN", naive_nan_ok)
		_record_check(report, "Baseline MA first NaN", ma_nan_ok)

		# STEP 6: Metrics zero handling
		print("\n[STEP 6] Metrics zero handling ...")
		zero_metrics = Metrics.get_all_metrics([0.0, 10.0], [0.0, 9.0])
		zero_ok = zero_metrics.get("ignored_zero_count", 0) == 1
		_record_check(report, "MAPE skip zero actual", zero_ok, f"ignored={zero_metrics.get('ignored_zero_count')}")

		# STEP 7: Sensitivity analysis
		print("\n[STEP 7] Sensitivity analysis ...")
		sens = run_sensitivity_analysis(
			train_series,
			test_series,
			interval_num=7,
			method="equal-width",
			pad_pct=pad_pct,
			base_mape=float(fts_metrics.get("mape", 0.0)),
		)
		report["sensitivity"] = sens
		_record_check(report, "Sensitivity 3 cases", len(sens.get("cases", [])) == 3)

		# STEP 8: ANN
		print("\n[STEP 8] ANN Model ...")
		ann = ANNModel()
		ann_cfg = {"epoch": 10, "neuron": 8, "layers": 1, "lr": 0.01}
		ann_out = ann.train_predict(train_series, test_series, ann_cfg, progress_callback=None)
		ann_metrics = Metrics.get_all_metrics(test_series.values, ann_out.get("forecast", []))
		report["models"]["ANN"] = ann_metrics
		print("ANN metrics  :", ann_metrics)

		# STEP 9: ARIMA
		print("\n[STEP 9] ARIMA Model ...")
		arima = ARIMAModel()
		arima_cfg = {"p": 1, "d": 1, "q": 1, "seasonal": False, "P": 0, "D": 0, "Q": 0, "s": 12}
		arima_out = arima.run(train_series, test_series, arima_cfg)
		arima_metrics = Metrics.get_all_metrics(test_series.values, arima_out.get("forecast", []))
		report["models"]["ARIMA"] = arima_metrics
		print("ARIMA metrics:", arima_metrics)

		report["status"] = "FAIL" if report["has_failures"] else "PASS"
		print("\n=== SMOKE BACKEND SELESAI ===")
		print(f"Status: {report['status']}")
		return 0 if report["status"] == "PASS" else 1

	except Exception as e:
		report["errors"].append(traceback.format_exc())
		report["status"] = "FAIL"
		print("\n=== SMOKE BACKEND GAGAL ===")
		print("Error:", e)
		traceback.print_exc()
		return 1

	finally:
		if report.get("status") == "RUNNING":
			report["status"] = "FAIL"
		_write_report(report_path, report)
		print(f"Report saved: {report_path}")


if __name__ == "__main__":
	sys.exit(main())
