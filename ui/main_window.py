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
Main Application Window

Version: 1.0.1
Created: December 2025
"""

import sys
import os
import shutil
import json
from datetime import datetime

import pandas as pd
from PyQt6.QtCore import pyqtSlot, QDateTime, QThread, pyqtSignal
from PyQt6.QtGui import QTextCursor, QCursor
from PyQt6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QVBoxLayout, QWidget
from PyQt6.QtCore import QAbstractTableModel, Qt, QModelIndex
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QGraphicsScene
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

from config.config_manager import ConfigManager
from database.db_manager import DBManager
from database.importer import DataImporter
from database.bq_downloader import BigQueryDownloader
from ui.export_manager import ExportManager
from ui.main_window_ui import Ui_MainWindow
from ui.progress_dialog import ProgressDialog
from utils.app_logger import AppLogger
from utils import logging_events as EVT
from workers.calc_thread import CalculationWorker
from utils.run_context import RunContext


class BigQueryDownloadWorker(QThread):
	"""Worker thread for BigQuery data download with progress tracking."""
	
	progress_updated = pyqtSignal(int)
	download_finished = pyqtSignal(bool, str)  # (success, result_path_or_error)
	download_status = pyqtSignal(str)  # Status message for UI
	
	def __init__(self, parent=None):
		super().__init__(parent)
		self._is_cancelled = False
		
	def cancel_download(self):
		"""Cancel the download process."""
		self._is_cancelled = True
		
	def run(self):
		"""Execute BigQuery download in background thread."""
		try:
			if self._is_cancelled:
				return
				
			self.download_status.emit("Menginisialisasi BigQuery downloader...")
			self.progress_updated.emit(10)
			
			downloader = BigQueryDownloader()
			
			if self._is_cancelled:
				return
				
			self.download_status.emit("Menghubungkan ke BigQuery...")
			self.progress_updated.emit(30)
			
			if self._is_cancelled:
				return
				
			self.download_status.emit("Mengunduh data dari BigQuery...")
			self.progress_updated.emit(50)
			
			# Call download_data without filename for auto-generation
			success, result = downloader.download_data()
			
			if self._is_cancelled:
				return
				
			if success:
				self.download_status.emit("Download berhasil!")
				self.progress_updated.emit(100)
			else:
				self.download_status.emit("Download gagal!")
				
			self.download_finished.emit(success, result)
			
		except Exception as e:
			if not self._is_cancelled:
				error_msg = f"Error saat download: {str(e)}"
				self.download_status.emit("Download gagal!")
				self.download_finished.emit(False, error_msg)


def _fmt_dt_from_ms(ms: int | float | None) -> str:
	try:
		return pd.to_datetime(int(ms), unit="ms").strftime("%Y-%m-%d %H:%M:%S")
	except Exception:
		return str(ms)



class InteractiveChartWidget:
	"""Handler untuk grafik interaktif dengan tooltip hover dan checkbox toggle (RUN 4)."""
	
	def __init__(self, graphics_view, checkboxes: dict, data_source_callback, logger=None):
		"""
		Args:
			graphics_view: QGraphicsView widget untuk embed matplotlib
			checkboxes: dict {'sensor_name': QCheckBox widget}
			data_source_callback: Function() -> pd.DataFrame (return data untuk plot)
			logger: AppLogger instance (optional)
		"""
		self.graphics_view = graphics_view
		self.checkboxes = checkboxes
		self.data_source_callback = data_source_callback
		self.logger = logger
		self._last_df = None
		self._container = None
		self.toolbar = None
		
		# Create matplotlib figure - use tight_layout
		self.figure = Figure(figsize=(8, 4), dpi=100, facecolor='#2e2e2e')
		self.canvas = FigureCanvasQTAgg(self.figure)
		self.ax = self.figure.add_subplot(111)
		
		# Styling
		self.ax.set_facecolor('#1e1e1e')
		self.ax.tick_params(colors='white')
		self.ax.spines['bottom'].set_color('white')
		self.ax.spines['left'].set_color('white')
		self.ax.spines['top'].set_visible(False)
		self.ax.spines['right'].set_visible(False)
		self.ax.grid(True, alpha=0.3, color='gray')
		
		# Embed canvas + toolbar - directly to parent widget for auto-resize
		parent = self.graphics_view.parentWidget()
		parent_layout = parent.layout()
		if parent_layout is None:
			parent_layout = QVBoxLayout(parent)
			parent.setLayout(parent_layout)
		parent_layout.setContentsMargins(0, 0, 0, 0)
		parent_layout.setSpacing(0)
		
		# Hide the QGraphicsView and add canvas directly to parent
		self.graphics_view.hide()
		
		self.toolbar = NavigationToolbar2QT(self.canvas, parent)
		parent_layout.addWidget(self.toolbar)
		parent_layout.addWidget(self.canvas)
		# Set stretch factor to make canvas expand (check layout type)
		from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QGridLayout
		if isinstance(parent_layout, (QVBoxLayout, QHBoxLayout)):
			parent_layout.setStretchFactor(self.canvas, 1)
		elif isinstance(parent_layout, QGridLayout):
			# For grid layout, make canvas expand by setting row/column stretch
			canvas_item = parent_layout.itemAt(parent_layout.count() - 1)
			if canvas_item:
				row, column, rowspan, colspan = parent_layout.getItemPosition(parent_layout.count() - 1)
				parent_layout.setRowStretch(row, 1)
				parent_layout.setColumnStretch(column, 1)
		
		# Line references (untuk toggle visibility)
		self.lines = {}  # {'sensor_name': Line2D object}
		
		# Annotation for hover tooltip
		self.annot = None
		
		# Connect hover event
		self.canvas.mpl_connect('motion_notify_event', self._on_hover)
		
		# Connect checkbox signals
		for sensor_name, checkbox in self.checkboxes.items():
			if checkbox is not None:
				checkbox.stateChanged.connect(lambda state, name=sensor_name: self._toggle_line(name, state))
	
	def plot_data(self):
		"""Main plot function - dipanggil saat data ready."""
		try:
			df = self.data_source_callback()

			if df is None or df.empty:
				self.ax.clear()
				self.ax.set_facecolor('#1e1e1e')
				self.ax.text(0.5, 0.5, 'No Data Available', 
							ha='center', va='center', color='white', fontsize=14)
				self.canvas.draw()
				return
			
			# Normalize data for consistent indexing
			df = df.copy()
			if 'timestamp' in df.columns:
				df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
				df = df.dropna(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
			self._last_df = df

			# Clear previous plot
			self.ax.clear()
			self.lines.clear()
			
			# Re-apply styling after clear
			self.ax.set_facecolor('#1e1e1e')
			self.ax.tick_params(colors='white')
			self.ax.grid(True, alpha=0.3, color='gray')
			
			# Plot each sensor (if checkbox checked)
			colors = {
				'voltage': '#FF6B6B',    # Red
				'current': '#4ECDC4',    # Cyan
				'watt': '#FFE66D',       # Yellow
				'energy_kwh': '#95E1D3', # Green
				'frequency': '#F38181',  # Pink
				'pf': '#AA96DA'          # Purple
			}
			
			labels = {
				'voltage': 'Tegangan (V)',
				'current': 'Arus (A)',
				'watt': 'Daya (W)',
				'energy_kwh': 'Energi (kWh)',
				'frequency': 'Frekuensi (Hz)',
				'pf': 'Power Factor'
			}
			
			if 'timestamp' not in df.columns:
				self.ax.text(0.5, 0.5, 'Invalid Data Format', 
							ha='center', va='center', color='white', fontsize=14)
				self.canvas.draw()
				return
			
			x = df['timestamp']
			
			for sensor_name, checkbox in self.checkboxes.items():
				if checkbox is None:
					continue
				if sensor_name not in df.columns:
					continue
				
				if checkbox.isChecked():
					line, = self.ax.plot(
						x, df[sensor_name],
						label=labels.get(sensor_name, sensor_name),
						color=colors.get(sensor_name, 'white'),
						linewidth=2,
						marker='o',
						markersize=2,
						alpha=0.8
					)
					line.set_picker(5)
					self.lines[sensor_name] = line
			
			# Format x-axis (datetime)
			import matplotlib.dates as mdates
			self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
			if len(df) > 24:
				self.ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
			else:
				self.ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
			self.figure.autofmt_xdate()  # Rotate date labels
			
			# Labels
			self.ax.set_xlabel('Time', color='white', fontsize=10)
			self.ax.set_ylabel('Value', color='white', fontsize=10)
			self.ax.set_title('Sensor Data Visualization', color='white', fontsize=12, pad=10)
			
			# Legend
			if self.lines:
				self.ax.legend(loc='upper left', facecolor='#2e2e2e', edgecolor='white', 
							  labelcolor='white', framealpha=0.9, fontsize=8)
			
			# Create annotation (tooltip) - initially hidden
			self.annot = self.ax.annotate(
				'', xy=(0, 0), xytext=(10, 10), textcoords='offset points',
				bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.9),
				arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'),
				fontsize=9, color='black'
			)
			self.annot.set_visible(False)
			
			# Apply tight layout so chart fills the available area
			self.figure.tight_layout()
			self.canvas.draw()
			
			if self.logger:
				self.logger.log("INFO", f"Chart plotted with {len(self.lines)} active lines")
				
		except Exception as e:
			if self.logger:
				self.logger.log("ERROR", f"Failed to plot chart: {e}")
	
	def _toggle_line(self, sensor_name, state):
		"""Toggle visibility line saat checkbox di-check/uncheck."""
		# Replot semua data (lebih simple daripada toggle individual line)
		self.plot_data()
	
	def _on_hover(self, event):
		"""Handler saat mouse hover di atas grafik."""
		try:
			if event.inaxes != self.ax:
				if self.annot and self.annot.get_visible():
					self.annot.set_visible(False)
					self.canvas.draw_idle()
				return
			
			# Check if mouse near any line
			for sensor_name, line in self.lines.items():
				cont, ind = line.contains(event)
				if cont:
					# Mouse near this line - show tooltip
					self._update_annot(line, ind, sensor_name)
					return
			
			# No line near mouse - hide tooltip
			if self.annot and self.annot.get_visible():
				self.annot.set_visible(False)
				self.canvas.draw_idle()
		except Exception:
			pass
	
	def _update_annot(self, line, ind, sensor_name):
		"""Update tooltip content."""
		try:
			if not self.annot:
				return
			if self._last_df is None or self._last_df.empty:
				return

			# Get data point coordinates
			x_data = line.get_xdata()
			y_data = line.get_ydata()
			
			# Get index of nearest point
			idx = ind['ind'][0]
			x_val = x_data[idx]
			y_val = y_data[idx]
			
			# Format tooltip text with full sensor context
			row = self._last_df.iloc[min(idx, len(self._last_df) - 1)]
			ts_val = row.get("timestamp")
			if isinstance(ts_val, pd.Timestamp):
				time_str = ts_val.strftime('%Y-%m-%d %H:%M:%S')
			else:
				time_str = str(ts_val)
			label_map = {
				"voltage": "V",
				"current": "A",
				"watt": "W",
				"energy_kwh": "E(kWh)",
				"frequency": "F(Hz)",
				"pf": "PF",
			}
			lines = [f"Timestamp: {time_str}"]
			for key, short in label_map.items():
				if key in row.index:
					try:
						val = float(row[key])
					except Exception:
						val = None
					if val is None or pd.isna(val):
						val_str = "-"
					elif key == "energy_kwh":
						val_str = f"{val:.4f}"
					else:
						val_str = f"{val:.2f}"
					lines.append(f"{short}: {val_str}")
			tooltip_text = "\n".join(lines)
			
			self.annot.set_text(tooltip_text)
			self.annot.xy = (x_val, y_val)
			self.annot.set_visible(True)
			self.canvas.draw_idle()
		except Exception:
			pass


class InteractiveResultChart:
	"""Handler grafik hasil analisis (Resume) dengan tooltip dan toolbar."""

	def __init__(self, graphics_view, checkboxes: dict, labels: dict, colors: dict, logger=None):
		self.graphics_view = graphics_view
		self.checkboxes = checkboxes
		self.labels = labels
		self.colors = colors
		self.logger = logger
		self._container = None
		self._last_index = None
		self.series_map: dict[str, pd.Series] = {}
		self.title = ""

		self.figure = Figure(figsize=(8, 4), dpi=100, facecolor="#2e2e2e")
		self.canvas = FigureCanvasQTAgg(self.figure)
		self.ax = self.figure.add_subplot(111)

		self.ax.set_facecolor("#1e1e1e")
		self.ax.tick_params(colors="white")
		self.ax.spines["bottom"].set_color("white")
		self.ax.spines["left"].set_color("white")
		self.ax.spines["top"].set_visible(False)
		self.ax.spines["right"].set_visible(False)
		self.ax.grid(True, alpha=0.3, color="gray")

		# Embed canvas + toolbar - directly to parent widget for auto-resize
		parent = self.graphics_view.parentWidget()
		parent_layout = parent.layout()
		if parent_layout is None:
			parent_layout = QVBoxLayout(parent)
			parent.setLayout(parent_layout)
		parent_layout.setContentsMargins(0, 0, 0, 0)
		parent_layout.setSpacing(0)
		
		# Hide the QGraphicsView and add canvas directly to parent
		self.graphics_view.hide()
		
		self.toolbar = NavigationToolbar2QT(self.canvas, parent)
		parent_layout.addWidget(self.toolbar)
		parent_layout.addWidget(self.canvas)
		# Set stretch factor to make canvas expand (check layout type)
		from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QGridLayout
		if isinstance(parent_layout, (QVBoxLayout, QHBoxLayout)):
			parent_layout.setStretchFactor(self.canvas, 1)
		elif isinstance(parent_layout, QGridLayout):
			# For grid layout, make canvas expand by setting row/column stretch
			canvas_item = parent_layout.itemAt(parent_layout.count() - 1)
			if canvas_item:
				row, column, rowspan, colspan = parent_layout.getItemPosition(parent_layout.count() - 1)
				parent_layout.setRowStretch(row, 1)
				parent_layout.setColumnStretch(column, 1)

		self.lines = {}
		self.annot = None
		self.canvas.mpl_connect("motion_notify_event", self._on_hover)

		for key, checkbox in self.checkboxes.items():
			if checkbox is not None:
				checkbox.stateChanged.connect(lambda _state, _k=key: self.plot())

	def set_series(self, series_map: dict[str, pd.Series], title: str) -> None:
		self.series_map = series_map or {}
		self.title = title
		if self.series_map:
			first = next(iter(self.series_map.values()))
			self._last_index = list(first.index)
		else:
			self._last_index = None
		self.plot()

	def plot(self) -> None:
		try:
			self.ax.clear()
			self.lines.clear()
			self.ax.set_facecolor("#1e1e1e")
			self.ax.tick_params(colors="white")
			self.ax.grid(True, alpha=0.3, color="gray")

			if not self.series_map:
				self.ax.text(0.5, 0.5, "No Data Available", ha="center", va="center", color="white", fontsize=14)
				self.canvas.draw()
				return

			import matplotlib.dates as mdates

			for key, series in self.series_map.items():
				checkbox = self.checkboxes.get(key)
				if checkbox is not None and not checkbox.isChecked():
					continue
				if series is None or series.empty:
					continue
				line, = self.ax.plot(
					series.index,
					series.values,
					label=self.labels.get(key, key),
					color=self.colors.get(key, "white"),
					linewidth=2,
					marker="o",
					markersize=2,
					alpha=0.85,
				)
				line.set_picker(5)
				self.lines[key] = line

			self.ax.set_title(self.title, color="white", fontsize=12, pad=10)
			self.ax.set_xlabel("Time", color="white", fontsize=10)
			self.ax.set_ylabel("Value", color="white", fontsize=10)
			self.ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
			self.figure.autofmt_xdate()

			if self.lines:
				self.ax.legend(loc="upper left", facecolor="#2e2e2e", edgecolor="white", labelcolor="white", framealpha=0.9, fontsize=8)

			self.annot = self.ax.annotate(
				"", xy=(0, 0), xytext=(10, 10), textcoords="offset points",
				bbox=dict(boxstyle="round,pad=0.5", fc="yellow", alpha=0.9),
				arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0"),
				fontsize=9, color="black",
			)
			self.annot.set_visible(False)
			
			# Apply tight layout so chart fills the available area
			self.figure.tight_layout()
			self.canvas.draw()
		except Exception as e:
			if self.logger:
				self.logger.log("ERROR", f"Failed to plot result chart: {e}")

	def _on_hover(self, event):
		try:
			if event.inaxes != self.ax:
				if self.annot and self.annot.get_visible():
					self.annot.set_visible(False)
					self.canvas.draw_idle()
				return

			for key, line in self.lines.items():
				cont, ind = line.contains(event)
				if cont:
					self._update_annot(line, ind, key)
					return

			if self.annot and self.annot.get_visible():
				self.annot.set_visible(False)
				self.canvas.draw_idle()
		except Exception:
			pass

	def _update_annot(self, line, ind, key):
		try:
			if not self.annot or self._last_index is None:
				return
			idx = ind["ind"][0]
			x_val = line.get_xdata()[idx]
			y_val = line.get_ydata()[idx]
			ts_val = self._last_index[min(idx, len(self._last_index) - 1)]
			if isinstance(ts_val, pd.Timestamp):
				time_str = ts_val.strftime("%Y-%m-%d %H:%M:%S")
			else:
				time_str = str(ts_val)
			label = self.labels.get(key, key)
			tooltip_text = f"Timestamp: {time_str}\n{label}: {float(y_val):.4f}"
			self.annot.set_text(tooltip_text)
			self.annot.xy = (x_val, y_val)
			self.annot.set_visible(True)
			self.canvas.draw_idle()
		except Exception:
			pass


class MainWindow(QMainWindow, Ui_MainWindow):
	"""Main Window untuk PPDL V1.0 (versi dasar RUN-4).

	Tanggung jawab:
	- Inisialisasi UI dan konfigurasi
	- Memuat data awal dari SQLite (jika ada)
	- Mengambil parameter dari UI dan validasi
	- Menjalankan CalculationWorker dan menampilkan ProgressDialog
	"""

	def __init__(self) -> None:
		super().__init__()
		self.setupUi(self)

		self._startup_in_progress: bool = True

		# Backend managers
		self.config_mgr = ConfigManager()
		self.db_mgr = DBManager()
		self.current_config = self.config_mgr.load_config()

		# State
		self.raw_data: pd.DataFrame | None = None
		self.worker: CalculationWorker | None = None
		self.download_worker: BigQueryDownloadWorker | None = None  # BigQuery download worker
		self.analysis_results: dict | None = None
		self.progress_dlg: ProgressDialog | None = None
		self._last_run_params: dict | None = None
		self._initiation_completed: bool = False
		self._last_export_file: str | None = None
		self._last_logged_avg_range: tuple[pd.Timestamp, pd.Timestamp] | None = None
		self._last_logged_daily_date = None

		# Plotting
		self.figure: Figure | None = None
		self.canvas: FigureCanvasQTAgg | None = None
		self.ax = None

		# Logger
		self.logger = AppLogger()
		self.logger.sig_log_updated.connect(self.append_log_ui)

		self._init_ui_state()
		self._connect_signals()
		self._init_plot_canvas()
		# DEPRECATED: Replaced by InteractiveChartWidget (RUN 4)
		# self._init_home_plot_canvases()
		# Initialize interactive charts (RUN 4)
		self._init_interactive_charts()
		# Pastikan cache runtime bersih saat startup (antisisa jika crash sebelumnya)
		self._reset_runtime_cache_on_start()
		self._load_initial_data()
		
		# RUN-3 ST-04: Enforce parameter consistency after startup complete
		self._startup_in_progress = False
		self._enforce_parameter_lock_consistency()

	# ------------------------------------------------------------------
	# Setup
	# ------------------------------------------------------------------

	def _reset_runtime_cache_on_start(self) -> None:
		"""Bersihkan cache SQLite saat startup agar selalu default.

		Digunakan untuk menghindari sisa data apabila aplikasi sebelumnya
		crash dan tidak sempat menjalankan pembersihan di closeEvent.
		"""

		try:
			deleted_map = self.db_mgr.clear_all_runtime()
			self.logger.log(
				"INFO",
				f"Startup reset: cleared raw={deleted_map.get('raw_deleted',0)} rows, exp={deleted_map.get('exp_deleted',0)} rows.",
			)
		except Exception as e:
			self.logger.log("ERROR", f"Failed startup cache reset: {e}")

	def _init_ui_state(self) -> None:
		"""Mengisi nilai default kontrol UI dari konfigurasi."""

		# Global split ratio (0-100)
		self.Param_initial_value_general_trainortestplit.setValue(int(self.current_config["global"]["split_ratio"] * 100))
		self.Param_initial_value_general_trainortestplit.setRange(10, 90)
		self.Param_initial_value_general_trainortestplit.setRange(10, 90)

		# FTS
		self.Param_initial_value_FTS_interval.setValue(int(self.current_config["fts"]["interval"]))
		if hasattr(self, "Param_initial_value_FTS_sensitivity"):
			self.Param_initial_value_FTS_sensitivity.setEnabled(True)
		if hasattr(self, "Param_initial_value_FTS_equalwidth"):
			self.Param_initial_value_FTS_equalwidth.blockSignals(True)
			self.Param_initial_value_FTS_equalwidth.clear()
			# Add proper options for FTS partition method
			self.Param_initial_value_FTS_equalwidth.addItems([
				"Equal Width (Jarak Sebaran)", 
				"Equal Frequency (Frekuensi)"
			])
			self.Param_initial_value_FTS_equalwidth.setCurrentText("Equal Width (Jarak Sebaran)")
			self.Param_initial_value_FTS_equalwidth.setEditable(False)  # Make it non-editable for clear options
			self.Param_initial_value_FTS_equalwidth.blockSignals(False)

		# ANN
		ann = self.current_config["ann"]
		self.Param_initial_value_ANN_epoch.setValue(int(ann["epoch"]))
		self.Param_initial_value_ANN_neuronperlayer.setValue(int(ann["neuron"]))
		self.Param_initial_value_ANN_hiddenlayer.setValue(int(ann.get("layers", 1)))
		if hasattr(self, "Param_initial_value_ANN_learningrate"):
			self.Param_initial_value_ANN_learningrate.setValue(float(ann.get("lr", 0.01)))
		if hasattr(self, "Param_initial_value_ANN_batchsize"):
			self.Param_initial_value_ANN_batchsize.setValue(32)
		if hasattr(self, "Param_initial_value_ANN_lagwindowK"):
			self.Param_initial_value_ANN_lagwindowK.setValue(1)
		if hasattr(self, "Param_initial_value_ANN_activationfunction"):
			self.Param_initial_value_ANN_activationfunction.blockSignals(True)
			self.Param_initial_value_ANN_activationfunction.clear()
			self.Param_initial_value_ANN_activationfunction.addItems(["relu", "tanh", "sigmoid", "linear"])
			self.Param_initial_value_ANN_activationfunction.setCurrentText("relu")
			self.Param_initial_value_ANN_activationfunction.blockSignals(False)

		# ARIMA
		arima = self.current_config["arima"]
		self.Param_initial_value_ARIMA_nonSeasonal_p.setValue(int(arima["p"]))
		self.Param_initial_value_ARIMA_nonSeasonal_d.setValue(int(arima["d"]))
		self.Param_initial_value_ARIMA_nonSeasonal_q.setValue(int(arima["q"]))
		self.Param_Status_Submit_ARIMA_seasonal.setChecked(bool(arima["seasonal"]))
		self.Param_initial_value_ARIMA_Seasonal_s.setValue(int(arima["s"]))

		# Update parameter ranges (CATATAN.md spec)
		self.Param_initial_value_FTS_interval.setRange(3, 100)
		self.Param_initial_value_ANN_neuronperlayer.setRange(1, 1000)
		self.Param_initial_value_ANN_epoch.setRange(10, 10000)
		self.Param_initial_value_ANN_hiddenlayer.setRange(1, 5)
		self.Param_initial_value_ARIMA_nonSeasonal_p.setRange(0, 12)
		self.Param_initial_value_ARIMA_nonSeasonal_d.setRange(0, 3)
		self.Param_initial_value_ARIMA_nonSeasonal_q.setRange(0, 12)
		self.Param_initial_value_ARIMA_Seasonal_s.setRange(0, 300)

		# Initialize Forecasting Horizon (RUN 2)
		if self.Param_initial_value_general_forecasting is not None:
			self.Param_initial_value_general_forecasting.blockSignals(True)
			self.Param_initial_value_general_forecasting.clear()
			self.Param_initial_value_general_forecasting.addItems(["1", "2", "3"])
			self.Param_initial_value_general_forecasting.setCurrentText("1")
			self.Param_initial_value_general_forecasting.blockSignals(False)

		# RUN-3 ST-02: Initialize checkbox LOCK - all unchecked by default for manual control
		if self.Param_Status_Submit_general is not None:
			self.Param_Status_Submit_general.setChecked(False)
		if self.Param_Status_Submit_FTS is not None:
			self.Param_Status_Submit_FTS.setChecked(False)
		if hasattr(self, "Param_initial_value_FTS_sensitivity_state"):
			self.Param_initial_value_FTS_sensitivity_state.setChecked(False)
		if self.Param_Status_Submit_ANN is not None:
			self.Param_Status_Submit_ANN.setChecked(False)
		if self.Param_Status_Submit_ARIMA_nonseasonal is not None:
			# RUN-3: Always unchecked by default, user must manually choose
			self.Param_Status_Submit_ARIMA_nonseasonal.setChecked(False)
		if self.Param_Status_Submit_ARIMA_seasonal is not None:
			# RUN-3: Always unchecked by default, user must manually choose
			self.Param_Status_Submit_ARIMA_seasonal.setChecked(False)

		# Progress setup awal 0, tombol Start akan di-enable
		# oleh _check_all_locks bila syarat terpenuhi (RUN 2).
		if hasattr(self, "progressBar_Status_Setup"):
			self.progressBar_Status_Setup.setMinimum(0)
			self.progressBar_Status_Setup.setMaximum(100)
			self.progressBar_Status_Setup.setValue(0)

		# Panel Main: progress bar import dari desain di-set ke 0
		if hasattr(self, "progressBar"):
			self.progressBar.setMinimum(0)
			self.progressBar.setMaximum(100)
			self.progressBar.setValue(0)

		if self.select_avg_tanggal_awal is not None:
			self.select_avg_tanggal_awal.setEnabled(True)
			self.select_avg_tanggal_awal.setCalendarPopup(True)
		if self.select_avg_tanggal_akhir is not None:
			self.select_avg_tanggal_akhir.setEnabled(True)
			self.select_avg_tanggal_akhir.setCalendarPopup(True)
		if self.select_daily_tanggal_awal is not None:
			self.select_daily_tanggal_awal.setEnabled(True)
			self.select_daily_tanggal_awal.setCalendarPopup(True)

		# Initialize combobox_Limit_log (Tab Log - RUN 5)
		if hasattr(self, "combobox_Limit_log") and self.combobox_Limit_log is not None:
			self.combobox_Limit_log.clear()
			self.combobox_Limit_log.addItems(['100', '500', '1000', '2000'])
			self.combobox_Limit_log.setCurrentText('1000')  # Default 1000 lines
			self._current_log_limit = 1000
		else:
			self._current_log_limit = 1000  # Fallback
		if hasattr(self, "progressBar_3"):
			self.progressBar_3.setMinimum(0)
			self.progressBar_3.setMaximum(100)
			self.progressBar_3.setValue(0)
		if hasattr(self, "progressBar_export_resume"):
			self.progressBar_export_resume.setMinimum(0)
			self.progressBar_export_resume.setMaximum(100)
			self.progressBar_export_resume.setValue(0)
		if hasattr(self, "label_status_inisiasidata"):
			self.label_status_inisiasidata.setText("")

		self.start_analysis_PB.setEnabled(False)
		if hasattr(self, "Param_initial_value_FTS_sensitivity_state"):
			self._on_fts_sensitivity_lock_changed(None)
		self._reset_metrics_labels()

	def _connect_signals(self) -> None:
		self.start_analysis_PB.clicked.connect(self.start_analysis)

		# Optional buttons yang mungkin ada di desain final.
		if hasattr(self, "pushButton_cancel"):
			self.pushButton_cancel.clicked.connect(self.cancel_analysis)
		if hasattr(self, "pushButton_clear_data"):
			self.pushButton_clear_data.clicked.connect(self.clear_data)
		if hasattr(self, "pushButton_export_excel"):
			self.pushButton_export_excel.clicked.connect(self.export_results_to_excel)
		if hasattr(self, "Export_Btn_LOG"):
			self.Export_Btn_LOG.clicked.connect(self.export_log_file)
		if hasattr(self, "pushButton_open_db"):
			self.pushButton_open_db.clicked.connect(self._open_database_spreadsheet)

		# Panel Data & Perbarui Data (RUN-C)
		if hasattr(self, "download_BTN"):
			self.download_BTN.clicked.connect(self.on_download_clicked)
		if hasattr(self, "CANCEL_Download_Button"):
			self.CANCEL_Download_Button.clicked.connect(self.on_download_cancel_clicked)
		if hasattr(self, "browse_folder_location"):
			self.browse_folder_location.clicked.connect(self.on_browse_folder_clicked)
		if hasattr(self, "initate_button"):
			self.initate_button.clicked.connect(self.on_initiate_data_clicked)
		if hasattr(self, "button_export_path"):
			self.button_export_path.clicked.connect(self._choose_resume_export_path)
		if hasattr(self, "button_openfile"):
			self.button_openfile.clicked.connect(self._handle_resume_export_action)

		# Checkbox LOCK signals (RUN 2)
		if self.Param_Status_Submit_general is not None:
			self.Param_Status_Submit_general.stateChanged.connect(self._on_submit_general_changed)
		if self.Param_Status_Submit_FTS is not None:
			self.Param_Status_Submit_FTS.stateChanged.connect(self._on_submit_fts_changed)
		if hasattr(self, "Param_initial_value_FTS_sensitivity_state"):
			self.Param_initial_value_FTS_sensitivity_state.stateChanged.connect(
				self._on_fts_sensitivity_lock_changed
			)
		if self.Param_Status_Submit_ANN is not None:
			self.Param_Status_Submit_ANN.stateChanged.connect(self._on_submit_ann_changed)
		if self.Param_Status_Submit_ARIMA_nonseasonal is not None:
			self.Param_Status_Submit_ARIMA_nonseasonal.stateChanged.connect(self._on_arima_mode_changed)
		if self.Param_Status_Submit_ARIMA_seasonal is not None:
			self.Param_Status_Submit_ARIMA_seasonal.stateChanged.connect(self._on_arima_mode_changed)

		# Connect log limit combobox (RUN 5)
		if hasattr(self, "combobox_Limit_log") and self.combobox_Limit_log is not None:
			self.combobox_Limit_log.currentTextChanged.connect(self._on_log_limit_changed)

		# HOME interactions: range & checkbox changes re-render views
		try:
			if self.select_avg_tanggal_awal is not None:
				self.select_avg_tanggal_awal.dateTimeChanged.connect(
					lambda *_: self._refresh_home_dashboard(use_progress=False, preserve_range=True, preserve_daily=True)
				)
			if self.select_avg_tanggal_akhir is not None:
				self.select_avg_tanggal_akhir.dateTimeChanged.connect(
					lambda *_: self._refresh_home_dashboard(use_progress=False, preserve_range=True, preserve_daily=True)
				)
			if self.select_daily_tanggal_awal is not None:
				self.select_daily_tanggal_awal.dateTimeChanged.connect(
					lambda *_: self._refresh_home_dashboard(use_progress=False, preserve_range=True, preserve_daily=True)
				)
			for chk in [
				self.checkBox_avg_tegangan, self.checkBox_avg_arus, self.checkBox_avg_daya,
				self.checkBox_avg_energi, self.checkBox_avg_frekuensi, self.checkBox_avg_pf,
				self.checkBox_daily_tegangan, self.checkBox_daily_arus, self.checkBox_daily_daya,
				self.checkBox_daily_energi, self.checkBox_daily_frekuensi, self.checkBox_daily_pf,
			]:
				if chk is not None:
					chk.stateChanged.connect(
						lambda *_: self._refresh_home_dashboard(use_progress=False, preserve_range=True, preserve_daily=True)
					)
		except Exception:
			pass

		# Perubahan parameter untuk progress setup
		for name in [
			"Param_initial_value_general_trainortestplit",
			"Param_initial_value_FTS_interval",
			"Param_initial_value_ANN_epoch",
			"Param_initial_value_ANN_neuronperlayer",
			"Param_initial_value_ARIMA_nonSeasonal_p",
			"Param_initial_value_ARIMA_nonSeasonal_d",
			"Param_initial_value_ARIMA_nonSeasonal_q",
			"Param_initial_value_ARIMA_Seasonal_s",
		]:
			w = getattr(self, name, None)
			if w is not None:
				try:
					w.valueChanged.connect(self._update_setup_progress)  # type: ignore[arg-type]
				except Exception:
					pass
		if hasattr(self, "Param_Status_Submit_ARIMA_seasonal"):
			try:
				self.Param_Status_Submit_ARIMA_seasonal.stateChanged.connect(self._update_setup_progress)  # type: ignore[arg-type]
			except Exception:
				pass

	def _load_initial_data(
		self,
		reset_on_startup: bool | None = None,
		refresh_home: bool = True,
	) -> None:
		"""Mencoba memuat data telemetry dari SQLite."""

		if reset_on_startup is None:
			reset_on_startup = True
			try:
				if isinstance(self.current_config.get("global"), dict):
					reset_on_startup = bool(
						self.current_config["global"].get("reset_on_startup", True)
					)
			except Exception:
				reset_on_startup = True

		if reset_on_startup and not self._initiation_completed:
			try:
				deleted_map = self.db_mgr.clear_all_runtime()
				self.raw_data = None
				self._initiation_completed = False
				self.logger.log(
					"INFO",
					(
						"Startup reset enabled. Cleared runtime cache: "
						f"raw={deleted_map.get('raw_deleted', 0)} rows, "
						f"exp={deleted_map.get('exp_deleted', 0)} rows."
					),
				)
			except Exception as e:
				self.logger.log("ERROR", f"Failed to clear runtime cache on startup: {e}")

		df = self.db_mgr.fetch_data()
		if df is not None and not df.empty:
			self.raw_data = df
			# TV-03: Trigger target variable population after successful data load
			self._populate_target_variable_combobox()
		else:
			self.raw_data = None
			self.logger.log("INFO", "No data found in DB on startup.")

		self._update_data_status_label()
		self._load_database_table()

		# Refresh status setup & tombol Start (RUN 2: use checkbox LOCK mechanism)
		self._check_all_locks()

		# Jika data sudah ada, hidupkan juga dashboard Home (tanpa progress bar import)
		if refresh_home and self.raw_data is not None and not self.raw_data.empty:
			self._refresh_home_dashboard(use_progress=False)

		self._load_database_table()

	def _load_database_table(self) -> None:
		"""Menampilkan data telemetry pada tab Database."""
		table = getattr(self, "tableView_stored_db", None)
		if table is None:
			return
		try:
			df = self.db_mgr.get_all_raw_data_for_table()
		except Exception:
			df = pd.DataFrame()
		if df is None or df.empty:
			table.setModel(None)
			return
		model = self._PandasModel(df)
		table.setModel(model)
		table.resizeColumnsToContents()

	def _populate_target_variable_combobox(self) -> None:
		"""Populate target variable combobox dengan sensor options yang bermakna (TV-01/TV-02)."""
		if not hasattr(self, "Param_initial_value_general_variabeltraget") or self.Param_initial_value_general_variabeltraget is None:
			self.logger.log("WARNING", "Target variable combobox not found, skipping population")
			return
		
		# TV-01: Target Variable Options Definition
		target_options = [
			('watt', 'W - Daya (Watt)'),
			('voltage', 'V - Tegangan (Voltage)'),
			('current', 'A - Arus (Current)'),
			('frequency', 'F - Frekuensi (Frequency)'),
			('energy_kwh', 'E - Energi (kWh)'),
			('pf', 'PF - Power Factor')
		]
		
		try:
			# TV-02: Clear existing and populate meaningful options
			self.Param_initial_value_general_variabeltraget.blockSignals(True)
			self.Param_initial_value_general_variabeltraget.clear()
			
			for value, display_text in target_options:
				self.Param_initial_value_general_variabeltraget.addItem(display_text, value)
			
			# TV-04: Set meaningful default (W - Daya)
			self.Param_initial_value_general_variabeltraget.setCurrentIndex(0)
			
			self.Param_initial_value_general_variabeltraget.blockSignals(False)
			
			# E2E-01: UI Integration Testing Validation
			current_selection = self.Param_initial_value_general_variabeltraget.currentText()
			current_data = self.Param_initial_value_general_variabeltraget.currentData()
			validation_msg = (
				f"🔍 E2E-01 UI VALIDATION: QComboBox populated successfully | "
				f"Options={len(target_options)} | Default='{current_selection}' | "
				f"Value='{current_data}' | Status=READY_FOR_SELECTION"
			)
			self.logger.log("INFO", validation_msg)
			
			# LOG-01: Critical Parameter Format Standardization - UI Population
			self.logger.log("INFO", f"🔑 CRITICAL PARAM: TARGET_VARIABLE='{current_data}' ({current_selection}) - UI POPULATED")
			
			self.logger.log("INFO", f"Target variable combobox populated with {len(target_options)} options, default: W - Daya")
		except Exception as e:
			self.logger.log("ERROR", f"Failed to populate target variable combobox: {e}")

	def _choose_resume_export_path(self) -> None:
		"""Pilih path file untuk export Resume (PDF)."""
		default_name = f"resume_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
		file_path, _ = QFileDialog.getSaveFileName(
			self,
			"Export Resume PDF",
			default_name,
			"PDF Files (*.pdf)",
		)
		if not file_path:
			return
		self._last_export_file = file_path
		if hasattr(self, "folderpath_Export") and self.folderpath_Export is not None:
			self.folderpath_Export.setText(file_path)

	def _handle_resume_export_action(self) -> None:
		"""Export Resume PDF lalu buka file."""
		success = self._export_resume_report()
		if success and self._last_export_file and os.path.exists(self._last_export_file):
			try:
				os.startfile(self._last_export_file)
			except Exception:
				pass

	def _export_resume_report(self) -> bool:
		"""Generate PDF Resume dengan progres bar."""
		if not self.analysis_results:
			QMessageBox.warning(self, "No Results", "Run analysis first before exporting.")
			return False

		file_path = None
		if hasattr(self, "folderpath_Export") and self.folderpath_Export is not None:
			path_text = self.folderpath_Export.text().strip()
			if path_text:
				file_path = path_text
		if not file_path:
			self._choose_resume_export_path()
			file_path = self._last_export_file
		if not file_path:
			return False

		try:
			raw_df = self._get_analysis_raw_df()
		except Exception:
			raw_df = pd.DataFrame()

		params = self._last_run_params or self.get_ui_params() or {}

		def _progress(val: int, _msg: str) -> None:
			if hasattr(self, "progressBar_export_resume") and self.progressBar_export_resume is not None:
				self.progressBar_export_resume.setValue(val)

		_progress(0, "Preparing")
		success, message = ExportManager.export_resume_report(
			self.analysis_results,
			raw_df,
			params,
			file_path,
			logger=self.logger,
			progress_cb=_progress,
		)
		if success:
			self._last_export_file = file_path
			_progress(100, "Done")
			QMessageBox.information(self, "Success", message)
			return True
		else:
			QMessageBox.critical(self, "Export Failed", message)
			return False

	def _open_database_spreadsheet(self) -> None:
		"""Ekspor data DB ke file temp dan buka di spreadsheet default."""
		self._load_database_table()
		try:
			df = self.db_mgr.get_all_raw_data_for_table()
		except Exception as e:
			self.logger.log("ERROR", f"Failed to load DB for export: {e}")
			QMessageBox.warning(self, "Open SQL", "Gagal memuat data database.")
			return
		if df is None or df.empty:
			QMessageBox.warning(self, "Open SQL", "Tidak ada data untuk dibuka.")
			return
		try:
			import tempfile

			temp_dir = tempfile.gettempdir()
			file_name = f"ppdl_db_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
			temp_path = os.path.join(temp_dir, file_name)
			df.to_csv(temp_path, index=False)
			os.startfile(temp_path)
			self.logger.log("SUCCESS", f"Open SQL exported to temp file: {temp_path}")
		except Exception as e:
			self.logger.log("ERROR", f"Open SQL failed: {e}")
			QMessageBox.warning(self, "Open SQL", f"Gagal membuka file:\n{e}")

	# ------------------------------------------------------------------
	# Parameter & Validasi
	# ------------------------------------------------------------------

	def _update_data_status_label(self) -> None:
		"""Update label status data di panel Main/Data.

		Perilaku:
		- Awal: kosong (tidak ada teks).
		- Setelah ada data tapi inisiasi belum dinyatakan selesai:
		  "Data Loaded (N rows)".
		- Setelah proses inisiasi data selesai 100%:
		  "Data Ready (N rows)".
		"""

		label = getattr(self, "label_status_inisiasidata", None)
		if label is None:
			return

		if self.raw_data is None or getattr(self.raw_data, "empty", True):
			label.setText("")
			return

		row_count = len(self.raw_data)
		if self._initiation_completed:
			label.setText(f"Data Ready ({row_count} rows)")
		else:
			label.setText(f"Data Loaded ({row_count} rows)")

	def _update_setup_progress(self) -> None:
		"""Update progress bar berdasarkan checkbox LOCK (RUN 2)."""

		bar = getattr(self, "progressBar_Status_Setup", None)
		if bar is None:
			return

		def _checked(widget) -> bool:
			return widget is not None and widget.isChecked()

		arima_mode_ok = False
		if self.Param_Status_Submit_ARIMA_seasonal is not None and self.Param_Status_Submit_ARIMA_nonseasonal is not None:
			seasonal = self.Param_Status_Submit_ARIMA_seasonal.isChecked()
			nonseasonal = self.Param_Status_Submit_ARIMA_nonseasonal.isChecked()
			arima_mode_ok = seasonal ^ nonseasonal

		fts_locked = _checked(self.Param_Status_Submit_FTS)
		if hasattr(self, "Param_initial_value_FTS_sensitivity_state"):
			fts_locked = fts_locked and self.Param_initial_value_FTS_sensitivity_state.isChecked()

		total = 4
		checked = (
			int(_checked(self.Param_Status_Submit_general))
			+ int(fts_locked)
			+ int(_checked(self.Param_Status_Submit_ANN))
			+ int(arima_mode_ok)
		)
		progress = int((checked / total) * 100)
		bar.setValue(progress)

	def _reset_metrics_labels(self) -> None:
		"""Reset label MAE/MAPE/RMSE agar tidak tampil 'TextLabel'."""
		names = [
			"label_mae_fts_train", "label_mae_fts_test", "label_mae_naive", "label_mae_ma",
			"label_mae_ann_train", "label_mae_ann_test", "label_mae_arima_train", "label_mae_arima_test",
			"label_mape_fts_train", "label_mape_fts_test", "label_mape_naive", "label_mape_ma",
			"label_mape_ann_train", "label_mape_ann_test", "label_mape_arima_train", "label_mape_arima_test",
			"label_rmse_fts_train", "label_rmse_fts_test", "label_rmse_naive", "label_rmse_ma",
			"label_rmse_ann_train", "label_rmse_ann_test", "label_rmse_arima_train", "label_rmse_arima_test",
			"label_mape_fts_ttest", "label_mape_fts_naive", "label_mape_fts_ma",
			"label_rmse_fts_naive", "label_rmse_fts_ma",
		]
		for name in names:
			w = getattr(self, name, None)
			if w is not None:
				try:
					w.setText("-")
				except Exception:
					pass

	def _set_enabled(self, widget, enabled: bool) -> None:
		if widget is None:
			return
		try:
			widget.setEnabled(enabled)
		except Exception:
			pass

	# RUN-3 ST-04: State validation system implementation
	def _validate_parameter_state(self, param_name: str, operation: str) -> bool:
		"""Validate if parameter operation is allowed in current state.
		
		Args:
			param_name: Name of parameter (e.g., 'fts_interval', 'uod_min')
			operation: Operation type ('read', 'write', 'lock', 'unlock')
			
		Returns:
			bool: True if operation is allowed, False otherwise
		"""
		# During startup, suppress all validation
		if getattr(self, "_startup_in_progress", False):
			return operation == 'read'  # Only allow reads during startup
		
		# Check if parameter is currently locked
		if 'fts' in param_name.lower():
			locked = getattr(self, 'Param_Status_Submit_FTS', None)
			if locked and locked.isChecked() and operation == 'write':
				return False
		elif 'ann' in param_name.lower():
			locked = getattr(self, 'Param_Status_Submit_ANN', None)
			if locked and locked.isChecked() and operation == 'write':
				return False
		elif 'arima' in param_name.lower():
			locked_seasonal = getattr(self, 'Param_Status_Submit_ARIMA_seasonal', None)
			locked_nonseasonal = getattr(self, 'Param_Status_Submit_ARIMA_nonseasonal', None)
			if ((locked_seasonal and locked_seasonal.isChecked()) or 
				(locked_nonseasonal and locked_nonseasonal.isChecked())) and operation == 'write':
				return False
				
		return True

	def _enforce_parameter_lock_consistency(self) -> None:
		"""Ensure all parameter locks are consistently applied across UI."""
		# RUN-3 ST-04: Parameter state machine enforcement
		if getattr(self, "_startup_in_progress", False):
			return
			
		# Validate FTS parameter consistency
		fts_locked = getattr(self, 'Param_Status_Submit_FTS', None)
		if fts_locked and fts_locked.isChecked():
			self._lock_fts_controls(True)
			
		# Validate ANN parameter consistency
		ann_locked = getattr(self, 'Param_Status_Submit_ANN', None)
		if ann_locked and ann_locked.isChecked():
			self._lock_ann_controls(True)
			
		# Validate ARIMA parameter consistency
		arima_seasonal = getattr(self, 'Param_Status_Submit_ARIMA_seasonal', None)
		arima_nonseasonal = getattr(self, 'Param_Status_Submit_ARIMA_nonseasonal', None)
		if ((arima_seasonal and arima_seasonal.isChecked()) or 
			(arima_nonseasonal and arima_nonseasonal.isChecked())):
			self._lock_arima_controls(True)

	def _unified_parameter_lock_handler(self, tab_name: str, locked: bool) -> None:
		"""RUN-4 PL-01: Unified lock mechanism for all parameter tabs.
		
		Args:
			tab_name: 'general', 'fts', 'ann', 'arima'
			locked: True to lock parameters, False to unlock
		"""
		if tab_name == 'general':
			self._lock_general_controls(locked)
		elif tab_name == 'fts':
			self._lock_fts_controls(locked)
		elif tab_name == 'ann':
			self._lock_ann_controls(locked)
		elif tab_name == 'arima':
			self._lock_arima_controls(locked)
		
		# Log unified lock state change
		if not getattr(self, "_startup_in_progress", False):
			lock_state = "LOCKED" if locked else "UNLOCKED"
			self.logger.log("INFO", f"Parameter Lock {tab_name.upper()} -> State: {lock_state}")

	def _lock_general_controls(self, locked: bool) -> None:
		self._set_enabled(getattr(self, "Param_initial_value_general_variabeltraget", None), not locked)
		self._set_enabled(getattr(self, "Param_initial_value_general_trainortestplit", None), not locked)
		self._set_enabled(getattr(self, "Param_initial_value_general_forecasting", None), not locked)

	def _lock_fts_controls(self, locked: bool) -> None:
		"""RUN-4 PL-02: Enhanced FTS parameter lock validation with unified coverage."""
		# Core FTS parameters - consistent with unified lock mechanism
		self._set_enabled(getattr(self, "Param_initial_value_FTS_interval", None), not locked)
		self._set_enabled(getattr(self, "Param_initial_value_FTS_equalwidth", None), not locked)
		self._set_enabled(getattr(self, "Param_initial_value_FTS_sensitivity_state", None), not locked)
		
		# RUN-4 PL-02: Comprehensive UoD parameter lock enforcement
		self._set_enabled(getattr(self, "Param_initial_value_FTS_uod_min", None), not locked)
		self._set_enabled(getattr(self, "Param_initial_value_FTS_uod_max", None), not locked)
		self._set_enabled(getattr(self, "Param_initial_value_FTS_pad_percent", None), not locked)
		
		# RUN-4 PL-02: Sensitivity parameter with nested lock behavior
		sensitivity_widget = getattr(self, "Param_initial_value_FTS_sensitivity", None)
		if sensitivity_widget is not None:
			if locked:
				# When FTS is locked, sensitivity is also locked regardless of its state
				self._set_enabled(sensitivity_widget, False)
			else:
				# When FTS is unlocked, sensitivity follows its own lock state
				locked_sensitivity = False
				if hasattr(self, "Param_initial_value_FTS_sensitivity_state"):
					locked_sensitivity = self.Param_initial_value_FTS_sensitivity_state.isChecked()
				self._set_enabled(sensitivity_widget, not locked_sensitivity)

	def _lock_ann_controls(self, locked: bool) -> None:
		"""RUN-4 PL-03: Standardized ANN parameter lock implementation with comprehensive coverage."""
		# Core ANN architecture parameters
		self._set_enabled(getattr(self, "Param_initial_value_ANN_epoch", None), not locked)
		self._set_enabled(getattr(self, "Param_initial_value_ANN_neuronperlayer", None), not locked)
		self._set_enabled(getattr(self, "Param_initial_value_ANN_hiddenlayer", None), not locked)
		
		# Training parameters with consistent lock behavior
		self._set_enabled(getattr(self, "Param_initial_value_ANN_learningrate", None), not locked)
		self._set_enabled(getattr(self, "Param_initial_value_ANN_batchsize", None), not locked)
		
		# Advanced parameters - RUN-4 PL-03: Unified lock coverage
		self._set_enabled(getattr(self, "Param_initial_value_ANN_lagwindowK", None), not locked)
		self._set_enabled(getattr(self, "Param_initial_value_ANN_activationfunction", None), not locked)

	def _lock_arima_controls(self, locked: bool) -> None:
		"""RUN-4 PL-04: Comprehensive ARIMA parameter lock mechanism for data consistency."""
		# Non-seasonal order parameters (p,d,q) - consistent lock behavior
		self._set_enabled(getattr(self, "Param_initial_value_ARIMA_nonSeasonal_p", None), not locked)
		self._set_enabled(getattr(self, "Param_initial_value_ARIMA_nonSeasonal_d", None), not locked)
		self._set_enabled(getattr(self, "Param_initial_value_ARIMA_nonSeasonal_q", None), not locked)
		
		# Seasonal order parameters (P,D,Q,s) - RUN-4 PL-04: Unified lock coverage
		self._set_enabled(getattr(self, "Param_initial_value_ARIMA_Seasonal_P", None), not locked)
		self._set_enabled(getattr(self, "Param_initial_value_ARIMA_Seasonal_D", None), not locked)
		self._set_enabled(getattr(self, "Param_initial_value_ARIMA_Seasonal_Q", None), not locked)
		self._set_enabled(getattr(self, "Param_initial_value_ARIMA_Seasonal_s", None), not locked)

	def _on_submit_general_changed(self, _state) -> None:
		"""RUN-4 PL-01: Updated to use unified lock mechanism."""
		if self.Param_Status_Submit_general is None:
			return
		locked = self.Param_Status_Submit_general.isChecked()
		
		if locked:
			# LM-01/LM-02: Lock Validation Enhancement - Target Variable Lock Validation
			target_display = "-"
			target_value = "watt"  # Default fallback
			
			if hasattr(self, "Param_initial_value_general_variabeltraget") and self.Param_initial_value_general_variabeltraget is not None:
				try:
					target_display = str(self.Param_initial_value_general_variabeltraget.currentText()).strip()
					
					# Extract target_value using currentData() or text parsing
					current_data = self.Param_initial_value_general_variabeltraget.currentData()
					if current_data:
						target_value = str(current_data)
					else:
						# Fallback: parse display text
						text_mapping = {
							"W - Daya": "watt", "V - Tegangan": "voltage", "A - Arus": "current",
							"F - Frekuensi": "frequency", "E - Energi": "energy_kwh", "PF - Power Factor": "pf"
						}
						for display_key, value in text_mapping.items():
							if display_key in target_display:
								target_value = value
								break
				except Exception as e:
					self.logger.log("WARNING", f"Failed to extract target variable during lock: {e}")
					target_display = "-"
					target_value = "watt"
			
			# LM-02: Ensure target_value exists dalam raw_data.columns
			if self.raw_data is not None and not self.raw_data.empty:
				if target_value not in self.raw_data.columns:
					available_cols = list(self.raw_data.columns)
					warning_msg = f"Cannot lock: Target variable '{target_value}' not found in data.\n\nAvailable columns: {', '.join(available_cols)}"
					self.logger.log("WARNING", f"Lock validation failed: target_variable '{target_value}' not found in columns")
					QMessageBox.warning(self, "Lock Validation Failed", warning_msg)
					# Uncheck the lock dan return
					self.Param_Status_Submit_general.blockSignals(True)
					self.Param_Status_Submit_general.setChecked(False)
					self.Param_Status_Submit_general.blockSignals(False)
					self._check_all_locks()
					return
				
				# LM-03: Data Quality Lock Check
				target_series = self.raw_data[target_value]
				non_null_count = target_series.count()
				total_count = len(target_series)
				min_threshold = 10  # Minimum required non-null values
				
				if non_null_count < min_threshold:
					warning_msg = f"Cannot lock: Insufficient data for target variable '{target_value}': {non_null_count}/{total_count} valid values (minimum {min_threshold} required)"
					self.logger.log("WARNING", f"Lock validation failed: insufficient data for target_variable '{target_value}' ({non_null_count}/{total_count})")
					QMessageBox.warning(self, "Lock Validation Failed", warning_msg)
					# Uncheck the lock dan return
					self.Param_Status_Submit_general.blockSignals(True)
					self.Param_Status_Submit_general.setChecked(False)
					self.Param_Status_Submit_general.blockSignals(False)
					self._check_all_locks()
					return
		
		self._unified_parameter_lock_handler('general', locked)
		
		if not locked:
			self._check_all_locks()
			return
		if getattr(self, "_startup_in_progress", False):
			self._check_all_locks()
			return
		
		# Extract parameters for logging
		target_display = "-"
		target_value = "watt"
		if hasattr(self, "Param_initial_value_general_variabeltraget") and self.Param_initial_value_general_variabeltraget is not None:
			try:
				target_display = str(self.Param_initial_value_general_variabeltraget.currentText()).strip()
				current_data = self.Param_initial_value_general_variabeltraget.currentData()
				if current_data:
					target_value = str(current_data)
				else:
					text_mapping = {
						"W - Daya": "watt", "V - Tegangan": "voltage", "A - Arus": "current",
						"F - Frekuensi": "frequency", "E - Energi": "energy_kwh", "PF - Power Factor": "pf"
					}
					for display_key, value in text_mapping.items():
						if display_key in target_display:
							target_value = value
							break
			except Exception:
				target_display = "-"
				target_value = "watt"
		
		split_pct = None
		try:
			split_pct = float(self.Param_initial_value_general_trainortestplit.value())
		except Exception:
			split_pct = None
		
		forecast = "-"
		if self.Param_initial_value_general_forecasting is not None:
			try:
				forecast = str(self.Param_initial_value_general_forecasting.currentText()).strip()
			except Exception:
				forecast = "-"
		if not forecast:
			forecast = "1"
		
		# LM-04: Contract Compliant Logging
		msg = (
			f"🔒 CONTRACT COMPLIANT lock applied -> Target Variable: {target_display} ({target_value}) | "
			f"Train/Test Split: {split_pct} | Forecasting: {forecast} -> Lock_1_General validates Split Ratio + Target Variable"
		)
		self.logger.log("INFO", msg)
		
		# LOG-01: Critical Parameters Format Standardization in Lock
		self.logger.log("INFO", f"🔑 CRITICAL PARAM: TARGET_VARIABLE='{target_value}' ({target_display})")
		self.logger.log("INFO", f"🔑 CRITICAL PARAM: FORECASTING_HORIZON='{forecast}' ({forecast} periods)")
		
		# E2E-02: Lock Mechanism Contract Validation
		self.logger.log("INFO", f"🔍 E2E-02 LOCK VALIDATION: Target_validation=PASSED | Data_check=PASSED | Lock_applied=SUCCESS | Contract_requirement=SATISFIED")
		
		self._check_all_locks()

	def _on_submit_fts_changed(self, _state) -> None:
		"""RUN-4 PL-02: Updated to use unified lock mechanism."""
		if self.Param_Status_Submit_FTS is None:
			return
		locked = self.Param_Status_Submit_FTS.isChecked()
		self._unified_parameter_lock_handler('fts', locked)
		
		if not locked:
			self._check_all_locks()
			return
		if getattr(self, "_startup_in_progress", False):
			self._check_all_locks()
			return
		interval = "-"
		try:
			interval = str(self.Param_initial_value_FTS_interval.value())
		except Exception:
			pass
		partition = "-"
		if hasattr(self, "Param_initial_value_FTS_equalwidth"):
			try:
				partition = str(self.Param_initial_value_FTS_equalwidth.currentText()).strip()
			except Exception:
				partition = "-"
		sensitivity = "-"
		if hasattr(self, "Param_initial_value_FTS_sensitivity"):
			try:
				sensitivity_val = float(self.Param_initial_value_FTS_sensitivity.value())
				sensitivity = f"{sensitivity_val:.3f}"
			except Exception:
				sensitivity = "-"
		valid = "OFF"
		if hasattr(self, "Param_initial_value_FTS_sensitivity_state"):
			try:
				valid = "ON" if self.Param_initial_value_FTS_sensitivity_state.isChecked() else "OFF"
			except Exception:
				valid = "OFF"
		# Glass Box Formatting
		msg = (
			f"Initial Data Parameter for FTS submitted -> Interval : {interval} | "
			f"Partition : {partition} | Sensitivity : {sensitivity} | Valid : {valid} -> Value lock for analysis"
		)
		self.logger.log("INFO", msg)
		self._check_all_locks()
		if not locked:
			self._check_all_locks()
			return
		if getattr(self, "_startup_in_progress", False):
			self._check_all_locks()
			return
		interval = "-"
		try:
			interval = str(self.Param_initial_value_FTS_interval.value())
		except Exception:
			pass
		partition = "-"
		if hasattr(self, "Param_initial_value_FTS_equalwidth"):
			try:
				partition = str(self.Param_initial_value_FTS_equalwidth.currentText()).strip()
			except Exception:
				partition = "-"
		sensitivity = "-"
		if hasattr(self, "Param_initial_value_FTS_sensitivity"):
			try:
				sensitivity_val = float(self.Param_initial_value_FTS_sensitivity.value())
				sensitivity = f"{sensitivity_val:.3f}"
			except Exception:
				sensitivity = "-"
		valid = "OFF"
		if hasattr(self, "Param_initial_value_FTS_sensitivity_state"):
			try:
				valid = "ON" if self.Param_initial_value_FTS_sensitivity_state.isChecked() else "OFF"
			except Exception:
				valid = "OFF"
		# Glass Box Formatting
		msg = (
			f"Initial Data Parameter for FTS submitted -> Interval : {interval} | "
			f"Partition : {partition} | Sensitivity : {sensitivity} | Valid : {valid} -> Value lock for analysis"
		)
		self.logger.log("INFO", msg)
		self._check_all_locks()

	def _on_fts_sensitivity_lock_changed(self, _state) -> None:
		# RUN-3 ST-01: Suppress validation events during startup for clean state
		if getattr(self, "_startup_in_progress", False):
			return
		
		# Toggle enable/disable of sensitivity input based on lock checkbox
		sens_widget = getattr(self, "Param_initial_value_FTS_sensitivity", None)
		sens_lock = getattr(self, "Param_initial_value_FTS_sensitivity_state", None)
		if sens_widget is None or sens_lock is None:
			self._check_all_locks()
			return
		locked = bool(sens_lock.isChecked())
		self._set_enabled(sens_widget, not locked)
		valid = "ON" if locked else "OFF"
		self.logger.log("INFO", f"FTS Sensitivity Valid-LOCK changed -> Valid : {valid}")
		self._check_all_locks()
	def _on_submit_ann_changed(self, _state) -> None:
		"""RUN-4 PL-03: Updated to use unified lock mechanism."""
		if self.Param_Status_Submit_ANN is None:
			return
		locked = self.Param_Status_Submit_ANN.isChecked()
		self._unified_parameter_lock_handler('ann', locked)
		
		if not locked:
			self._check_all_locks()
			return
		if getattr(self, "_startup_in_progress", False):
			self._check_all_locks()
			return

		epoch = "-"
		neurons = "-"
		layers = "-"
		try:
			epoch = str(self.Param_initial_value_ANN_epoch.value())
			neurons = str(self.Param_initial_value_ANN_neuronperlayer.value())
			layers = str(self.Param_initial_value_ANN_hiddenlayer.value())
		except Exception:
			pass

		lr = "-"
		if hasattr(self, "Param_initial_value_ANN_learningrate"):
			try:
				lr = f"{float(self.Param_initial_value_ANN_learningrate.value()):.4f}"
			except Exception:
				lr = "-"

		batch = "-"
		if hasattr(self, "Param_initial_value_ANN_batchsize"):
			try:
				batch = str(self.Param_initial_value_ANN_batchsize.value())
			except Exception:
				batch = "-"

		lag = "-"
		if hasattr(self, "Param_initial_value_ANN_lagwindowK"):
			try:
				lag = str(self.Param_initial_value_ANN_lagwindowK.value())
			except Exception:
				lag = "-"

		activation = "-"
		if hasattr(self, "Param_initial_value_ANN_activationfunction"):
			try:
				activation = str(self.Param_initial_value_ANN_activationfunction.currentText()).strip()
			except Exception:
				activation = "-"

		msg = (
			f"Initial Data Parameter for ANN submitted -> Epoch : {epoch} | Layers : {layers} | "
			f"Neuron/Layers : {neurons} | LR : {lr} | Batch : {batch} | Lag K : {lag} | Activation : {activation} -> Value lock for analysis"
		)
		self.logger.log("INFO", msg)
		self._check_all_locks()
		if not locked:
			self._check_all_locks()
			return
		if getattr(self, "_startup_in_progress", False):
			self._check_all_locks()
			return

		epoch = "-"
		neurons = "-"
		layers = "-"
		try:
			epoch = str(self.Param_initial_value_ANN_epoch.value())
			neurons = str(self.Param_initial_value_ANN_neuronperlayer.value())
			layers = str(self.Param_initial_value_ANN_hiddenlayer.value())
		except Exception:
			pass

		lr = "-"
		if hasattr(self, "Param_initial_value_ANN_learningrate"):
			try:
				lr = f"{float(self.Param_initial_value_ANN_learningrate.value()):.4f}"
			except Exception:
				lr = "-"

		batch = "-"
		if hasattr(self, "Param_initial_value_ANN_batchsize"):
			try:
				batch = str(self.Param_initial_value_ANN_batchsize.value())
			except Exception:
				batch = "-"

		lag = "-"
		if hasattr(self, "Param_initial_value_ANN_lagwindowK"):
			try:
				lag = str(self.Param_initial_value_ANN_lagwindowK.value())
			except Exception:
				lag = "-"

		activation = "-"
		if hasattr(self, "Param_initial_value_ANN_activationfunction"):
			try:
				activation = str(self.Param_initial_value_ANN_activationfunction.currentText()).strip()
			except Exception:
				activation = "-"

		msg = (
			f"Initial Data Parameter for ANN submitted -> Epoch : {epoch} | Layers : {layers} | "
			f"Neuron/Layers : {neurons} | LR : {lr} | Batch : {batch} | Lag K : {lag} | Activation : {activation} -> Value lock for analysis"
		)
		self.logger.log("INFO", msg)
		self._check_all_locks()

	def _check_all_locks(self):
		"""Check apakah semua checkbox LOCK sudah di-check (RUN 2).
		
		START ANALYSIS button hanya enabled jika:
		1. ALL checkbox LOCK di-check
		2. Data sudah ada (self.raw_data not None)
		"""
		# Check if all checkboxes exist and are checked
		all_locked = True
		
		if self.Param_Status_Submit_general is not None:
			all_locked = all_locked and self.Param_Status_Submit_general.isChecked()
		else:
			all_locked = False
			
		fts_locked = False
		if self.Param_Status_Submit_FTS is not None:
			fts_locked = self.Param_Status_Submit_FTS.isChecked()
			if hasattr(self, "Param_initial_value_FTS_sensitivity_state"):
				fts_locked = fts_locked and self.Param_initial_value_FTS_sensitivity_state.isChecked()
			all_locked = all_locked and fts_locked
		else:
			all_locked = False
			
		if self.Param_Status_Submit_ANN is not None:
			all_locked = all_locked and self.Param_Status_Submit_ANN.isChecked()
		else:
			all_locked = False
			
		seasonal = False
		nonseasonal = False
		if self.Param_Status_Submit_ARIMA_seasonal is not None:
			seasonal = self.Param_Status_Submit_ARIMA_seasonal.isChecked()
		if self.Param_Status_Submit_ARIMA_nonseasonal is not None:
			nonseasonal = self.Param_Status_Submit_ARIMA_nonseasonal.isChecked()

		arima_locked = seasonal ^ nonseasonal
		all_locked = all_locked and arima_locked
		
		data_ready = self.raw_data is not None and len(self.raw_data) > 0
		
		# Enable START ANALYSIS hanya jika both conditions true
		can_start = all_locked and data_ready
		
		if hasattr(self, 'start_analysis_PB') and self.start_analysis_PB is not None:
			self.start_analysis_PB.setEnabled(can_start)

		self._update_setup_progress()

		# Update status message (hanya log sekali saat perubahan state)
		if not hasattr(self, '_last_lock_state'):
			self._last_lock_state = can_start
		
		if can_start and not self._last_lock_state:
			self.logger.log_event(
				lvl1="INFO",
				lvl2="INITIAL",
				lvl3="CAL",
				lvl4="GENERAL",
				evt=EVT.PARAM_LOCK_APPLIED,
				route_to=["MAIN", "RESUME"],
				fields=["status=READY"],
			)
			self._last_lock_state = True
		elif not can_start and self._last_lock_state:
			if not all_locked:
				self.logger.log_event(
					lvl1="WARN",
					lvl2="INITIAL",
					lvl3="CAL",
					lvl4="GENERAL",
					evt=EVT.PARAM_LOCK_REJECTED,
					route_to=["MAIN", "RESUME"],
					fields=["status=NOT_READY"],
					cause="missing_lock_tabs",
					result="status=REJECTED",
				)
			elif not data_ready:
				self.logger.lo("INFO", "All parameters LOCKED - Ready to start analysis",		cause="no_data_loaded",
					result="status=REJECTED",
				)
			self._last_lock_state = False

	def get_ui_params(self) -> dict | None:
		"""Mengambil semua parameter dari UI + validasi dasar.

		Mengembalikan dict parameter atau None jika validation error.
		"""

		try:
			split_ratio = self.Param_initial_value_general_trainortestplit.value() / 100.0
			if not 0.1 <= split_ratio <= 0.9:
				raise ValueError("Split ratio harus antara 10% dan 90%.")

			fts_interval = self.Param_initial_value_FTS_interval.value()
			if fts_interval < 3:
				raise ValueError("FTS Interval minimal 3.")
			fts_sensitivity = None
			fts_sensitivity_locked = False
			fts_equalwidth = None
			if hasattr(self, "Param_initial_value_FTS_sensitivity"):
				fts_sensitivity = float(self.Param_initial_value_FTS_sensitivity.value())
			if hasattr(self, "Param_initial_value_FTS_sensitivity_state"):
				fts_sensitivity_locked = self.Param_initial_value_FTS_sensitivity_state.isChecked()
			if hasattr(self, "Param_initial_value_FTS_equalwidth"):
				try:
					fts_display_text = str(self.Param_initial_value_FTS_equalwidth.currentText()).strip()
					# Convert display text to FTS logic format
					if "Equal Width" in fts_display_text or "Jarak Sebaran" in fts_display_text:
						fts_equalwidth = "equal-width"
					elif "Equal Frequency" in fts_display_text or "Frekuensi" in fts_display_text:
						fts_equalwidth = "equal-frequency"
					else:
						fts_equalwidth = "equal-width"  # Default fallback
				except Exception:
					fts_equalwidth = "equal-width"  # Default fallback

			# Forecasting Horizon (RUN 2)
			forecast_horizon = 1  # Default
			if self.Param_initial_value_general_forecasting is not None:
				try:
					forecast_horizon = int(self.Param_initial_value_general_forecasting.currentText())
				except Exception:
					forecast_horizon = 1
			
			# PC-01: Target Variable Extraction
			target_variable = "watt"  # Default fallback
			if hasattr(self, "Param_initial_value_general_variabeltraget") and self.Param_initial_value_general_variabeltraget is not None:
				try:
					# Extract value using currentData() first, fallback to text parsing
					current_data = self.Param_initial_value_general_variabeltraget.currentData()
					if current_data:
						target_variable = str(current_data)
					else:
						# Fallback: parse display text to column names
						display_text = str(self.Param_initial_value_general_variabeltraget.currentText()).strip()
						text_mapping = {
							"W - Daya": "watt", "V - Tegangan": "voltage", "A - Arus": "current",
							"F - Frekuensi": "frequency", "E - Energi": "energy_kwh", "PF - Power Factor": "pf"
						}
						for display_key, value in text_mapping.items():
							if display_key in display_text:
								target_variable = value
								break
				except Exception as e:
					self.logger.log("WARNING", f"Failed to extract target variable: {e}, using default 'watt'")
					target_variable = "watt"
			
			# PC-03: Target Variable Data Validation
			if self.raw_data is not None and not self.raw_data.empty:
				if target_variable not in self.raw_data.columns:
					available_cols = list(self.raw_data.columns)
					raise ValueError(f"Target variable '{target_variable}' not found in data. Available columns: {available_cols}")
				
				# PC-04: Data Quality Check
				target_series = self.raw_data[target_variable]
				non_null_count = target_series.count()
				total_count = len(target_series)
				min_threshold = 10  # Minimum required non-null values
				
				if non_null_count < min_threshold:
					raise ValueError(f"Insufficient data for target variable '{target_variable}': {non_null_count}/{total_count} valid values (minimum {min_threshold} required)")
				else:
					self.logger.log("INFO", f"Target variable '{target_variable}' validated: {non_null_count}/{total_count} valid values")
					
					# E2E-01: Parameter Collection Validation
					self.logger.log("INFO", f"🔍 E2E-01 PARAM VALIDATION: target_variable extraction successful | Value='{target_variable}' | Data_quality={non_null_count}/{total_count} | Status=COLLECTION_OK")
			resample_method = None
			if isinstance(self.current_config.get("global"), dict):
				resample_method = self.current_config["global"].get("resample_method")
			if not resample_method:
				resample_method = "mean"

			epoch = self.Param_initial_value_ANN_epoch.value()
			neuron = self.Param_initial_value_ANN_neuronperlayer.value()
			if int(epoch) < 1:
				raise ValueError("ANN Epoch minimal 1.")
			if int(neuron) < 1:
				raise ValueError("ANN Neuron minimal 1.")

			p = self.Param_initial_value_ARIMA_nonSeasonal_p.value()
			d = self.Param_initial_value_ARIMA_nonSeasonal_d.value()
			q = self.Param_initial_value_ARIMA_nonSeasonal_q.value()
			if int(p) < 0 or int(d) < 0 or int(q) < 0:
				raise ValueError("ARIMA p,d,q tidak boleh negatif.")
			seasonal = self.Param_Status_Submit_ARIMA_seasonal.isChecked()
			nonseasonal = self.Param_Status_Submit_ARIMA_nonseasonal.isChecked()
			if seasonal and nonseasonal:
				raise ValueError("ARIMA hanya boleh memilih salah satu mode: seasonal atau nonseasonal.")
			if not seasonal and not nonseasonal:
				raise ValueError("Pilih salah satu mode ARIMA: seasonal atau nonseasonal.")
			s = self.Param_initial_value_ARIMA_Seasonal_s.value() if seasonal else 0
			if seasonal and int(s) < 1:
				raise ValueError("ARIMA seasonal period (s) minimal 1.")

			params = {
				"global": {
					"split_ratio": split_ratio,
					"forecast_horizon": forecast_horizon,
					"resample_method": resample_method,
					"target_variable": target_variable  # PC-02: Include target variable in parameters
				},
				"fts": {
					"interval": fts_interval,
					"sensitivity": fts_sensitivity,
					"sensitivity_locked": fts_sensitivity_locked,
					"partition": fts_equalwidth,
				},
				"ann": {
					"epoch": epoch,
					"neuron": neuron,
					"layers": int(self.Param_initial_value_ANN_hiddenlayer.value()),
					"lr": 0.01,
				},
				"arima": {
					"p": p,
					"d": d,
					"q": q,
					"seasonal": seasonal,
					"P": 0,
					"D": 1,
					"Q": 0,
					"s": s,
				},
			}
			if int(params["ann"]["layers"]) < 1:
				raise ValueError("ANN Hidden Layers minimal 1.")
			return params
		except Exception as e:
			try:
				self.logger.log("WARNING", f"Invalid Parameter: {e}")
			except Exception:
				pass
			QMessageBox.warning(self, "Invalid Parameter", str(e))
			return None

	def _emit_calc_blocks_run4(self, *, params: dict, analysis_df: pd.DataFrame) -> None:
		"""RUN-4 Ex_Plan-6: emit CALC blocks untuk DATA_* dan PARAM_*.

		Blok ditulis ke:
		- [calc]_[detail]_<GUID>.log
		- [global]_[view]_<GUID>.log
		"""

		logger = getattr(self, "logger", None)
		if logger is None or not hasattr(logger, "emit_calc_block"):
			return

		# ----------------------------
		# DATA_* blocks
		# ----------------------------
		full_df = self.raw_data if self.raw_data is not None else self.db_mgr.fetch_data()
		if full_df is None:
			full_df = pd.DataFrame()

		start_ms, end_ms = self._get_selected_average_range_ms()
		source_path = getattr(self, "_last_import_file_path", None)
		source_file = getattr(self, "_last_import_file_name", None)
		src_total_found = getattr(self, "_last_import_total_found", None)
		src_inserted = getattr(self, "_last_import_inserted", None)

		source_counts = {}
		if not full_df.empty and "source" in full_df.columns:
			try:
				source_counts = full_df["source"].value_counts(dropna=False).to_dict()
			except Exception:
				source_counts = {}

		data_load_steps = [
			"input: raw_telemetry (SQLite) via DBManager.fetch_data()",
			f"source_file={source_file}",
			f"source_path={source_path}",
			f"import_rows_found={src_total_found}",
			f"import_rows_inserted={src_inserted}",
			f"db_rows_total={int(len(full_df))}",
			f"analysis_rows={int(len(analysis_df))}",
			f"avg_range_start_ms={start_ms} ({_fmt_dt_from_ms(start_ms)})",
			f"avg_range_end_ms={end_ms} ({_fmt_dt_from_ms(end_ms)})",
			f"source_counts={source_counts}",
		]
		data_load_result = [
			f"rows_total={int(len(full_df))}",
			f"rows_analysis={int(len(analysis_df))}",
			"status=OK",
		]
		logger.emit_calc_block(
			block="DATA_INGESTION",
			idx=1,
			scope="BASE",
			method="GENERAL",
			steps=data_load_steps,
			result_lines=data_load_result,
		)

		unit_map = {
			"ts_server": "ms_epoch",
			"timestamp": "datetime",
			"watt": "W",
			"voltage": "V",
			"current": "A",
			"frequency": "Hz",
			"energy_kwh": "kWh",
			"pf": "ratio",
			"source": "text",
		}
		schema_steps = ["input: DataFrame columns + dtype + unit mapping"]
		for col in list(full_df.columns):
			try:
				dtype = str(full_df[col].dtype)
			except Exception:
				dtype = "unknown"
			unit = unit_map.get(col, "-")
			schema_steps.append(f"col={col} dtype={dtype} unit={unit}")
		logger.emit_calc_block(
			block="DATA_SCHEMA",
			idx=1,
			scope="BASE",
			method="GENERAL",
			steps=schema_steps,
			result_lines=[f"columns={len(full_df.columns)}", "status=OK"],
		)

		range_steps = ["input: ts_server (ms epoch)"]
		range_result: list[str] = []
		if not full_df.empty and "ts_server" in full_df.columns:
			try:
				ts = pd.to_numeric(full_df["ts_server"], errors="coerce").dropna().astype("int64").sort_values()
				range_steps.append(f"rows_ts_nonnull={int(ts.shape[0])}")
				if not ts.empty:
					min_ms = int(ts.iloc[0])
					max_ms = int(ts.iloc[-1])
					range_result.append(f"range_start={_fmt_dt_from_ms(min_ms)}")
					range_result.append(f"range_end={_fmt_dt_from_ms(max_ms)}")

					diffs = ts.diff().dropna()
					median_ms = int(diffs.median()) if not diffs.empty else 0
					gap_count = int((diffs > (2 * median_ms)).sum()) if median_ms > 0 else 0
					range_steps.append(f"median_delta_ms={median_ms}")
					range_steps.append(f"gap_count_delta_gt_2x_median={gap_count}")
					range_result.append(f"median_delta_ms={median_ms}")
					range_result.append(f"gap_count={gap_count}")
			except Exception as e:
				range_steps.append(f"error={type(e).__name__}")
				range_result.append("status=FAIL")
		else:
			range_result.append("status=EMPTY")

		logger.emit_calc_block(
			block="DATA_RANGE",
			idx=1,
			scope="BASE",
			method="GENERAL",
			steps=range_steps,
			result_lines=range_result or ["status=OK"],
		)

		clean_steps = [
			"rule: DataImporter._flatten_telemetry requires ts_server_ms and W fields",
			"rule: DataImporter._flatten_telemetry drops record when (voltage in {0,-1}) AND (pf == 0.0)",
			"rule: Preprocessor.resample_data handles missing via ffill then bfill then fillna(0)",
			"rule: Preprocessor.resample_data supports resample_method in {mean,ffill,linear}",
		]
		clean_result = ["status=OK"]
		logger.emit_calc_block(
			block="DATA_CLEAN",
			idx=1,
			scope="CAL",
			method="GENERAL",
			steps=clean_steps,
			result_lines=clean_result,
		)

		valid_steps = ["input: full_df validity checks per column"]
		valid_result: list[str] = []
		if not full_df.empty:
			valid_result.append(f"rows_total={int(len(full_df))}")
			for col in ["ts_server", "watt", "voltage", "current", "frequency", "energy_kwh", "pf"]:
				if col in full_df.columns:
					try:
						n_missing = int(pd.isna(full_df[col]).sum())
					except Exception:
						n_missing = 0
					valid_result.append(f"missing_{col}={n_missing}")
		if not analysis_df.empty:
			valid_result.append(f"rows_analysis={int(len(analysis_df))}")
		if not valid_result:
			valid_result = ["status=EMPTY"]
		else:
			valid_result.append("status=OK")
		logger.emit_calc_block(
			block="DATA_VALID",
			idx=1,
			scope="BASE",
			method="GENERAL",
			steps=valid_steps,
			result_lines=valid_result,
		)

		# ----------------------------
		# PARAM_* blocks
		# ----------------------------
		g = params.get("global", {}) if isinstance(params.get("global"), dict) else {}
		fts = params.get("fts", {}) if isinstance(params.get("fts"), dict) else {}
		ann = params.get("ann", {}) if isinstance(params.get("ann"), dict) else {}
		arima = params.get("arima", {}) if isinstance(params.get("arima"), dict) else {}

		target_var = "-"
		try:
			target_var = str(self.Param_initial_value_general_variabeltraget.currentText()).strip()
		except Exception:
			target_var = "-"

		logger.emit_calc_block(
			block="PARAM_GENERAL_SUBMIT",
			idx=1,
			scope="CAL",
			method="GENERAL",
			steps=[
				f"?target={target_var}",
				f"?split_ratio={g.get('split_ratio')}",
				f"?forecast_horizon={g.get('forecast_horizon')}",
				f"?resample_method={g.get('resample_method')}",
			],
			result_lines=["status=CAPTURED"],
		)

		g_locked = bool(getattr(self, "Param_Status_Submit_general", None).isChecked()) if getattr(self, "Param_Status_Submit_general", None) is not None else False
		logger.emit_calc_block(
			block="PARAM_GENERAL_LOCK",
			idx=1,
			scope="CAL",
			method="GENERAL",
			steps=[f"lock_general={g_locked}"],
			result_lines=[f"locked={g_locked}", "status=OK"],
		)

		logger.emit_calc_block(
			block="PARAM_FTS_SUBMIT",
			idx=1,
			scope="CAL",
			method="FTS",
			steps=[
				f"?interval={fts.get('interval')}",
				f"?partition={fts.get('partition')}",
				f"?sensitivity={fts.get('sensitivity')}",
				f"?sensitivity_locked={fts.get('sensitivity_locked')}",
			],
			result_lines=["status=CAPTURED"],
		)

		logger.emit_calc_block(
			block="PARAM_ANN_SUBMIT",
			idx=1,
			scope="CAL",
			method="ANN",
			steps=[
				f"?epoch={ann.get('epoch')}",
				f"?neuron={ann.get('neuron')}",
				f"?layers={ann.get('layers')}",
				f"?lr={ann.get('lr')}",
			],
			result_lines=["status=CAPTURED"],
		)

		logger.emit_calc_block(
			block="PARAM_ARIMA_SUBMIT",
			idx=1,
			scope="CAL",
			method="ARIMA",
			steps=[
				f"?seasonal={arima.get('seasonal')}",
				f"?order=({arima.get('p')},{arima.get('d')},{arima.get('q')})",
				f"?seasonal_order=({arima.get('P')},{arima.get('D')},{arima.get('Q')},{arima.get('s')})",
			],
			result_lines=["status=CAPTURED"],
		)

		# All lock status (ringkas, sesuai gate start analysis)
		fts_locked = bool(getattr(self, "Param_Status_Submit_FTS", None).isChecked()) if getattr(self, "Param_Status_Submit_FTS", None) is not None else False
		ann_locked = bool(getattr(self, "Param_Status_Submit_ANN", None).isChecked()) if getattr(self, "Param_Status_Submit_ANN", None) is not None else False
		seasonal = bool(getattr(self, "Param_Status_Submit_ARIMA_seasonal", None).isChecked()) if getattr(self, "Param_Status_Submit_ARIMA_seasonal", None) is not None else False
		nonseasonal = bool(getattr(self, "Param_Status_Submit_ARIMA_nonseasonal", None).isChecked()) if getattr(self, "Param_Status_Submit_ARIMA_nonseasonal", None) is not None else False
		arima_locked = bool(seasonal ^ nonseasonal)
		all_locked = bool(g_locked and fts_locked and ann_locked and arima_locked)
		data_ready = bool(self.raw_data is not None and len(self.raw_data) > 0)

		logger.emit_calc_block(
			block="PARAM_ALL_LOCK",
			idx=1,
			scope="CAL",
			method="GENERAL",
			steps=[
				f"lock_general={g_locked}",
				f"lock_fts={fts_locked}",
				f"lock_ann={ann_locked}",
				f"lock_arima_seasonal={seasonal}",
				f"lock_arima_nonseasonal={nonseasonal}",
				f"data_ready={data_ready}",
			],
			result_lines=[f"all_locked={all_locked}", "status=OK"],
		)

	def _emit_calc_blocks_run5_home(self) -> None:
		"""RUN-5 Ex_Plan-6: emit CALC blocks untuk HOME (Average & Daily).

		Target blok (Doc_for_Ex_Plan-6: 8.2 & 8.3):
		- HOME_AVG_RANGE/COUNT/V/A/W/E/HZ/PF/SUMMARY
		- HOME_DAILY_GROUP/COUNT/METRIC/SUMMARY
		"""

		logger = getattr(self, "logger", None)
		if logger is None or not hasattr(logger, "emit_calc_block"):
			return

		run_guid = None
		try:
			run_guid = logger.get_run_guid() if hasattr(logger, "get_run_guid") else None
		except Exception:
			run_guid = None
		if not run_guid:
			return

		if getattr(self, "_calc_home_emitted_guid", None) == run_guid:
			return

		def _fmt_ts(ts) -> str:
			try:
				return pd.to_datetime(ts).strftime("%Y-%m-%d %H:%M:%S")
			except Exception:
				return str(ts)

		def _safe_float(x) -> float:
			try:
				return float(x)
			except Exception:
				return 0.0

		def _series_stats(series: pd.Series) -> dict:
			s = pd.to_numeric(series, errors="coerce")
			n_total = int(len(s))
			n_valid = int(s.notna().sum())
			n_missing = int(n_total - n_valid)
			if n_valid <= 0:
				return {
					"n_total": n_total,
					"n_valid": 0,
					"n_missing": n_missing,
					"min": 0.0,
					"max": 0.0,
					"mean": 0.0,
					"std": 0.0,
					"sum": 0.0,
				}
			return {
				"n_total": n_total,
				"n_valid": n_valid,
				"n_missing": n_missing,
				"min": _safe_float(s.min()),
				"max": _safe_float(s.max()),
				"mean": _safe_float(s.mean()),
				"std": _safe_float(s.std(ddof=0)),
				"sum": _safe_float(s.sum()),
			}

		def _sample_head_tail(df_in: pd.DataFrame, *, n: int = 3) -> list[str]:
			if df_in is None or df_in.empty:
				return ["sample: EMPTY"]
			cols = [c for c in ["ts", "voltage", "current", "watt", "frequency", "pf", "energy_kwh"] if c in df_in.columns]

			def _fmt_row(row) -> str:
				try:
					ts_val = _fmt_ts(row.get("ts"))
					parts = [f"ts={ts_val}"]
					if "voltage" in cols:
						parts.append(f"V={_safe_float(row.get('voltage')):.3f}")
					if "current" in cols:
						parts.append(f"A={_safe_float(row.get('current')):.3f}")
					if "watt" in cols:
						parts.append(f"W={_safe_float(row.get('watt')):.3f}")
					if "frequency" in cols:
						parts.append(f"Hz={_safe_float(row.get('frequency')):.3f}")
					if "pf" in cols:
						parts.append(f"PF={_safe_float(row.get('pf')):.3f}")
					if "energy_kwh" in cols:
						parts.append(f"E_kwh={_safe_float(row.get('energy_kwh')):.6f}")
					return "sample: " + " | ".join(parts)
				except Exception:
					return "sample: <unavailable>"

			head = df_in[cols].head(n)
			tail = df_in[cols].tail(n)
			out: list[str] = [f"sample_head_n={int(len(head))}"]
			out.extend([_fmt_row(r) for r in head.to_dict(orient="records")])
			out.append(f"sample_tail_n={int(len(tail))}")
			out.extend([_fmt_row(r) for r in tail.to_dict(orient="records")])
			return out

		df = self._query_raw_df()
		if df is None or df.empty:
			# HOME UI akan menampilkan 0; tetap tulis blok agar traceable.
			logger.emit_calc_block(
				block="HOME_AVG_RANGE",
				idx=1,
				scope="BASE",
				method="GENERAL",
				steps=["input: DBManager.fetch_data() -> _query_raw_df()", "status: no rows available"],
				result_lines=["rows_total=0", "status=EMPTY"],
			)
			logger.emit_calc_block(
				block="HOME_DAILY_GROUP",
				idx=1,
				scope="BASE",
				method="GENERAL",
				steps=["input: DBManager.fetch_data() -> _query_raw_df()", "status: no rows available"],
				result_lines=["rows_total=0", "status=EMPTY"],
			)
			self._calc_home_emitted_guid = run_guid
			return

		# ----------------------------
		# Average (8.2) - mengikuti logika _refresh_home_dashboard
		# ----------------------------
		start_ts = df["ts"].iloc[0]
		end_ts = df["ts"].iloc[-1]
		start_sel = None
		end_sel = None
		try:
			if self.select_avg_tanggal_awal is not None and self.select_avg_tanggal_awal.dateTime().isValid():
				start_sel = pd.to_datetime(self.select_avg_tanggal_awal.dateTime().toPyDateTime())
			if self.select_avg_tanggal_akhir is not None and self.select_avg_tanggal_akhir.dateTime().isValid():
				end_sel = pd.to_datetime(self.select_avg_tanggal_akhir.dateTime().toPyDateTime())
		except Exception:
			start_sel, end_sel = None, None
		if start_sel is not None:
			start_ts = start_sel
		if end_sel is not None:
			end_ts = end_sel
		if end_ts < start_ts:
			start_ts, end_ts = end_ts, start_ts

		df_avg = df[(df["ts"] >= start_ts) & (df["ts"] <= end_ts)].copy()
		avg_fallback = False
		if df_avg.empty:
			df_avg = df.copy()
			avg_fallback = True

		logger.emit_calc_block(
			block="HOME_AVG_RANGE",
			idx=1,
			scope="BASE",
			method="GENERAL",
			steps=[
				"input: df = _query_raw_df() sorted by ts",
				f"range_selected_start={_fmt_ts(start_ts)}",
				f"range_selected_end={_fmt_ts(end_ts)}",
				"rule: clamp (swap) if end < start",
				"filter: df_avg = df[(ts>=start) & (ts<=end)]",
				f"fallback_to_full_df={avg_fallback}",
				*_sample_head_tail(df_avg, n=3),
			],
			result_lines=[
				f"rows_total={int(len(df))}",
				f"rows_avg={int(len(df_avg))}",
				f"range_used_start={_fmt_ts(df_avg['ts'].iloc[0])}",
				f"range_used_end={_fmt_ts(df_avg['ts'].iloc[-1])}",
				"status=OK",
			],
		)

		miss_lines: list[str] = []
		for col in ["voltage", "current", "watt", "frequency", "pf", "energy_kwh"]:
			if col not in df_avg.columns:
				continue
			try:
				miss_lines.append(f"missing_{col}={int(pd.isna(df_avg[col]).sum())}")
			except Exception:
				miss_lines.append(f"missing_{col}=0")
		logger.emit_calc_block(
			block="HOME_AVG_COUNT",
			idx=1,
			scope="BASE",
			method="GENERAL",
			steps=["input: df_avg from HOME_AVG_RANGE#01", "note: mean() ignores NaN by default"],
			result_lines=[f"rows={int(len(df_avg))}", *miss_lines, "status=OK"],
		)

		v_stats = _series_stats(df_avg["voltage"])
		a_stats = _series_stats(df_avg["current"])
		w_stats = _series_stats(df_avg["watt"])
		hz_stats = _series_stats(df_avg["frequency"])
		pf_stats = _series_stats(df_avg["pf"])

		logger.emit_calc_block(
			block="HOME_AVG_V",
			idx=1,
			scope="BASE",
			method="GENERAL",
			steps=[
				"input: voltage (V) from df_avg",
				f"formula: Avg.Period.V = sum(V_valid) / count(V_valid)",
				f"n_total={v_stats['n_total']} n_valid={v_stats['n_valid']} n_missing={v_stats['n_missing']}",
			],
			result_lines=[
				f"‘V={v_stats['mean']:.6f} V",
				f"count={v_stats['n_valid']}",
				"status=OK",
			],
		)

		logger.emit_calc_block(
			block="HOME_AVG_A",
			idx=1,
			scope="BASE",
			method="GENERAL",
			steps=[
				"input: current (A) from df_avg",
				f"formula: Avg.Period.A = sum(A_valid) / count(A_valid)",
			],
			result_lines=[
				f"‘A={a_stats['mean']:.6f} A",
				f"count={a_stats['n_valid']}",
				"status=OK",
			],
		)

		logger.emit_calc_block(
			block="HOME_AVG_W",
			idx=1,
			scope="BASE",
			method="GENERAL",
			steps=[
				"input: watt (W) from df_avg",
				f"n_total={w_stats['n_total']} n_valid={w_stats['n_valid']} n_missing={w_stats['n_missing']}",
				"op: W_avg = mean(watt_i) over valid (non-NaN) rows",
			],
			result_lines=[
				f"‘W={w_stats['mean']:.6f} W",
				f"formula: Avg.Period.W = sum(W_valid) / count(W_valid)",
			],
		)

		energy_steps: list[str] = [
			"input: df_avg with ts (datetime) + watt (W) + optional energy_kwh (kWh)",
			"rule: if energy_kwh has >=2 valid values -> E = last - first (clamped >=0)",
			"else: E = sum(watt * dt_hours)/1000 (numerical integration)",
		]
		energy_method = "INTEGRATE_WATT_DT"
		energy_total_kwh = 0.0
		try:
			energy_vals = df_avg["energy_kwh"].dropna() if "energy_kwh" in df_avg.columns else pd.Series([], dtype=float)
			if len(energy_vals) >= 2:
				energy_method = "SENSOR_DELTA"
				e_first = float(energy_vals.iloc[0])
				e_last = float(energy_vals.iloc[-1])
				delta = max(0.0, e_last - e_first)
				
				energy_total_kwh = delta
				energy_steps.append(f"E_first={e_first:.6f} kWh")
				energy_steps.append(f"E_last={e_last:.6f} kWh")
				energy_steps.append(f"delta={delta:.6f} kWh")
				energy_steps.append("formula: E = E_last - E_first")
			else:
				dt_h = df_avg["ts"].diff().dt.total_seconds().fillna(0) / 3600.0
				energy_chunk = (df_avg["watt"].fillna(0) * dt_h) / 1000.0
				energy_total_kwh = energy_chunk.sum()
				energy_steps.append(f"dt_hours_total={dt_h.sum():.6f} h")
				energy_steps.append("formula: E = sum(Watt * dt_hours) / 1000")
		except Exception as e:
			energy_steps.append(f"error_calc_energy: {e}")
			energy_total_kwh = 0.0

		logger.emit_calc_block(
			block="HOME_AVG_E",
			idx=1,
			scope="BASE",
			method="GENERAL",
			steps=energy_steps,
			result_lines=[
				f"‘E={energy_total_kwh:.6f} kWh",
				f"method={energy_method}",
				"status=OK",
			],
		)

		logger.emit_calc_block(
			block="HOME_AVG_HZ",
			idx=1,
			scope="BASE",
			method="GENERAL",
			steps=[
				"input: frequency (Hz) from df_avg",
				f"n_total={hz_stats['n_total']} n_valid={hz_stats['n_valid']} n_missing={hz_stats['n_missing']}",
				"op: Hz_avg = mean(frequency_i) over valid (non-NaN) rows",
			],
			result_lines=[
				f"‘Hz={hz_stats['mean']:.6f} Hz",
				f"count={hz_stats['n_valid']}",
				f"formula: Avg.Period.F = sum(F_valid) / count(F_valid)",
				"status=OK",
			],
		)

		logger.emit_calc_block(
			block="HOME_AVG_PF",
			idx=1,
			scope="BASE",
			method="GENERAL",
			steps=[
				"input: pf from df_avg",
				f"n_total={pf_stats['n_total']} n_valid={pf_stats['n_valid']} n_missing={pf_stats['n_missing']}",
				"op: PF_avg = mean(pf_i) over valid (non-NaN) rows",
			],
			result_lines=[
				f"‘PF={pf_stats['mean']:.6f}",
				f"count={pf_stats['n_valid']}",
				f"formula: Avg.Period.PF = sum(PF_valid) / count(PF_valid)",
				"status=OK",
			],
		)

		logger.emit_calc_block(
			block="HOME_SUMMARY_REFRESH",
			idx=1,
			scope="BASE",
			method="GENERAL",
			steps=[
				"Aggregating all HOME_AVG_* blocks",
				"note: E is total energy in selected range (kWh), not mean",
			],
			result_lines=[
				f"rows={int(len(df_avg))}",
				f"‘V={v_stats['mean']:.6f} V",
				f"‘A={a_stats['mean']:.6f} A",
				f"‘W={w_stats['mean']:.6f} W",
				f"‘kWh={energy_total_kwh:.6f} kWh",
				f"‘Hz={hz_stats['mean']:.6f} Hz",
				f"‘PF={pf_stats['mean']:.6f}",
				"status=OK",
			],
		)

		# ----------------------------
		# Daily (8.3) - mengikuti logika _refresh_home_dashboard
		# ----------------------------
		chosen = end_ts
		try:
			if self.select_daily_tanggal_awal is not None:
				chosen = pd.to_datetime(self.select_daily_tanggal_awal.dateTime().toPyDateTime())
		except Exception:
			chosen = end_ts
		chosen_day = pd.to_datetime(chosen).normalize()
		df_daily = df[(df["ts"] >= chosen_day) & (df["ts"] < chosen_day + pd.Timedelta(days=1))].copy()
		daily_fallback = False
		if df_daily.empty:
			last_day = pd.to_datetime(df["ts"].iloc[-1]).normalize()
			df_daily = df[(df["ts"] >= last_day) & (df["ts"] < last_day + pd.Timedelta(days=1))].copy()
			chosen_day = last_day
			daily_fallback = True

		logger.emit_calc_block(
			block="HOME_DAILY_GROUP",
			idx=1,
			scope="BASE",
			method="GENERAL",
			steps=[
				"input: df = _query_raw_df() sorted by ts",
				f"date_selected={pd.to_datetime(chosen).strftime('%Y-%m-%d')}",
				"rule: chosen_day = normalize(date_selected) (00:00:00)",
				"filter: df_daily = df[(ts>=chosen_day) & (ts<chosen_day+1d)]",
				f"fallback_to_last_day={daily_fallback}",
				*_sample_head_tail(df_daily, n=3),
			],
			result_lines=[
				f"day_used={pd.to_datetime(chosen_day).strftime('%Y-%m-%d')}",
				f"rows_daily={int(len(df_daily))}",
				"status=OK",
			],
		)

		daily_miss: list[str] = []
		for col in ["voltage", "current", "watt", "frequency", "pf", "energy_kwh"]:
			if col not in df_daily.columns:
				continue
			try:
				daily_miss.append(f"missing_{col}={int(pd.isna(df_daily[col]).sum())}")
			except Exception:
				daily_miss.append(f"missing_{col}=0")
		logger.emit_calc_block(
			block="HOME_DAILY_COUNT",
			idx=1,
			scope="BASE",
			method="GENERAL",
			steps=["input: df_daily from HOME_DAILY_GROUP#01", "note: mean() ignores NaN by default"],
			result_lines=[f"rows={int(len(df_daily))}", *daily_miss, "status=OK"],
		)

		if df_daily.empty:
			dv_stats = da_stats = dw_stats = dhz_stats = dpf_stats = {
				"n_total": 0,
				"n_valid": 0,
				"n_missing": 0,
				"min": 0.0,
				"max": 0.0,
				"mean": 0.0,
				"std": 0.0,
				"sum": 0.0,
			}
			daily_energy_total_kwh = 0.0
		else:
			dv_stats = _series_stats(df_daily["voltage"])
			da_stats = _series_stats(df_daily["current"])
			dw_stats = _series_stats(df_daily["watt"])
			dhz_stats = _series_stats(df_daily["frequency"])
			dpf_stats = _series_stats(df_daily["pf"])
			daily_energy_total_kwh = self._energy_kwh(df_daily)

		logger.emit_calc_block(
			block="HOME_DAILY_METRIC",
			idx=1,
			scope="BASE",
			method="GENERAL",
			steps=[
				"input: df_daily (1 day) from HOME_DAILY_GROUP#01",
				"op: daily V/A/W/Hz/PF = mean(series) over valid rows (NaN ignored)",
				"op: daily E(kWh) uses same definition as _energy_kwh(df)",
			],
			result_lines=[
				f"‘V={dv_stats['mean']:.6f} V",
				f"‘A={da_stats['mean']:.6f} A",
				f"‘W={dw_stats['mean']:.6f} W",
				f"‘kWh={_safe_float(daily_energy_total_kwh):.6f} kWh",
				f"‘Hz={dhz_stats['mean']:.6f} Hz",
				f"‘PF={dpf_stats['mean']:.6f}",
				"status=OK",
			],
		)

		logger.emit_calc_block(
			block="HOME_DAILY_SUMMARY",
			idx=1,
			scope="BASE",
			method="GENERAL",
			steps=[
				"input: outputs from HOME_DAILY_* blocks",
				"note: E is total energy in the day (kWh), not mean",
			],
			result_lines=[
				f"day={pd.to_datetime(chosen_day).strftime('%Y-%m-%d')}",
				f"rows={int(len(df_daily))}",
				f"‘V={dv_stats['mean']:.6f} V",
				f"‘A={da_stats['mean']:.6f} A",
				f"‘W={dw_stats['mean']:.6f} W",
				f"‘kWh={_safe_float(daily_energy_total_kwh):.6f} kWh",
				f"‘Hz={dhz_stats['mean']:.6f} Hz",
				f"‘PF={dpf_stats['mean']:.6f}",
				"status=OK",
			],
		)

		self._calc_home_emitted_guid = run_guid

	# ------------------------------------------------------------------
	# Analisis
	# ------------------------------------------------------------------

	# ---------------------- Table Model for pandas ----------------------
	class _PandasModel(QAbstractTableModel):
		def __init__(self, df: pd.DataFrame) -> None:
			super().__init__()
			self._df = df.reset_index(drop=True)

		def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # type: ignore[override]
			return 0 if self._df is None else len(self._df)

		def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # type: ignore[override]
			return 0 if self._df is None else len(self._df.columns)

		def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):  # type: ignore[override]
			if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
				return None
			val = self._df.iat[index.row(), index.column()]
			return "" if pd.isna(val) else str(val)

		def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):  # type: ignore[override]
			if role != Qt.ItemDataRole.DisplayRole:
				return None
			if orientation == Qt.Orientation.Horizontal:
				return list(self._df.columns)[section]
			return section + 1

	def _init_plot_canvas(self) -> None:
		"""Inisialisasi canvas hasil analisis di Resume -> Graphic (R4)."""

		self._result_charts: dict[str, InteractiveResultChart] = {}

		# FTS chart
		view_fts = getattr(self, "graphicsView_FTS", None)
		if view_fts is not None:
			checkboxes_fts = {
				"ma": getattr(self, "checkBox_fts_graph_MA", None),
				"naive": getattr(self, "checkBox_fts_graph_NAIVE", None),
				"fts": getattr(self, "checkBox_fts_graph_FTS", None),
				"actual": getattr(self, "checkBox_fts_graph_AKTUAL", None),
			}
			labels_fts = {
				"ma": "MA",
				"naive": "Naive",
				"fts": "FTS",
				"actual": "Aktual",
			}
			colors_fts = {
				"ma": "#f39c12",
				"naive": "#7f8c8d",
				"fts": "#3498db",
				"actual": "#ecf0f1",
			}
			self._result_charts["fts"] = InteractiveResultChart(
				view_fts, checkboxes_fts, labels_fts, colors_fts, logger=self.logger
			)

		# ANN chart
		view_ann = getattr(self, "graphicsView_ANN", None)
		if view_ann is not None:
			checkboxes_ann = {
				"pred": getattr(self, "checkBox_ann_graph_PREDIKSI", None),
				"actual": getattr(self, "checkBox_ann_graph_AKTUAL", None),
			}
			labels_ann = {"pred": "Prediksi", "actual": "Aktual"}
			colors_ann = {"pred": "#2ecc71", "actual": "#ecf0f1"}
			self._result_charts["ann"] = InteractiveResultChart(
				view_ann, checkboxes_ann, labels_ann, colors_ann, logger=self.logger
			)

		# ARIMA chart
		view_arima = getattr(self, "graphicsView_ARIMA", None)
		if view_arima is not None:
			checkboxes_arima = {
				"pred": getattr(self, "checkBox_arima_graph_Prediksi", None),
				"actual": getattr(self, "checkBox_arima_graph_Aktual", None),
			}
			labels_arima = {"pred": "Prediksi", "actual": "Aktual"}
			colors_arima = {"pred": "#e74c3c", "actual": "#ecf0f1"}
			self._result_charts["arima"] = InteractiveResultChart(
				view_arima, checkboxes_arima, labels_arima, colors_arima, logger=self.logger
			)

		for chart_key, chart in self._result_charts.items():
			for checkbox in chart.checkboxes.values():
				if checkbox is not None:
					checkbox.setChecked(True)

	def _init_home_plot_canvases(self) -> None:
		"""Siapkan Matplotlib canvas untuk tab Home (Average & Daily) agar interaktif.

		Canvas + toolbar akan ditambahkan ke parent masing-masing QGraphicsView,
		lalu QGraphicsView disembunyikan.
		"""

		try:
			# Average
			if self.graphic_HOME_average_1 is not None:
				parent = self.graphic_HOME_average_1.parentWidget()
				from PyQt6.QtWidgets import QVBoxLayout
				layout = parent.layout() or QVBoxLayout(parent)
				parent.setLayout(layout)
				self.home_avg_fig = Figure(figsize=(7, 3.8), dpi=100)
				self.home_avg_canvas = FigureCanvasQTAgg(self.home_avg_fig)
				self.home_avg_ax = self.home_avg_fig.add_subplot(111)
				self.home_avg_toolbar = NavigationToolbar2QT(self.home_avg_canvas, parent)
				if self.graphic_HOME_average_1.isVisible():
					self.graphic_HOME_average_1.hide()
				layout.addWidget(self.home_avg_toolbar)
				layout.addWidget(self.home_avg_canvas)

			# Daily
			if self.graphic_HOME_daily_2 is not None:
				parent2 = self.graphic_HOME_daily_2.parentWidget()
				from PyQt6.QtWidgets import QVBoxLayout
				layout2 = parent2.layout() or QVBoxLayout(parent2)
				parent2.setLayout(layout2)
				self.home_daily_fig = Figure(figsize=(7, 3.8), dpi=100)
				self.home_daily_canvas = FigureCanvasQTAgg(self.home_daily_fig)
				self.home_daily_ax = self.home_daily_fig.add_subplot(111)
				self.home_daily_toolbar = NavigationToolbar2QT(self.home_daily_canvas, parent2)
				if self.graphic_HOME_daily_2.isVisible():
					self.graphic_HOME_daily_2.hide()
				layout2.addWidget(self.home_daily_toolbar)
				layout2.addWidget(self.home_daily_canvas)
		except Exception as e:
			self.logger.log("ERROR", f"Init Home canvases failed: {e}")

	def _init_interactive_charts(self) -> None:
		"""Initialize 2 interactive charts: Average tab 2 & Daily tab 2 (RUN 4)."""
		try:
			# Chart 1: Average Tab 2 (graphic_HOME_average_1)
			checkboxes_avg = {
				'voltage': self.checkBox_avg_tegangan,      # Tegangan
				'current': self.checkBox_avg_arus,      # Arus
				'watt': self.checkBox_avg_daya,         # Daya
				'energy_kwh': self.checkBox_avg_energi,   # Energi
				'frequency': self.checkBox_avg_frekuensi,    # Frekuensi
				'pf': self.checkBox_avg_pf           # Power Factor
			}
			
			if self.graphic_HOME_average_1 is not None:
				self.chart_average = InteractiveChartWidget(
					graphics_view=self.graphic_HOME_average_1,
					checkboxes=checkboxes_avg,
					data_source_callback=self._get_data_for_average_chart,
					logger=self.logger
				)
				if not getattr(self, "_startup_in_progress", False):
					self.logger.log("INFO", "Average interactive chart initialized")
			else:
				self.chart_average = None
			
			# Chart 2: Daily Tab 2 (graphic_HOME_daily_2)
			checkboxes_daily = {
				'voltage': self.checkBox_daily_tegangan,
				'current': self.checkBox_daily_arus,
				'watt': self.checkBox_daily_daya,
				'energy_kwh': self.checkBox_daily_energi,
				'frequency': self.checkBox_daily_frekuensi,
				'pf': self.checkBox_daily_pf
			}
			
			if self.graphic_HOME_daily_2 is not None:
				self.chart_daily = InteractiveChartWidget(
					graphics_view=self.graphic_HOME_daily_2,
					checkboxes=checkboxes_daily,
					data_source_callback=self._get_data_for_daily_chart,
					logger=self.logger
				)
				if not getattr(self, "_startup_in_progress", False):
					self.logger.log("INFO", "Daily interactive chart initialized")
			else:
				self.chart_daily = None
			
			# Set default: ALL checkboxes CHECKED
			for checkbox in list(checkboxes_avg.values()) + list(checkboxes_daily.values()):
				if checkbox is not None:
					checkbox.blockSignals(True)
					checkbox.setChecked(True)
					checkbox.blockSignals(False)
					
		except Exception as e:
			self.logger.log("ERROR", f"Failed to initialize interactive charts: {e}")

	@pyqtSlot()
	def start_analysis(self) -> None:
		"""Memulai proses analisis di background thread."""

		if self.raw_data is None or self.raw_data.empty:
			self.logger.log_event(
				lvl1="WARN",
				lvl2="MAIN",
				lvl3="CAL",
				lvl4="GENERAL",
				evt=EVT.UI_CLICK_START_ANALYSIS,
				route_to=["HOME", "RESUME"],
				fields=["status=BLOCKED"],
				cause="no_data_loaded",
				result="status=BLOCKED",
			)
			QMessageBox.warning(self, "Error", "No Data Loaded!")
			return

		params = self.get_ui_params()
		if not params:
			return
		
		# PF-01: Contract-Required Validation Implementation
		# Add target variable validation sesuai contract specification
		target_variable = params.get('global', {}).get('target_variable')
		if not target_variable:
			self.logger.log_event(
				lvl1="ERROR",
				lvl2="MAIN", 
				lvl3="CAL",
				lvl4="PRE_FLIGHT",
				evt=EVT.UI_CLICK_START_ANALYSIS,
				route_to=["HOME", "RESUME"],
				fields=["status=BLOCKED"],
				cause="target_variable_missing",
				result="status=BLOCKED"
			)
			QMessageBox.critical(self, "Pre-Flight Check Failed", "Target variable not found in parameters!")
			return
		
		# PF-02: Target Variable Existence Check
		if target_variable not in self.raw_data.columns:
			available_cols = list(self.raw_data.columns)
			error_msg = f"Target variable '{target_variable}' not found in data.\n\nAvailable columns: {', '.join(available_cols)}"
			self.logger.log_event(
				lvl1="ERROR",
				lvl2="MAIN",
				lvl3="CAL", 
				lvl4="PRE_FLIGHT",
				evt=EVT.UI_CLICK_START_ANALYSIS,
				route_to=["HOME", "RESUME"],
				fields=["status=BLOCKED"],
				cause=f"target_variable_not_found:{target_variable}",
				result="status=BLOCKED"
			)
			QMessageBox.critical(self, "Pre-Flight Check Failed", error_msg)
			return
		
		# PF-03: Data Sufficiency Validation
		target_series = self.raw_data[target_variable]
		non_null_count = target_series.count()
		total_count = len(target_series)
		min_threshold = 10  # Minimum required non-null values
		
		if non_null_count < min_threshold:
			error_msg = f"Insufficient data for target variable '{target_variable}': {non_null_count}/{total_count} valid values (minimum {min_threshold} required)"
			self.logger.log_event(
				lvl1="ERROR",
				lvl2="MAIN",
				lvl3="CAL",
				lvl4="PRE_FLIGHT", 
				evt=EVT.UI_CLICK_START_ANALYSIS,
				route_to=["HOME", "RESUME"],
				fields=["status=BLOCKED"],
				cause=f"insufficient_data:{target_variable}:{non_null_count}/{total_count}",
				result="status=BLOCKED"
			)
			QMessageBox.critical(self, "Pre-Flight Check Failed", error_msg)
			return
		
		# PF-04: Contract Compliance Logging
		self.logger.log("INFO", f"✅ Pre-flight check passed: target_variable='{target_variable}' ({non_null_count}/{total_count} valid)")
		
		# E2E-02: Contract Compliance Testing Validation
		self.logger.log("INFO", f"🔍 E2E-02 CONTRACT VALIDATION: Pre-flight_check=PASSED | Target_validation=OK | Data_sufficiency=OK | Contract_compliance=ENFORCED")

		analysis_df = self._get_analysis_raw_df()
		if analysis_df is None or analysis_df.empty:
			self.logger.log_event(
				lvl1="WARN",
				lvl2="MAIN",
				lvl3="CAL",
				lvl4="GENERAL",
				evt=EVT.UI_CLICK_START_ANALYSIS,
				route_to=["HOME", "RESUME"],
				fields=["status=BLOCKED"],
				cause="no_data_in_selected_range",
				result="status=BLOCKED",
			)
			QMessageBox.warning(
				self,
				"No Data in Range",
				"Tidak ada data pada rentang tanggal Average yang dipilih.",
			)
			return

		# RUN-1 Ex_Plan-6: buat GUID run dan siapkan artefak log per-run.
		try:
			run_ctx = RunContext.new()
			self._last_run_guid = run_ctx.guid
			self.logger.start_run(run_ctx)
		except Exception:
			# Tidak boleh memblokir start analysis bila ada masalah pada artefak log.
			pass

		self.logger.log_event(
			lvl1="INIT",
			lvl2="MAIN",
			lvl3="CAL",
			lvl4="GENERAL",
			evt=EVT.UI_CLICK_START_ANALYSIS,
			route_to=["HOME", "RESUME"],
			fields=["status=START"],
		)

		# RUN-4 Ex_Plan-6: CALC blocks (DATA_* + PARAM_*).
		try:
			self._emit_calc_blocks_run4(params=params, analysis_df=analysis_df)
		except Exception:
			pass

		# RUN-5 Ex_Plan-6: CALC blocks (HOME Average/Daily).
		try:
			self._emit_calc_blocks_run5_home()
		except Exception:
			pass

		# Simpan konfigurasi terakhir
		self.config_mgr.save_config(params)
		self._last_run_params = params
		self.logger.log("INFO", "[pipeli] ===== START RUN =====")
		self.logger.log("INIT", "Starting new analysis run with current configuration.")
		try:
			df_src = analysis_df
			if not df_src.empty:
				start_ts = pd.to_datetime(df_src["ts_server"].iloc[0], unit="ms")
				end_ts = pd.to_datetime(df_src["ts_server"].iloc[-1], unit="ms")
				self.logger.log(
					"INFO",
					f"[source] Rows={len(df_src)} | Range={start_ts} -> {end_ts}",
				)
		except Exception:
			pass
		try:
			glob = params.get("global", {})
			fts = params.get("fts", {})
			ann = params.get("ann", {})
			arima = params.get("arima", {})
			self.logger.log(
				"INFO",
				(
					"[param] "
					f"Split={glob.get('split_ratio', 0) * 100:.0f}% | "
					f"Horizon={glob.get('forecast_horizon', 1)}"
				),
			)
			self.logger.log(
				"INFO",
				(
					"[param] FTS interval="
					f"{fts.get('interval')} | "
					f"sensitivity={fts.get('sensitivity')} | "
					f"valid_lock={fts.get('sensitivity_locked')}"
				),
			)
			self.logger.log(
				"INFO",
				(
					"[param] ANN "
					f"epochs={ann.get('epoch')} | "
					f"neurons={ann.get('neuron')} | "
					f"layers={ann.get('layers')} | "
					f"lr={ann.get('lr')}"
				),
			)
			arima_mode = "seasonal" if arima.get("seasonal") else "nonseasonal"
			self.logger.log(
				"INFO",
				(
					"[param] ARIMA "
					f"mode={arima_mode} | "
					f"order=({arima.get('p')},{arima.get('d')},{arima.get('q')}) | "
					f"s={arima.get('s')}"
				),
			)
		except Exception:
			pass

		# Siapkan worker & dialog
		self.worker = CalculationWorker(analysis_df, params)
		self.progress_dlg = ProgressDialog(self)
		self.start_analysis_PB.setEnabled(False)
		self.analysis_results = None
		
		# Routing sinyal worker
		self.worker.sig_step_update.connect(self.progress_dlg.update_progress)
		self.worker.sig_finished.connect(self.on_analysis_finished)
		self.worker.sig_error.connect(self.on_analysis_error)
		self.worker.sig_cancelled.connect(self.on_analysis_cancelled)
		self.worker.sig_log.connect(self.logger.log)
		# Jika user menekan Cancel di dialog, anggap sebagai permintaan cancel pipeline
		self.progress_dlg.rejected.connect(self.cancel_analysis)

		self.progress_dlg.show()
		self.worker.start()

	@pyqtSlot(dict)
	def on_analysis_finished(self, results: dict) -> None:
		"""Dipanggil saat worker selesai 100%."""

		self.analysis_results = results
		if self.progress_dlg is not None:
			self.progress_dlg.execution_finished()
		self.logger.log("SUCCESS", "Analysis pipeline finished. Rendering results...")
		# Render grafik & resume text (basic)
		try:
			self.plot_results(results)
			self.update_resume_text(results)
			self._update_metrics_labels(results)
		except Exception as e:  # pragma: no cover - fallback UI
			self.logger.log("ERROR", f"Failed to render results: {e}")

		try:
			self.logger.log("INFO", "[eval] ===== Evaluasi Prediksi =====")
			for method in ["fts", "ann", "arima"]:
				if method in results:
					m = results[method]["metrics"]
					self.logger.log(
						"RESULT",
						(
							f"[eval] {method.upper()} "
							f"MAE={m['mae']:.6f} | "
							f"RMSE={m['rmse']:.6f} | "
							f"MAPE={m['mape']:.4f}%"
						),
					)
		except Exception:
			pass

		try:
			df_live = self._query_raw_df()
			if not df_live.empty:
				last = df_live.iloc[-1]
				self.logger.log(
					"INFO",
					(
						"[resume] Live: "
						f"V={float(last['voltage']):.2f} | "
						f"I={float(last['current']):.2f} | "
						f"P={float(last['watt']):.2f} W | "
						f"PF={float(last['pf']):.2f} | "
						f"F={float(last['frequency']):.2f} Hz"
					),
				)
		except Exception:
			pass

		try:
			forecast_line = []
			for method in ["fts", "ann", "arima"]:
				forecast = results.get(method, {}).get("forecast", [])
				if forecast:
					forecast_line.append(f"{method.upper()}={float(forecast[0]):.4f} W")
			if forecast_line:
				self.logger.log(
					"INFO",
					f"[resume] Prediksi t+1: {' | '.join(forecast_line)}",
				)
		except Exception:
			pass

		# Persist summary ke database (experiment_log & experiment_results)
		try:
			self._persist_experiment_to_db(results)
		except Exception as e:  # pragma: no cover - tidak boleh jatuhkan UI
			self.logger.log("ERROR", f"Failed to persist experiment to DB: {e}")

		self.logger.log("INFO", "[pipeli] ===== END RUN (OK) =====")
		self.start_analysis_PB.setEnabled(True)
		self.worker = None
		QMessageBox.information(self, "Success", "Analysis complete!")

	@pyqtSlot(str)
	def on_analysis_error(self, msg: str) -> None:
		"""Menangani error dari thread worker."""

		if self.progress_dlg is not None:
			self.progress_dlg.reject()
		self.logger.log("ERROR", f"Analysis failed: {msg}")
		self.logger.log("INFO", "[pipeli] ===== END RUN (FAILED) =====")
		self.start_analysis_PB.setEnabled(True)
		self.worker = None
		QMessageBox.critical(self, "Analysis Failed", f"Error occurred:\n{msg}")

	@pyqtSlot()
	def on_analysis_cancelled(self) -> None:
		"""Dipanggil saat worker membatalkan eksekusi karena user menekan Cancel."""

		if self.progress_dlg is not None:
			self.progress_dlg.reject()
		self.logger.log("INFO", "Analysis cancelled by user.")
		self.logger.log("INFO", "[pipeli] ===== END RUN (CANCELLED) =====")
		self.start_analysis_PB.setEnabled(True)
		self.worker = None
		QMessageBox.information(self, "Cancelled", "Analysis has been cancelled by user.")

	def plot_results(self, results: dict) -> None:
		"""Render grafik perbandingan Actual vs Prediksi."""
		charts: dict[str, InteractiveResultChart] = getattr(self, "_result_charts", {})
		if not charts or "data" not in results:
			return

		test_data = results["data"]["test"]
		x_axis = test_data.index

		def _series(values) -> pd.Series:
			try:
				n = min(len(values), len(x_axis))
				return pd.Series(list(values)[:n], index=x_axis[:n])
			except Exception:
				return pd.Series([], dtype=float)

		if "fts" in charts:
			series_map = {"actual": pd.Series(test_data.values, index=x_axis)}
			if "fts" in results:
				series_map["fts"] = _series(results["fts"].get("forecast", []))
			if "naive" in results:
				series_map["naive"] = _series(results["naive"].get("forecast", []))
			if "ma" in results:
				series_map["ma"] = _series(results["ma"].get("forecast", []))
			if len(x_axis) > 0:
				start_date = x_axis[0].strftime("%d-%b-%Y")
				end_date = x_axis[-1].strftime("%d-%b-%Y")
				title = f"FTS Result ({start_date} to {end_date})"
			else:
				title = "FTS Result"
			charts["fts"].set_series(series_map, title)

		if "ann" in charts:
			series_map = {"actual": pd.Series(test_data.values, index=x_axis)}
			if "ann" in results:
				series_map["pred"] = _series(results["ann"].get("forecast", []))
			if len(x_axis) > 0:
				start_date = x_axis[0].strftime("%d-%b-%Y")
				end_date = x_axis[-1].strftime("%d-%b-%Y")
				title = f"ANN Result ({start_date} to {end_date})"
			else:
				title = "ANN Result"
			charts["ann"].set_series(series_map, title)

		if "arima" in charts:
			series_map = {"actual": pd.Series(test_data.values, index=x_axis)}
			if "arima" in results:
				series_map["pred"] = _series(results["arima"].get("forecast", []))
			if len(x_axis) > 0:
				start_date = x_axis[0].strftime("%d-%b-%Y")
				end_date = x_axis[-1].strftime("%d-%b-%Y")
				title = f"ARIMA Result ({start_date} to {end_date})"
			else:
				title = "ARIMA Result"
			charts["arima"].set_series(series_map, title)

		# Pindah ke tab Graphic (R4)
		try:
			for i in range(self.tabWidget.count()):
				page = self.tabWidget.widget(i)
				if page.objectName() == "Resume":
					self.tabWidget.setCurrentIndex(i)
					break
		except Exception:
			pass

		try:
			for i in range(self.tabWidget_Resume_container.count()):
				page = self.tabWidget_Resume_container.widget(i)
				if page.objectName() == "Resume_GRAPHIC":
					self.tabWidget_Resume_container.setCurrentIndex(i)
					break
		except Exception:
			pass

		try:
			self.tabWidget_graph_container.setCurrentIndex(0)
		except Exception:
			pass

	def update_resume_text(self, results: dict) -> None:
		"""Menampilkan ringkasan metrik di Tab Resume."""

		if not hasattr(self, "textEdit_resume"):
			return

		lines: list[str] = ["=== ANALYSIS SUMMARY ===", ""]
		for method in ["fts", "ann", "arima"]:
			if method in results:
				m = results[method]["metrics"]
				lines.append(f"[{method.upper()}]")
				lines.append(f"MAE : {m.get('mae', 0.0):.4f}")
				lines.append(f"MAPE: {m.get('mape', 0.0):.4f}%")
				lines.append(f"RMSE: {m.get('rmse', 0.0):.4f}")
				lines.append("-" * 20)

		self.textEdit_resume.setText("\n".join(lines))

	def _update_metrics_labels(self, results: dict) -> None:
		"""Isi label MAE/MAPE/RMSE di tab Initial untuk FTS/ANN/ARIMA (+baseline).

		Mendukung dua skema metrics:
		- metrics = {mae, mape, rmse}
		- metrics = {train: {mae, mape, rmse}, test: {mae, mape, rmse}}
		"""

		def _pair(metrics: dict) -> tuple[dict, dict]:
			if not isinstance(metrics, dict):
				return ({}, {})
			if "train" in metrics and "test" in metrics:
				return (metrics.get("train", {}), metrics.get("test", {}))
			return (metrics, metrics)

		def _fmt(x):
			try:
				return f"{float(x):.4f}"
			except Exception:
				return "-"

		def _set(name: str, val: str) -> None:
			w = getattr(self, name, None)
			if w is not None:
				try:
					w.setText(val)
				except Exception:
					pass

		for method, prefix in [("fts", "_fts"), ("ann", "_ann"), ("arima", "_arima")]:
			if method not in results:
				continue
			train, test = _pair(results[method].get("metrics", {}))
			_set(f"label_mae{prefix}_train", _fmt(train.get("mae")))
			_set(f"label_mae{prefix}_test", _fmt(test.get("mae")))
			_set(f"label_mape{prefix}_train", _fmt(train.get("mape")))
			_set(f"label_mape{prefix}_test", _fmt(test.get("mape")))
			_set(f"label_rmse{prefix}_train", _fmt(train.get("rmse")))
			_set(f"label_rmse{prefix}_test", _fmt(test.get("rmse")))
			if method == "fts":
				_set("label_mape_fts_ttest", _fmt(test.get("mape")))

		for base_name, label_suffix in [("naive", "_naive"), ("ma", "_ma")]:
			m = results.get(base_name, {}).get("metrics", {})
			if m:
				_set(f"label_mae{label_suffix}", _fmt(m.get("mae")))
				_set(f"label_mape{label_suffix}", _fmt(m.get("mape")))
				_set(f"label_rmse{label_suffix}", _fmt(m.get("rmse")))
				_set(f"label_mape_fts{label_suffix}", _fmt(m.get("mape")))
				_set(f"label_rmse_fts{label_suffix}", _fmt(m.get("rmse")))

	def append_log_ui(self, html_msg: str) -> None:
		"""Append satu baris log berformat HTML ke widget log dengan STRICT limit (RUN 5)."""

		# Prefer widget log khusus bila tersedia
		log_widget = getattr(self, "textBrowser", None)
		if log_widget is None:
			log_widget = getattr(self, "textEdit_resume", None)
		if log_widget is None:
			return

		# Append new log
		log_widget.append(html_msg)
		
		# Auto scroll ke bawah
		log_widget.moveCursor(QTextCursor.MoveOperation.End)
		
		# Apply strict limit (RUN 5)
		self._apply_log_limit()

	def _apply_log_limit(self):
		"""Apply strict limit ke log textBrowser.
		
		STRICT CUT-OFF: Hanya keep last N lines sesuai limit.
		User TIDAK BISA scroll melewati limit.
		"""
		log_widget = getattr(self, "textBrowser", None)
		if log_widget is None:
			return
		
		doc = log_widget.document()
		total_blocks = doc.blockCount()
		
		if total_blocks <= self._current_log_limit:
			return  # Belum melebihi limit
		
		# Calculate blocks to remove
		blocks_to_remove = total_blocks - self._current_log_limit
		
		# Remove from top
		cursor = QTextCursor(doc)
		cursor.movePosition(QTextCursor.MoveOperation.Start)
		
		for _ in range(blocks_to_remove):
			cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
			cursor.removeSelectedText()
			cursor.deleteChar()  # Remove newline

	def _on_log_limit_changed(self, new_limit_text):
		"""Handler saat user ubah limit log (RUN 5)."""
		try:
			new_limit = int(new_limit_text)
			self._current_log_limit = new_limit
			
			# Apply limit ke existing log
			self._apply_log_limit()
			
			self.logger.log("INFO", f"Log display limit changed to: {new_limit} lines")
		except ValueError:
			pass  # Invalid value, ignore

	@pyqtSlot()
	def cancel_analysis(self) -> None:
		"""Slot untuk tombol Cancel di UI atau dialog progress."""

		if self.worker is not None and self.worker.isRunning():
			self.logger.log("INFO", "User requested analysis cancellation.")
			self.worker.stop()
		else:
			# Tidak ada worker aktif; biarkan dialog (jika ada) sekadar tertutup
			self.logger.log("INFO", "Cancel clicked but no active worker.")

	@pyqtSlot()
	def clear_data(self) -> None:
		"""Menghapus seluruh data telemetry dari database dan reset status UI."""

		if self.worker is not None and self.worker.isRunning():
			QMessageBox.warning(
				self,
				"Cannot Clear Data",
				"Analysis is currently running. Please cancel it first.",
			)
			return

		reply = QMessageBox.question(
			self,
			"Clear All Data",
			"This will delete all raw telemetry data from the database. Continue?",
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
			QMessageBox.StandardButton.No,
		)
		if reply != QMessageBox.StandardButton.Yes:
			return

		deleted = self.db_mgr.clear_raw_data()
		self.raw_data = None
		self.start_analysis_PB.setEnabled(False)
		self._initiation_completed = False
		self._update_data_status_label()
		self.logger.log("INFO", f"Cleared raw telemetry table. Deleted rows: {deleted}.")
		QMessageBox.information(self, "Data Cleared", "All telemetry data has been removed.")
		self._update_setup_progress()

	@pyqtSlot()
	def export_results_to_excel(self) -> None:
		"""Mengekspor hasil analisis terakhir ke file PDF (RUN 5 - Updated)."""

		if not self.analysis_results:
			QMessageBox.warning(self, "No Results", "Run analysis first before exporting.")
			return

		file_path, _ = QFileDialog.getSaveFileName(
			self,
			"Export Results to PDF",
			f"hasil_analisis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
			"PDF Files (*.pdf)",
		)
		if not file_path:
			return

		try:
			self.logger.log("PROCESS", "Generating PDF report...")
			params = self._last_run_params or self.get_ui_params() or {}
			try:
				raw_df = self._get_analysis_raw_df()
			except Exception:
				raw_df = pd.DataFrame()
			success, message = ExportManager.export_to_pdf(
				self.analysis_results,
				file_path,
				logger=self.logger,
				params=params,
				raw_df=raw_df,
			)
			
			if success:
				QMessageBox.information(self, "Success", message)
				
				# Ask if want to open file
				reply = QMessageBox.question(
					self, "Open File", 
					"Apakah ingin membuka PDF report sekarang?",
					QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
				)
				
				if reply == QMessageBox.StandardButton.Yes:
					import os
					os.startfile(file_path)  # Windows only
			else:
				QMessageBox.critical(self, "Error", f"Export gagal:\n{message}")
				
		except Exception as e:  # pragma: no cover - UI error path
			self.logger.log("ERROR", f"Failed to export results: {e}")
			QMessageBox.critical(self, "Export Failed", f"Failed to export results:\n{e}")

	@pyqtSlot()
	def export_log_file(self) -> None:
		"""Export log (RUN-5) atau artefak akademik (RUN-3 Ex_Plan-6)."""

		run_guid = self.logger.get_run_guid() if hasattr(self.logger, "get_run_guid") else None
		run_logs = self.logger.get_run_log_paths() if hasattr(self.logger, "get_run_log_paths") else {}
		has_run_logs = bool(run_guid and run_logs)

		if has_run_logs:
			choice = QMessageBox.question(
				self,
				"Export Log",
				"Pilih jenis export:\n\n"
				"- Yes  : Artefak Akademik (PPDL_LOG_<GUID>.zip + snapshot)\n"
				"- No   : Full Log (session_full.log)\n"
				"- Cancel: Batal",
				QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
				QMessageBox.StandardButton.Yes,
			)

			if choice == QMessageBox.StandardButton.Cancel:
				return

			if choice == QMessageBox.StandardButton.Yes:
				# Export artefak akademik Run-3 ke folder yang dipilih user.
				target_dir = QFileDialog.getExistingDirectory(
					self,
					"Export Artefak Akademik (Folder Output)",
					"",
				)
				if not target_dir:
					return
				try:
					raw_df = self._get_analysis_raw_df()
				except Exception:
					raw_df = pd.DataFrame()
				params = self._last_run_params or self.get_ui_params() or {}
				ok, msg = ExportManager.export_academic_artifacts_run3(
					logger=self.logger,
					raw_df=raw_df,
					params=params,
					output_dir=target_dir,
					include_csv=True,
				)
				if ok:
					QMessageBox.information(self, "Success", msg)
				else:
					QMessageBox.critical(self, "Export Failed", msg)
				return

		log_path = self.logger.get_log_path()
		if not log_path or not os.path.exists(log_path):
			QMessageBox.warning(self, "No Log", "No log file is available for export.")
			return

		target_path, _ = QFileDialog.getSaveFileName(
			self,
			"Export Full Log",
			f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
			"Text Files (*.txt);;HTML Files (*.html);;All Files (*.*)",
		)
		if not target_path:
			return

		try:
			shutil.copy2(log_path, target_path)
			self.logger.log("SUCCESS", f"Full log exported to {os.path.basename(target_path)}")
			QMessageBox.information(self, "Success", f"Log lengkap berhasil diekspor ke:\n{target_path}")
		except Exception as e:  # pragma: no cover - UI error path
			self.logger.log("ERROR", f"Export log failed: {e}")
			QMessageBox.critical(self, "Error", f"Export gagal:\n{e}")

	@pyqtSlot()
	def on_download_clicked(self) -> None:
		"""Download data dari BigQuery ke folder Downloads system.
		
		Panggil BigQueryDownloader.download_data() dengan progress tracking,
		loading indicator, dan auto-save ke folder Downloads.
		"""
		
		# Check if download already in progress
		if self.download_worker is not None and self.download_worker.isRunning():
			QMessageBox.warning(
				self,
				"Download Sedang Berjalan",
				"Download BigQuery sedang dalam proses. Silakan tunggu hingga selesai atau tekan tombol CANCEL."
			)
			return
		
		try:
			# Set loading cursor
			self.setCursor(QCursor(Qt.CursorShape.WaitCursor))
			
			# Reset progress bar
			if hasattr(self, "progressBar"):
				self.progressBar.setValue(0)
				self.progressBar.setVisible(True)
			
			# Create and start download worker
			self.download_worker = BigQueryDownloadWorker(self)
			
			# Connect worker signals
			self.download_worker.progress_updated.connect(self._on_download_progress)
			self.download_worker.download_finished.connect(self._on_download_finished)
			self.download_worker.download_status.connect(self._on_download_status)
			
			# Enable cancel button if exists
			if hasattr(self, "CANCEL_Download_Button"):
				self.CANCEL_Download_Button.setEnabled(True)
			
			# Start download in background
			self.download_worker.start()
			
			self.logger.log(
				"INFO",
				"BigQuery download started by user"
			)
			
		except Exception as e:
			# Restore cursor on error
			self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
			
			error_msg = f"Gagal memulai download: {str(e)}"
			QMessageBox.critical(
				self,
				"Error Download",
				error_msg
			)
			
			self.logger.log(
				"ERROR",
				f"BigQuery download failed to start: {error_msg}"
			)
			
			if hasattr(self, "progressBar"):
				self.progressBar.setValue(0)
		
	def _on_download_progress(self, percentage: int) -> None:
		"""Update progress bar during download."""
		if hasattr(self, "progressBar"):
			self.progressBar.setValue(percentage)
		
	def _on_download_status(self, status: str) -> None:
		"""Update status during download."""
		self.logger.log("INFO", f"BigQuery download status: {status}")
		
	def _on_download_finished(self, success: bool, result: str) -> None:
		"""Handle download completion - success or failure."""
		# Restore normal cursor
		self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
		
		# Disable cancel button
		if hasattr(self, "CANCEL_Download_Button"):
			self.CANCEL_Download_Button.setEnabled(False)
		
		if success:
			# Success - show file location
			file_path = result
			file_name = os.path.basename(file_path)
			QMessageBox.information(
				self,
				"Download Berhasil",
				f"Data BigQuery berhasil diunduh ke folder Downloads system!\n\n"
				f"File: {file_name}\n"
				f"Lokasi: {file_path}\n\n"
				f"File ini sekarang dapat diimpor melalui panel 'Data' di sebelah kiri."
			)
			
			self.logger.log(
				"INFO",
				f"BigQuery download completed successfully. File saved: {file_path}"
			)
			
			# Auto-refresh file list in Data panel if possible
			self._refresh_download_files_list()
			
		else:
			# Failure - show error message
			error_msg = result
			QMessageBox.critical(
				self,
				"Download Gagal",
				f"Download dari BigQuery gagal!\n\nError: {error_msg}"
			)
			
			self.logger.log(
				"ERROR",
				f"BigQuery download failed: {error_msg}"
			)
		
		# Reset progress bar
		if hasattr(self, "progressBar"):
			self.progressBar.setValue(0 if not success else 100)
		
		# Cleanup worker
		if self.download_worker is not None:
			self.download_worker.deleteLater()
			self.download_worker = None
			
	def _refresh_download_files_list(self) -> None:
		"""Refresh file list in Data panel to show newly downloaded files."""
		try:
			# Try to refresh combo box that shows JSON files
			if hasattr(self, "comboBox") and hasattr(self, "folderpath_OPEN"):
				# Get system Downloads folder path
				downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
				
				if os.path.exists(downloads_dir):
					# Set folder path to system Downloads
					self.folderpath_OPEN.setText(downloads_dir)
					
					# Update combo box with JSON files from Downloads
					combo = self.comboBox
					combo.clear()
					
					# Filter hanya file JSON yang berasal dari BigQuery (prefix data_bq_)
					json_files = [
						f for f in os.listdir(downloads_dir) 
						if f.lower().endswith(".json") and f.startswith("data_bq_")
					]
					json_files.sort(reverse=True)  # Newest first
					
					if json_files:
						combo.addItems(json_files)
						# Enable initiate button if exists
						if hasattr(self, "initate_button"):
							self.initate_button.setEnabled(True)
					else:
						combo.addItem("-- No BigQuery data files found --")
						if hasattr(self, "initate_button"):
							self.initate_button.setEnabled(False)
							
		except Exception as e:
			self.logger.log("WARNING", f"Could not refresh download files list: {e}")

	@pyqtSlot()
	def on_download_cancel_clicked(self) -> None:
		"""Cancel BigQuery download process if running."""
		
		if self.download_worker is not None and self.download_worker.isRunning():
			# Cancel the download
			self.download_worker.cancel_download()
			self.download_worker.quit()
			self.download_worker.wait()  # Wait for thread to finish
			
			# Restore UI state
			self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
			
			if hasattr(self, "progressBar"):
				self.progressBar.setValue(0)
				
			if hasattr(self, "CANCEL_Download_Button"):
				self.CANCEL_Download_Button.setEnabled(False)
			
			# Cleanup worker
			self.download_worker.deleteLater()
			self.download_worker = None
			
			QMessageBox.information(
				self,
				"Download Dibatalkan",
				"Download BigQuery telah dibatalkan oleh pengguna."
			)
			
			self.logger.log("INFO", "BigQuery download cancelled by user.")
		else:
			# No active download
			self.logger.log("INFO", "User clicked cancel but no active BigQuery download.")
			if hasattr(self, "progressBar"):
				self.progressBar.setValue(0)

	@pyqtSlot()
	def on_browse_folder_clicked(self) -> None:
		"""Memilih folder berisi banyak file JSON untuk inisiasi data."""
		import os

		folder = QFileDialog.getExistingDirectory(self, "Pilih Folder Data JSON")
		if not folder:
			self.logger.log_event(
				lvl1="INFO",
				lvl2="MAIN",
				lvl3="BASE",
				lvl4="GENERAL",
				evt=EVT.UI_SELECT_FOLDER,
				route_to=["DATABASE"],
				fields=["status=CANCEL"],
				result="status=CANCEL",
			)
			return

		if hasattr(self, "folderpath_OPEN"):
			self.folderpath_OPEN.setText(folder)

		# Isi dropdown dengan daftar file JSON di folder (SORTED)
		combo = getattr(self, "comboBox", None)
		json_files: list[str] = []
		if combo is not None:
			combo.clear()
			json_files = [
				f
				for f in os.listdir(folder)
				if f.lower().endswith(".json")
			]
			json_files.sort()  # Sort alphabetically
			if json_files:
				combo.addItems(json_files)
				# Enable initiate button
				if hasattr(self, "initate_button"):
					self.initate_button.setEnabled(True)
			else:
				combo.addItem("-- No JSON files found --")
				# Disable initiate button
				if hasattr(self, "initate_button"):
					self.initate_button.setEnabled(False)
		lvl1 = "INFO" if json_files else "WARN"
		result = "status=OK" if json_files else "status=EMPTY"
		self.logger.log_event(
			lvl1=lvl1,
			lvl2="MAIN",
			lvl3="BASE",
			lvl4="GENERAL",
			evt=EVT.UI_SELECT_FOLDER,
			route_to=["DATABASE"],
			fields=[f"path={folder}", f"json_files={len(json_files)}"],
			result=result,
		)

	@pyqtSlot()
	def on_initiate_data_clicked(self) -> None:
		"""Import SELECTED JSON file from comboBox."""

		import os

		folder = getattr(self, "folderpath_OPEN", None)
		if folder is None or not folder.text().strip():  # type: ignore[union-attr]
			self.logger.log_event(
				lvl1="WARN",
				lvl2="MAIN",
				lvl3="CAL",
				lvl4="GENERAL",
				evt=EVT.UI_CLICK_IMPORT,
				route_to=["DATABASE"],
				fields=["status=BLOCKED"],
				cause="no_folder_selected",
				result="status=BLOCKED",
			)
			QMessageBox.warning(self, "No Folder", "Silakan pilih folder data terlebih dahulu.")
			return

		folder_path = folder.text().strip()  # type: ignore[union-attr]
		if not os.path.isdir(folder_path):
			self.logger.log_event(
				lvl1="WARN",
				lvl2="MAIN",
				lvl3="CAL",
				lvl4="GENERAL",
				evt=EVT.UI_CLICK_IMPORT,
				route_to=["DATABASE"],
				fields=[f"path={folder_path}", "status=BLOCKED"],
				cause="invalid_folder_path",
				result="status=BLOCKED",
			)
			QMessageBox.warning(self, "Invalid Folder", "Path folder tidak valid.")
			return

		# Get SELECTED file from comboBox
		combo = getattr(self, "comboBox", None)
		if combo is None:
			self.logger.log_event(
				lvl1="ERROR",
				lvl2="MAIN",
				lvl3="CAL",
				lvl4="GENERAL",
				evt=EVT.UI_CLICK_IMPORT,
				route_to=["DATABASE"],
				fields=["status=BLOCKED"],
				cause="combobox_missing",
				result="status=BLOCKED",
			)
			QMessageBox.warning(self, "Error", "ComboBox not found.")
			return

		selected_file = combo.currentText()
		if not selected_file or selected_file == "-- No JSON files found --":
			self.logger.log_event(
				lvl1="WARN",
				lvl2="MAIN",
				lvl3="CAL",
				lvl4="GENERAL",
				evt=EVT.UI_CLICK_IMPORT,
				route_to=["DATABASE"],
				fields=["status=BLOCKED"],
				cause="no_json_selected",
				result="status=BLOCKED",
			)
			QMessageBox.warning(self, "No File Selected", "Please select a JSON file from the list.")
			return

		# Build full path
		file_path = os.path.join(folder_path, selected_file)
		if not os.path.exists(file_path):
			self.logger.log_event(
				lvl1="WARN",
				lvl2="MAIN",
				lvl3="CAL",
				lvl4="GENERAL",
				evt=EVT.UI_CLICK_IMPORT,
				route_to=["DATABASE"],
				fields=[f"file={selected_file}", "status=BLOCKED"],
				cause="file_not_found",
				result="status=BLOCKED",
			)
			QMessageBox.warning(self, "File Not Found", f"File {selected_file} tidak ditemukan.")
			return

		# Simpan jejak sumber terakhir (untuk CALC trace Ex_Plan-6).
		self._last_import_file_path = file_path
		self._last_import_file_name = selected_file

		self.logger.log_event(
			lvl1="INFO",
			lvl2="MAIN",
			lvl3="BASE",
			lvl4="GENERAL",
			evt=EVT.UI_SELECT_JSON,
			route_to=["DATABASE"],
			fields=[f"file={selected_file}", f"path={file_path}"],
		)
		self.logger.log_event(
			lvl1="INIT",
			lvl2="DATABASE",
			lvl3="CAL",
			lvl4="GENERAL",
			evt=EVT.DATA_INGESTION_START,
			route_to=["HOME", "INITIAL"],
			fields=[f"file={selected_file}"],
		)

		importer = DataImporter(self.db_mgr)

		# Progress aggregator: gunakan 0-100 untuk seluruh proses (import + sync HOME + INITIAL)
		if hasattr(self, "progressBar_3"):
			self.progressBar_3.setMinimum(0)
			self.progressBar_3.setMaximum(100)
			self.progressBar_3.setValue(10)

		# Import single file
		res = importer.import_from_json(file_path)
		status = res.get("status")
		total_found = 0
		inserted_total = 0
		errors = 0

		if status == "success":
			total_found = res.get("total_found", 0)
			inserted_total = res.get("inserted_new", 0)
			self._last_import_total_found = int(total_found)
			self._last_import_inserted = int(inserted_total)
			self.logger.log_event(
				lvl1="SUCCESS",
				lvl2="DATABASE",
				lvl3="RPT",
				lvl4="GENERAL",
				evt=EVT.DATA_INGESTION_DONE,
				route_to=["HOME", "INITIAL"],
				fields=[
					f"file={selected_file}",
					f"rows_found={int(total_found)}",
					f"rows_inserted={int(inserted_total)}",
				],
			)
		elif status == "error":
			errors = 1
			self._last_import_total_found = int(total_found)
			self._last_import_inserted = int(inserted_total)
			self.logger.log_event(
				lvl1="FAIL",
				lvl2="DATABASE",
				lvl3="RPT",
				lvl4="GENERAL",
				evt=EVT.DATA_INGESTION_DONE,
				route_to=["HOME", "INITIAL"],
				fields=[f"file={selected_file}", "status=FAIL"],
				cause=str(res.get("message", "unknown_error")),
				result="status=FAIL",
			)
			QMessageBox.warning(self, "Import Error", res.get('message', 'Unknown error'))

		if hasattr(self, "progressBar_3"):
			self.progressBar_3.setValue(40)

		status_text = f"File: {selected_file} | Rows: {total_found} | Inserted: {inserted_total}"
		if errors:
			status_text += f" | Errors: {errors}"

		if hasattr(self, "label_status_inisiasidata"):
			self.label_status_inisiasidata.setText(status_text)

		# status_text tetap ditampilkan ke UI label; log sudah tercatat via EVT DB_IMPORT_DONE

		# SYNCHRONIZE PROCESS: Refresh Tab HOME + Tab INITIAL
		self._initiation_completed = True

		# Progress 40-70%: Load initial data (for Tab Initial readiness check)
		self._load_initial_data(reset_on_startup=False, refresh_home=False)
		if hasattr(self, "progressBar_3"):
			self.progressBar_3.setValue(70)

		# Progress 70-100%: Refresh Home dashboard (Average + Daily)
		self._refresh_home_dashboard(use_progress=True)

		# Final progress 100%
		if hasattr(self, "progressBar_3"):
			self.progressBar_3.setValue(100)

		self.logger.log("INFO", "Synchronize process completed: Tab Home + Tab Initial refreshed")

	def _query_raw_df(self) -> pd.DataFrame:
		"""Ambil data dari DB dan siapkan kolom waktu sebagai datetime.

		Return DataFrame dengan kolom: ts (datetime), watt, voltage
		"""

		df = self.db_mgr.fetch_data()
		if df is None or df.empty:
			return pd.DataFrame()
		df = df.copy()
		df["ts"] = pd.to_datetime(df["ts_server"], unit="ms")
		df = df.sort_values("ts").reset_index(drop=True)
		# Pastikan kolom sensor tambahan tersedia
		for c in ["current", "frequency", "energy_kwh", "pf"]:
			if c not in df.columns:
				df[c] = 0.0
		return df[["ts", "watt", "voltage", "current", "frequency", "energy_kwh", "pf"]]

	def _get_selected_average_range_ms(self) -> tuple[int | None, int | None]:
		start_ms = None
		end_ms = None
		try:
			if self.select_avg_tanggal_awal is not None and self.select_avg_tanggal_awal.dateTime().isValid():
				start_dt = self.select_avg_tanggal_awal.dateTime().toPyDateTime()
				start_ms = int(pd.Timestamp(start_dt).value // 1_000_000)
			if self.select_avg_tanggal_akhir is not None and self.select_avg_tanggal_akhir.dateTime().isValid():
				end_dt = self.select_avg_tanggal_akhir.dateTime().toPyDateTime()
				end_ms = int(pd.Timestamp(end_dt).value // 1_000_000)
		except Exception:
			return (None, None)
		if start_ms is not None and end_ms is not None and end_ms < start_ms:
			start_ms, end_ms = end_ms, start_ms
		return (start_ms, end_ms)

	def _get_analysis_raw_df(self) -> pd.DataFrame:
		"""Ambil data untuk analisis sesuai range Average yang dipilih."""
		df = self.raw_data if self.raw_data is not None else self.db_mgr.fetch_data()
		if df is None or df.empty:
			return pd.DataFrame()
		start_ms, end_ms = self._get_selected_average_range_ms()
		if start_ms is None or end_ms is None:
			return df
		filtered = df[(df["ts_server"] >= start_ms) & (df["ts_server"] <= end_ms)].copy()
		return filtered

	def _energy_kwh(self, df: pd.DataFrame) -> float:
		"""Hitung energi (kWh) dari rentang pembacaan.

		Jika kolom energy_kwh tersedia, gunakan selisih (akhir - awal).
		Fallback ke integral numerik sederhana sum(W * dt_hours)/1000.
		"""

		try:
			if df is None or len(df) < 2:
				return 0.0
			if "energy_kwh" in df.columns:
				energy_vals = df["energy_kwh"].dropna()
				if len(energy_vals) >= 2:
					energy = float(energy_vals.iloc[-1] - energy_vals.iloc[0])
					return max(0.0, energy)
			dt = df["ts"].diff().dt.total_seconds().fillna(0) / 3600.0
			energy = float((df["watt"] * dt).sum() / 1000.0)
			return max(0.0, energy)
		except Exception:
			return 0.0

	def _adjust_energy_series(self, df: pd.DataFrame, ts_col: str) -> pd.Series:
		"""Hitung energi ter-adjust (awal = 0) untuk tabel/grafik HOME."""
		if df is None or df.empty:
			return pd.Series(dtype=float)
		if "energy_kwh" in df.columns and df["energy_kwh"].notna().any():
			base = df["energy_kwh"].dropna().iloc[0]
			return df["energy_kwh"] - base
		if ts_col not in df.columns or "watt" not in df.columns:
			return pd.Series([0.0] * len(df), index=df.index)
		dt_h = df[ts_col].diff().dt.total_seconds().fillna(0) / 3600.0
		return (df["watt"] * dt_h).cumsum() / 1000.0

	def _apply_adjusted_energy(self, df: pd.DataFrame, ts_col: str) -> pd.DataFrame:
		if df is None or df.empty:
			return df
		out = df.copy()
		out["energy_kwh"] = self._adjust_energy_series(out, ts_col)
		return out

	def _build_home_table(self, df: pd.DataFrame, ts_col: str) -> pd.DataFrame:
		if df is None or df.empty:
			return df
		tbl = df.copy()
		tbl["Energi(kWh)"] = self._adjust_energy_series(tbl, ts_col)
		tbl.drop(columns=["energy_kwh"], errors="ignore", inplace=True)
		rename_map = {
			ts_col: "Timestamp",
			"watt": "Daya(W)",
			"voltage": "Tegangan(V)",
			"current": "Arus(A)",
			"frequency": "Frekuensi(Hz)",
			"pf": "PF",
		}
		tbl.rename(columns=rename_map, inplace=True)
		return tbl

	def _set_lcd(self, lcd, value: float) -> None:
		try:
			if lcd is not None:
				lcd.display(float(value))
		except Exception:
			pass

	def _set_table(self, view, df: pd.DataFrame) -> None:
		try:
			if view is None:
				return
			model = MainWindow._PandasModel(df)
			view.setModel(model)
		except Exception:
			pass

	def _draw_home_matplotlib(self, canvas: FigureCanvasQTAgg | None, ax, df: pd.DataFrame, params: list[str], title: str) -> None:
		"""Render ke Matplotlib canvas (interaktif: pan/zoom, coord tooltip)."""

		try:
			if canvas is None or ax is None or df is None or df.empty:
				return
			import matplotlib.dates as mdates

			ax.clear()
			ax.grid(True, alpha=0.3)
			ax.set_title(title)
			ax.set_xlabel("Time")
			colors = {
				"voltage": "tab:orange",
				"watt": "tab:blue",
				"energy": "tab:green",
				"energy_kwh": "tab:green",
				"current": "tab:red",
				"frequency": "tab:purple",
				"pf": "tab:brown",
			}

			# Energi dari sensor bila diminta; fallback ke integrasi daya
			if "energy_kwh" in params and "energy_kwh" in df.columns:
				ax.plot(df["ts"], df["energy_kwh"], label="Energi (kWh)", color=colors["energy_kwh"], lw=1.5)
			elif "energy" in params:
				cdf = df.copy()
				dt_h = cdf["ts"].diff().dt.total_seconds().fillna(0) / 3600.0
				cdf["energy"] = (cdf["watt"] * dt_h).cumsum() / 1000.0
				ax.plot(cdf["ts"], cdf["energy"], label="Energi (kWh)", color=colors["energy"], lw=1.5)

			if "watt" in params:
				ax.plot(df["ts"], df["watt"], label="Daya (W)", color=colors["watt"], alpha=0.85, lw=1.2)

			if "voltage" in params:
				ax.plot(df["ts"], df["voltage"], label="Tegangan (V)", color=colors["voltage"], alpha=0.85, lw=1.0)

			if "current" in params and "current" in df.columns:
				ax.plot(df["ts"], df["current"], label="Arus (A)", color=colors["current"], alpha=0.85, lw=1.0)

			if "frequency" in params and "frequency" in df.columns:
				ax.plot(df["ts"], df["frequency"], label="Frekuensi (Hz)", color=colors["frequency"], alpha=0.85, lw=1.0)

			if "pf" in params and "pf" in df.columns:
				ax.plot(df["ts"], df["pf"], label="PF", color=colors["pf"], alpha=0.85, lw=1.0)

			ax.legend(loc="best")
			ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
			canvas.draw()

			# Basic coordinate tooltip in status: show time & value under cursor
			def _fmt_coord(x, y):
				try:
					return f"t={mdates.num2date(x).strftime('%Y-%m-%d %H:%M:%S')}, y={y:.3f}"
				except Exception:
					return f"x={x:.3f}, y={y:.3f}"
			ax.format_coord = _fmt_coord
		except Exception as e:
			self.logger.log("ERROR", f"Failed to draw home graph: {e}")

	def _get_data_for_average_chart(self) -> pd.DataFrame:
		"""Data source callback untuk Average chart (RUN 4)."""
		try:
			df = self.db_mgr.get_all_raw_data_for_table()
			return self._apply_adjusted_energy(df, "timestamp")
		except Exception:
			return pd.DataFrame()

	def _get_data_for_daily_chart(self) -> pd.DataFrame:
		"""Data source callback untuk Daily chart (RUN 4)."""
		try:
			if self.select_daily_tanggal_awal is None:
				return pd.DataFrame()
			
			# Get selected date from daily date picker
			selected_qdate = self.select_daily_tanggal_awal.date()
			selected_date = selected_qdate.toPyDate()
			
			df = self.db_mgr.get_daily_data_for_table(selected_date)
			return self._apply_adjusted_energy(df, "timestamp")
		except Exception:
			return pd.DataFrame()

	def _should_log_no_data(self) -> bool:
		if getattr(self, "_startup_in_progress", False):
			return False
		if self.raw_data is None or getattr(self.raw_data, "empty", True):
			return False
		return True

	def _format_dt(self, dt_value) -> str:
		try:
			return pd.to_datetime(dt_value).strftime("%d/%m/%Y %H:%M:%S")
		except Exception:
			return str(dt_value)

	def _log_home_range_change(
		self,
		start_ts: pd.Timestamp | None,
		end_ts: pd.Timestamp | None,
		daily_date,
	) -> None:
		if getattr(self, "_startup_in_progress", False):
			return
		if start_ts is not None and end_ts is not None:
			key = (pd.to_datetime(start_ts), pd.to_datetime(end_ts))
			if self._last_logged_avg_range != key:
				self._last_logged_avg_range = key
				self.logger.log_event(
					lvl1="INFO",
					lvl2="HOME",
					lvl3="BASE",
					lvl4="GENERAL",
					evt=EVT.UI_SET_RANGE_AVG,
					route_to=["HOME"],
					fields=[f"start={self._format_dt(key[0])}", f"end={self._format_dt(key[1])}"],
				)
		if daily_date is not None and self._last_logged_daily_date != daily_date:
			self._last_logged_daily_date = daily_date
			try:
				date_text = pd.to_datetime(daily_date).strftime("%d/%m/%Y")
			except Exception:
				date_text = str(daily_date)
			self.logger.log_event(
				lvl1="INFO",
				lvl2="HOME",
				lvl3="BASE",
				lvl4="GENERAL",
				evt=EVT.UI_SET_RANGE_DAILY,
				route_to=["HOME"],
				fields=[f"date={date_text}"],
			)

	def _load_dashboard_average(self, preserve_range: bool = False) -> None:
		"""Load dashboard Average dengan data dari database (RUN 3)."""
		try:
			# Get statistics from database
			stats = self.db_mgr.get_dashboard_average_stats()
			
			if stats is None:
				# No data available - clear dashboard
				self._clear_dashboard_average()
				if self._should_log_no_data():
					self.logger.log("INFO", "No data available for dashboard Average")
				return
			
			# Update groupBox_16 (Info) - Date Range
			start_date = stats['date_range']['start']
			end_date = stats['date_range']['end']
			
			if self.select_avg_tanggal_awal is not None:
				if not preserve_range or not self.select_avg_tanggal_awal.dateTime().isValid():
					self.select_avg_tanggal_awal.blockSignals(True)
					self.select_avg_tanggal_awal.setDateTime(QDateTime(start_date))
					self.select_avg_tanggal_awal.blockSignals(False)
			
			if self.select_avg_tanggal_akhir is not None:
				if not preserve_range or not self.select_avg_tanggal_akhir.dateTime().isValid():
					self.select_avg_tanggal_akhir.blockSignals(True)
					self.select_avg_tanggal_akhir.setDateTime(QDateTime(end_date))
					self.select_avg_tanggal_akhir.blockSignals(False)
			
			# Update jumlah data
			if self.value_avg_jumlahdata is not None:
				self.value_avg_jumlahdata.display(stats['row_count'])
			
			# Update groupBox_18 (Rata-Rata) - Average Values
			avgs = stats['averages']
			if self.value_avg_daya is not None:
				self.value_avg_daya.display(avgs['watt'])
			if self.value_avg_arus is not None:
				self.value_avg_arus.display(avgs['current'])
			if self.value_avg_tegangan is not None:
				self.value_avg_tegangan.display(avgs['voltage'])
			if self.value_avg_energi is not None:
				self.value_avg_energi.display(avgs['energy_kwh'])
			if self.value_avg_frekuensi is not None:
				self.value_avg_frekuensi.display(avgs['frequency'])
			if self.value_avg_pf is not None:
				self.value_avg_pf.display(avgs['pf'])
			
			# Update tabel_HOME_average_2 (QTableView)
			df = self.db_mgr.get_all_raw_data_for_table()
			df_display = self._build_home_table(df, "timestamp")
			
			if not df_display.empty and self.tabel_HOME_average_2 is not None:
				model = self._PandasModel(df_display)
				self.tabel_HOME_average_2.setModel(model)
				
				# Auto-resize columns
				self.tabel_HOME_average_2.resizeColumnsToContents()
				
				start_text = self._format_dt(start_date)
				end_text = self._format_dt(end_date)
				self.logger.log(
					"SUCCESS",
					f"Dashboard Average loaded: {len(df)} rows range date time start: {start_text} - {end_text}",
				)
			else:
				self.logger.log("WARNING", "DataFrame empty for table view")
			
			# Update chart (RUN 4)
			if hasattr(self, 'chart_average') and self.chart_average is not None:
				self.chart_average.plot_data()
				
		except Exception as e:
			self.logger.log("ERROR", f"Failed to load dashboard Average: {e}")

	def _clear_dashboard_average(self) -> None:
		"""Clear all dashboard Average widgets (RUN 3)."""
		try:
			# Reset LCD displays to 0
			if self.value_avg_jumlahdata is not None:
				self.value_avg_jumlahdata.display(0)
			if self.value_avg_daya is not None:
				self.value_avg_daya.display(0)
			if self.value_avg_arus is not None:
				self.value_avg_arus.display(0)
			if self.value_avg_tegangan is not None:
				self.value_avg_tegangan.display(0)
			if self.value_avg_energi is not None:
				self.value_avg_energi.display(0)
			if self.value_avg_frekuensi is not None:
				self.value_avg_frekuensi.display(0)
			if self.value_avg_pf is not None:
				self.value_avg_pf.display(0)
			
			# Clear table
			if self.tabel_HOME_average_2 is not None:
				self.tabel_HOME_average_2.setModel(None)
		except Exception:
			pass

	def _load_dashboard_daily(self, target_date=None, preserve_date: bool = False) -> None:
		"""Load data untuk Tab Home -> Daily dashboard (RUN 4)."""
		try:
			if preserve_date and self.select_daily_tanggal_awal is not None:
				try:
					target_date = self.select_daily_tanggal_awal.dateTime().toPyDateTime().date()
				except Exception:
					pass

			# If no target_date specified, get last date from database
			if target_date is None:
				stats_avg = self.db_mgr.get_dashboard_average_stats()
				if stats_avg is None:
					if self._should_log_no_data():
						self.logger.log("WARNING", "No data available for daily dashboard")
					self._clear_dashboard_daily()
					return
				target_date = stats_avg['date_range']['end'].date()  # Use last date
			
			# Query stats for selected date
			stats = self.db_mgr.get_dashboard_daily_stats(target_date)
			
			if stats is None:
				# No data for this date
				if self._should_log_no_data():
					self.logger.log("WARNING", f"No data for date: {target_date}")
				self._clear_dashboard_daily()
				return
			
			# Update groupBox_19 (Info) - Selected Date
			from datetime import datetime
			q_date = QDateTime(datetime.combine(target_date, datetime.min.time()))
			
			if self.select_daily_tanggal_awal is not None:
				if not preserve_date or not self.select_daily_tanggal_awal.dateTime().isValid():
					self.select_daily_tanggal_awal.blockSignals(True)
					self.select_daily_tanggal_awal.setDateTime(q_date)
					self.select_daily_tanggal_awal.blockSignals(False)
			
			# Update jumlah data
			if self.value_daily_jumlahdata is not None:
				self.value_daily_jumlahdata.display(stats['row_count'])
			
			# Update groupBox_21 (Rata-Rata) - Average Values for that day
			avgs = stats['averages']
			if self.value_daily_daya is not None:
				self.value_daily_daya.display(avgs['watt'])
			if self.value_daily_arus is not None:
				self.value_daily_arus.display(avgs['current'])
			if self.value_daily_tegangan is not None:
				self.value_daily_tegangan.display(avgs['voltage'])
			if self.value_daily_energi is not None:
				self.value_daily_energi.display(avgs['energy_kwh'])
			if self.value_daily_frekuensi is not None:
				self.value_daily_frekuensi.display(avgs['frequency'])
			if self.value_daily_pf is not None:
				self.value_daily_pf.display(avgs['pf'])
			
			# Update tabel_HOME_daily_2 (QTableView)
			df = self.db_mgr.get_daily_data_for_table(target_date)
			df_display = self._build_home_table(df, "timestamp")
			
			if not df_display.empty and self.tabel_HOME_daily_2 is not None:
				model = self._PandasModel(df_display)
				self.tabel_HOME_daily_2.setModel(model)
				self.tabel_HOME_daily_2.resizeColumnsToContents()
				
				daily_start = df["timestamp"].iloc[0]
				daily_end = df["timestamp"].iloc[-1]
				start_text = self._format_dt(daily_start)
				end_text = self._format_dt(daily_end)
				self.logger.log(
					"SUCCESS",
					f"Dashboard Daily loaded: {len(df)} rows range date time start: {start_text} - {end_text}",
				)
			else:
				if self._should_log_no_data():
					self.logger.log("WARNING", f"No data for date: {target_date}")
			
			# Update chart (RUN 4)
			if hasattr(self, 'chart_daily') and self.chart_daily is not None:
				self.chart_daily.plot_data()
				
		except Exception as e:
			self.logger.log("ERROR", f"Failed to load dashboard Daily: {e}")

	def _clear_dashboard_daily(self) -> None:
		"""Clear all dashboard Daily widgets (RUN 4)."""
		try:
			# Reset LCD displays to 0
			if self.value_daily_jumlahdata is not None:
				self.value_daily_jumlahdata.display(0)
			if self.value_daily_daya is not None:
				self.value_daily_daya.display(0)
			if self.value_daily_arus is not None:
				self.value_daily_arus.display(0)
			if self.value_daily_tegangan is not None:
				self.value_daily_tegangan.display(0)
			if self.value_daily_energi is not None:
				self.value_daily_energi.display(0)
			if self.value_daily_frekuensi is not None:
				self.value_daily_frekuensi.display(0)
			if self.value_daily_pf is not None:
				self.value_daily_pf.display(0)
			
			# Clear table
			if self.tabel_HOME_daily_2 is not None:
				self.tabel_HOME_daily_2.setModel(None)
		except Exception:
			pass

	def _refresh_home_dashboard(self, use_progress: bool = True, preserve_range: bool = False, preserve_daily: bool = False) -> None:
		"""Sinkronkan Tab HOME (Average & Daily) setelah inisiasi atau perubahan kontrol.

		- Average Tab 1: tabel seluruh rentang (atau sesuai range widget)
		- Average Tab 2: grafik parameter terpilih
		- Daily Tab 1/2: data harian dari tanggal terpilih (atau terakhir)
		- Ringkasan: jumlah data, rata-rata, energi, dsb. yang tersedia
		"""

		# RUN 3: Load dashboard Average
		self._load_dashboard_average(preserve_range=preserve_range)

		# RUN 4: Load dashboard Daily
		self._load_dashboard_daily(preserve_date=preserve_daily)

		df = self._query_raw_df()
		if df.empty:
			return

		# Helper untuk progress bar import (progressBar_3)
		def _bump(val: int) -> None:
			if use_progress and hasattr(self, "progressBar_3") and self.progressBar_3.maximum() <= 100:
				try:
					cur = int(self.progressBar_3.value())
					self.progressBar_3.setMaximum(100)
					self.progressBar_3.setValue(min(100, cur + val))
				except Exception:
					pass

		# --- Average range ---
		start_ts = df["ts"].iloc[0]
		end_ts = df["ts"].iloc[-1]
		try:
			if self.select_avg_tanggal_awal is not None:
				if self.select_avg_tanggal_awal.dateTime().isValid():
					start_ts = pd.to_datetime(self.select_avg_tanggal_awal.dateTime().toPyDateTime())
			if self.select_avg_tanggal_akhir is not None:
				if self.select_avg_tanggal_akhir.dateTime().isValid():
					end_ts = pd.to_datetime(self.select_avg_tanggal_akhir.dateTime().toPyDateTime())
		except Exception:
			pass
		# Clamp range
		if end_ts < start_ts:
			start_ts, end_ts = end_ts, start_ts
		daily_date = None
		try:
			if self.select_daily_tanggal_awal is not None and self.select_daily_tanggal_awal.dateTime().isValid():
				daily_date = self.select_daily_tanggal_awal.dateTime().toPyDateTime().date()
		except Exception:
			daily_date = None
		self._log_home_range_change(start_ts, end_ts, daily_date)

		# Tampilkan default rentang ke widget (gunakan epoch ms yang robust)
		try:
			if self.select_avg_tanggal_awal is not None:
				if not preserve_range or not self.select_avg_tanggal_awal.dateTime().isValid():
					start_ms = int(pd.Timestamp(start_ts).value // 1_000_000)
					# Hindari rekursi: blokir sinyal saat set nilai programmatically
					self.select_avg_tanggal_awal.blockSignals(True)
					self.select_avg_tanggal_awal.setDateTime(QDateTime.fromMSecsSinceEpoch(start_ms))
					self.select_avg_tanggal_awal.blockSignals(False)
		except Exception:
			pass
		try:
			if self.select_avg_tanggal_akhir is not None:
				if not preserve_range or not self.select_avg_tanggal_akhir.dateTime().isValid():
					end_ms = int(pd.Timestamp(end_ts).value // 1_000_000)
					self.select_avg_tanggal_akhir.blockSignals(True)
					self.select_avg_tanggal_akhir.setDateTime(QDateTime.fromMSecsSinceEpoch(end_ms))
					self.select_avg_tanggal_akhir.blockSignals(False)
		except Exception:
			pass
		df_avg = df[(df["ts"] >= start_ts) & (df["ts"] <= end_ts)].copy()
		if df_avg.empty:
			df_avg = df.copy()
		_bump(10)

		# Update Average table
		avg_tbl = self._build_home_table(df_avg, "ts")
		self._set_table(self.tabel_HOME_average_2, avg_tbl)
		if self.value_avg_jumlahdata is not None:
			try:
				self.value_avg_jumlahdata.display(int(len(avg_tbl)))
			except Exception:
				pass
		_bump(10)

		# Average summary
		avg_watt = float(df_avg["watt"].mean())
		avg_volt = float(df_avg["voltage"].mean())
		avg_curr = float(df_avg["current"].mean())
		avg_freq = float(df_avg["frequency"].mean())
		avg_pf = float(df_avg["pf"].mean())
		avg_energy = self._energy_kwh(df_avg)
		self._set_lcd(self.value_avg_daya, avg_watt)
		self._set_lcd(self.value_avg_tegangan, avg_volt)
		self._set_lcd(self.value_avg_arus, avg_curr)
		self._set_lcd(self.value_avg_frekuensi, avg_freq)
		self._set_lcd(self.value_avg_pf, avg_pf)
		self._set_lcd(self.value_avg_energi, avg_energy)
		try:
			self.logger.log_event(
				lvl1="INFO",
				lvl2="HOME",
				lvl3="BASE",
				lvl4="GENERAL",
				evt=EVT.HOME_AVG_CALC,
				route_to=["HOME"],
				fields=[
					f"rows={len(avg_tbl)}",
					f"æV={avg_volt:.2f}",
					f"æA={avg_curr:.2f}",
					f"æW={avg_watt:.2f}",
					f"ækWh={avg_energy:.4f}",
					f"æHz={avg_freq:.2f}",
					f"æPF={avg_pf:.2f}",
				],
			)
		except Exception:
			pass
		_bump(10)

		# Average graph params
		avg_params: list[str] = []
		if getattr(self.checkBox_avg_daya, "isChecked", lambda: False)():
			avg_params.append("watt")
		if getattr(self.checkBox_avg_tegangan, "isChecked", lambda: False)():
			avg_params.append("voltage")
		if getattr(self.checkBox_avg_energi, "isChecked", lambda: False)():
			avg_params.append("energy_kwh")
		if getattr(self.checkBox_avg_arus, "isChecked", lambda: False)():
			avg_params.append("current")
		if getattr(self.checkBox_avg_frekuensi, "isChecked", lambda: False)():
			avg_params.append("frequency")
		if getattr(self.checkBox_avg_pf, "isChecked", lambda: False)():
			avg_params.append("pf")
		# Jika tak ada yang dicentang, tampilkan minimal Daya
		if not avg_params:
			avg_params = ["watt"]
		# Arus/Frekuensi/PF belum tersedia di DB; di-skip bila dicentang
		# OLD approach - creates popup windows!
		# self._draw_home_matplotlib(getattr(self, "home_avg_canvas", None), getattr(self, "home_avg_ax", None), df_avg, avg_params, "Average")
		# NEW R4: Use InteractiveChartWidget instead (initialized in _init_interactive_charts)
		_bump(15)

		# --- Daily range (selected date atau last date) ---
		if self.select_daily_tanggal_awal is not None:
			try:
				chosen = pd.to_datetime(self.select_daily_tanggal_awal.dateTime().toPyDateTime())
			except Exception:
				chosen = end_ts
		else:
			chosen = end_ts
		chosen_day = chosen.normalize()
		df_daily = df[(df["ts"] >= chosen_day) & (df["ts"] < chosen_day + pd.Timedelta(days=1))].copy()
		if df_daily.empty:
			# fallback ke hari terakhir yang ada data
			last_day = end_ts.normalize()
			df_daily = df[(df["ts"] >= last_day) & (df["ts"] < last_day + pd.Timedelta(days=1))].copy()
			try:
				if self.select_daily_tanggal_awal is not None:
					if not preserve_daily or not self.select_daily_tanggal_awal.dateTime().isValid():
						self.select_daily_tanggal_awal.blockSignals(True)
						self.select_daily_tanggal_awal.setDateTime(last_day.to_pydatetime())
						self.select_daily_tanggal_awal.blockSignals(False)
			except Exception:
				pass
		_bump(10)

		# Daily table & count
		daily_tbl = self._build_home_table(df_daily, "ts")
		self._set_table(self.tabel_HOME_daily_2, daily_tbl)
		if self.value_daily_jumlahdata is not None:
			try:
				self.value_daily_jumlahdata.display(int(len(daily_tbl)))
			except Exception:
				pass
		_bump(10)

		# Daily summary
		if df_daily.empty:
			daily_watt = 0.0
			daily_volt = 0.0
			daily_curr = 0.0
			daily_freq = 0.0
			daily_pf = 0.0
			daily_energy = 0.0
		else:
			daily_watt = float(df_daily["watt"].mean())
			daily_volt = float(df_daily["voltage"].mean())
			daily_curr = float(df_daily["current"].mean())
			daily_freq = float(df_daily["frequency"].mean())
			daily_pf = float(df_daily["pf"].mean())
			daily_energy = self._energy_kwh(df_daily)
		self._set_lcd(self.value_daily_daya, daily_watt)
		self._set_lcd(self.value_daily_tegangan, daily_volt)
		self._set_lcd(self.value_daily_arus, daily_curr)
		self._set_lcd(self.value_daily_frekuensi, daily_freq)
		self._set_lcd(self.value_daily_pf, daily_pf)
		self._set_lcd(self.value_daily_energi, daily_energy)
		try:
			self.logger.log_event(
				lvl1="INFO",
				lvl2="HOME",
				lvl3="BASE",
				lvl4="GENERAL",
				evt=EVT.HOME_DAILY_CALC,
				route_to=["HOME"],
				fields=[
					f"rows={len(daily_tbl)}",
					f"æV={daily_volt:.2f}",
					f"æA={daily_curr:.2f}",
					f"æW={daily_watt:.2f}",
					f"ækWh={daily_energy:.4f}",
					f"æHz={daily_freq:.2f}",
					f"æPF={daily_pf:.2f}",
				],
			)
		except Exception:
			pass
		_bump(10)

		# Daily graph params
		daily_params: list[str] = []
		if getattr(self.checkBox_daily_daya, "isChecked", lambda: False)():
			daily_params.append("watt")
		if getattr(self.checkBox_daily_tegangan, "isChecked", lambda: False)():
			daily_params.append("voltage")
		if getattr(self.checkBox_daily_energi, "isChecked", lambda: False)():
			daily_params.append("energy_kwh")
		if getattr(self.checkBox_daily_arus, "isChecked", lambda: False)():
			daily_params.append("current")
		if getattr(self.checkBox_daily_frekuensi, "isChecked", lambda: False)():
			daily_params.append("frequency")
		if getattr(self.checkBox_daily_pf, "isChecked", lambda: False)():
			daily_params.append("pf")
		if not daily_params:
			daily_params = ["watt"]
		# OLD approach - creates popup windows!
		# self._draw_home_matplotlib(getattr(self, "home_daily_canvas", None), getattr(self, "home_daily_ax", None), df_daily, daily_params, "Daily")
		# NEW R4: Use InteractiveChartWidget instead (initialized in _init_interactive_charts)
		_bump(15)

		# Pastikan progress 100% dan log proses
		try:
			if use_progress and hasattr(self, "progressBar_3"):
				self.progressBar_3.setMaximum(100)
				self.progressBar_3.setValue(100)
			self.logger.log_event(
				lvl1="INFO",
				lvl2="HOME",
				lvl3="BASE",
				lvl4="GENERAL",
				evt=EVT.HOME_SUMMARY_REFRESH,
				route_to=["HOME"],
				fields=[f"avg_rows={len(avg_tbl)}", f"daily_rows={len(daily_tbl)}"],
				result="status=SYNCED",
			)
		except Exception:
			pass

	def closeEvent(self, event) -> None:  # type: ignore[override]
		"""Override closeEvent untuk memastikan worker & resource dibersihkan."""

		if self.worker is not None and self.worker.isRunning():
			reply = QMessageBox.question(
				self,
				"Quit While Running",
				"Analysis is still running. Do you really want to quit?",
				QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
				QMessageBox.StandardButton.No,
			)
			if reply != QMessageBox.StandardButton.Yes:
				event.ignore()
				return
			self.worker.stop()

		# Bersihkan cache runtime (SQLite raw telemetry) agar aplikasi selalu default
		try:
			deleted_map = self.db_mgr.clear_all_runtime()
			self.raw_data = None
			self._initiation_completed = False
			if hasattr(self, "progressBar"):
				self.progressBar.setValue(0)
			if hasattr(self, "progressBar_3"):
				self.progressBar_3.setValue(0)
			self.start_analysis_PB.setEnabled(False)
			self._update_data_status_label()
			self.logger.log("INFO", f"Main window closing. Cleared runtime cache: raw={deleted_map.get('raw_deleted',0)} rows, exp={deleted_map.get('exp_deleted',0)} rows.")
		except Exception as e:
			self.logger.log("ERROR", f"Failed to clear runtime cache on exit: {e}")
		try:
			from utils.resource_manager import ResourceManager

			ResourceManager.cleanup()
		except Exception:
			# Jangan blokir penutupan hanya karena cleanup gagal
			pass
		super().closeEvent(event)

	def _persist_experiment_to_db(self, results: dict) -> None:
		"""Menyimpan ringkasan eksperimen ke SQLite (log + hasil per metode).

		Menggunakan DBManager.save_experiment_log dan save_result.
		"""

		if not results:
			return

		params = self._last_run_params or self.get_ui_params() or {}
		config_json = json.dumps(params, default=str)
		try:
			split_ratio = float(params.get("global", {}).get("split_ratio", 0.0))
		except Exception:
			split_ratio = 0.0

		run_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		run_id = self.db_mgr.save_experiment_log(run_date, config_json, split_ratio)
		self.logger.log("SUCCESS", f"Experiment log saved with run_id={run_id}")

		for method in ["fts", "ann", "arima"]:
			if method not in results:
				continue
			entry = results[method]
			metrics = entry.get("metrics", {})
			artifacts = entry.get("artifacts", {})
			forecast = entry.get("forecast", [])
			artifacts_json = json.dumps(artifacts, default=str)
			forecast_json = json.dumps(forecast, default=float)
			self.db_mgr.save_result(run_id, method.upper(), metrics, artifacts_json, forecast_json)
		self.logger.log("SUCCESS", "Experiment results stored to database for all methods.")
	def _on_arima_mode_changed(self, _state) -> None:
		"""Pastikan hanya satu checkbox ARIMA yang aktif (seasonal/nonseasonal)."""

		if self.Param_Status_Submit_ARIMA_seasonal is None or self.Param_Status_Submit_ARIMA_nonseasonal is None:
			return

		seasonal = self.Param_Status_Submit_ARIMA_seasonal.isChecked()
		nonseasonal = self.Param_Status_Submit_ARIMA_nonseasonal.isChecked()

		if seasonal and nonseasonal:
			sender = self.sender()
			if sender is not None:
				sender.blockSignals(True)
				try:
					sender.setChecked(False)
				finally:
					sender.blockSignals(False)
			QMessageBox.warning(
				self,
				"Invalid ARIMA Mode",
				"Untuk Initial Metode ARIMA hanya bisa pilih satu parameter seasonal atau nonseasonal.",
			)

		# RUN-4 PL-04: Use unified lock mechanism for ARIMA parameters
		locked = seasonal or nonseasonal
		self._unified_parameter_lock_handler('arima', locked)
		self._log_submit_arima(seasonal, nonseasonal)
		self._check_all_locks()

	def _log_submit_arima(self, seasonal: bool, nonseasonal: bool) -> None:
		if getattr(self, "_startup_in_progress", False):
			return
		if not seasonal and not nonseasonal:
			return
		mode = "seasonal" if seasonal else "nonseasonal"
		p = d = q = "-"
		try:
			p = str(self.Param_initial_value_ARIMA_nonSeasonal_p.value())
			d = str(self.Param_initial_value_ARIMA_nonSeasonal_d.value())
			q = str(self.Param_initial_value_ARIMA_nonSeasonal_q.value())
		except Exception:
			pass
		P = D = Q = "-"
		s = "-"
		if seasonal:
			if hasattr(self, "Param_initial_value_ARIMA_Seasonal_P"):
				try:
					P = str(self.Param_initial_value_ARIMA_Seasonal_P.value())
				except Exception:
					P = "-"
			if hasattr(self, "Param_initial_value_ARIMA_Seasonal_D"):
				try:
					D = str(self.Param_initial_value_ARIMA_Seasonal_D.value())
				except Exception:
					D = "-"
			if hasattr(self, "Param_initial_value_ARIMA_Seasonal_Q"):
				try:
					Q = str(self.Param_initial_value_ARIMA_Seasonal_Q.value())
				except Exception:
					Q = "-"
			if hasattr(self, "Param_initial_value_ARIMA_Seasonal_s"):
				try:
					s = str(self.Param_initial_value_ARIMA_Seasonal_s.value())
				except Exception:
					s = "-"
		else:
			s = "0"
		self.logger.log_event(
			lvl1="INIT",
			lvl2="INITIAL",
			lvl3="CAL",
			lvl4="ARIMA",
			evt=EVT.PARAM_ARIMA_SUBMIT,
			route_to=["MAIN", "RESUME"],
			fields=[
				f"?mode={mode}",
				f"?order=({p},{d},{q})",
				f"?seasonal_order=({P},{D},{Q},{s})",
			],
		)
		msg = f"Initial Data Parameter for ARIMA submitted -> Mode : {mode} | p,d,q : ({p},{d},{q}) | P,D,Q : ({P},{D},{Q}) | s : {s} -> Value lock for analysis"
		self.logger.log("INFO", msg)