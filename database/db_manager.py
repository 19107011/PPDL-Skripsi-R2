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
Database Management System

Version: 1.0.1
Created: December 2025
"""

import sqlite3
from typing import Any, Dict, List

import pandas as pd

from config.constants import DB_PATH, TBL_RAW, TBL_EXP_LOG, TBL_EXP_RES


class DBManager:
	"""Wrapper sederhana untuk operasi SQLite di PPDL V1.0.

	Tugas utama:
	- Inisialisasi skema database (tabel raw_telemetry, experiment_log, experiment_results)
	- Insert batch telemetry
	- Mengambil data mentah untuk diproses
	- Menyimpan log eksperimen dan hasil per metode
	"""

	def __init__(self, db_path: str = DB_PATH) -> None:
		self.db_path = db_path
		self._init_db()

	def _get_conn(self) -> sqlite3.Connection:
		return sqlite3.connect(self.db_path)

	def _init_db(self) -> None:
		"""Membuat tabel jika belum ada sesuai schema blueprint."""

		conn = self._get_conn()
		cur = conn.cursor()

		# 1. Tabel raw telemetry (extended sensor fields)
		cur.execute(
			f"""
			CREATE TABLE IF NOT EXISTS {TBL_RAW} (
				ts_server BIGINT PRIMARY KEY,
				watt REAL NOT NULL,
				voltage REAL,
				current REAL,
				frequency REAL,
				energy_kwh REAL,
				pf REAL,
				source TEXT DEFAULT 'main'
			)
			"""
		)
		cur.execute(
			f"CREATE INDEX IF NOT EXISTS idx_{TBL_RAW}_ts ON {TBL_RAW}(ts_server)"
		)

		# 2. Tabel experiment_log (header analisis)
		cur.execute(
			f"""
			CREATE TABLE IF NOT EXISTS {TBL_EXP_LOG} (
				run_id INTEGER PRIMARY KEY AUTOINCREMENT,
				run_date TEXT,
				config_snapshot TEXT,
				split_ratio REAL
			)
			"""
		)

		# 3. Tabel experiment_results (detail hasil per metode)
		cur.execute(
			f"""
			CREATE TABLE IF NOT EXISTS {TBL_EXP_RES} (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				run_id INTEGER,
				method_name TEXT,
				mae REAL,
				mape REAL,
				rmse REAL,
				artifacts_blob TEXT,
				forecast_blob TEXT,
				FOREIGN KEY(run_id) REFERENCES {TBL_EXP_LOG}(run_id)
			)
			"""
		)

		# Pastikan kolom tambahan ada (migrasi jika tabel lama)
		try:
			cur.execute(f"PRAGMA table_info({TBL_RAW})")
			cols = [row[1] for row in cur.fetchall()]
			for col, sql in [
				("current", f"ALTER TABLE {TBL_RAW} ADD COLUMN current REAL"),
				("frequency", f"ALTER TABLE {TBL_RAW} ADD COLUMN frequency REAL"),
				("energy_kwh", f"ALTER TABLE {TBL_RAW} ADD COLUMN energy_kwh REAL"),
				("pf", f"ALTER TABLE {TBL_RAW} ADD COLUMN pf REAL"),
			]:
				if col not in cols:
					try:
						cur.execute(sql)
					except Exception:
						pass
		except Exception:
			pass

		conn.commit()
		conn.close()

	# ------------------------------------------------------------------
	# Telemetry
	# ------------------------------------------------------------------

	def bulk_insert_telemetry(self, data_list: List[Dict[str, Any]]) -> int:
		"""Insert data telemetry secara batch.

		Menggunakan INSERT OR IGNORE agar tidak dobel jika primary key sama.
		"""

		if not data_list:
			return 0

		conn = self._get_conn()
		cur = conn.cursor()
		try:
			cur.executemany(
				f"""
				INSERT OR IGNORE INTO {TBL_RAW}
					(ts_server, watt, voltage, current, frequency, energy_kwh, pf, source)
				VALUES
					(:ts_server, :watt, :voltage, :current, :frequency, :energy_kwh, :pf, :source)
				""",
				data_list,
			)
			conn.commit()
			# rowcount bisa -1 untuk executemany di sqlite, jadi gunakan len(list)
			return len(data_list)
		except Exception as e:  # pragma: no cover - log sederhana
			print(f"[ERR] Bulk Insert Failed: {e}")
			conn.rollback()
			return 0
		finally:
			conn.close()

	def fetch_data(self) -> pd.DataFrame:
		"""Mengambil seluruh data telemetry terurut waktu sebagai DataFrame."""

		conn = self._get_conn()
		try:
			try:
				# Jalur normal: gunakan pandas read_sql_query
				df = pd.read_sql_query(
					f"SELECT ts_server, watt, voltage, current, frequency, energy_kwh, pf, source FROM {TBL_RAW} ORDER BY ts_server ASC",
					conn,
				)
			except RecursionError:
				# Workaround untuk error RecursionError di beberapa versi pandas:
				# bangun DataFrame manual via sqlite3 cursor
				cur = conn.cursor()
				cur.execute(
					f"SELECT ts_server, watt, voltage, current, frequency, energy_kwh, pf, source FROM {TBL_RAW} ORDER BY ts_server ASC"
				)
				rows = cur.fetchall()
				cols = [desc[0] for desc in cur.description]
				df = pd.DataFrame(rows, columns=cols)
			return df
		finally:
			conn.close()

	def clear_raw_data(self) -> int:
		"""Menghapus seluruh isi tabel telemetry mentah.

		Mengembalikan jumlah baris yang terhapus (approximate untuk keperluan UI).
		"""

		conn = self._get_conn()
		cur = conn.cursor()
		try:
			cur.execute(f"DELETE FROM {TBL_RAW}")
			deleted = cur.rowcount if cur.rowcount is not None else 0
			conn.commit()
			return deleted
		except Exception as e:  # pragma: no cover - log sederhana
			print(f"[ERR] Clear Raw Data Failed: {e}")
			conn.rollback()
			return 0
		finally:
			conn.close()

	def clear_experiment_data(self) -> int:
		"""Menghapus isi tabel experiment (log & results) untuk runtime-only storage.

		Urutan: hapus dulu results baru logs agar foreign key tidak bermasalah.
		Mengembalikan jumlah total baris yang dihapus (aproksimasi).
		"""

		conn = self._get_conn()
		cur = conn.cursor()
		deleted_total = 0
		try:
			cur.execute(f"DELETE FROM {TBL_EXP_RES}")
			deleted_total += cur.rowcount if cur.rowcount is not None else 0
			cur.execute(f"DELETE FROM {TBL_EXP_LOG}")
			deleted_total += cur.rowcount if cur.rowcount is not None else 0
			conn.commit()
			return deleted_total
		except Exception as e:
			print(f"[ERR] Clear Experiment Data Failed: {e}")
			conn.rollback()
			return deleted_total
		finally:
			conn.close()

	def clear_all_runtime(self) -> Dict[str, int]:
		"""Bersihkan semua tabel yang dipakai runtime: raw & experiment tables."""

		return {
			"raw_deleted": self.clear_raw_data(),
			"exp_deleted": self.clear_experiment_data(),
		}

	def get_row_count_raw(self) -> int:
		"""Return total row count in raw_telemetry table."""
		conn = self._get_conn()
		cur = conn.cursor()
		cur.execute(f"SELECT COUNT(*) FROM {TBL_RAW}")
		count = cur.fetchone()[0]
		conn.close()
		return count

	def _get_energy_range(self, cur: sqlite3.Cursor, start_ts: int | None = None, end_ts: int | None = None) -> float:
		where_clause = "WHERE energy_kwh IS NOT NULL"
		params: tuple[Any, ...] = ()
		if start_ts is not None and end_ts is not None:
			where_clause = "WHERE ts_server >= ? AND ts_server <= ? AND energy_kwh IS NOT NULL"
			params = (start_ts, end_ts)

		cur.execute(
			f"SELECT energy_kwh FROM {TBL_RAW} {where_clause} ORDER BY ts_server ASC LIMIT 1",
			params,
		)
		first_row = cur.fetchone()
		cur.execute(
			f"SELECT energy_kwh FROM {TBL_RAW} {where_clause} ORDER BY ts_server DESC LIMIT 1",
			params,
		)
		last_row = cur.fetchone()
		if not first_row or not last_row:
			return 0.0
		try:
			energy = float(last_row[0]) - float(first_row[0])
			return max(0.0, energy)
		except Exception:
			return 0.0

	def get_dashboard_average_stats(self) -> Dict[str, Any] | None:
		"""Query agregasi statistik untuk Tab Home -> Average.
		
		Returns:
			dict: {
				'date_range': {'start': datetime, 'end': datetime},
				'row_count': int,
				'averages': {'watt': float, 'voltage': float, ...}
			}
		"""
		conn = self._get_conn()
		cur = conn.cursor()
		
		try:
			# Query date range
			cur.execute(f"""
				SELECT 
					MIN(ts_server) as first_ts,
					MAX(ts_server) as last_ts,
					COUNT(*) as total_rows
				FROM {TBL_RAW}
			""")
			row = cur.fetchone()
			
			if not row or row[0] is None:
				return None  # No data
			
			first_ts, last_ts, total_rows = row
			
			# Convert epoch ms to datetime
			from datetime import datetime
			start_date = datetime.fromtimestamp(first_ts / 1000.0)
			end_date = datetime.fromtimestamp(last_ts / 1000.0)
			
			# Query averages
			cur.execute(f"""
				SELECT 
					AVG(watt) as avg_watt,
					AVG(voltage) as avg_voltage,
					AVG(current) as avg_current,
					AVG(frequency) as avg_frequency,
					AVG(pf) as avg_pf
				FROM {TBL_RAW}
			""")
			avg_row = cur.fetchone()
			energy_range = self._get_energy_range(cur)
			
			return {
				'date_range': {
					'start': start_date,
					'end': end_date
				},
				'row_count': total_rows,
				'averages': {
					'watt': round(avg_row[0], 2) if avg_row[0] else 0.0,
					'voltage': round(avg_row[1], 2) if avg_row[1] else 0.0,
					'current': round(avg_row[2], 2) if avg_row[2] else 0.0,
					'frequency': round(avg_row[3], 2) if avg_row[3] else 0.0,
					'energy_kwh': round(energy_range, 4) if energy_range else 0.0,
					'pf': round(avg_row[4], 2) if avg_row[4] else 0.0
				}
			}
			
		except Exception as e:
			print(f"[ERROR] Dashboard query failed: {e}")
			return None
		finally:
			conn.close()

	def get_all_raw_data_for_table(self) -> pd.DataFrame:
		"""Get ALL data dari raw_telemetry untuk tabel display.
		
		Returns:
			DataFrame dengan columns: timestamp, watt, voltage, current, frequency, energy_kwh, pf
		"""
		conn = self._get_conn()
		
		try:
			query = f"""
				SELECT 
					ts_server,
					watt,
					voltage,
					current,
					frequency,
					energy_kwh,
					pf
				FROM {TBL_RAW}
				ORDER BY ts_server ASC
			"""
			
			df = pd.read_sql_query(query, conn)
			
			# Convert epoch ms to datetime
			df['timestamp'] = pd.to_datetime(df['ts_server'], unit='ms')
			df = df.drop(columns=['ts_server'])
			
			# Reorder columns
			df = df[['timestamp', 'watt', 'voltage', 'current', 'frequency', 'energy_kwh', 'pf']]
			
			return df
			
		except Exception as e:
			print(f"[ERROR] Failed to load raw data: {e}")
			return pd.DataFrame()  # Empty DataFrame
		finally:
			conn.close()

	def get_dashboard_daily_stats(self, target_date) -> Dict[str, Any] | None:
		"""Query agregasi statistik untuk Tab Home -> Daily by selected date.
		
		Args:
			target_date: Date yang dipilih user (datetime.date object)
		
		Returns:
			dict: {'date': date, 'row_count': int, 'averages': {...}}
		"""
		from datetime import datetime, timedelta
		
		conn = self._get_conn()
		cur = conn.cursor()
		
		try:
			# Convert date to epoch ms range (00:00:00 to 23:59:59)
			start_ts = int(datetime.combine(target_date, datetime.min.time()).timestamp() * 1000)
			end_ts = int(datetime.combine(target_date, datetime.max.time()).timestamp() * 1000)
			
			# Query row count for that day
			cur.execute(f"""
				SELECT COUNT(*) 
				FROM {TBL_RAW}
				WHERE ts_server >= ? AND ts_server <= ?
			""", (start_ts, end_ts))
			
			row_count = cur.fetchone()[0]
			
			if row_count == 0:
				return None  # No data for this date
			
			# Query averages for that day
			cur.execute(f"""
				SELECT 
					AVG(watt) as avg_watt,
					AVG(voltage) as avg_voltage,
					AVG(current) as avg_current,
					AVG(frequency) as avg_frequency,
					AVG(pf) as avg_pf
				FROM {TBL_RAW}
				WHERE ts_server >= ? AND ts_server <= ?
			""", (start_ts, end_ts))
			
			avg_row = cur.fetchone()
			energy_range = self._get_energy_range(cur, start_ts, end_ts)
			
			return {
				'date': target_date,
				'row_count': row_count,
				'averages': {
					'watt': round(avg_row[0], 2) if avg_row[0] else 0.0,
					'voltage': round(avg_row[1], 2) if avg_row[1] else 0.0,
					'current': round(avg_row[2], 2) if avg_row[2] else 0.0,
					'frequency': round(avg_row[3], 2) if avg_row[3] else 0.0,
					'energy_kwh': round(energy_range, 4) if energy_range else 0.0,
					'pf': round(avg_row[4], 2) if avg_row[4] else 0.0
				}
			}
			
		except Exception as e:
			print(f"[ERROR] Daily dashboard query failed: {e}")
			return None
		finally:
			conn.close()

	def get_daily_data_for_table(self, target_date) -> pd.DataFrame:
		"""Get data untuk tanggal tertentu (filtered by date).
		
		Args:
			target_date: Date yang dipilih user
		
		Returns:
			DataFrame dengan columns: timestamp, watt, voltage, current, frequency, energy_kwh, pf
		"""
		from datetime import datetime
		
		conn = self._get_conn()
		
		try:
			# Convert date to epoch ms range
			start_ts = int(datetime.combine(target_date, datetime.min.time()).timestamp() * 1000)
			end_ts = int(datetime.combine(target_date, datetime.max.time()).timestamp() * 1000)
			
			query = f"""
				SELECT 
					ts_server,
					watt,
					voltage,
					current,
					frequency,
					energy_kwh,
					pf
				FROM {TBL_RAW}
				WHERE ts_server >= ? AND ts_server <= ?
				ORDER BY ts_server ASC
			"""
			
			df = pd.read_sql_query(query, conn, params=(start_ts, end_ts))
			
			if df.empty:
				return pd.DataFrame()
			
			# Convert epoch ms to datetime
			df['timestamp'] = pd.to_datetime(df['ts_server'], unit='ms')
			df = df.drop(columns=['ts_server'])
			
			# Reorder columns
			df = df[['timestamp', 'watt', 'voltage', 'current', 'frequency', 'energy_kwh', 'pf']]
			
			return df
			
		except Exception as e:
			print(f"[ERROR] Failed to load daily data: {e}")
			return pd.DataFrame()
		finally:
			conn.close()

	# ------------------------------------------------------------------
	# Experiment log & results
	# ------------------------------------------------------------------

	def save_experiment_log(self, run_date: str, config_json: str, split_ratio: float) -> int:
		"""Menyimpan header eksperimen dan mengembalikan run_id."""

		conn = self._get_conn()
		cur = conn.cursor()
		cur.execute(
			f"""
			INSERT INTO {TBL_EXP_LOG} (run_date, config_snapshot, split_ratio)
			VALUES (?, ?, ?)
			""",
			(run_date, config_json, split_ratio),
		)
		conn.commit()
		run_id = cur.lastrowid
		conn.close()
		return run_id

	def save_result(
		self,
		run_id: int,
		method: str,
		metrics: Dict[str, float],
		artifacts_json: str,
		forecast_json: str,
	) -> None:
		"""Menyimpan hasil per metode ke tabel experiment_results."""

		conn = self._get_conn()
		cur = conn.cursor()
		cur.execute(
			f"""
			INSERT INTO {TBL_EXP_RES}
				(run_id, method_name, mae, mape, rmse, artifacts_blob, forecast_blob)
			VALUES (?, ?, ?, ?, ?, ?, ?)
			""",
			(
				run_id,
				method,
				metrics.get("mae", 0.0),
				metrics.get("mape", 0.0),
				metrics.get("rmse", 0.0),
				artifacts_json,
				forecast_json,
			),
		)
		conn.commit()
		conn.close()
