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
Application Logging System

Version: 1.0.1
Created: December 2025
"""

import datetime
import os

from PyQt6.QtCore import QObject, pyqtSignal

from utils.logging_events import ALL_EVENTS
from utils.logging_spec import (
	CAUSE_SEP,
	FIELD_SEP,
	RESULT_SEP,
	LVL1_ALLOWED,
	LVL2_ALLOWED,
	LVL3_ALLOWED,
	LVL4_ALLOWED,
	contains_forbidden,
	format_route,
	normalize_tag,
	validate_tag,
)
from utils.resource_manager import ResourceManager
from utils.run_context import RunContext


class AppLogger(QObject):
	"""Logger sederhana dengan output berwarna ke UI dan file log penuh.

	- Mengirim HTML ke UI lewat sinyal `sig_log_updated`.
	- Menyimpan semua log ke file teks di folder temp ResourceManager.
	"""

	sig_log_updated = pyqtSignal(str)

	COLOR_INFO = "#1f4e79"
	COLOR_SUCCESS = "#1e5631"
	COLOR_WARN = "#b45309"
	COLOR_ERROR = "#8b0000"
	COLOR_DEBUG = "#6b7280"
	COLOR_DEFAULT = "#2c3e50"

	# Event yang wajib masuk SUMMARY VIEW (Doc_for_Ex_Plan-6: 6.1)
	_SUMMARY_EVENTS: set[str] = {
		"UI_SELECT_FOLDER",
		"UI_SELECT_JSON",
		"UI_CLICK_IMPORT",
		"DB_IMPORT_START",
		"DB_IMPORT_DONE",
		"PARAM_GENERAL_SUBMIT",
		"PARAM_FTS_SUBMIT",
		"PARAM_ANN_SUBMIT",
		"PARAM_ARIMA_SUBMIT",
		"PARAM_LOCK_APPLIED",
		"PARAM_LOCK_REJECTED",
		"UI_CLICK_START_ANALYSIS",
		"PRE_RESAMPLE",
		"PRE_SPLIT",
		"FTS_METRICS",
		"ANN_METRICS",
		"ARIMA_METRICS",
		"EXPORT_START",
		"EXPORT_DONE",
		"RPT_BUILD_START",
		"RPT_BUILD_DONE",
	}

	# Prefix legacy yang tetap dianggap "ringkas" dan boleh masuk summary.
	_SUMMARY_PREFIXES: tuple[str, ...] = ("[pipeli]", "[source]", "[param]", "[eval]", "[resume]")

	def __init__(self) -> None:
		super().__init__()
		log_dir = ResourceManager.get_temp_dir()
		self._session_log_path = os.path.join(log_dir, "session_full.log")
		self._log_path = self._session_log_path
		self._default_lvl2 = "MAIN"
		self._default_lvl3 = "BASE"
		self._default_lvl4 = "GENERAL"
		self._run_ctx: RunContext | None = None
		self._run_dir: str | None = None
		self._run_logs: dict[str, str] = {}
		with open(self._session_log_path, "w", encoding="utf-8") as f:
			f.write(f"--- LOG STARTED: {datetime.datetime.now()} ---\n")

	def _append_line(self, path: str, line: str) -> None:
		with open(path, "a", encoding="utf-8") as f:
			f.write(line + "\n")

	def _should_write_summary(self, message: str) -> bool:
		msg = str(message).lstrip()
		evt = AppLogger._infer_evt_code(msg)
		if evt and evt in self._SUMMARY_EVENTS:
			return True
		return msg.startswith(self._SUMMARY_PREFIXES)

	def _append_to_run_logs(self, header: str, message: str) -> None:
		if not self._run_logs:
			return
		line = f"{header} {message}"
		global_path = self._run_logs.get("global")
		if global_path:
			self._append_line(global_path, line)
		if self._should_write_summary(message):
			summary_path = self._run_logs.get("summary")
			if summary_path:
				self._append_line(summary_path, line)

	def start_run(self, run_ctx: RunContext) -> dict[str, str]:
		"""Mulai konteks run baru (GUID) dan siapkan file artefak log per-run.

		RUN-1 (Ex_Plan-6): menulis 3 baris header identitas pada 3 file log:
		- [summary]_[view]_<GUID>.log
		- [calc]_[detail]_<GUID>.log
		- [global]_[view]_<GUID>.log

		Untuk menjaga kompatibilitas, logger tetap mengirim output ke UI,
		dan default file sink diarahkan ke GLOBAL VIEW untuk run aktif.
		"""

		self._run_ctx = run_ctx
		self._run_dir = ResourceManager.create_run_dir(run_ctx.guid)

		guid = run_ctx.guid
		summary_path = os.path.join(self._run_dir, f"[summary]_[view]_{guid}.log")
		calc_path = os.path.join(self._run_dir, f"[calc]_[detail]_{guid}.log")
		global_path = os.path.join(self._run_dir, f"[global]_[view]_{guid}.log")

		identity = run_ctx.identity_lines()
		for path in (summary_path, calc_path, global_path):
			with open(path, "w", encoding="utf-8") as f:
				# 3 baris teratas WAJIB identik (kontrak Doc_for_Ex_Plan-6).
				f.write("\n".join(identity) + "\n")
				f.write("\n")
				f.write(f"--- LOG STARTED: {datetime.datetime.now()} ---\n")

		self._run_logs = {"summary": summary_path, "calc": calc_path, "global": global_path}
		self._log_path = global_path
		return dict(self._run_logs)

	def get_run_guid(self) -> str | None:
		return self._run_ctx.guid if self._run_ctx else None

	def get_run_dir(self) -> str | None:
		return self._run_dir

	def get_run_log_paths(self) -> dict[str, str]:
		return dict(self._run_logs)

	@staticmethod
	def _normalize_lvl1(level: str) -> str:
		"""Normalisasi level legacy ke LVL-1 kontrak (Doc_for_Ex_Plan-5).

		Kontrak LVL-1: DEBUG/INIT/INFO/GEN/WARN/FAIL/ERROR/SUCCESS
		"""

		value = normalize_tag(level)
		if value in LVL1_ALLOWED:
			return value
		legacy_map = {
			"WARNING": "WARN",
			"PROCESS": "GEN",
			"RESULT": "INFO",
			"FORMU": "INFO",
		}
		return legacy_map.get(value, "INFO")

	@staticmethod
	def _infer_evt_code(message: str) -> str | None:
		"""Ambil nilai EVT=... dari body log legacy jika ada."""

		msg = str(message)
		idx = msg.find("EVT=")
		if idx < 0:
			return None
		tail = msg[idx + 4 :]
		evt = tail.split()[0].strip()
		return normalize_tag(evt) if evt else None

	@staticmethod
	def _infer_lvl3(legacy_level: str, message: str) -> str:
		"""Infer LVL-3 (BASE/CAL/RPT) secara minimal untuk backward compatibility."""

		lv = str(legacy_level).strip().upper()
		msg = str(message).lstrip()

		evt = AppLogger._infer_evt_code(msg)
		if evt:
			if evt.endswith("_METRICS") or evt in {"EXPORT_DONE", "RPT_BUILD_DONE"}:
				return "RPT"
			if evt in {"EXPORT_START", "RPT_BUILD_START"}:
				return "CAL"
			if evt in {"UI_CLICK_START_ANALYSIS"}:
				return "CAL"
			if evt.startswith(("PRE_", "FTS_", "ANN_", "ARIMA_", "DB_", "PARAM_")):
				return "CAL"
			if evt.startswith(("HOME_", "UI_")):
				return "BASE"
			# Default aman jika EVT tidak dikenali.
			return "BASE"

		if lv in {"INIT", "PROCESS"}:
			return "CAL"
		if lv in {"RESULT", "SUCCESS"}:
			return "RPT"
		if lv in {"ERROR"}:
			# Error bisa terjadi pada CAL/RPT, tapi default aman untuk compat adalah CAL.
			return "CAL"
		if msg.startswith("[eval]") or msg.startswith("[resume]") or msg.startswith("[baseline]"):
			return "RPT"
		return "BASE"

	@staticmethod
	def _infer_lvl4(message: str) -> str:
		"""Infer LVL-4 (FTS/ANN/ARIMA/GENERAL) untuk log legacy (best-effort)."""

		msg_raw = str(message).lstrip()
		msg = msg_raw.lower()
		if msg.startswith("[fts]") or "evt=fts_" in msg or "EVT=FTS_" in msg_raw:
			return "FTS"
		if msg.startswith("[ann]") or "evt=ann_" in msg or "EVT=ANN_" in msg_raw:
			return "ANN"
		if msg.startswith("[arima]") or "evt=arima_" in msg or "EVT=ARIMA_" in msg_raw:
			return "ARIMA"
		return "GENERAL"

	@staticmethod
	def _format_header(timestamp: str, lvl1: str, lvl2: str, lvl3: str, lvl4: str) -> str:
		return f"[{timestamp}][{lvl1}][{lvl2}][{lvl3}][{lvl4}]"

	def log(
		self,
		level: str,
		message: str,
		*,
		lvl2: str | None = None,
		lvl3: str | None = None,
		lvl4: str | None = None,
		) -> None:
		"""Mencatat pesan dengan format log 4-level (backward compatible)."""

		timestamp = datetime.datetime.now().strftime("%H:%M:%S")
		legacy_level = str(level).strip().upper()
		lvl1_final = self._normalize_lvl1(legacy_level)
		lvl2_final = normalize_tag(lvl2) if lvl2 else self._default_lvl2
		lvl3_final = normalize_tag(lvl3) if lvl3 else self._infer_lvl3(legacy_level, message)
		lvl4_final = normalize_tag(lvl4) if lvl4 else self._infer_lvl4(message)
		header = self._format_header(timestamp, lvl1_final, lvl2_final, lvl3_final, lvl4_final)

		line = f"{header} {message}"
		# Session log selalu ditulis untuk backward compatibility.
		self._append_line(self._session_log_path, line)
		# Jika ada run aktif: tulis juga ke GLOBAL, dan ke SUMMARY bila eligible.
		self._append_to_run_logs(header, message)

		color = self.COLOR_DEFAULT
		if lvl1_final in ("GEN", "INIT", "INFO"):
			color = self.COLOR_INFO
		elif lvl1_final == "SUCCESS":
			color = self.COLOR_SUCCESS
		elif lvl1_final in ("WARN",):
			color = self.COLOR_WARN
		elif lvl1_final in ("FAIL", "ERROR"):
			color = self.COLOR_ERROR
		elif lvl1_final == "DEBUG":
			color = self.COLOR_DEBUG

		level_tag = lvl1_final
		meta_tag = f"[{lvl2_final}][{lvl3_final}][{lvl4_final}]"
		html_msg = (
			f"<span style='color:#555555;'>[{timestamp}]</span>"
			f"<span style='color:{color}; font-weight:bold;'>[{level_tag}]</span> "
			f"<span style='color:#555555; font-weight:bold;'>{meta_tag}</span> "
			f"<span style='color:{color}; font-weight:bold;'>{message}</span>"
		)
		self.sig_log_updated.emit(html_msg)

	def emit_calc_block(
		self,
		*,
		block: str,
		idx: int,
		scope: str,
		method: str,
		steps: list[str],
		result_lines: list[str],
	) -> None:
		"""Menulis CALC DETAIL block (Doc_for_Ex_Plan-6: bagian 7).

		Blok ditulis ke:
		- [calc]_[detail]_<GUID>.log
		- [global]_[view]_<GUID>.log

		Untuk saat ini, blok tidak ditampilkan ke UI agar tidak membanjiri.
		"""

		if not self._run_logs:
			return

		scope_v = normalize_tag(scope)
		method_v = normalize_tag(method)
		block_name = f"{str(block).strip()}#{int(idx):02d}"

		start_line = (
			f"===== START Calculation | BLOCK={block_name} | SCOPE={scope_v} | METHOD={method_v} ====="
		)
		mid_line = f"=={CAUSE_SEP} RESULT {RESULT_SEP}=="
		end_line = f"===== END Calculation | BLOCK={block_name} ====="

		payload: list[str] = [start_line]
		payload.extend([str(x).rstrip() for x in steps if str(x).strip()])
		payload.append(mid_line)
		payload.extend([str(x).rstrip() for x in result_lines if str(x).strip()])
		payload.append(end_line)
		payload.append("")  # spacing antar blok

		calc_path = self._run_logs.get("calc")
		global_path = self._run_logs.get("global")
		for p in [calc_path, global_path]:
			if not p:
				continue
			for ln in payload:
				self._append_line(p, ln)

	def log_event(
		self,
		*,
		lvl1: str,
		lvl2: str,
		lvl3: str,
		lvl4: str,
		evt: str,
		route_to: list[str] | None,
		fields: list[str] | None = None,
		cause: str | None = None,
		result: str | None = None,
		strict: bool = True,
	) -> None:
		"""Log event sesuai kontrak: wajib EVT dan ROUTE.

		Format body minimal:
		`EVT=<EVENT_CODE> | ROUTE: <ACTOR>  <TARGETS> | <fields...>  <cause>  <result>`
		"""

		lvl1_v = validate_tag(lvl1, LVL1_ALLOWED, "LVL-1")
		lvl2_v = validate_tag(lvl2, LVL2_ALLOWED, "LVL-2")
		lvl3_v = validate_tag(lvl3, LVL3_ALLOWED, "LVL-3")
		lvl4_v = validate_tag(lvl4, LVL4_ALLOWED, "LVL-4")
		evt_v = normalize_tag(evt)
		if strict and evt_v not in ALL_EVENTS:
			raise ValueError(f"EVT not in catalog: {evt_v}")

		route = format_route(lvl2_v, route_to)
		parts = [f"EVT={evt_v}", route]
		if fields:
			parts.extend([str(x).strip() for x in fields if str(x).strip()])
		msg = FIELD_SEP.join(parts)
		if cause:
			msg = f"{msg} {CAUSE_SEP} {cause}"
		if result:
			msg = f"{msg} {RESULT_SEP} {result}"

		forbidden = contains_forbidden(msg)
		if forbidden:
			if strict:
				raise ValueError(f"Forbidden word in log body: {forbidden!r}")
			msg = f"{msg}{FIELD_SEP}guard_forbidden={forbidden}"
			lvl1_v = "WARN"

		self.log(lvl1_v, msg, lvl2=lvl2_v, lvl3=lvl3_v, lvl4=lvl4_v)

	def get_log_path(self) -> str:
		"""Mengembalikan path file log penuh sesi ini."""

		return self._log_path
