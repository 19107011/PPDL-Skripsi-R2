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
Sensitivity Analysis Module

Version: 1.0.1
Created: December 2025
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from logic.fts_chen import FTSChen
from logic.metrics import Metrics


def _delta_mape(base_mape: float, case_mape: float) -> float:
	return float(case_mape - base_mape)


def _run_case(
	train_series: pd.Series,
	test_series: pd.Series,
	interval_num: int,
	method: str,
	pad_pct: float,
) -> float:
	model = FTSChen(interval_num=interval_num, method=method, pad_pct=pad_pct)
	model.fit(train_series)
	out = model.predict(test_series)
	forecast = out.get("forecast", [])
	actual_vals = test_series.values
	if len(forecast) == len(actual_vals) and len(actual_vals) > 1:
		metrics = Metrics.get_all_metrics(actual_vals[1:], forecast[1:])
	else:
		metrics = Metrics.get_all_metrics(actual_vals, forecast)
	return float(metrics.get("mape", 0.0))


def run_sensitivity_analysis(
	train_series: pd.Series,
	test_series: pd.Series,
	interval_num: int,
	method: str,
	pad_pct: float,
	base_mape: float,
) -> dict[str, Any]:
	"""Jalankan 3 skenario sensitivity analysis sesuai mockup."""

	cases: list[dict[str, Any]] = []

	# CASE 1: n + 2
	try:
		case_interval = int(interval_num) + 2
		case_mape = _run_case(train_series, test_series, case_interval, method, pad_pct)
		cases.append(
			{
				"id": "case1",
				"label": f"n = {case_interval}",
				"description": f"Increase intervals by 2 ({interval_num} -> {case_interval})",
				"config": {"interval": case_interval, "method": method, "pad_pct": pad_pct},
				"mape": case_mape,
				"delta": _delta_mape(base_mape, case_mape),
			}
		)
	except Exception:
		pass

	# CASE 2: swap method
	try:
		alt_method = "equal-frequency" if method == "equal-width" else "equal-width"
		case_mape = _run_case(train_series, test_series, interval_num, alt_method, pad_pct)
		cases.append(
			{
				"id": "case2",
				"label": f"method = {alt_method}",
				"description": f"Swap partition method ({method} -> {alt_method})",
				"config": {"interval": interval_num, "method": alt_method, "pad_pct": pad_pct},
				"mape": case_mape,
				"delta": _delta_mape(base_mape, case_mape),
			}
		)
	except Exception:
		pass

	# CASE 3: padPct + 0.05
	try:
		case_pad = float(pad_pct) + 0.05
		case_mape = _run_case(train_series, test_series, interval_num, method, case_pad)
		cases.append(
			{
				"id": "case3",
				"label": f"pad = {case_pad * 100:.0f}%",
				"description": f"Increase UoD padding by 5% ({pad_pct * 100:.0f}% -> {case_pad * 100:.0f}%)",
				"config": {"interval": interval_num, "method": method, "pad_pct": case_pad},
				"mape": case_mape,
				"delta": _delta_mape(base_mape, case_mape),
			}
		)
	except Exception:
		pass

	if not cases:
		return {
			"cases": [],
			"bestCase": None,
			"baselineMAPE": float(base_mape),
			"improvement": 0.0,
		}

	cases.sort(key=lambda item: item.get("mape", 0.0))
	best_case = cases[0]
	improvement = _delta_mape(base_mape, float(best_case.get("mape", 0.0)))

	return {
		"cases": cases,
		"bestCase": best_case.get("id"),
		"baselineMAPE": float(base_mape),
		"improvement": improvement,
	}
