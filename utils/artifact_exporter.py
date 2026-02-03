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
Export Artifact Handler

Version: 1.0.1
Created: December 2025
"""

from __future__ import annotations

import hashlib
import json
import os
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class ExportResult:
	ok: bool
	message: str
	paths: dict[str, str]


def _safe_mkdir(path: str) -> None:
	os.makedirs(path, exist_ok=True)


def _read_identity_lines(log_path: str) -> list[str]:
	try:
		with open(log_path, "r", encoding="utf-8") as f:
			lines = [f.readline().rstrip("\n") for _ in range(3)]
		return [x for x in lines if x.strip()]
	except Exception:
		return []


def _normalize_df_for_snapshot(df: pd.DataFrame | None) -> pd.DataFrame:
	if df is None or getattr(df, "empty", True):
		return pd.DataFrame()

	out = df.copy()
	if "timestamp" not in out.columns:
		if "ts_server" in out.columns:
			out["timestamp"] = pd.to_datetime(out["ts_server"], unit="ms", errors="coerce")
		else:
			# Fallback: gunakan index bila bisa.
			try:
				out["timestamp"] = pd.to_datetime(out.index, errors="coerce")
			except Exception:
				out["timestamp"] = pd.NaT
	else:
		out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce")

	# Normalize common columns when present
	for col in ["watt", "voltage", "current", "frequency", "energy_kwh", "pf", "synthetic"]:
		if col in out.columns:
			continue
		# legacy alias
		alias_map = {"W": "watt", "V": "voltage", "A": "current", "F": "frequency", "kWh": "energy_kwh"}
		for src, dest in alias_map.items():
			if dest == col and src in out.columns:
				out[col] = out[src]
				break

	# Sort by timestamp if available
	if "timestamp" in out.columns:
		out = out.sort_values("timestamp").reset_index(drop=True)
	return out


def export_params_snapshot(*, out_dir: str, guid: str, params: dict, identity_lines: list[str]) -> str:
	_safe_mkdir(out_dir)
	payload = {
		"run_guid": guid,
		"identity_lines": identity_lines,
		"exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
		"params": params,
	}
	path = os.path.join(out_dir, f"params_{guid}.json")
	with open(path, "w", encoding="utf-8") as f:
		json.dump(payload, f, ensure_ascii=False, indent=2)
	return path


def export_dataset_schema_range(*, out_dir: str, guid: str, df: pd.DataFrame) -> tuple[str, str]:
	_safe_mkdir(out_dir)
	dfn = _normalize_df_for_snapshot(df)

	unit_map = {
		"timestamp": "datetime",
		"ts_server": "ms_epoch",
		"watt": "W",
		"voltage": "V",
		"current": "A",
		"frequency": "Hz",
		"energy_kwh": "kWh",
		"pf": "ratio",
		"synthetic": "flag",
	}

	cols = []
	for col in dfn.columns:
		try:
			dtype = str(dfn[col].dtype)
		except Exception:
			dtype = "unknown"
		cols.append({"name": col, "dtype": dtype, "unit": unit_map.get(col)})

	schema = {
		"run_guid": guid,
		"exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
		"columns": cols,
	}

	schema_path = os.path.join(out_dir, f"dataset_schema_{guid}.json")
	with open(schema_path, "w", encoding="utf-8") as f:
		json.dump(schema, f, ensure_ascii=False, indent=2)

	row_count = int(len(dfn))
	missing_by_col = {c: int(dfn[c].isna().sum()) for c in dfn.columns}

	start_ts = None
	end_ts = None
	if "timestamp" in dfn.columns:
		ts = pd.to_datetime(dfn["timestamp"], errors="coerce").dropna()
		if not ts.empty:
			start_ts = ts.min()
			end_ts = ts.max()

	range_payload = {
		"run_guid": guid,
		"exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
		"rows": row_count,
		"range": {
			"start": start_ts.strftime("%Y-%m-%d %H:%M:%S") if start_ts is not None else None,
			"end": end_ts.strftime("%Y-%m-%d %H:%M:%S") if end_ts is not None else None,
		},
		"missing_by_col": missing_by_col,
	}

	range_path = os.path.join(out_dir, f"dataset_range_{guid}.json")
	with open(range_path, "w", encoding="utf-8") as f:
		json.dump(range_payload, f, ensure_ascii=False, indent=2)

	return schema_path, range_path


def export_dataset_snapshot_csv(
	*,
	out_dir: str,
	guid: str,
	df: pd.DataFrame,
	max_rows_full: int = 200_000,
) -> tuple[str, dict]:
	"""Export dataset snapshot CSV.

	Kebijakan:
	- Jika rows <= max_rows_full: simpan full.
	- Jika lebih: simpan head+tail (masing-masing 5.000) + metadata strategi.
	"""

	_safe_mkdir(out_dir)
	dfn = _normalize_df_for_snapshot(df)
	row_count = int(len(dfn))

	strategy = "full"
	head_n = 0
	tail_n = 0
	out_df = dfn
	if row_count > int(max_rows_full):
		strategy = "head_tail"
		head_n = min(5000, row_count)
		tail_n = min(5000, max(0, row_count - head_n))
		out_df = pd.concat([dfn.head(head_n), dfn.tail(tail_n)], ignore_index=True)

	path = os.path.join(out_dir, f"dataset_snapshot_{guid}.csv")

	sha256 = hashlib.sha256()
	with open(path, "w", encoding="utf-8", newline="") as f:
		# tulis CSV via pandas ke file handle
		out_df.to_csv(f, index=False)

	with open(path, "rb") as rf:
		for chunk in iter(lambda: rf.read(1024 * 1024), b""):
			sha256.update(chunk)

	meta = {
		"strategy": strategy,
		"rows_total": row_count,
		"rows_written": int(len(out_df)),
		"head_n": head_n,
		"tail_n": tail_n,
		"sha256": sha256.hexdigest(),
	}
	return path, meta


def export_log_zip(*, out_dir: str, guid: str, log_paths: dict[str, str]) -> str:
	_safe_mkdir(out_dir)
	zip_path = os.path.join(out_dir, f"PPDL_LOG_{guid}.zip")

	want = {
		"summary": f"[summary]_[view]_{guid}.log",
		"calc": f"[calc]_[detail]_{guid}.log",
		"global": f"[global]_[view]_{guid}.log",
	}

	with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
		for key, arc_name in want.items():
			src = log_paths.get(key)
			if not src or not os.path.exists(src):
				raise FileNotFoundError(f"Missing run log for zip: {key} -> {src}")
			zf.write(src, arcname=arc_name)

	return zip_path


def export_academic_artifacts(
	*,
	out_dir: str,
	guid: str,
	log_paths: dict[str, str],
	params: dict,
	raw_df: pd.DataFrame | None,
	include_csv: bool = True,
) -> ExportResult:
	"""Ekspor artefak akademik Run-3 (Doc_for_Ex_Plan-6: bagian 3)."""

	try:
		_safe_mkdir(out_dir)

		global_log = log_paths.get("global") or ""
		identity_lines = _read_identity_lines(global_log) if global_log else []

		params_path = export_params_snapshot(out_dir=out_dir, guid=guid, params=params, identity_lines=identity_lines)
		df_for_schema = raw_df if raw_df is not None else pd.DataFrame()
		schema_path, range_path = export_dataset_schema_range(out_dir=out_dir, guid=guid, df=df_for_schema)

		csv_path = ""
		csv_meta: dict = {}
		if include_csv and raw_df is not None and not raw_df.empty:
			csv_path, csv_meta = export_dataset_snapshot_csv(out_dir=out_dir, guid=guid, df=raw_df)
			# simpan metadata snapshot agar jelas bila head/tail
			meta_path = os.path.join(out_dir, f"dataset_snapshot_{guid}.meta.json")
			with open(meta_path, "w", encoding="utf-8") as f:
				json.dump({"run_guid": guid, "snapshot": csv_meta}, f, ensure_ascii=False, indent=2)
		else:
			meta_path = ""

		zip_path = export_log_zip(out_dir=out_dir, guid=guid, log_paths=log_paths)

		paths = {
			"log_zip": zip_path,
			"params_json": params_path,
			"dataset_schema_json": schema_path,
			"dataset_range_json": range_path,
		}
		if csv_path:
			paths["dataset_snapshot_csv"] = csv_path
		if meta_path:
			paths["dataset_snapshot_meta_json"] = meta_path

		return ExportResult(True, "OK", paths)
	except Exception as e:
		return ExportResult(False, str(e), {})
