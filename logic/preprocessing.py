import pandas as pd


class Preprocessor:
	"""Menyiapkan data sebelum masuk ke FTS/ANN/ARIMA.

	Tahapan:
	- konversi timestamp epoch ms -> datetime index
	- resampling ke interval tetap (default 5 menit) dengan mean
	- penanganan missing value (ffill lalu bfill/0)
	- split train/test sekuensial
	"""

	@staticmethod
	def resample_data(
		df: pd.DataFrame,
		interval_minutes: int = 5,
		resample_method: str = "mean",
		target_column: str = "watt",  # AP-03: Accept target_column parameter
	) -> dict:
		"""Resampling data target column ke interval tetap.

		Parameters
		----------
		df : DataFrame
			Minimal memiliki kolom 'ts_server' (epoch ms) dan target_column.
		interval_minutes : int
			Interval resampling dalam menit (default 5).
		resample_method : str
			Metode resample: "mean", "ffill", atau "linear".
		target_column : str
			Column name untuk target variable (default "watt").
		"""

		if df.empty:
			raise ValueError("Dataframe kosong, tidak bisa di-resample.")

		# AP-03: Validate target_column exists dalam DataFrame
		if "ts_server" not in df.columns or target_column not in df.columns:
			raise ValueError(f"Kolom 'ts_server' dan '{target_column}' wajib ada untuk preprocessing.")

		# 1. Convert timestamp ke datetime dan set index
		df = df.copy()
		df["datetime"] = pd.to_datetime(df["ts_server"], unit="ms")
		df = df.set_index("datetime").sort_index()

		# 2. Resampling target column (instead of hardcoded 'watt')
		rule = f"{interval_minutes}T"
		method = str(resample_method).strip().lower()
		if method in ("ffill", "forward-fill", "forward fill"):
			series_resampled = df[target_column].resample(rule).ffill()
		elif method in ("linear", "interpolate", "interp"):
			series_resampled = df[target_column].resample(rule).mean()
			series_resampled = series_resampled.interpolate(method="time")
		else:
			series_resampled = df[target_column].resample(rule).mean()

		# 3. Missing values: ffill lalu bfill/0 jika masih ada
		n_missing_before = int(series_resampled.isna().sum())
		series_clean = series_resampled.ffill()
		if series_clean.isna().any():
			series_clean = series_clean.bfill().fillna(0)

		artifacts = {
			"original_count": int(len(df)),
			"resampled_count": int(len(series_clean)),
			"missing_filled": n_missing_before,
			"interval_used": rule,
			"resample_method": method,
		}

		return {"data": series_clean, "artifacts": artifacts}

	@staticmethod
	def train_test_split(series: pd.Series, ratio: float = 0.8):
		"""Memecah data menjadi train dan test secara sekuensial.

		Parameters
		----------
		series : pd.Series
			Deret waktu hasil resampling.
		ratio : float
			Proporsi data training (0 < ratio < 1).
		"""

		if series.empty:
			raise ValueError("Series kosong, tidak bisa di-split.")

		n = len(series)
		train_size = int(n * ratio)
		if train_size <= 0 or train_size >= n:
			raise ValueError("Proporsi split menghasilkan train/test tidak valid.")

		train = series.iloc[:train_size]
		test = series.iloc[train_size:]
		return train, test
