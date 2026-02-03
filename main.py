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
Application Entry Point

Version: 1.0.1
Created: December 2025
"""

import random
import sys
import traceback

import numpy as np
from PyQt6.QtWidgets import QApplication, QMessageBox

from ui.main_window import MainWindow


def _setup_seeds(seed: int = 42) -> None:
	"""Set random seed dasar untuk Python, NumPy, dan (jika ada) TensorFlow."""

	random.seed(seed)
	np.random.seed(seed)
	try:  # pragma: no cover - optional dependency
		import tensorflow as tf  # type: ignore

		try:
			# TensorFlow 2.x
			getattr(tf.random, "set_seed")(seed)
		except Exception:
			pass
	except ImportError:
		# TensorFlow tidak wajib ter-install untuk sekadar membuka UI
		pass


def _global_excepthook(exc_type, exc_value, exc_tb) -> None:  # type: ignore[override]
	"""Global excepthook sederhana untuk menampilkan error fatal ke user."""

	trace_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
	print(trace_str, file=sys.stderr)
	try:
		QMessageBox.critical(
			None,
			"Fatal Error",
			f"An unexpected error occurred:\n{exc_value}",
		)
	except Exception:
		# Jika QApplication belum siap atau gagal, tetap keluar dengan kode error
		pass
	sys.exit(1)


def main() -> int:
	"""Fungsi main standar untuk menjalankan aplikasi Qt."""

	_setup_seeds(42)
	sys.excepthook = _global_excepthook

	# Clean orphaned cache directories from previous sessions
	try:
		from utils.resource_manager import ResourceManager
		ResourceManager.cleanup_orphaned_caches()
	except Exception as e:
		print(f"Warning: Failed to clean orphaned cache: {e}")

	app = QApplication(sys.argv)
	window = MainWindow()
	window.show()
	return app.exec()


if __name__ == "__main__":
	sys.exit(main())
