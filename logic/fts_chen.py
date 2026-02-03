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
Fuzzy Time Series Chen Method

Version: 1.0.1
Created: December 2025
"""

import numpy as np
import pandas as pd


class FTSChen:
	"""Implementasi Fuzzy Time Series (Chen 1996 - First Order).

	Prinsip glass box: menyimpan UoD, interval, FLR, dan FLRG
	sebagai artifacts untuk analisis skripsi.
	"""

	def __init__(
		self,
		interval_num: int = 7,
		method: str = "equal-width",
		pad_pct: float = 0.05,
	) -> None:
		"""Inisialisasi model.

		Parameters
		----------
		interval_num : int
			Jumlah interval partisi UoD.
		"""
		self.requested_intervals = int(interval_num)
		self.n_intervals = int(interval_num)
		self.partition_method = self._normalize_method(method)
		self.pad_pct = float(pad_pct)
		self.min_val: float = 0.0
		self.max_val: float = 0.0
		self.intervals: list[tuple[float, float]] = []
		self.midpoints: list[float] = []
		self.uod = None
		self.flrg: dict[int, list[tuple[int, float]]] = {}
		self.trained: bool = False

		# Artifacts untuk Bab 4
		self.artifacts: dict = {
			"requested_intervals": int(self.requested_intervals),
			"actual_intervals": None,
			"partition_method": str(self.partition_method),
			"pad_pct": float(self.pad_pct),
			"uod": None,
			"intervals": [],
			"midpoints": [],
			"fuzzified_train": [],
			"flr_table": [],  # list string "A1 -> A2"
			"flrg_table": {},  # dict "A1": "A2, A3"
			"flrg_raw": {},    # dict int -> list[(int, float)]
		}

	# ------------------------------------------------------------------
	# Tahap 1-2: UoD dan Partisi Interval
	# ------------------------------------------------------------------

	@staticmethod
	def _normalize_method(method) -> str:
		if method is None:
			return "equal-width"
		value = str(method).strip().lower()
		if value in ("equal width", "equal-width", "equalwidth"):
			return "equal-width"
		if value in ("equal frequency", "equal-frequency", "equalfrequency", "equal freq", "equal-freq"):
			return "equal-frequency"
		return "equal-width"

	def _generate_intervals(self, data: np.ndarray) -> None:
		"""Menentukan Universe of Discourse dan membagi menjadi interval.

		Mendukung partisi equal width / equal frequency.
		"""

		self.min_val = float(np.min(data))
		self.max_val = float(np.max(data))

		span = self.max_val - self.min_val
		pad = span * float(self.pad_pct)
		uod_min = self.min_val - pad
		uod_max = self.max_val + pad
		self.uod = (uod_min, uod_max)
		self.artifacts["uod"] = (uod_min, uod_max)

		self.intervals = []
		self.midpoints = []

		if self.partition_method == "equal-frequency":
			self._partition_equal_frequency(data, uod_min, uod_max)
		else:
			self._partition_equal_width(uod_min, uod_max)

		if not self.intervals:
			raise ValueError("Interval kosong. Cek parameter partition dan data.")

		self.n_intervals = len(self.intervals)
		self.artifacts["actual_intervals"] = int(self.n_intervals)
		self.artifacts["partition_method"] = str(self.partition_method)
		self.artifacts["pad_pct"] = float(self.pad_pct)
		self.artifacts["intervals"] = self.intervals
		self.artifacts["midpoints"] = self.midpoints

	def _partition_equal_width(self, uod_min: float, uod_max: float) -> None:
		n = self.n_intervals
		length = (uod_max - uod_min) / float(n)
		curr = uod_min
		for i in range(n):
			nxt = uod_max if i == n - 1 else curr + length
			self.intervals.append((curr, nxt))
			self.midpoints.append((curr + nxt) / 2.0)
			curr = nxt

	def _partition_equal_frequency(
		self,
		data: np.ndarray,
		uod_min: float,
		uod_max: float,
	) -> None:
		sorted_vals = np.sort(np.asarray(data, dtype=float))
		n = self.n_intervals
		points_per_bin = int(np.floor(len(sorted_vals) / float(n)))

		for i in range(n):
			if i == 0:
				lo = uod_min
			else:
				idx = i * points_per_bin
				lo = float(sorted_vals[idx])

			if i == n - 1:
				hi = uod_max
			else:
				idx = (i + 1) * points_per_bin
				hi = float(sorted_vals[idx])

			if lo == hi and i < n - 1:
				continue

			self.intervals.append((float(lo), float(hi)))
			self.midpoints.append((float(lo) + float(hi)) / 2.0)

	# ------------------------------------------------------------------
	# Tahap 3: Fuzzifikasi
	# ------------------------------------------------------------------

	def _fuzzify(self, value: float) -> int:
		"""Memetakan nilai numerik ke indeks fuzzy set (0..n-1)."""

		if not self.intervals:
			raise RuntimeError("Interval belum di-generate. Panggil fit() dulu.")

		n_intervals = len(self.intervals)

		# Clamp outlier
		if value < self.intervals[0][0]:
			return 0
		if value > self.intervals[-1][1]:
			return n_intervals - 1

		for i, (low, high) in enumerate(self.intervals):
			if i == n_intervals - 1:
				if low <= value <= high:
					return i
			else:
				if low <= value < high:
					return i

		return n_intervals - 1

	# ------------------------------------------------------------------
	# Training: FLR & FLRG
	# ------------------------------------------------------------------

	def fit(self, train_data: pd.Series) -> "FTSChen":
		"""Melatih model FTS dengan data training.

		Membentuk FLR (A(t-1) -> A(t)) dan FLRG (pengelompokan LHS).
		"""

		values = np.asarray(train_data.values, dtype=float)
		if values.size < 2:
			raise ValueError("Data training terlalu sedikit (< 2).")

		# 1. Generate UoD & Intervals
		self._generate_intervals(values)

		# 2. Fuzzifikasi
		fuzzy_labels: list[int] = [self._fuzzify(v) for v in values]
		self.artifacts["fuzzified_train"] = [f"A{i+1}" for i in fuzzy_labels]

		# 3. Bangun FLR dan FLRG (dengan support)
		self.flrg.clear()
		flr_list: list[str] = []
		flr_counts: dict[tuple[int, int], int] = {}

		for i in range(1, len(fuzzy_labels)):
			prev_state = fuzzy_labels[i - 1]
			curr_state = fuzzy_labels[i]

			flr_list.append(f"A{prev_state+1} -> A{curr_state+1}")

			key = (prev_state, curr_state)
			flr_counts[key] = flr_counts.get(key, 0) + 1

		self.artifacts["flr_table"] = flr_list

		from_totals: dict[int, int] = {}
		for (prev_state, _), count in flr_counts.items():
			from_totals[prev_state] = from_totals.get(prev_state, 0) + count

		self.flrg = {i: [] for i in range(self.n_intervals)}
		for (prev_state, curr_state), count in flr_counts.items():
			support = count / float(from_totals[prev_state])
			self.flrg[prev_state].append((curr_state, support))

		for k in list(self.flrg.keys()):
			group = self.flrg[k]
			if group:
				group.sort(key=lambda item: item[1], reverse=True)
			else:
				self.flrg[k] = [(k, 1.0)]

		readable_flrg: dict[str, str] = {}
		for k, rhs_states in self.flrg.items():
			rhs_str = ", ".join(
				f"A{s+1} ({support*100:.1f}%)" for s, support in rhs_states
			)
			readable_flrg[f"A{k+1}"] = rhs_str

		self.artifacts["flrg_raw"] = self.flrg
		self.artifacts["flrg_table"] = readable_flrg
		self.trained = True
		return self

	# ------------------------------------------------------------------
	# Prediksi
	# ------------------------------------------------------------------

	def _predict_from_state(self, state_idx: int) -> float:
		group = self.flrg.get(state_idx, [])
		if not group:
			pred_val = self.midpoints[state_idx]
		else:
			pred_val = sum(self.midpoints[idx] * support for idx, support in group)

		if self.uod is None:
			uod_min, uod_max = self.intervals[0][0], self.intervals[-1][1]
		else:
			uod_min, uod_max = self.uod
		pred_val = max(uod_min, min(uod_max, pred_val))
		return float(pred_val)

	def predict(self, test_data: pd.Series) -> dict:
		"""Melakukan prediksi untuk deret waktu test.

		Mengembalikan dict dengan kunci:
		- "forecast": list float
		- "artifacts": dict (UoD, intervals, FLR, FLRG, fuzzified_train)
		"""

		if not self.trained:
			raise RuntimeError("Model belum dilatih. Panggil fit() terlebih dahulu.")

		actuals = np.asarray(test_data.values, dtype=float)
		if actuals.size == 0:
			return {"forecast": [], "artifacts": self.artifacts}

		test_labels: list[int] = [self._fuzzify(v) for v in actuals]
		predictions: list = [None]

		for i in range(1, len(actuals)):
			prev_state_idx = test_labels[i - 1]
			predictions.append(self._predict_from_state(prev_state_idx))

		return {"forecast": predictions, "artifacts": self.artifacts}
