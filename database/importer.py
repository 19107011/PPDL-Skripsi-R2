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
Data Import Module

Version: 1.0.1
Created: December 2025
"""

import json
from typing import Any, Dict, List

from .db_manager import DBManager


class DataImporter:
	"""Importer data JSON RTDB / BigQuery export ke SQLite.

	Implementasi awal mengikuti struktur JSON yang sudah dipakai
	di FTS-Lab (JS) dan file contoh di folder `input_data`.
	"""

	def __init__(self, db_manager: DBManager) -> None:
		self.db = db_manager

	def _flatten_telemetry(self, raw: Any) -> List[Dict[str, Any]]:
		"""Mengubah struktur JSON nested menjadi list row datar.

		Mendukung pola umum:
		- {"devices": {"id": {"telemetry": {"key": {...}}}}}
		- Langsung objek telemetry: {"key": {...}}
		"""

		telemetry_node = raw

		if isinstance(raw, dict) and "devices" in raw:
			# Ambil device pertama
			dev_ids = list(raw["devices"].keys())
			if not dev_ids:
				return []
			dev_id = dev_ids[0]
			telemetry_node = raw["devices"][dev_id].get("telemetry", {})

		if not isinstance(telemetry_node, dict):
			return []

		rows: List[Dict[str, Any]] = []
		for _key, val in telemetry_node.items():
			if not isinstance(val, dict):
				continue

			# RTDB export biasanya pakai ts_server_ms dan W
			if "ts_server_ms" not in val or "W" not in val:
				continue

			ts = int(val["ts_server_ms"])
			watt = float(val.get("W", 0))
			voltage = float(val.get("V", 0))
			current = float(val.get("A", 0))
			frequency = float(val.get("F", 0))
			energy_kwh = float(val.get("kWh", 0))
			pf = float(val.get("pf", 0))
			if voltage in (0.0, -1.0) and pf == 0.0:
				continue

			rows.append(
				{
					"ts_server": ts,
					"watt": watt,
					"voltage": voltage,
					"current": current,
					"frequency": frequency,
					"energy_kwh": energy_kwh,
					"pf": pf,
					"source": "json_import",
				}
			)

		return rows

	def import_from_json(self, json_path: str) -> Dict[str, Any]:
		"""Membaca file JSON dan memasukkan data ke SQLite.

		Mengembalikan ringkasan proses sebagai dict.
		"""

		try:
			with open(json_path, "r", encoding="utf-8") as f:
				raw_data = json.load(f)

			rows = self._flatten_telemetry(raw_data)
			if not rows:
				return {
					"status": "empty",
					"total_found": 0,
					"inserted_new": 0,
					"message": "Tidak ada record valid (ts_server_ms & W).",
				}

			inserted = self.db.bulk_insert_telemetry(rows)

			return {
				"status": "success",
				"total_found": len(rows),
				"inserted_new": inserted,
			}

		except Exception as e:  # pragma: no cover - log sederhana
			return {"status": "error", "message": str(e)}
