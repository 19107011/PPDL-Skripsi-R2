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
Progress Dialog Component

Version: 1.0.1
Created: December 2025
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
	QDialog,
	QGridLayout,
	QLabel,
	QPushButton,
	QProgressBar,
	QVBoxLayout,
)


class ProgressDialog(QDialog):
	"""Dialog progress multi-task bergaya terminal modern."""

	def __init__(self, parent=None) -> None:
		super().__init__(parent)
		self.setWindowTitle("System Processing")
		self.setFixedSize(450, 350)
		self.setModal(True)

		self.setStyleSheet(
			"""
			QDialog { background-color: #1e1e1e; color: #ffffff; }
			QLabel { color: #dddddd; font-family: 'Segoe UI', sans-serif; }
			QProgressBar {
				border: 1px solid #444; border-radius: 3px;
				text-align: center; background-color: #2d2d2d;
			}
			QProgressBar::chunk { background-color: #3b8edb; }
			QPushButton {
				background-color: #444; color: white; border: none; padding: 8px;
			}
			QPushButton:enabled { background-color: #007acc; }
			QPushButton:disabled { background-color: #333; color: #777; }
			"""
		)

		layout = QVBoxLayout()
		layout.setSpacing(15)
		layout.setContentsMargins(20, 20, 20, 20)

		lbl_title = QLabel("Running Analysis...")
		lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #fff;")
		layout.addWidget(lbl_title)

		self.grid = QGridLayout()
		self.grid.setVerticalSpacing(10)

		self.task_widgets: dict[str, dict] = {}
		tasks = [
			("setup", "Initial Setup & Data Splitting"),
			("fts", "Fuzzy Time Series (Chen)"),
			("ann", "Artificial Neural Network"),
			("arima", "ARIMA / SARIMA Model"),
		]

		for i, (key, name) in enumerate(tasks):
			lbl_name = QLabel(f"{i + 1}. {name}")
			lbl_name.setStyleSheet("font-weight: bold;")
			self.grid.addWidget(lbl_name, i * 2, 0)

			lbl_status = QLabel("Pending")
			lbl_status.setStyleSheet("color: #888; font-style: italic;")
			lbl_status.setAlignment(Qt.AlignmentFlag.AlignRight)
			self.grid.addWidget(lbl_status, i * 2, 1)

			pbar = QProgressBar()
			pbar.setFixedHeight(5)
			pbar.setTextVisible(False)
			pbar.setRange(0, 100)
			pbar.setValue(0)
			self.grid.addWidget(pbar, i * 2 + 1, 0, 1, 2)

			self.task_widgets[key] = {
				"lbl_status": lbl_status,
				"pbar": pbar,
				"completed": False,
			}

		layout.addLayout(self.grid)
		layout.addStretch()

		self.lbl_current_action = QLabel("Waiting to start...")
		self.lbl_current_action.setStyleSheet(
			"color: #00ff00; font-family: 'Consolas'; font-size: 11px;"
		)
		layout.addWidget(self.lbl_current_action)

		self.btn_close = QPushButton("Cancel")
		self.btn_close.clicked.connect(self.reject)
		layout.addWidget(self.btn_close)

		self.setLayout(layout)

	def update_progress(self, task_id: str, status_msg: str, percent: int) -> None:
		"""Update tampilan baris progress untuk task tertentu."""

		if task_id not in self.task_widgets:
			return

		widgets = self.task_widgets[task_id]
		widgets["lbl_status"].setText(status_msg)
		widgets["pbar"].setValue(percent)

		self.lbl_current_action.setText(f"> [{task_id.upper()}] {status_msg}")

		if percent >= 100 and not widgets["completed"]:
			widgets["completed"] = True
			widgets["lbl_status"].setStyleSheet(
				"color: #00ff00; font-weight: bold;"
			)
			widgets["lbl_status"].setText("COMPLETED ✓")
			widgets["pbar"].setStyleSheet(
				"QProgressBar::chunk { background-color: #00ff00; }"
			)

	def execution_finished(self) -> None:
		"""Dipanggil saat semua task selesai dengan sukses."""

		self.lbl_current_action.setText("> All tasks finished successfully.")
		self.btn_close.setText("Close")
		self.btn_close.setEnabled(True)
