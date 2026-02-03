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
PDF Report Export Manager

Version: 1.0.1
Created: December 2025
"""

import os
import hashlib
import shutil
import subprocess
import tempfile
from typing import Dict, Any, List
from datetime import datetime
import io

import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas

# RUN-3: Try to import font registration modules (graceful fallback)
try:
	from reportlab.pdfmetrics import registerFont
	from reportlab.pdfbase.ttfonts import TTFont
	_FONT_REGISTRATION_AVAILABLE = True
except ImportError:
	_FONT_REGISTRATION_AVAILABLE = False
	registerFont = None
	TTFont = None

from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from reportlab.platypus.frames import Frame
import matplotlib.pyplot as plt
import matplotlib

from utils import logging_events as EVT
from utils.artifact_exporter import export_academic_artifacts

# RUN-3: Typography & Font System Enhancement
def _register_bahnschrift_fonts():
	"""Register Bahnschrift fonts for PDF generation (RUN-3)."""
	if not _FONT_REGISTRATION_AVAILABLE:
		return False
		
	try:
		# Try to register Bahnschrift fonts (Windows system fonts)
		# Note: These fonts may not be available on all systems
		bahnschrift_regular = r"C:\Windows\Fonts\bahnschrift.ttf"
		bahnschrift_light = r"C:\Windows\Fonts\BAHN____.ttf"  # Light Condensed variant
		
		# Register if available, otherwise fallback to Helvetica
		if os.path.exists(bahnschrift_regular):
			registerFont(TTFont('Bahnschrift', bahnschrift_regular))
			registerFont(TTFont('Bahnschrift-Bold', bahnschrift_regular))  # Same file, weight handled by ReportLab
		if os.path.exists(bahnschrift_light):
			registerFont(TTFont('Bahnschrift-Light', bahnschrift_light))
			
		return True
	except Exception:
		# Graceful fallback to Helvetica family
		return False

# Initialize font registration on module load
_BAHNSCHRIFT_AVAILABLE = _register_bahnschrift_fonts()

def _get_font_name(font_type: str) -> str:
	"""Get appropriate font name based on availability (RUN-3)."""
	if _BAHNSCHRIFT_AVAILABLE:
		font_map = {
			'heading': 'Bahnschrift-Bold',
			'heading-regular': 'Bahnschrift', 
			'body': 'Bahnschrift-Light',
			'body-fallback': 'Bahnschrift'
		}
		return font_map.get(font_type, 'Bahnschrift')
	else:
		# Fallback to Helvetica family
		font_map = {
			'heading': 'Helvetica-Bold',
			'heading-regular': 'Helvetica',
			'body': 'Helvetica',
			'body-fallback': 'Helvetica'
		}
		return font_map.get(font_type, 'Helvetica')

# RUN-2: Enhanced Chart Styling Configuration
CHART_CONFIG = {
    "dpi": 250,  # Enhanced DPI for publication quality
    "style": "seaborn-v0_8-whitegrid",  # Professional style
    "colors": {
        "primary": "#2563eb",
        "secondary": "#10b981", 
        "accent": "#f59e0b",
        "danger": "#ef4444",
        "methods": {
            "fts": "#2563eb",
            "ann": "#10b981", 
            "arima": "#8b5cf6",
            "actual": "#111827",
            "naive": "#6b7280",
            "ma": "#f59e0b",
            "pred": "#0ea5e9"
        },
        "sensors": {
            "watt": "#f59e0b",
            "energy_kwh": "#10b981",
            "voltage": "#ef4444", 
            "frequency": "#8b5cf6",
            "current": "#06b6d4",
            "pf": "#64748b"
        },
        "status": {
            "excellent": "#10b981",
            "good": "#fbbf24",
            "fair": "#f87171"
        }
    },
    "figure_params": {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "DejaVu Sans", "Liberation Sans"],
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
        "figure.titlesize": 11
    }
}


class ExportManager:

	"""Mengelola export hasil analisis ke file Excel multi-sheet.

	Struktur `results` mengikuti output CalculationWorker:
	{
	  "data": {"test": pd.Series, ...},
	  "fts": {"metrics": {...}, "forecast": [...], "artifacts": {...}},
	  "ann": {...},
	  "arima": {...},
	}
	"""

	@staticmethod
	def _apply_professional_styling(ax, title: str = None, xlabel: str = None, ylabel: str = None) -> None:
		"""Apply professional chart styling for publication quality."""
		# RUN-2: Enhanced Chart Styling
		# Apply professional styling
		ax.spines['top'].set_visible(False)
		ax.spines['right'].set_visible(False)
		ax.spines['left'].set_color('#e5e7eb')
		ax.spines['bottom'].set_color('#e5e7eb')
		ax.spines['left'].set_linewidth(0.5)
		ax.spines['bottom'].set_linewidth(0.5)
		
		# Enhanced grid
		ax.grid(True, alpha=0.15, linestyle='-', linewidth=0.5, color='#9ca3af')
		ax.set_axisbelow(True)
		
		# Professional typography
		if title:
			ax.set_title(title, fontsize=CHART_CONFIG['figure_params']['axes.titlesize'], 
					 fontweight='600', color='#1f2937', pad=12)
		if xlabel:
			ax.set_xlabel(xlabel, fontsize=CHART_CONFIG['figure_params']['axes.labelsize'],
					  color='#374151', labelpad=8)
		if ylabel:
			ax.set_ylabel(ylabel, fontsize=CHART_CONFIG['figure_params']['axes.labelsize'],
					  color='#374151', labelpad=8)
		
		# Enhanced tick styling
		ax.tick_params(axis='both', which='major', labelsize=CHART_CONFIG['figure_params']['xtick.labelsize'],
					  colors='#4b5563', width=0.5, length=3)
		ax.tick_params(axis='both', which='minor', width=0, length=0)

	@staticmethod
	def _setup_matplotlib_style() -> None:
		"""Setup matplotlib style for professional charts."""
		# RUN-2: Professional matplotlib configuration
		try:
			matplotlib.style.use(CHART_CONFIG['style'])
		except OSError:
			# Fallback to default if seaborn style not available
			pass
		
		# Apply professional parameters
		matplotlib.rcParams.update(CHART_CONFIG['figure_params'])
		matplotlib.rcParams['savefig.dpi'] = CHART_CONFIG['dpi']
		matplotlib.rcParams['figure.dpi'] = 100  # Display DPI
		matplotlib.rcParams['savefig.facecolor'] = 'white'
		matplotlib.rcParams['savefig.edgecolor'] = 'none'

	@staticmethod
	def _apply_professional_styling(ax, title: str = None, xlabel: str = None, ylabel: str = None) -> None:
		"""Apply professional chart styling for publication quality."""
		# RUN-2: Enhanced Chart Styling
		# Apply professional styling
		ax.spines['top'].set_visible(False)
		ax.spines['right'].set_visible(False)
		ax.spines['left'].set_color('#e5e7eb')
		ax.spines['bottom'].set_color('#e5e7eb')
		ax.spines['left'].set_linewidth(0.5)
		ax.spines['bottom'].set_linewidth(0.5)
		
		# Enhanced grid
		ax.grid(True, alpha=0.15, linestyle='-', linewidth=0.5, color='#9ca3af')
		ax.set_axisbelow(True)
		
		# Professional typography
		if title:
			ax.set_title(title, fontsize=CHART_CONFIG['figure_params']['axes.titlesize'], 
						 fontweight='600', color='#1f2937', pad=12)
		if xlabel:
			ax.set_xlabel(xlabel, fontsize=CHART_CONFIG['figure_params']['axes.labelsize'],
						  color='#374151', labelpad=8)
		if ylabel:
			ax.set_ylabel(ylabel, fontsize=CHART_CONFIG['figure_params']['axes.labelsize'],
						  color='#374151', labelpad=8)
		
		# Enhanced tick styling
		ax.tick_params(axis='both', which='major', labelsize=CHART_CONFIG['figure_params']['xtick.labelsize'],
					   colors='#4b5563', width=0.5, length=3)
		ax.tick_params(axis='both', which='minor', width=0, length=0)

	@staticmethod
	def _to_float(val, default: float = 0.0) -> float:
		try:
			return float(val)
		except (TypeError, ValueError):
			return float(default)

	@staticmethod
	def _fmt_metric(val) -> str:
		return f"{ExportManager._to_float(val):.4f}"

	@staticmethod
	def _fmt_mape(val) -> str:
		return f"{ExportManager._to_float(val):.2f}"

	@staticmethod
	def _fmt_date(val) -> str:
		if isinstance(val, pd.Timestamp):
			return val.strftime("%d/%m/%Y")
		try:
			return pd.to_datetime(val).strftime("%d/%m/%Y")
		except Exception:
			return "-"

	@staticmethod
	def _fmt_ts(val) -> str:
		if isinstance(val, pd.Timestamp):
			return val.strftime("%d-%m-%Y %H:%M:%S")
		try:
			return pd.to_datetime(val).strftime("%d-%m-%Y %H:%M:%S")
		except Exception:
			return "-"

	@staticmethod
	def _fmt_number(val, decimals: int = 2) -> str:
		try:
			if val is None or (isinstance(val, float) and pd.isna(val)):
				return "-"
			return f"{float(val):.{decimals}f}"
		except Exception:
			return "-"

	@staticmethod
	def _style_table(
		table: Table,
		align: str = "CENTER",
		font_size: int = 8,
		zebra: bool = True,
	) -> None:
		style = [
			("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
			("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
			("FONTNAME", (0, 0), (-1, 0), _get_font_name('heading') if _BAHNSCHRIFT_AVAILABLE else "Helvetica-Bold"),
			("ALIGN", (0, 0), (-1, -1), align),
			("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
			("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#334155")),
			("FONTSIZE", (0, 0), (-1, -1), font_size),
			("LEFTPADDING", (0, 0), (-1, -1), 4),
			("RIGHTPADDING", (0, 0), (-1, -1), 4),
			("TOPPADDING", (0, 0), (-1, -1), 3),
			("BOTTOMPADDING", (0, 0), (-1, -1), 3),
		]
		if zebra:
			style.append(
				("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")])
			)
		table.setStyle(TableStyle(style))

	@staticmethod
	def _draw_footer(canvas, doc, label: str) -> None:
		canvas.saveState()
		canvas.setFont(_get_font_name('body') if _BAHNSCHRIFT_AVAILABLE else "Helvetica", 8)  # RUN-3: Bahnschrift-Light
		canvas.setFillColor(colors.HexColor("#64748b"))
		canvas.drawString(doc.leftMargin, 1.1 * cm, label)
		canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 1.1 * cm, f"Page {canvas.getPageNumber()}")
		canvas.restoreState()
	
	@staticmethod
	def _draw_enhanced_footer(canvas, doc, label: str, total_pages: int, is_title_page: bool = False) -> None:
		"""Enhanced footer dengan watermark dan page numbering format 'Page x of y'."""
		canvas.saveState()
		
		# RUN-2: Watermark Implementation
		logo_path = "output_data/logo-trilogi-clean.png"  # Use cleaned PNG asset
		if os.path.exists(logo_path):
			try:
				# Center watermark (all pages)
				canvas.saveState()
				canvas.setFillAlpha(0.15)  # Standard watermark opacity
				page_width, page_height = doc.pagesize
				logo_width = 300  # Increased from 200
				logo_height = 300  # Increased from 200
				x = (page_width - logo_width) / 2
				y = (page_height - logo_height) / 2
				canvas.drawImage(logo_path, x, y, width=logo_width, height=logo_height, 
								preserveAspectRatio=True, mask='auto')
				canvas.restoreState()
				
				# Top-right watermark (except title page)
				if not is_title_page:
					canvas.saveState()
					canvas.setFillAlpha(0.2)
					logo_tr_width = 60
					logo_tr_height = 60
					x_tr = page_width - doc.rightMargin - logo_tr_width - 0.5*cm
					y_tr = page_height - doc.topMargin + 0.5*cm
					canvas.drawImage(logo_path, x_tr, y_tr, width=logo_tr_width, height=logo_tr_height,
									preserveAspectRatio=True, mask='auto')
					canvas.restoreState()
			except Exception:
				pass  # Graceful fallback if logo not found
		
		# Footer text and page numbering
		canvas.setFont(_get_font_name('body') if _BAHNSCHRIFT_AVAILABLE else "Helvetica", 8)
		canvas.setFillColor(colors.HexColor("#64748b"))
		canvas.setFillAlpha(1.0)
		
		# Left: PPDL Resume Report (preserve existing)
		canvas.drawString(doc.leftMargin, 1.1 * cm, "PPDL Resume Report")
		
		# Right: Page numbering - BETTER FIX: Dynamic total calculation 
		if not is_title_page:
			page_num = canvas.getPageNumber()
			# Use dynamic estimation that grows with actual content
			estimated_total = max(page_num + 3, total_pages if total_pages > page_num else page_num + 5)
			canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 1.1 * cm, f"Page {page_num} of {estimated_total}")
		
		canvas.restoreState()

	@staticmethod
	def _generate_title_page(elements, styles, params: Dict = None) -> None:
		"""RUN-1: Generate professional title page sesuai format-1.png."""
		try:
			# Professional title page styling
			title_main_style = ParagraphStyle(
				'TitleMain',
				parent=styles['Title'],
				fontSize=24,
				textColor=colors.HexColor('#1e3a8a'),
				alignment=TA_CENTER,
				spaceAfter=30,
				fontName=_get_font_name('heading')  # RUN-3: Bahnschrift-Bold
			)
			
			title_sub_style = ParagraphStyle(
				'TitleSub',
				parent=styles['Heading2'],
				fontSize=16,
				textColor=colors.HexColor('#2563eb'),
				alignment=TA_CENTER,
				spaceAfter=20,
				fontName=_get_font_name('heading-regular')  # RUN-3: Bahnschrift
			)
			
			method_style = ParagraphStyle(
				'MethodStyle',
				parent=styles['Normal'],
				fontSize=12,
				alignment=TA_CENTER,
				spaceAfter=15,
				fontName=_get_font_name('body')  # RUN-3: Bahnschrift-Light
			)
			
			date_style = ParagraphStyle(
				'DateStyle',
				parent=styles['Normal'],
				fontSize=10,
				alignment=TA_CENTER,
				spaceAfter=10,
				fontName=_get_font_name('body')  # RUN-3: Bahnschrift-Light
			)
			
			# Add spacing for title page
			elements.append(Spacer(1, 4*cm))
			
			# Main title
			elements.append(Paragraph("RESUME REPORT", title_main_style))
			
			# Spacing
			elements.append(Spacer(1, 2*cm))
			
			# Subtitle
			elements.append(Paragraph("PREDIKSI PEMAKAIAN DAYA LISTRIK", title_sub_style))
			
			# Spacing
			elements.append(Spacer(1, 1.5*cm))
			
			# Primary method
			elements.append(Paragraph("<b>PRIMARY METHOD</b>", method_style))
			elements.append(Paragraph("<i>Fuzzy Time Series</i>", method_style))
			
			# Spacing
			elements.append(Spacer(1, 1*cm))
			
			# Comparative methods
			elements.append(Paragraph("<b>COMPARATIVE METHODS</b>", method_style))
			elements.append(Paragraph("<i>Artificial Neural Network, dan Autoregressive<br/>Integrated Moving Average</i>", method_style))
			
			# Spacing
			elements.append(Spacer(1, 3*cm))
			
			# Generated date
			generated_date = datetime.now().strftime('%d %B %Y, %H:%M:%S')
			# FIX: Use actual GUID from system export (params should contain export_id)
			run_guid = params.get('export_id', params.get('run_guid', 
									 hashlib.md5(f"{generated_date}".encode()).hexdigest()[:8].upper())) if params else 'Unknown'
			
			elements.append(Paragraph(f"[Generated: {generated_date}]", date_style))
			elements.append(Paragraph(f"[Run ID: {run_guid}]", date_style))
			
		except Exception:
			# Fallback to simple title if styling fails
			elements.append(Spacer(1, 4*cm))
			elements.append(Paragraph("RESUME REPORT", styles['Title']))
			elements.append(Paragraph("PREDIKSI PEMAKAIAN DAYA LISTRIK", styles['Heading2']))
		
		# Page break after title
		elements.append(PageBreak())
	
	@staticmethod
	def _generate_table_of_contents(elements, styles, results: Dict) -> None:
		"""RUN-1: Generate dynamic table of contents."""
		toc_style = ParagraphStyle(
			'TOCTitle',
			parent=styles['Heading1'],
			fontSize=20,
			textColor=colors.HexColor('#1e3a8a'),
			alignment=TA_CENTER,
			spaceAfter=30,
			fontName=_get_font_name('heading')  # RUN-3: Bahnschrift-Bold
		)
		
		toc_entry_style = ParagraphStyle(
			'TOCEntry',
			parent=styles['Normal'],
			fontSize=11,
			alignment=TA_LEFT,
			spaceAfter=8,
			leftIndent=20,
			fontName=_get_font_name('body')  # RUN-3: Bahnschrift-Light
		)
		
		# TOC Title
		elements.append(Spacer(1, 2*cm))
		elements.append(Paragraph("TABLE OF CONTENT", toc_style))
		elements.append(Spacer(1, 1*cm))
		
		# FIX: Dynamic TOC with realistic page estimates
		current_page = 3  # Start after title page + TOC
		toc_entries = [
			("1. Executive Summary", str(current_page)),
		]
		current_page += 2  # Executive summary takes ~2 pages
		
		toc_entries.append(("2. Data Overview", str(current_page)))
		current_page += 1
		
		toc_entries.append(("3. Analysis Configuration", str(current_page)))
		current_page += 1
		
		# Add dynamic sections based on available results
		section_num = 4
		if 'fts' in results:
			toc_entries.append((f"{section_num}. Fuzzy Time Series Analysis", str(current_page)))
			current_page += 4  # FTS analysis with math doc takes ~4 pages
			section_num += 1
		
		if 'ann' in results:
			toc_entries.append((f"{section_num}. Artificial Neural Network Analysis", str(current_page)))
			current_page += 2
			section_num += 1
		
		if 'arima' in results:
			toc_entries.append((f"{section_num}. ARIMA Analysis", str(current_page)))
			current_page += 2
			section_num += 1
		
		toc_entries.extend([
			(f"{section_num}. Model Comparison", str(current_page)),
			(f"{section_num + 1}. Statistical Analysis", str(current_page + 2)),
			(f"{section_num + 2}. Technical Details", str(current_page + 4))
		])
		
		# Create TOC table
		toc_data = []
		for entry, page in toc_entries:
			toc_data.append([entry, "...", page])
		
		toc_table = Table(toc_data, colWidths=[12*cm, 2*cm, 2*cm])
		toc_table.setStyle(TableStyle([
			('ALIGN', (0, 0), (-1, -1), 'LEFT'),
			('ALIGN', (2, 0), (2, -1), 'RIGHT'),
			('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
			('FONTSIZE', (0, 0), (-1, -1), 11),
			('BOTTOMPADDING', (0, 0), (-1, -1), 8),
			('TOPPADDING', (0, 0), (-1, -1), 4),
		]))
		
		elements.append(toc_table)
		elements.append(PageBreak())
	
	@staticmethod
	def _normalize_raw_df(raw_df: pd.DataFrame | None) -> pd.DataFrame:
		if raw_df is None or raw_df.empty:
			return pd.DataFrame()
		df = raw_df.copy()
		rename_map = {}
		for src, dest in {
			"W": "watt",
			"V": "voltage",
			"A": "current",
			"F": "frequency",
			"kWh": "energy_kwh",
		}.items():
			if src in df.columns and dest not in df.columns:
				rename_map[src] = dest
		if rename_map:
			df = df.rename(columns=rename_map)
		if "timestamp" in df.columns:
			df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
		elif "ts_server" in df.columns:
			df["timestamp"] = pd.to_datetime(df["ts_server"], unit="ms", errors="coerce")
		else:
			df["timestamp"] = pd.NaT
		for col in ["watt", "voltage", "current", "frequency", "energy_kwh", "pf"]:
			if col not in df.columns:
				df[col] = pd.NA
		if "synthetic" not in df.columns:
			df["synthetic"] = pd.NA
		df = df[["timestamp", "watt", "voltage", "current", "frequency", "energy_kwh", "pf", "synthetic"]]
		df = df.sort_values("timestamp").reset_index(drop=True)
		return df

	@staticmethod
	def _compute_median_interval_seconds(df: pd.DataFrame) -> float:
		if df.empty or "timestamp" not in df.columns:
			return 0.0
		ts = pd.to_datetime(df["timestamp"], errors="coerce").dropna().sort_values()
		if len(ts) < 2:
			return 0.0
		diffs = ts.diff().dt.total_seconds().dropna()
		if diffs.empty:
			return 0.0
		median_val = diffs.median()
		try:
			return float(median_val)
		except Exception:
			return 0.0

	@staticmethod
	def _build_global_resume_chart(df: pd.DataFrame) -> Image | None:
		if df is None or df.empty:
			return None
		df_plot = df.dropna(subset=["timestamp"]).copy()
		if df_plot.empty:
			return None
		max_points = 800
		if len(df_plot) > max_points:
			stride = max(1, len(df_plot) // max_points)
			df_plot = df_plot.iloc[::stride, :].copy()

		# RUN-2: Professional styling setup
		ExportManager._setup_matplotlib_style()
		
		# RUN-2: Use standardized color scheme
		colors_map = CHART_CONFIG['colors']['sensors']
		labels_map = {
			"watt": "Daya (W)",
			"energy_kwh": "Energi (kWh)",
			"voltage": "Tegangan (V)",
			"frequency": "Frekuensi (Hz)",
			"current": "Arus (A)",
			"pf": "PF",
		}

		fig, ax = plt.subplots(figsize=(6.8, 3.2))
		for key in ["watt", "energy_kwh", "voltage", "frequency", "current", "pf"]:
			if key in df_plot.columns and df_plot[key].notna().any():
				ax.plot(
					df_plot["timestamp"],
					df_plot[key],
					label=labels_map.get(key, key),
					color=colors_map.get(key, CHART_CONFIG['colors']['primary']),
					linewidth=1.6,  # RUN-2: Slightly thicker lines
					alpha=0.85  # RUN-2: Slight transparency for overlap
				)
		
		# RUN-2: Apply professional styling
		ExportManager._apply_professional_styling(ax, 
			title="Global Resume - Sensor Trends",
			xlabel="Time", 
			ylabel="Value")
		
		# RUN-2: Enhanced legend styling
		legend = ax.legend(fontsize=CHART_CONFIG['figure_params']['legend.fontsize'], 
						 loc="upper left", frameon=True, fancybox=True, 
						 shadow=True, framealpha=0.9)
		legend.get_frame().set_facecolor('white')
		legend.get_frame().set_edgecolor('#e5e7eb')
		legend.get_frame().set_linewidth(0.5)
		
		fig.autofmt_xdate()
		plt.tight_layout()

		img_buffer = io.BytesIO()
		# RUN-2: Enhanced DPI for publication quality
		plt.savefig(img_buffer, format="png", dpi=CHART_CONFIG['dpi'], bbox_inches="tight")
		img_buffer.seek(0)
		plt.close(fig)
		return Image(img_buffer, width=16 * cm, height=7 * cm)

	@staticmethod
	def _build_single_series_chart(
		df: pd.DataFrame,
		key: str,
		title: str,
		color: str,
		y_label: str,
	) -> Image | None:
		if df is None or df.empty or key not in df.columns:
			return None
		df_plot = df.dropna(subset=["timestamp", key]).copy()
		if df_plot.empty:
			return None
		max_points = 800
		if len(df_plot) > max_points:
			stride = max(1, len(df_plot) // max_points)
			df_plot = df_plot.iloc[::stride, :].copy()

		# RUN-2: Professional styling setup
		ExportManager._setup_matplotlib_style()
		
		fig, ax = plt.subplots(figsize=(6.8, 3.0))
		
		# RUN-2: Use standardized color or fallback to sensor colors
		final_color = CHART_CONFIG['colors']['sensors'].get(key, color)
		
		ax.plot(
			df_plot["timestamp"],
			df_plot[key],
			label=title,
			color=final_color,
			linewidth=1.8,  # RUN-2: Slightly thicker for single series
			alpha=0.9
		)
		
		# RUN-2: Apply professional styling
		ExportManager._apply_professional_styling(ax, title=title, xlabel="Time", ylabel=y_label)
		
		# RUN-2: Enhanced legend styling
		legend = ax.legend(fontsize=CHART_CONFIG['figure_params']['legend.fontsize'], 
						 loc="upper left", frameon=True, fancybox=True,
						 shadow=True, framealpha=0.9)
		legend.get_frame().set_facecolor('white')
		legend.get_frame().set_edgecolor('#e5e7eb')
		legend.get_frame().set_linewidth(0.5)
		
		fig.autofmt_xdate()
		plt.tight_layout()

		img_buffer = io.BytesIO()
		# RUN-2: Enhanced DPI
		plt.savefig(img_buffer, format="png", dpi=CHART_CONFIG['dpi'], bbox_inches="tight")
		img_buffer.seek(0)
		plt.close(fig)
		return Image(img_buffer, width=16 * cm, height=6.5 * cm)

	@staticmethod
	def _build_forecast_chart(
		series_map: dict[str, pd.Series],
		title: str,
	) -> Image | None:
		if not series_map:
			return None
		
		# RUN-2: Professional styling setup
		ExportManager._setup_matplotlib_style()
		
		fig, ax = plt.subplots(figsize=(6.8, 3.2))
		
		# RUN-2: Use standardized color scheme
		colors = CHART_CONFIG['colors']['methods']
		
		# RUN-2: Enhanced line styling
		line_styles = {
			"actual": {"linewidth": 2.0, "alpha": 0.95, "linestyle": "-"},
			"fts": {"linewidth": 1.8, "alpha": 0.85, "linestyle": "-"},
			"ann": {"linewidth": 1.8, "alpha": 0.85, "linestyle": "--"},
			"arima": {"linewidth": 1.8, "alpha": 0.85, "linestyle": "-."},
			"naive": {"linewidth": 1.5, "alpha": 0.75, "linestyle": ":"},
			"ma": {"linewidth": 1.5, "alpha": 0.75, "linestyle": ":"},
			"pred": {"linewidth": 1.8, "alpha": 0.85, "linestyle": "-"}
		}
		
		for key, series in series_map.items():
			if series is None or series.empty:
				continue
			
			style = line_styles.get(key, {"linewidth": 1.6, "alpha": 0.85, "linestyle": "-"})
			
			ax.plot(
				series.index,
				series.values,
				label=key.upper() if key not in {"actual", "pred"} else key.title(),
				color=colors.get(key, CHART_CONFIG['colors']['primary']),
				**style
			)
		
		# RUN-2: Apply professional styling
		ExportManager._apply_professional_styling(ax, title=title, xlabel="Time", ylabel="Value (W)")
		
		# RUN-2: Enhanced legend styling with better positioning
		legend = ax.legend(fontsize=CHART_CONFIG['figure_params']['legend.fontsize'], 
						 loc="best", frameon=True, fancybox=True,
						 shadow=True, framealpha=0.95, ncol=2 if len(series_map) > 4 else 1)
		legend.get_frame().set_facecolor('white')
		legend.get_frame().set_edgecolor('#e5e7eb')
		legend.get_frame().set_linewidth(0.5)
		
		fig.autofmt_xdate()
		plt.tight_layout()

		img_buffer = io.BytesIO()
		# RUN-2: Enhanced DPI
		plt.savefig(img_buffer, format="png", dpi=CHART_CONFIG['dpi'], bbox_inches="tight")
		img_buffer.seek(0)
		plt.close(fig)
		return Image(img_buffer, width=16 * cm, height=6.5 * cm)

	@staticmethod
	def _render_latex_to_png(latex: str, dpi: int = 120) -> str | None:
		"""
		Render LaTeX formula to PNG image.
		RUN-3 Note: This system preserves original LaTeX fonts as per requirements.
		Mathematical formulas maintain their LaTeX rendering and are NOT affected by Bahnschrift fonts.
		"""
		pdflatex_path = shutil.which("pdflatex")
		if not pdflatex_path:
			return None
		try:
			import fitz  # PyMuPDF
		except Exception:
			return None

		cache_dir = os.path.join(tempfile.gettempdir(), "ppdl_latex_cache")
		os.makedirs(cache_dir, exist_ok=True)
		key = hashlib.sha1(latex.encode("utf-8")).hexdigest()
		png_path = os.path.join(cache_dir, f"{key}.png")
		if os.path.exists(png_path):
			return png_path

		work_dir = tempfile.mkdtemp(prefix="ppdl_latex_")
		try:
			tex_path = os.path.join(work_dir, "formula.tex")
			pdf_path = os.path.join(work_dir, "formula.pdf")
			content = (
				r"\documentclass{article}"
				"\n"
				r"\usepackage{amsmath,amssymb}"
				"\n"
				r"\pagestyle{empty}"
				"\n"
				r"\begin{document}"
				"\n"
				r"\tiny"
				"\n"
				r"\["
				"\n"
				r"\textstyle "
				f"{latex}"
				"\n"
				r"\]"
				"\n"
				r"\end{document}"
			)
			with open(tex_path, "w", encoding="utf-8") as f:
				f.write(content)

			cmd = [
				pdflatex_path,
				"-interaction=nonstopmode",
				"-halt-on-error",
				"-output-directory",
				work_dir,
				tex_path,
			]
			result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
			if result.returncode != 0 or not os.path.exists(pdf_path):
				return None

			doc = fitz.open(pdf_path)
			if doc.page_count < 1:
				return None
			page = doc[0]
			text_info = page.get_text("dict")
			clip_rect = None
			for block in text_info.get("blocks", []):
				if block.get("type") != 0:
					continue
				for line in block.get("lines", []):
					for span in line.get("spans", []):
						bbox = fitz.Rect(span.get("bbox"))
						clip_rect = bbox if clip_rect is None else clip_rect | bbox
			if clip_rect is None:
				clip_rect = page.rect
			padding = 4
			clip_rect = fitz.Rect(
				clip_rect.x0 - padding,
				clip_rect.y0 - padding,
				clip_rect.x1 + padding,
				clip_rect.y1 + padding,
			)
			scale = dpi / 72.0
			mat = fitz.Matrix(scale, scale)
			pix = page.get_pixmap(matrix=mat, clip=clip_rect, alpha=False)
			pix.save(png_path)
			doc.close()
			return png_path
		except Exception:
			return None
		finally:
			try:
				shutil.rmtree(work_dir)
			except Exception:
				pass

	@staticmethod
	def _generate_statistical_analysis_table(df: pd.DataFrame, column: str, title: str, unit: str) -> Table | None:
		"""
		RUN-4: Generate 4×3 statistical analysis table for data analysis section.
		Format: [Statistic, Value, Date] for rata-rata, puncak, terendah
		"""
		if df is None or df.empty or column not in df.columns:
			return None
		
		# Clean data - remove NaN values
		df_clean = df.dropna(subset=[column, "timestamp"]).copy()
		if df_clean.empty:
			return None
		
		try:
			# Calculate statistics
			mean_val = df_clean[column].mean()
			max_val = df_clean[column].max() 
			min_val = df_clean[column].min()
			
			# Find dates for max and min values
			max_date = df_clean[df_clean[column] == max_val]["timestamp"].iloc[0]
			min_date = df_clean[df_clean[column] == min_val]["timestamp"].iloc[0]
			
			# Format dates
			if hasattr(max_date, 'strftime'):
				max_date_str = max_date.strftime('%Y-%m-%d %H:%M')
				min_date_str = min_date.strftime('%Y-%m-%d %H:%M')
			else:
				max_date_str = str(max_date)[:16]  # Truncate if string
				min_date_str = str(min_date)[:16]
			
			# Create table data (4×3 format)
			table_data = [
				['Statistik', 'Nilai', 'Tanggal'],  # Header
				['Rata-rata', f'{mean_val:.2f} {unit}', '-'],  # Mean doesn't have specific date
				['Puncak (Tertinggi)', f'{max_val:.2f} {unit}', max_date_str],
				['Terendah', f'{min_val:.2f} {unit}', min_date_str]
			]
			
			# Create table with styling
			table = Table(table_data, colWidths=[4*cm, 3.5*cm, 4*cm])
			
			# Apply professional styling (RUN-3: Bahnschrift fonts)
			table_style = TableStyle([
				# Header styling
				('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4e79')),
				('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
				('FONTNAME', (0, 0), (-1, 0), _get_font_name('heading') if _BAHNSCHRIFT_AVAILABLE else 'Helvetica-Bold'),
				('FONTSIZE', (0, 0), (-1, 0), 10),
				('ALIGN', (0, 0), (-1, 0), 'CENTER'),
				
				# Body styling
				('FONTNAME', (0, 1), (-1, -1), _get_font_name('body') if _BAHNSCHRIFT_AVAILABLE else 'Helvetica'),
				('FONTSIZE', (0, 1), (-1, -1), 9),
				('ALIGN', (0, 0), (0, -1), 'LEFT'),  # First column left align
				('ALIGN', (1, 1), (-1, -1), 'CENTER'),  # Value and date columns center
				
				# Borders and spacing
				('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#334155')),
				('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
				('TOPPADDING', (0, 0), (-1, -1), 6),
				('BOTTOMPADDING', (0, 0), (-1, -1), 6),
				('LEFTPADDING', (0, 0), (-1, -1), 8),
				('RIGHTPADDING', (0, 0), (-1, -1), 8),
				
				# Zebra striping
				('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')])
			])
			
			table.setStyle(table_style)
			return table
			
		except Exception:
			return None  # Graceful fallback

	@staticmethod
	def _generate_mathematical_process_doc(elements: list, styles, parameter_name: str) -> None:
		"""
		RUN-4: Generate mathematical process documentation for statistical calculations.
		Uses LaTeX notation to document calculation methodology.
		"""
		try:
			# Subtitle for mathematical process
			math_style = ParagraphStyle(
				'MathProcess',
				parent=styles['Normal'],
				fontSize=9,
				spaceAfter=8,
				spaceBefore=8,
				textColor=colors.HexColor('#374151'),
				fontName=_get_font_name('body') if _BAHNSCHRIFT_AVAILABLE else 'Helvetica'
			)
			
			# Mathematical formulas for statistical calculations
			formulas = [
				r"Rata-rata: \bar{x} = \frac{1}{n} \sum_{i=1}^{n} x_i",
				r"Puncak: \max(x) = \max\{x_1, x_2, \ldots, x_n\}",
				r"Terendah: \min(x) = \min\{x_1, x_2, \ldots, x_n\}"
			]
			
			elements.append(Paragraph(f"<b>Proses Matematis {parameter_name}:</b>", math_style))
			
			# Use existing LaTeX rendering system (preserves LaTeX fonts per RUN-3)
			ExportManager._append_latex_images(elements, formulas, max_width_cm=6.0)
			
			# Add explanation paragraph
			explanation = (
				f"Statistik {parameter_name.lower()} dihitung menggunakan metode: "
				"(1) rata-rata aritmetika untuk nilai tengah, "
				"(2) nilai maksimum untuk identifikasi puncak beban, "
				"(3) nilai minimum untuk analisis beban terendah. "
				"Tanggal dan waktu kejadian puncak serta terendah dicatat untuk analisis temporal."
			)
			
			elements.append(Paragraph(explanation, math_style))
			elements.append(Spacer(1, 0.3*cm))
			
		except Exception:
			# Graceful fallback - add simple text explanation
			simple_explanation = (
				f"Proses matematis {parameter_name}: Rata-rata = jumlah/n, "
				f"Puncak = nilai maksimum, Terendah = nilai minimum."
			)
			elements.append(Paragraph(simple_explanation, styles['Normal']))
			elements.append(Spacer(1, 0.2*cm))

	@staticmethod
	def _generate_forecast_comparison_table(
		test_series: pd.Series,
		forecast_data: Dict,
		table_type: str = "main",
		models: List[str] = None
	) -> Table | None:
		"""
		RUN-5: Generate forecast comparison tables for Resume Graphic section.
		
		Args:
			test_series: Actual test data
			forecast_data: Dictionary with forecast results from models
			table_type: "main" (5×4), "fts_sub" (5×3), "ann" (5×3), "arima" (5×3)
			models: List of model names to include
			
		Returns:
			Table object or None if data insufficient
		"""
		if test_series is None or test_series.empty:
			return None
		
		try:
			# Take last 5 time periods for comparison
			n_periods = min(5, len(test_series))
			if n_periods < 3:  # Need minimum data
				return None
				
			# Get the last n_periods of actual data
			actual_data = test_series.tail(n_periods)
			timestamps = actual_data.index
			
			# Prepare table data based on type
			if table_type == "main":
				# 5×4 FTS Main Comparison Table
				headers = ['Tanggal/Waktu', 'Aktual', 'FTS', 'Naive', 'Moving Average']
				table_data = [headers]
				
				for i, (timestamp, actual_val) in enumerate(actual_data.items()):
					# Format timestamp
					if hasattr(timestamp, 'strftime'):
						time_str = timestamp.strftime('%Y-%m-%d %H:%M')
					else:
						time_str = str(timestamp)[:16]
					
					row = [time_str, f'{actual_val:.2f}']
					
					# Add FTS forecast
					if 'fts' in forecast_data and forecast_data['fts'].get('forecast'):
						fts_forecast = forecast_data['fts']['forecast']
						if i < len(fts_forecast):
							row.append(f'{fts_forecast[i]:.2f}')
						else:
							row.append('-')
					else:
						row.append('-')
					
					# Add Naive forecast
					if 'naive' in forecast_data and forecast_data['naive'].get('forecast'):
						naive_forecast = forecast_data['naive']['forecast']
						if i < len(naive_forecast):
							row.append(f'{naive_forecast[i]:.2f}')
						else:
							row.append('-')
					else:
						row.append('-')
					
					# Add Moving Average forecast
					if 'ma' in forecast_data and forecast_data['ma'].get('forecast'):
						ma_forecast = forecast_data['ma']['forecast']
						if i < len(ma_forecast):
							row.append(f'{ma_forecast[i]:.2f}')
						else:
							row.append('-')
					else:
						row.append('-')
					
					table_data.append(row)
				
				col_widths = [3.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 3*cm]
				
			elif table_type in ["fts_sub", "ann", "arima"]:
				# 5×3 Sub Tables
				if table_type == "fts_sub":
					model_name = models[0] if models else "FTS"
					headers = ['Tanggal/Waktu', 'Aktual', model_name]
					# Map model names to forecast keys
					if model_name == "FTS":
						forecast_key = 'fts'
					elif model_name == "Naive":
						forecast_key = 'naive'
					elif model_name == "Moving Average":
						forecast_key = 'ma'
					else:
						forecast_key = 'fts'  # Default fallback
				elif table_type == "ann":
					headers = ['Tanggal/Waktu', 'Aktual', 'ANN Predicted']
					forecast_key = 'ann'
				else:  # arima
					headers = ['Tanggal/Waktu', 'Aktual', 'ARIMA Predicted']
					forecast_key = 'arima'
				
				table_data = [headers]
				
				for i, (timestamp, actual_val) in enumerate(actual_data.items()):
					# Format timestamp
					if hasattr(timestamp, 'strftime'):
						time_str = timestamp.strftime('%Y-%m-%d %H:%M')
					else:
						time_str = str(timestamp)[:16]
					
					row = [time_str, f'{actual_val:.2f}']
					
					# Add model forecast
					if forecast_key in forecast_data and forecast_data[forecast_key].get('forecast'):
						model_forecast = forecast_data[forecast_key]['forecast']
						if i < len(model_forecast):
							row.append(f'{model_forecast[i]:.2f}')
						else:
							row.append('-')
					else:
						row.append('-')
					
					table_data.append(row)
				
				col_widths = [4*cm, 3*cm, 3*cm]
			else:
				return None
			
			# Create table with styling
			table = Table(table_data, colWidths=col_widths)
			
			# Apply professional styling (RUN-3: Bahnschrift fonts)
			table_style = TableStyle([
				# Header styling
				('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4e79')),
				('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
				('FONTNAME', (0, 0), (-1, 0), _get_font_name('heading') if _BAHNSCHRIFT_AVAILABLE else 'Helvetica-Bold'),
				('FONTSIZE', (0, 0), (-1, 0), 10),
				('ALIGN', (0, 0), (-1, 0), 'CENTER'),
				
				# Body styling
				('FONTNAME', (0, 1), (-1, -1), _get_font_name('body') if _BAHNSCHRIFT_AVAILABLE else 'Helvetica'),
				('FONTSIZE', (0, 1), (-1, -1), 9),
				('ALIGN', (0, 1), (0, -1), 'LEFT'),  # Timestamp column left align
				('ALIGN', (1, 1), (-1, -1), 'CENTER'),  # Value columns center align
				
				# Borders and spacing
				('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#334155')),
				('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
				('TOPPADDING', (0, 0), (-1, -1), 6),
				('BOTTOMPADDING', (0, 0), (-1, -1), 6),
				('LEFTPADDING', (0, 0), (-1, -1), 8),
				('RIGHTPADDING', (0, 0), (-1, -1), 8),
				
				# Zebra striping
				('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')])
			])
			
			table.setStyle(table_style)
			return table
			
		except Exception:
			return None  # Graceful fallback

	@staticmethod
	def _append_latex_images(
		elements: list,
		formulas: list[str],
		max_width_cm: float = 5.5,
	) -> None:
		fallback_style = getSampleStyleSheet()["Normal"]
		for formula in formulas:
			png_path = ExportManager._render_latex_to_png(formula)
			if png_path and os.path.exists(png_path):
				img = Image(png_path)
				if img.imageWidth > 0 and img.imageHeight > 0:
					max_width = max_width_cm * cm
					if img.imageWidth > max_width:
						scale = max_width / float(img.imageWidth)
						img.drawWidth = max_width
						img.drawHeight = img.imageHeight * scale
				elements.append(img)
				elements.append(Spacer(1, 0.15 * cm))
			else:
				elements.append(Paragraph(f"<font face='Courier'>{formula}</font>", fallback_style))
				elements.append(Spacer(1, 0.15 * cm))

	@staticmethod
	def _append_fts_math_doc(
		elements: list,
		styles,
		subheading_style: ParagraphStyle,
		results: Dict,
		params: Dict | None,
	) -> None:
		fts = results.get("fts", {})
		if not fts:
			elements.append(Paragraph("FTS results tidak tersedia.", styles["Normal"]))
			return

		train_series = results.get("data", {}).get("train")
		test_series = results.get("data", {}).get("test")
		fts_art = fts.get("artifacts", {}) or {}

		intervals = fts_art.get("intervals", []) or []
		fuzzified = fts_art.get("fuzzified_train", []) or []
		flr_table = fts_art.get("flr_table", []) or []
		flrg_table = fts_art.get("flrg_table", {}) or {}
		uod = fts_art.get("uod")

		min_y = None
		max_y = None
		if isinstance(train_series, pd.Series) and not train_series.empty:
			min_y = float(train_series.min())
			max_y = float(train_series.max())

		span = (max_y - min_y) if (min_y is not None and max_y is not None) else None
		pad_pct = ExportManager._get_param(params, "fts", "pad_pct", default=None)
		if pad_pct is None:
			pad_pct = ExportManager._get_param(params, "fts", "padPct", default=0.05)
		try:
			pad_pct = float(pad_pct)
		except (TypeError, ValueError):
			pad_pct = 0.05

		uod_min = None
		uod_max = None
		if isinstance(uod, (list, tuple)) and len(uod) == 2:
			uod_min = ExportManager._to_float(uod[0])
			uod_max = ExportManager._to_float(uod[1])
		elif min_y is not None and max_y is not None and span is not None:
			pad = span * pad_pct
			uod_min = min_y - pad
			uod_max = max_y + pad

		pad_val = None
		if min_y is not None and uod_min is not None:
			pad_val = min_y - uod_min

		formula_map = {
			"uod": [
				r"D = [D_{min}, D_{max}]",
				r"D_{min} = \min(y) - pad",
				r"D_{max} = \max(y) + pad",
				r"pad = padPct \times (\max(y) - \min(y))",
			],
			"partition": [
				r"w = \frac{D_{max} - D_{min}}{n}",
				r"A_i = [D_{min} + (i-1)w,\ D_{min} + i w)",
				r"A_n = [D_{min} + (n-1)w,\ D_{max}]",
				r"mid(A_i) = \frac{lo_i + hi_i}{2}",
			],
			"fuzzification": [
				r"L_t = A_i,\ \text{jika } y_t \in [lo_i, hi_i)",
			],
			"flr": [
				r"A_i \to A_j",
				r"FLR = \{(L_{t-1}, L_t)\}",
			],
			"flrg": [
				r"A_i \to \{A_{j_1}, A_{j_2}, \ldots\}",
				r"support(A_i \to A_j) = \frac{count(A_i \to A_j)}{\sum_j count(A_i \to A_j)}",
			],
			"forecast": [
				r"\hat{y}_{t+1} = \sum_j support(L_t \to A_j)\, mid_j",
				r"\hat{y}_{t+1} = mid(L_t)\quad \text{(fallback)}",
			],
			"metrics": [
				r"MAE = \frac{1}{n}\sum_{t=1}^{n}|Y_t - \hat{Y}_t|",
				r"RMSE = \sqrt{\frac{1}{n}\sum_{t=1}^{n}(Y_t - \hat{Y}_t)^2}",
				r"MAPE = \frac{100\%}{n}\sum_{t=1}^{n}\left|\frac{Y_t - \hat{Y}_t}{Y_t}\right|",
			],
			"baseline": [
				r"\hat{y}_{t+1} = y_t\quad \text{(Naive)}",
				r"\hat{y}_{t+1} = \frac{1}{w}\sum_{i=t-w+1}^{t} y_i\quad \text{(Moving Average)}",
			],
			"sensitivity": [
				r"\Delta MAPE = MAPE_{FTS} - MAPE_{Baseline}",
			],
		}

		def _make_table(rows: list[list[str]], col_widths: list[float]) -> Table:
			tbl = Table(rows, colWidths=col_widths)
			ExportManager._style_table(tbl, font_size=8)
			return tbl

		# 1) UoD
		elements.append(Paragraph("6.1 Universe of Discourse (UoD)", subheading_style))
		elements.append(
			Paragraph(
				"Formula: D = [D_min, D_max], D_min = min(y) - pad, D_max = max(y) + pad, pad = padPct * (max(y) - min(y)).",
				styles["Normal"],
			)
		)
		ExportManager._append_latex_images(elements, formula_map["uod"])
		elements.append(
			Paragraph(
				(
					f"Calculation: min(y)={ExportManager._fmt_number(min_y, 4)}, "
					f"max(y)={ExportManager._fmt_number(max_y, 4)}, "
					f"span={ExportManager._fmt_number(span, 4)}, "
					f"padPct={pad_pct * 100:.1f}%, "
					f"D_min={ExportManager._fmt_number(uod_min, 4)}, "
					f"D_max={ExportManager._fmt_number(uod_max, 4)}"
				),
				styles["Normal"],
			)
		)
		# LaTeX Calculation
		calc_latex_uod = [
			f"pad = {pad_pct:.3f} \\times ({ExportManager._fmt_number(max_y, 4)} - {ExportManager._fmt_number(min_y, 4)}) = {ExportManager._fmt_number(span * pad_pct if span else 0, 4)}",
			f"D_{{min}} = {ExportManager._fmt_number(min_y, 4)} - {ExportManager._fmt_number(span * pad_pct if span else 0, 4)} = {ExportManager._fmt_number(uod_min, 4)}",
			f"D_{{max}} = {ExportManager._fmt_number(max_y, 4)} + {ExportManager._fmt_number(span * pad_pct if span else 0, 4)} = {ExportManager._fmt_number(uod_max, 4)}"
		]
		elements.append(Paragraph("<b>LaTeX Calculation Steps:</b>", styles["Normal"]))
		ExportManager._append_latex_images(elements, calc_latex_uod)
		elements.append(Spacer(1, 0.2 * cm))

		# 2) Partition
		partition_method = ExportManager._get_param(params, "fts", "partition", default="equal-width")
		elements.append(Paragraph("6.2 Partitioning (Equal-Width / Equal-Frequency)", subheading_style))
		elements.append(
			Paragraph(
				"Formula: w = (D_max - D_min) / n; A_i = [D_min + (i-1)w, D_min + i w), A_n = [D_min + (n-1)w, D_max].",
				styles["Normal"],
			)
		)
		ExportManager._append_latex_images(elements, formula_map["partition"])
		n_intervals = ExportManager._get_param(params, "fts", "interval", default=len(intervals) or "-")
		if isinstance(uod_min, float) and isinstance(uod_max, float) and isinstance(n_intervals, int):
			width = (uod_max - uod_min) / float(n_intervals) if n_intervals else None
		else:
			width = None
		elements.append(
			Paragraph(
				(
					f"Method={partition_method}, n={n_intervals}, "
					f"width={ExportManager._fmt_number(width, 4)}"
				),
				styles["Normal"],
			)
		)
		# LaTeX Calculation for partition
		if isinstance(uod_min, float) and isinstance(uod_max, float) and isinstance(n_intervals, int) and n_intervals > 0:
			calc_latex_partition = [
				f"w = \\frac{{{ExportManager._fmt_number(uod_max, 4)} - {ExportManager._fmt_number(uod_min, 4)}}}{{{n_intervals}}} = {ExportManager._fmt_number(width, 4)}",
				f"A_1 = [{ExportManager._fmt_number(uod_min, 4)}, {ExportManager._fmt_number(uod_min + width if width else 0, 4)})",
				f"A_2 = [{ExportManager._fmt_number(uod_min + width if width else 0, 4)}, {ExportManager._fmt_number(uod_min + 2*width if width else 0, 4)})",
				f"\\vdots",
				f"A_{{{n_intervals}}} = [{ExportManager._fmt_number(uod_min + (n_intervals-1)*width if width else 0, 4)}, {ExportManager._fmt_number(uod_max, 4)}]"
			]
			elements.append(Paragraph("<b>LaTeX Calculation Steps:</b>", styles["Normal"]))
			ExportManager._append_latex_images(elements, calc_latex_partition)
		if intervals:
			interval_rows = [["ID", "Lower", "Upper", "Midpoint"]]
			for idx, bounds in enumerate(intervals[:10], start=1):
				lo, hi = bounds
				mid = (ExportManager._to_float(lo) + ExportManager._to_float(hi)) / 2.0
				interval_rows.append(
					[
						f"A{idx}",
						ExportManager._fmt_number(lo, 4),
						ExportManager._fmt_number(hi, 4),
						ExportManager._fmt_number(mid, 4),
					]
				)
			elements.append(_make_table(interval_rows, [2 * cm, 4 * cm, 4 * cm, 4 * cm]))
			if len(intervals) > 10:
				elements.append(Paragraph(f"... {len(intervals) - 10} interval lainnya ...", styles["Italic"]))
		elements.append(Spacer(1, 0.2 * cm))

		# 3) Fuzzification
		elements.append(Paragraph("6.3 Fuzzification", subheading_style))
		
		# RUN-6: Enhanced step-by-step fuzzification calculation
		elements.append(
			Paragraph(
				"<b>Proses Fuzzification:</b> Mengkonversi nilai numerik menjadi label linguistik berdasarkan interval partisi.",
				styles["Normal"],
			)
		)
		elements.append(
			Paragraph(
				"Formula: L_t = A_i jika y_t berada pada interval [lo_i, hi_i).",
				styles["Normal"],
			)
		)
		ExportManager._append_latex_images(elements, formula_map["fuzzification"])
		
		# Add detailed calculation steps
		if isinstance(train_series, pd.Series) and not train_series.empty and fuzzified and intervals:
			# Show interval definitions first
			elements.append(Paragraph("<b>Definisi Interval:</b>", styles["Normal"]))
			interval_rows = [["Interval", "Batas Bawah", "Batas Atas", "Label"]]
			for i, (lo, hi) in enumerate(intervals):
				interval_rows.append([f"Interval {i+1}", f"{lo:.3f}", f"{hi:.3f}", f"A{i+1}"])
			
			elements.append(_make_table(interval_rows, [3*cm, 3*cm, 3*cm, 2*cm]))
			elements.append(Spacer(1, 0.2 * cm))
			
			# Show step-by-step calculation examples
			elements.append(Paragraph("<b>Contoh Perhitungan Fuzzification:</b>", styles["Normal"]))
			sample_count = min(5, len(train_series), len(fuzzified))
			calc_rows = [["Timestamp", "Nilai Aktual (y_t)", "Kondisi", "Label (L_t)"]]
			
			for i in range(sample_count):
				ts_val = train_series.index[i]
				actual_val = train_series.iloc[i]
				label = fuzzified[i]
				
				# Find which interval this value belongs to
				condition = "Tidak ditemukan"
				for j, (lo, hi) in enumerate(intervals):
					if lo <= actual_val < hi:
						condition = f"{lo:.3f} ≤ {actual_val:.3f} < {hi:.3f}"
						break
				
				calc_rows.append([
					ExportManager._fmt_ts(ts_val),
					f"{actual_val:.3f}",
					condition,
					str(label)
				])
			
			elements.append(_make_table(calc_rows, [4*cm, 3*cm, 4.5*cm, 2*cm]))
		else:
			elements.append(Paragraph("Sample fuzzification tidak tersedia.", styles["Normal"]))
		elements.append(Spacer(1, 0.2 * cm))

		# 4) FLR
		elements.append(Paragraph("6.4 Fuzzy Logical Relationship (FLR)", subheading_style))
		
		# RUN-6: Enhanced FLR step-by-step calculation
		elements.append(
			Paragraph(
				"<b>Proses Fuzzy Logical Relationship (FLR):</b> Membentuk hubungan logis antara label linguistik consecutive.",
				styles["Normal"],
			)
		)
		elements.append(
			Paragraph(
				"Formula: FLR = {(L_{t-1}, L_t)} atau A_i -> A_j.",
				styles["Normal"],
			)
		)
		ExportManager._append_latex_images(elements, formula_map["flr"])
		
		# Enhanced FLR calculation with step-by-step example
		if flr_table and fuzzified and len(fuzzified) > 1:
			elements.append(Paragraph("<b>Contoh Perhitungan FLR:</b>", styles["Normal"]))
			
			# Show how first few FLRs are created
			example_rows = [["t", "L_{t-1}", "L_t", "FLR"]]
			sample_count = min(5, len(fuzzified) - 1)
			
			for i in range(1, sample_count + 1):  # Start from 1 since we need t-1
				prev_label = fuzzified[i-1]
				curr_label = fuzzified[i]
				flr_relation = f"{prev_label} -> {curr_label}"
				example_rows.append([str(i+1), str(prev_label), str(curr_label), flr_relation])
			
			elements.append(_make_table(example_rows, [2*cm, 3*cm, 3*cm, 4*cm]))
			elements.append(Spacer(1, 0.2 * cm))
			
			# Show complete FLR table (first 10)
			elements.append(Paragraph("<b>Daftar FLR yang Terbentuk:</b>", styles["Normal"]))
			flr_rows = [["No", "Relation"]]
			for idx, rel in enumerate(flr_table[:10], start=1):
				flr_rows.append([str(idx), rel])
			elements.append(_make_table(flr_rows, [2 * cm, 10 * cm]))
			if len(flr_table) > 10:
				elements.append(Paragraph(f"... {len(flr_table) - 10} relasi lainnya ...", styles["Italic"]))
		else:
			elements.append(Paragraph("FLR tidak tersedia.", styles["Normal"]))
		elements.append(Spacer(1, 0.2 * cm))

		# 5) FLRG
		elements.append(Paragraph("6.5 Fuzzy Logical Relationship Group (FLRG)", subheading_style))
		
		# RUN-6: Enhanced FLRG step-by-step calculation
		elements.append(
			Paragraph(
				"<b>Proses FLRG:</b> Mengelompokkan FLR berdasarkan antecedent yang sama.",
				styles["Normal"],
			)
		)
		elements.append(
			Paragraph(
				"Formula: A_i -> {A_j} dengan support = count(A_i->A_j) / total(A_i).",
				styles["Normal"],
			)
		)
		ExportManager._append_latex_images(elements, formula_map["flrg"])
		if flrg_table:
			flrg_rows = [["Group", "Next States (Support)"]]
			for idx, (lhs, rhs) in enumerate(list(flrg_table.items())[:10], start=1):
				_ = idx
				# FIX: Wrap content using Paragraph for proper text wrapping
				flrg_rows.append([
					Paragraph(str(lhs), styles["Normal"]),
					Paragraph(str(rhs), styles["Normal"])
				])
			
			# Enhanced table with wrapping support
			flrg_table_obj = Table(flrg_rows, colWidths=[3 * cm, 12 * cm])
			flrg_table_obj.setStyle(TableStyle([
				('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
				('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
				('ALIGN', (0, 0), (-1, -1), 'LEFT'),
				('FONTNAME', (0, 0), (-1, 0), _get_font_name('body')),
				('FONTSIZE', (0, 0), (-1, -1), 9),
				('BOTTOMPADDING', (0, 0), (-1, 0), 6),
				('TOPPADDING', (0, 0), (-1, 0), 6),
				('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
				('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Top alignment for wrapped content
				('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
			]))
			elements.append(flrg_table_obj)
			
			if len(flrg_table) > 10:
				elements.append(Paragraph(f"... {len(flrg_table) - 10} group lainnya ...", styles["Italic"]))
		else:
			elements.append(Paragraph("FLRG tidak tersedia.", styles["Normal"]))
		elements.append(Spacer(1, 0.2 * cm))

		# 6) Forecasting
		elements.append(Paragraph("6.6 Forecasting (Cheng Method)", subheading_style))
		
		# RUN-6: Enhanced forecasting step-by-step calculation
		elements.append(
			Paragraph(
				"<b>Proses Forecasting (Cheng Method):</b> Memprediksi nilai berdasarkan FLRG dengan weighted average.",
				styles["Normal"],
			)
		)
		elements.append(
			Paragraph(
				"Formula: y_hat(t+1) = Σ(support_j × midpoint_j) / Σ(support_j).",
				styles["Normal"],
			)
		)
		elements.append(
			Paragraph(
				"Fallback: Jika FLRG tidak ditemukan, gunakan y_hat = midpoint dari interval aktual.",
				styles["Normal"],
			)
		)
		ExportManager._append_latex_images(elements, formula_map["forecast"])
		
		# Enhanced forecasting example with calculation steps
		forecast = fts.get("forecast", []) or []
		if isinstance(test_series, pd.Series) and forecast and flrg_table and intervals:
			elements.append(Paragraph("<b>Contoh Perhitungan Forecasting:</b>", styles["Normal"]))
			
			# Show interval midpoints first
			midpoint_rows = [["Interval", "Batas", "Midpoint"]]
			midpoints = {}
			for i, (lo, hi) in enumerate(intervals):
				mid = (lo + hi) / 2
				midpoints[f"A{i+1}"] = mid
				midpoint_rows.append([f"A{i+1}", f"[{lo:.3f}, {hi:.3f})", f"{mid:.3f}"])
			
			elements.append(_make_table(midpoint_rows, [2*cm, 4*cm, 3*cm]))
			elements.append(Spacer(1, 0.2 * cm))
			
			# Show sample forecast calculation
			elements.append(Paragraph("<b>Hasil Prediksi vs Aktual:</b>", styles["Normal"]))
		forecast = fts.get("forecast", []) or []
		if isinstance(test_series, pd.Series) and forecast:
			forecast_rows = [["t", "Timestamp", "Actual (W)", "Pred (W)"]]
			added = 0
			for idx, pred in enumerate(forecast):
				if pred is None or (isinstance(pred, float) and pd.isna(pred)):
					continue
				if idx >= len(test_series):
					break
				forecast_rows.append(
					[
						str(idx + 1),
						ExportManager._fmt_ts(test_series.index[idx]),
						ExportManager._fmt_number(test_series.iloc[idx], 3),
						ExportManager._fmt_number(pred, 3),
					]
				)
				added += 1
				if added >= 10:
					break
			if added > 0:
				elements.append(_make_table(forecast_rows, [1 * cm, 5 * cm, 3 * cm, 3 * cm]))
				# LaTeX Calculation for forecasting example
				if added >= 3:  # Show calculation for first few predictions
					calc_latex_forecast = [
						"\\text{Example calculation for } t=1:",
						f"\\hat{{y}}_{{t+1}} = \\sum_j support(L_t \\to A_j) \\times mid_j",
						f"\\hat{{y}}_1 = {ExportManager._fmt_number(forecast[0], 3)}\ W",
						"\\text{(detailed FLRG lookup omitted for brevity)}"
					]
					elements.append(Paragraph("<b>LaTeX Calculation Example:</b>", styles["Normal"]))
					ExportManager._append_latex_images(elements, calc_latex_forecast)
			else:
				elements.append(Paragraph("Forecast sample tidak tersedia.", styles["Normal"]))
		else:
			elements.append(Paragraph("Forecast sample tidak tersedia.", styles["Normal"]))
		elements.append(Spacer(1, 0.2 * cm))

		# 7) Metrics
		elements.append(Paragraph("6.7 Evaluation Metrics", subheading_style))
		elements.append(
			Paragraph(
				"Formula: MAE = mean(|y - y_hat|), RMSE = sqrt(mean((y - y_hat)^2)), MAPE = mean(|(y - y_hat)/y|) * 100.",
				styles["Normal"],
			)
		)
		ExportManager._append_latex_images(elements, formula_map["metrics"])
		metrics = fts.get("metrics", {}) or {}
		metric_rows = [
			["Metric", "Value"],
			["MAE", ExportManager._fmt_metric(metrics.get("mae"))],
			["RMSE", ExportManager._fmt_metric(metrics.get("rmse"))],
			["MAPE (%)", ExportManager._fmt_mape(metrics.get("mape"))],
		]
		elements.append(_make_table(metric_rows, [4 * cm, 6 * cm]))
		# LaTeX Calculation for metrics
		if test_series is not None and forecast and len(forecast) >= len(test_series):
			n_test = len(test_series)
			calc_latex_metrics = [
				f"n = {n_test}\ \\text{{(test samples)}}",
				f"MAE = \\frac{{1}}{{{n_test}}}\\sum_{{t=1}}^{{{n_test}}}|Y_t - \\hat{{Y}}_t| = {ExportManager._fmt_metric(metrics.get('mae'))}",
				f"RMSE = \\sqrt{{\\frac{{1}}{{{n_test}}}\\sum_{{t=1}}^{{{n_test}}}(Y_t - \\hat{{Y}}_t)^2}} = {ExportManager._fmt_metric(metrics.get('rmse'))}",
				f"MAPE = \\frac{{100\\%}}{{{n_test}}}\\sum_{{t=1}}^{{{n_test}}}\\left|\\frac{{Y_t - \\hat{{Y}}_t}}{{Y_t}}\\right| = {ExportManager._fmt_mape(metrics.get('mape'))}\\%"
			]
			elements.append(Paragraph("<b>LaTeX Calculation Steps:</b>", styles["Normal"]))
			ExportManager._append_latex_images(elements, calc_latex_metrics)
		elements.append(Spacer(1, 0.2 * cm))

		# 8) Baseline
		elements.append(Paragraph("6.8 Baseline Models Comparison", subheading_style))
		
		# RUN-6: Enhanced baseline comparison with detailed methodology
		elements.append(
			Paragraph(
				"<b>Metodologi Baseline Models:</b> Perbandingan dengan model sederhana untuk evaluasi performa FTS.",
				styles["Normal"],
			)
		)
		
		# Add detailed formulas for each baseline method
		baseline_formulas = [
			r"Naive\ Method: \hat{y}_{t+1} = y_t",
			r"Moving\ Average: \hat{y}_{t+1} = \frac{1}{w}\sum_{i=0}^{w-1} y_{t-i}",
			r"MAE = \frac{1}{n}\sum_{t=1}^{n} |y_t - \hat{y}_t|",
			r"RMSE = \sqrt{\frac{1}{n}\sum_{t=1}^{n} (y_t - \hat{y}_t)^2}"
		]
		
		elements.append(Paragraph("<b>Formula Matematis Baseline:</b>", styles["Normal"]))
		ExportManager._append_latex_images(elements, baseline_formulas)
		
		# Enhanced baseline comparison table with statistical analysis
		baseline_rows = [["Model", "MAE", "RMSE", "MAPE (%)", "Deskripsi"]]
		
		# Add FTS for comparison
		fts_metrics = fts.get("metrics", {})
		if fts_metrics:
			baseline_rows.append([
				"FTS (Chen)",
				ExportManager._fmt_metric(fts_metrics.get("mae")),
				ExportManager._fmt_metric(fts_metrics.get("rmse")),
				ExportManager._fmt_mape(fts_metrics.get("mape")),
				"Fuzzy Time Series"
			])
		
		for base_key, label, desc in [
			("naive", "Naive", "y(t+1) = y(t)"), 
			("ma", "Moving Average", "y(t+1) = mean(window)")
		]:
			base_metrics = results.get(base_key, {}).get("metrics", {})
			if base_metrics:
				baseline_rows.append(
					[
						label,
						ExportManager._fmt_metric(base_metrics.get("mae")),
						ExportManager._fmt_metric(base_metrics.get("rmse")),
						ExportManager._fmt_mape(base_metrics.get("mape")),
						desc
					]
				)
		if len(baseline_rows) > 1:
			elements.append(_make_table(baseline_rows, [4 * cm, 3 * cm, 3 * cm, 3 * cm, 6 * cm]))
		else:
			elements.append(Paragraph("Baseline metrics tidak tersedia.", styles["Normal"]))
		elements.append(Spacer(1, 0.2 * cm))

		# 9) Sensitivity Analysis
		elements.append(Paragraph("6.9 Sensitivity Analysis", subheading_style))
		
		# RUN-6: Enhanced sensitivity analysis with detailed methodology
		elements.append(
			Paragraph(
				"<b>Metodologi Sensitivity Analysis:</b> Analisis perubahan parameter dan evaluasi robustness model FTS.",
				styles["Normal"],
			)
		)
		
		# Add detailed formulas for sensitivity metrics
		sensitivity_formulas = [
			r"\Delta\ MAPE = MAPE_{FTS} - MAPE_{Baseline}",
			r"Relative\ Error = \frac{|MAPE_{FTS} - MAPE_{Baseline}|}{MAPE_{Baseline}} \times 100\%",
			r"Improvement\ Ratio = \frac{MAPE_{Baseline} - MAPE_{FTS}}{MAPE_{Baseline}} \times 100\%",
			r"Performance\ Index = \frac{1}{1 + RMSE} \times 100\%"
		]
		
		elements.append(Paragraph("<b>Formula Sensitivity Metrics:</b>", styles["Normal"]))
		ExportManager._append_latex_images(elements, sensitivity_formulas)
		
		sens = results.get("sensitivity") or {}
		cases = sens.get("cases", [])
		if cases:
			# Enhanced sensitivity table with additional metrics
			sens_rows = [["Case", "MAPE (%)", "Delta (%)", "Improvement (%)", "Status"]]
			for case in cases:
				mape_val = case.get("mape", 0)
				delta_val = case.get("delta", 0)
				improvement = abs(delta_val) if delta_val < 0 else 0
				status = "Better" if delta_val < 0 else "Worse" if delta_val > 0 else "Equal"
				
				sens_rows.append(
					[
						case.get("label", "-"),
						ExportManager._fmt_mape(mape_val),
						ExportManager._fmt_mape(delta_val),
						f"{improvement:.2f}%" if improvement > 0 else "-",
						status
					]
				)
			elements.append(_make_table(sens_rows, [4 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm]))
		else:
			elements.append(Paragraph("Sensitivity analysis tidak tersedia.", styles["Normal"]))
		elements.append(Spacer(1, 0.2 * cm))

	@staticmethod
	def _get_date_range_from_series(series: pd.Series | None) -> str:
		if series is None or len(series) == 0:
			return "Unknown"
		try:
			start = series.index.min()
			end = series.index.max()
			return f"{ExportManager._fmt_date(start)} - {ExportManager._fmt_date(end)}"
		except Exception:
			return "Unknown"

	@staticmethod
	def _get_date_range_from_df(raw_df: pd.DataFrame | None) -> str:
		if raw_df is None or raw_df.empty:
			return "Unknown"
		try:
			if "ts_server" in raw_df.columns:
				ts = pd.to_datetime(raw_df["ts_server"], unit="ms", errors="coerce")
			elif "timestamp" in raw_df.columns:
				ts = pd.to_datetime(raw_df["timestamp"], errors="coerce")
			else:
				return "Unknown"
			if ts.isna().all():
				return "Unknown"
			return f"{ExportManager._fmt_date(ts.min())} - {ExportManager._fmt_date(ts.max())}"
		except Exception:
			return "Unknown"

	@staticmethod
	def _get_device_name(raw_df: pd.DataFrame | None) -> str:
		if raw_df is None or raw_df.empty:
			return "Unknown Device"
		for key in ["device_name", "device", "device_id", "deviceId"]:
			if key in raw_df.columns:
				series = raw_df[key].dropna()
				if not series.empty:
					return str(series.iloc[0])
		return "Unknown Device"

	@staticmethod
	def _get_param(params: Dict | None, *keys, default=None):
		if not params:
			return default
		cursor = params
		for key in keys:
			if not isinstance(cursor, dict) or key not in cursor:
				return default
			cursor = cursor[key]
		return cursor if cursor is not None else default

	@staticmethod
	def _build_comparison(rows: list[dict]) -> tuple[list[dict], str | None]:
		if not rows:
			return [], None
		ranked = sorted(rows, key=lambda item: item.get("mape", 0.0))
		rank_map = {item["method"]: idx + 1 for idx, item in enumerate(ranked)}
		best_method = ranked[0]["method"]
		for row in rows:
			row["rank"] = rank_map.get(row["method"], "-")
		return rows, best_method

	@staticmethod
	def _collect_comparison_rows(results: Dict) -> tuple[list[dict], str | None]:
		rows = []
		for key, label in [("fts", "FTS"), ("ann", "ANN"), ("arima", "ARIMA")]:
			if key not in results:
				continue
			metrics = results[key].get("metrics", {})
			rows.append(
				{
					"method": label,
					"mae": ExportManager._to_float(metrics.get("mae")),
					"rmse": ExportManager._to_float(metrics.get("rmse")),
					"mape": ExportManager._to_float(metrics.get("mape")),
				}
			)
		return ExportManager._build_comparison(rows)

	@staticmethod
	def _append_executive_summary(
		elements: list,
		styles,
		title_style: ParagraphStyle,
		heading_style: ParagraphStyle,
		results: Dict,
		params: Dict | None = None,
		raw_df: pd.DataFrame | None = None,
	) -> None:
		"""Executive Summary Page dengan KPI Dashboard untuk enhanced professional presentation."""
		
		# Extract key information
		norm_df = ExportManager._normalize_raw_df(raw_df)
		device_name = ExportManager._get_device_name(raw_df)
		date_range = ExportManager._get_date_range_from_df(raw_df)
		full_series = results.get("data", {}).get("full")
		total_points = len(norm_df) if not norm_df.empty else (len(full_series) if full_series is not None else 0)
		
		# Collect comparison rows and identify best model
		comp_rows, best_method = ExportManager._collect_comparison_rows(results)
		
		# Get best model MAPE
		best_mape = None
		for row in comp_rows:
			if row.get("method") == best_method:
				best_mape = row.get("mape")
				break
		
		# Get FTS sensitivity analysis
		sens = results.get("sensitivity") or {}
		best_case_id = sens.get("bestCase")
		best_case_label = "N/A"
		for case in sens.get("cases", []):
			if case.get("id") == best_case_id:
				best_case_label = case.get("label", "N/A")
				break
		
		# Executive Summary Page
		elements.append(Spacer(1, 1*cm))
		elements.append(Paragraph("EXECUTIVE SUMMARY", title_style))
		elements.append(Spacer(1, 0.5*cm))
		
		# KPI Dashboard - Project Overview
		overview_style = ParagraphStyle(
			"OverviewStyle",
			parent=styles["Normal"],
			fontSize=12,
			textColor=colors.HexColor("#374151"),
			spaceAfter=8,
		)
		
		# Project Info Box
		project_info = f"""
		<b>Device:</b> {device_name}<br/>
		<b>Analysis Period:</b> {date_range}<br/>
		<b>Data Points:</b> {total_points:,} measurements<br/>
		<b>Methods:</b> FTS (Cheng), ANN (MLP), ARIMA<br/>
		<b>Generated:</b> {datetime.now().strftime('%d %B %Y, %H:%M')}
		"""
		elements.append(Paragraph(project_info, overview_style))
	@staticmethod
	def _enhance_performance_comparison(
		elements: list,
		styles,
		heading_style: ParagraphStyle,
		results: Dict
	) -> None:
		"""RUN-5 SA-04: Advanced model comparison with performance trends and strengths/weaknesses analysis."""
		
		elements.append(Paragraph("⚖️ Advanced Model Performance Comparison", heading_style))
		elements.append(Spacer(1, 0.3*cm))
		
		comp_rows, best_method = ExportManager._collect_comparison_rows(results)
		
		if not comp_rows:
			elements.append(Paragraph("No performance data available for comparison.", styles['Normal']))
			return
		
		subheading_style = ParagraphStyle(
			'PerfSubheading',
			parent=styles['Heading3'],
			fontSize=10,
			textColor=colors.HexColor('#ea580c'),
			spaceAfter=6
		)
		
		# SA-04.1: Performance Strengths & Weaknesses Analysis
		elements.append(Paragraph("1. Model Strengths & Weaknesses Analysis", subheading_style))
		
		# Analyze each model's characteristics
		for row in comp_rows:
			method = row.get('method', 'Unknown')
			mape = row.get('mape', 0)
			mae = row.get('mae', 0)
			rmse = row.get('rmse', 0)
			
			# Determine model characteristics based on performance
			strengths = []
			weaknesses = []
			
			if method.upper() == 'FTS':
				strengths = ["Fast computation", "Good for fuzzy patterns", "Interpretable intervals"]
				if mape <= 10:
					strengths.append("Excellent accuracy")
				else:
					weaknesses.append("Accuracy could be improved")
				weaknesses.append("Sensitive to parameter tuning")
				
			elif method.upper() == 'ANN':
				strengths = ["Learns complex patterns", "Non-linear modeling", "Adaptive learning"]
				if mape <= 8:
					strengths.append("Superior pattern recognition")
				else:
					weaknesses.append("May need more training data")
				weaknesses.extend(["Black box model", "Requires careful tuning"])
				
			elif method.upper() == 'ARIMA':
				strengths = ["Statistical foundation", "Trend modeling", "Seasonality handling"]
				if mape <= 12:
					strengths.append("Good statistical fit")
				else:
					weaknesses.append("May not capture complex patterns")
				weaknesses.append("Assumes linear relationships")
			
			# Performance classification
			perf_icon = "🥇" if method == best_method else "🥈" if mape <= 15 else "🥉"
			perf_class = "Excellent" if mape <= 5 else "Good" if mape <= 10 else "Acceptable" if mape <= 20 else "Needs Improvement"
			
			elements.append(Paragraph(f"{perf_icon} **{method}** - {perf_class} Performance", styles['Heading4']))
			elements.append(Paragraph(f"MAPE: {mape:.2f}% | MAE: {mae:.2f} | RMSE: {rmse:.2f}", styles['Normal']))
			elements.append(Paragraph(f"**Strengths:** {', '.join(strengths)}", styles['Normal']))
			elements.append(Paragraph(f"**Areas for Improvement:** {', '.join(weaknesses)}", styles['Normal']))
			elements.append(Spacer(1, 0.2*cm))
		
		elements.append(Spacer(1, 0.3*cm))
		
		# SA-04.2: Cross-Model Performance Analysis
		elements.append(Paragraph("2. Cross-Model Performance Analysis", subheading_style))
		
		# Calculate performance statistics
		mape_values = [row.get('mape', 0) for row in comp_rows]
		best_mape = min(mape_values)
		worst_mape = max(mape_values)
		avg_mape = sum(mape_values) / len(mape_values) if mape_values else 0
		mape_range = worst_mape - best_mape
		
		# Performance insights
		insights = [
			f"📊 **Performance Overview**:",
			f"   • Best Model: {best_method} (MAPE: {best_mape:.2f}%)",
			f"   • Average Performance: {avg_mape:.2f}% MAPE",
			f"   • Performance Range: {mape_range:.2f}% spread between models",
			f"",
			f"🎯 **Model Selection Guidance**:"
		]
		
		if mape_range < 3:
			insights.append("   • Models show similar performance - choose based on interpretability needs")
		elif mape_range < 8:
			insights.append("   • Moderate performance difference - best model recommended for production")
		else:
			insights.append("   • Significant performance gap - strongly recommend best performing model")
		
		# Ensemble recommendations
		if len(comp_rows) >= 2:
			top_2_models = sorted(comp_rows, key=lambda x: x.get('mape', float('inf')))[:2]
			if top_2_models[1].get('mape', 0) - top_2_models[0].get('mape', 0) < 5:
				insights.extend([
					f"",
					f"🔗 **Ensemble Opportunity**:",
					f"   • Top 2 models show similar performance",
					f"   • Consider ensemble averaging for improved robustness",
					f"   • Potential accuracy improvement: 1-3% MAPE reduction"
				])
		
		# Business recommendations
		insights.extend([
			f"",
			f"💼 **Business Recommendations**:",
			f"   • Production Deployment: Use {best_method} for primary forecasting",
			f"   • Backup Strategy: Maintain secondary model for validation",
			f"   • Monitoring: Track performance degradation over time",
			f"   • Update Schedule: {'Monthly' if best_mape > 10 else 'Quarterly'} model retraining recommended"
		])
		
		for insight in insights:
			if insight.strip():  # Skip empty lines
				elements.append(Paragraph(insight, styles['Normal']))
		
	@staticmethod
	def _assess_data_quality_enhanced(
		elements: list,
		styles,
		heading_style: ParagraphStyle,
		raw_df: pd.DataFrame | None
	) -> None:
		"""RUN-5 SA-03: Enhanced data quality assessment with statistical indicators and recommendations."""
		
		if raw_df is None or raw_df.empty:
			elements.append(Paragraph("⚠️ Data Quality Assessment: No data available", heading_style))
			return
		
		norm_df = ExportManager._normalize_raw_df(raw_df)
		if norm_df.empty:
			elements.append(Paragraph("⚠️ Data Quality Assessment: Unable to process data", heading_style))
			return
		
		elements.append(Paragraph("🔍 Advanced Data Quality Assessment", heading_style))
		elements.append(Spacer(1, 0.3*cm))
		
		subheading_style = ParagraphStyle(
			'QualitySubheading',
			parent=styles['Heading3'],
			fontSize=10,
			textColor=colors.HexColor('#dc2626'),
			spaceAfter=6
		)
		
		# SA-03.1: Missing Data Analysis
		elements.append(Paragraph("1. Missing Data Analysis", subheading_style))
		
		energy_cols = [col for col in norm_df.columns if col not in ['datetime']]
		missing_analysis = []
		
		for col in energy_cols[:5]:  # Limit to first 5 sensors
			if col in norm_df.columns:
				missing_count = norm_df[col].isnull().sum()
				missing_percent = (missing_count / len(norm_df)) * 100
				status = "✅ Excellent" if missing_percent == 0 else "⚠️ Good" if missing_percent < 5 else "❌ Poor"
				
				missing_analysis.append([
					col,
					str(missing_count),
					f"{missing_percent:.1f}%",
					status
				])
		
		if missing_analysis:
			missing_table_data = [['Sensor', 'Missing Count', 'Missing %', 'Quality Status']] + missing_analysis
			missing_table = Table(missing_table_data, colWidths=[3*cm, 2.5*cm, 2.5*cm, 3*cm])
			missing_table.setStyle(TableStyle([
				('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc2626')),
				('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
				('ALIGN', (0, 0), (-1, -1), 'CENTER'),
				('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
				('FONTSIZE', (0, 0), (-1, -1), 9),
				('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
			]))
			elements.append(missing_table)
		
		elements.append(Spacer(1, 0.3*cm))
		
		# SA-03.2: Outlier Detection & Statistical Consistency
		elements.append(Paragraph("2. Outlier Detection & Statistical Consistency", subheading_style))
		
		outlier_summary = []
		overall_outliers = 0
		total_points = 0
		
		for col in energy_cols[:3]:  # Analyze first 3 sensors
			if col in norm_df.columns:
				# IQR method for outlier detection
				Q1 = norm_df[col].quantile(0.25)
				Q3 = norm_df[col].quantile(0.75)
				IQR = Q3 - Q1
				lower_bound = Q1 - 1.5 * IQR
				upper_bound = Q3 + 1.5 * IQR
				
				outliers = ((norm_df[col] < lower_bound) | (norm_df[col] > upper_bound)).sum()
				outlier_rate = (outliers / len(norm_df)) * 100
				
				# Statistical measures
				mean_val = norm_df[col].mean()
				std_val = norm_df[col].std()
				cv = (std_val / mean_val) * 100 if mean_val > 0 else 0  # Coefficient of variation
				
				overall_outliers += outliers
				total_points += len(norm_df)
				
				stability_status = "✅ Stable" if cv < 20 else "⚠️ Moderate" if cv < 50 else "❌ Volatile"
				
				outlier_summary.append([
					col,
					f"{outliers}",
					f"{outlier_rate:.1f}%",
					f"{cv:.1f}%",
					stability_status
				])
		
		if outlier_summary:
			outlier_table_data = [['Sensor', 'Outliers', 'Outlier Rate', 'Variability (CV)', 'Stability']] + outlier_summary
			outlier_table = Table(outlier_table_data, colWidths=[2.5*cm, 2*cm, 2.5*cm, 2.5*cm, 2.5*cm])
			outlier_table.setStyle(TableStyle([
				('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc2626')),
				('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
				('ALIGN', (0, 0), (-1, -1), 'CENTER'),
				('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
				('FONTSIZE', (0, 0), (-1, -1), 8),
				('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
			]))
			elements.append(outlier_table)
		
		# SA-03.3: Data Quality Recommendations
		elements.append(Spacer(1, 0.3*cm))
		elements.append(Paragraph("3. Data Quality Recommendations", subheading_style))
		
		overall_outlier_rate = (overall_outliers / total_points) * 100 if total_points > 0 else 0
		total_missing = sum(norm_df[col].isnull().sum() for col in energy_cols if col in norm_df.columns)
		overall_missing_rate = (total_missing / (len(energy_cols) * len(norm_df))) * 100 if len(energy_cols) > 0 else 0
		
		recommendations = [
			f"📊 **Overall Data Quality Score**: {100 - overall_missing_rate - overall_outlier_rate:.1f}/100",
			f"",
			f"🔧 **Immediate Actions Required**:"
		]
		
		if overall_missing_rate > 5:
			recommendations.extend([
				f"   • ❌ High missing data rate ({overall_missing_rate:.1f}%) - Review data collection processes",
				f"   • Implement data validation checks at source"
			])
		elif overall_missing_rate > 1:
			recommendations.append(f"   • ⚠️ Moderate missing data ({overall_missing_rate:.1f}%) - Monitor data collection")
		else:
			recommendations.append(f"   • ✅ Excellent data completeness ({100-overall_missing_rate:.1f}%)")
		
		if overall_outlier_rate > 5:
			recommendations.extend([
				f"   • ❌ High outlier rate ({overall_outlier_rate:.1f}%) - Investigate sensor calibration",
				f"   • Consider data preprocessing with outlier filtering"
			])
		elif overall_outlier_rate > 2:
			recommendations.append(f"   • ⚠️ Moderate outlier rate ({overall_outlier_rate:.1f}%) - Regular sensor maintenance")
		else:
			recommendations.append(f"   • ✅ Low outlier rate ({overall_outlier_rate:.1f}%) - Good sensor stability")
		
		recommendations.extend([
			f"",
			f"💡 **Long-term Improvements**:",
			f"   • Implement real-time data quality monitoring",
			f"   • Setup automated alerts for data anomalies", 
			f"   • Regular sensor calibration schedule",
			f"   • Data preprocessing pipeline optimization"
		])
		
		for rec in recommendations:
			if rec.strip():  # Skip empty lines
				elements.append(Paragraph(rec, styles['Normal']))
		
	@staticmethod
	def _generate_predictive_insights(
		elements: list,
		styles,
		heading_style: ParagraphStyle,
		results: Dict
	) -> None:
		"""RUN-5 SA-02: Advanced predictive insights with confidence intervals and scenario analysis."""
		
		elements.append(Paragraph("🔮 Predictive Insights & Scenario Analysis", heading_style))
		elements.append(Spacer(1, 0.3*cm))
		
		# Collect model performance data
		comp_rows, best_method = ExportManager._collect_comparison_rows(results)
		
		# SA-02.1: Forecast Confidence Analysis
		subheading_style = ParagraphStyle(
			'InsightSubheading',
			parent=styles['Heading3'],
			fontSize=10,
			textColor=colors.HexColor('#7c3aed'),
			spaceAfter=6
		)
		
		elements.append(Paragraph("1. Forecast Confidence Assessment", subheading_style))
		
		# Calculate confidence levels based on MAPE
		confidence_analysis = []
		for row in comp_rows:
			method = row.get('method', 'Unknown')
			mape = row.get('mape', 0)
			
			# Confidence classification based on MAPE ranges
			if mape <= 5:
				confidence = "Very High (95%+)"
				icon = "🟢"
			elif mape <= 10:
				confidence = "High (85-95%)"
				icon = "🟡"
			elif mape <= 20:
				confidence = "Moderate (70-85%)"
				icon = "🟠"
			else:
				confidence = "Low (<70%)"
				icon = "🔴"
			
			confidence_analysis.append([
				f"{icon} {method}",
				f"{mape:.2f}%",
				confidence
			])
		
		if confidence_analysis:
			conf_table_data = [['Model', 'MAPE', 'Confidence Level']] + confidence_analysis
			conf_table = Table(conf_table_data, colWidths=[4*cm, 2.5*cm, 4.5*cm])
			conf_table.setStyle(TableStyle([
				('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7c3aed')),
				('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
				('ALIGN', (0, 0), (-1, -1), 'CENTER'),
				('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
				('FONTSIZE', (0, 0), (-1, -1), 9),
				('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
			]))
			elements.append(conf_table)
		
		elements.append(Spacer(1, 0.3*cm))
		
		# SA-02.2: Scenario Analysis
		elements.append(Paragraph("2. Scenario Analysis & Business Recommendations", subheading_style))
		
		# Get best and worst models
		best_mape = min([row.get('mape', float('inf')) for row in comp_rows])
		worst_mape = max([row.get('mape', 0) for row in comp_rows])
		
		best_model = next((row.get('method') for row in comp_rows if row.get('mape') == best_mape), 'Unknown')
		worst_model = next((row.get('method') for row in comp_rows if row.get('mape') == worst_mape), 'Unknown')
		
		# Business scenarios based on performance
		scenarios = [
			f"🎯 **Best Case Scenario ({best_model})**",
			f"   • Accuracy: {best_mape:.2f}% MAPE - Excellent predictive performance",
			f"   • Business Impact: High confidence in demand forecasting",
			f"   • Recommendation: Deploy for production energy planning",
			f"",
			f"⚠️ **Worst Case Scenario ({worst_model})**", 
			f"   • Accuracy: {worst_mape:.2f}% MAPE - Requires improvement",
			f"   • Business Impact: Limited reliability for critical decisions",
			f"   • Recommendation: Use as backup or require manual validation",
			f"",
			f"📊 **Performance Range Analysis**",
			f"   • Accuracy Spread: {worst_mape - best_mape:.2f}% difference between models",
			f"   • Model Consistency: {'High' if (worst_mape - best_mape) < 5 else 'Moderate' if (worst_mape - best_mape) < 10 else 'Low'}",
			f"   • Ensemble Potential: {'Recommended' if len(comp_rows) >= 2 else 'Single model sufficient'}"
		]
		
		for scenario in scenarios:
			if scenario.strip():  # Skip empty lines
				elements.append(Paragraph(scenario, styles['Normal']))
		
		elements.append(Spacer(1, 0.4*cm))
		
		# KPI Cards Table
		kpi_style = ParagraphStyle(
			"KPIStyle",
			parent=styles["Normal"],
			fontSize=10,
			textColor=colors.HexColor("#1f2937"),
		)
		
		# Build KPI Dashboard as table
		kpi_headers = ["Key Performance Indicator", "Value", "Status"]
		kpi_rows = [kpi_headers]
		
		# Model Performance KPIs
		if best_method and best_mape is not None:
			mape_status = "EXCELLENT" if best_mape < 5 else "GOOD" if best_mape < 10 else "FAIR"
			kpi_rows.append(["Best Model", best_method, f"MAPE: {ExportManager._fmt_mape(best_mape)}%"])
			kpi_rows.append(["Model Accuracy", mape_status, f"{ExportManager._fmt_mape(best_mape)}%"])
		else:
			kpi_rows.append(["Best Model", "N/A", "PENDING"])
			kpi_rows.append(["Model Accuracy", "N/A", "PENDING"])
		
		# Data Quality KPIs
		if not norm_df.empty:
			data_completeness = (norm_df["watt"].notna().sum() / len(norm_df)) * 100
			completeness_status = "EXCELLENT" if data_completeness >= 95 else "GOOD" if data_completeness >= 80 else "NEEDS ATTENTION"
			kpi_rows.append(["Data Completeness", completeness_status, f"{data_completeness:.1f}%"])
		else:
			kpi_rows.append(["Data Completeness", "N/A", "NO DATA"])
		
		# Sensitivity Analysis KPI
		improvement_pct = ExportManager._to_float(sens.get("improvement", 0.0))
		if improvement_pct < 0:
			sens_status = "OPTIMIZATION AVAILABLE"
			sens_value = f"Potential improvement: {abs(improvement_pct):.2f}%"
		else:
			sens_status = "OPTIMAL"
			sens_value = "Current configuration is optimal"
		kpi_rows.append(["Configuration Status", sens_status, sens_value])
		kpi_rows.append(["Recommended Setting", best_case_label, "From sensitivity analysis"])
		
		# Create KPI table
		kpi_table = Table(kpi_rows, colWidths=[6*cm, 4*cm, 6*cm])
		ExportManager._style_table(kpi_table, align="LEFT", font_size=9)
		
		# Style the KPI table with status colors
		status_styles = []
		for i, row in enumerate(kpi_rows[1:], 1):  # Skip header
			if "EXCELLENT" in row[1] or "OPTIMAL" in row[1]:
				status_styles.append(("BACKGROUND", (1, i), (1, i), colors.HexColor("#d1fae5")))
			elif "GOOD" in row[1] or "OPTIMIZATION" in row[1]:
				status_styles.append(("BACKGROUND", (1, i), (1, i), colors.HexColor("#fef3c7")))
			elif "NEEDS ATTENTION" in row[1] or "NO DATA" in row[1]:
				status_styles.append(("BACKGROUND", (1, i), (1, i), colors.HexColor("#fee2e2")))
		
		if status_styles:
			kpi_table.setStyle(TableStyle(status_styles))
		
		elements.append(Paragraph("Key Performance Indicators", heading_style))
		elements.append(kpi_table)
		elements.append(Spacer(1, 0.5*cm))
		
		# Quick Insights Generator
		elements.append(Paragraph("Quick Insights", heading_style))
		
		insights = []
		
		# Model performance insights
		if best_method and best_mape is not None:
			if best_mape < 5:
				insights.append(f"🟢 <b>Excellent Performance:</b> {best_method} achieved outstanding accuracy with MAPE of {ExportManager._fmt_mape(best_mape)}%, indicating highly reliable predictions.")
			elif best_mape < 10:
				insights.append(f"🟡 <b>Good Performance:</b> {best_method} delivered solid results with MAPE of {ExportManager._fmt_mape(best_mape)}%, suitable for practical forecasting.")
			else:
				insights.append(f"🔴 <b>Room for Improvement:</b> {best_method} achieved MAPE of {ExportManager._fmt_mape(best_mape)}%. Consider parameter optimization or alternative approaches.")
		
		# Data quality insights
		if not norm_df.empty:
			median_interval = ExportManager._compute_median_interval_seconds(norm_df)
			if median_interval > 0:
				if median_interval <= 60:
					insights.append("🟢 <b>High-Resolution Data:</b> Median measurement interval of {:.0f} seconds provides excellent temporal granularity for forecasting.".format(median_interval))
				elif median_interval <= 300:
					insights.append("🟡 <b>Good Resolution:</b> Median measurement interval of {:.1f} minutes offers adequate temporal resolution.".format(median_interval/60))
				else:
					insights.append("🔴 <b>Low Resolution:</b> Median measurement interval of {:.1f} minutes may limit short-term prediction accuracy.".format(median_interval/60))
		
		# Sensitivity insights
		if improvement_pct < -2:
			insights.append(f"🚀 <b>Optimization Opportunity:</b> Switching to {best_case_label} configuration could improve MAPE by {abs(improvement_pct):.2f}%.")
		elif improvement_pct < 0:
			insights.append(f"🔧 <b>Minor Optimization:</b> {best_case_label} configuration shows marginal improvement of {abs(improvement_pct):.2f}%.")
		else:
			insights.append("✅ <b>Optimal Configuration:</b> Current parameter settings are already optimal for this dataset.")
		
		# Data pattern insights
		if not norm_df.empty and norm_df["watt"].notna().any():
			watt_std = norm_df["watt"].std()
			watt_mean = norm_df["watt"].mean()
			cv = (watt_std / watt_mean) * 100 if watt_mean != 0 else 0
			if cv < 10:
				insights.append("📈 <b>Stable Power Pattern:</b> Low variability (CV={:.1f}%) indicates predictable consumption patterns.".format(cv))
			elif cv < 30:
				insights.append("📊 <b>Moderate Variability:</b> Power consumption shows moderate variation (CV={:.1f}%).".format(cv))
			else:
				insights.append("📉 <b>High Variability:</b> Significant power fluctuations (CV={:.1f}%) present forecasting challenges.".format(cv))
		
		# Render insights
		for insight in insights:
			elements.append(Paragraph(insight, overview_style))
			elements.append(Spacer(1, 0.2*cm))
		
		elements.append(Spacer(1, 0.5*cm))
		
		# Visual Executive Dashboard - Model Comparison Chart
		if comp_rows:
			elements.append(Paragraph("Model Performance Comparison", heading_style))
			
			# RUN-2: Professional styling setup
			ExportManager._setup_matplotlib_style()
			
			# Create comparison chart
			fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
			
			# MAPE Comparison Bar Chart
			methods = [row["method"] for row in comp_rows]
			mapes = [row.get("mape", 0) for row in comp_rows]
			# RUN-2: Use standardized colors
			colors_bar = [CHART_CONFIG['colors']['status']['excellent'] if method == best_method 
						 else CHART_CONFIG['colors']['status']['fair'] for method in methods]
			
			bars = ax1.bar(methods, mapes, color=colors_bar, alpha=0.8, 
						 edgecolor='white', linewidth=1.5)
			
			# RUN-2: Apply professional styling
			ExportManager._apply_professional_styling(ax1, 
				title='Model Accuracy (Lower is Better)',
				ylabel='MAPE (%)')
			
			# RUN-2: Enhanced value labels with professional styling
			for bar, mape in zip(bars, mapes):
				height = bar.get_height()
				ax1.text(bar.get_x() + bar.get_width()/2., height + 0.1,
						f'{mape:.2f}%', ha='center', va='bottom',
						fontweight='600', color='#1f2937', fontsize=8)
			
			# Model Ranking Pie Chart
			if len(comp_rows) > 1:
				best_share = 50
				others_share = 50 / (len(comp_rows) - 1)
				sizes = [best_share] + [others_share] * (len(comp_rows) - 1)
				# RUN-2: Use status colors for consistency
				colors_pie = [CHART_CONFIG['colors']['status']['excellent'],
							 CHART_CONFIG['colors']['status']['good'],
							 CHART_CONFIG['colors']['status']['fair']][:len(comp_rows)]
				
				wedges, texts, autotexts = ax2.pie(sizes, labels=methods, autopct='%1.0f%%', 
													  colors=colors_pie, startangle=90,
													  explode=[0.05 if m == best_method else 0 for m in methods])
				# RUN-2: Style pie chart text
				for autotext in autotexts:
					autotext.set_color('white')
					autotext.set_fontweight('600')
					autotext.set_fontsize(8)
				for text in texts:
					text.set_fontsize(8)
					text.set_color('#1f2937')
				
				ax2.set_title('Model Performance Distribution', 
							 fontsize=CHART_CONFIG['figure_params']['axes.titlesize'],
							 fontweight='600', color='#1f2937', pad=12)
			else:
				ax2.text(0.5, 0.5, 'Only one model\navailable', ha='center', va='center', 
						 transform=ax2.transAxes, fontsize=10, color='#6b7280')
				ax2.set_title('Model Distribution',
							 fontsize=CHART_CONFIG['figure_params']['axes.titlesize'],
							 fontweight='600', color='#1f2937', pad=12)
			
			plt.tight_layout()
			
			# Save chart to BytesIO
			img_buffer = io.BytesIO()
			# RUN-2: Enhanced DPI
			plt.savefig(img_buffer, format='png', dpi=CHART_CONFIG['dpi'], bbox_inches='tight')
			img_buffer.seek(0)
			plt.close(fig)
			
			# Add chart to PDF
			chart_img = Image(img_buffer, width=16*cm, height=6*cm)
			elements.append(chart_img)
			elements.append(Spacer(1, 0.5*cm))
		
		# Recommendations Section
		elements.append(Paragraph("Executive Recommendations", heading_style))
		
		recommendations = []
		
		# Primary recommendation
		if best_method and best_mape is not None:
			recommendations.append(f"<b>1. Model Selection:</b> Deploy {best_method} as the primary forecasting model with {ExportManager._fmt_mape(best_mape)}% MAPE accuracy.")
		
		# Optimization recommendation
		if improvement_pct < -1:
			recommendations.append(f"<b>2. Configuration Optimization:</b> Implement {best_case_label} parameters to achieve potential {abs(improvement_pct):.2f}% accuracy improvement.")
		elif improvement_pct < 0:
			recommendations.append(f"<b>2. Fine-tuning:</b> Consider {best_case_label} configuration for marginal performance gains.")
		else:
			recommendations.append("<b>2. Configuration:</b> Current parameter settings are optimal; maintain existing configuration.")
		
		# Data quality recommendation
		if not norm_df.empty:
			data_completeness = (norm_df["watt"].notna().sum() / len(norm_df)) * 100
			if data_completeness < 95:
				recommendations.append(f"<b>3. Data Quality:</b> Address {100-data_completeness:.1f}% missing data to improve model reliability.")
			else:
				recommendations.append("<b>3. Data Quality:</b> Excellent data completeness supports reliable forecasting.")
		
		# Monitoring recommendation
		recommendations.append("<b>4. Monitoring:</b> Implement continuous model performance monitoring and periodic retraining based on new data patterns.")
		
		for rec in recommendations:
			elements.append(Paragraph(rec, overview_style))
			elements.append(Spacer(1, 0.2*cm))
		
		elements.append(PageBreak())

	@staticmethod
	def _generate_statistical_summary(
		elements: list,
		styles,
		heading_style: ParagraphStyle,
		raw_df: pd.DataFrame | None,
		results: Dict
	) -> None:
		"""RUN-5 SA-01: Comprehensive statistical analysis with consumption patterns, seasonality, and efficiency metrics."""
		
		if raw_df is None or raw_df.empty:
			return
		
		norm_df = ExportManager._normalize_raw_df(raw_df)
		if norm_df.empty:
			return
		
		# Statistical Summary Section Header
		elements.append(Paragraph("📊 Statistical Analysis & Insights", heading_style))
		elements.append(Spacer(1, 0.3*cm))
		
		# SA-01.1: Consumption Patterns Analysis
		subheading_style = ParagraphStyle(
			'StatSubheading',
			parent=styles['Heading3'],
			fontSize=10,
			textColor=colors.HexColor('#2563eb'),
			spaceAfter=6
		)
		
		elements.append(Paragraph("1. Consumption Patterns Analysis", subheading_style))
		
		# Peak vs Off-peak analysis
		if 'datetime' in norm_df.columns:
			norm_df['hour'] = pd.to_datetime(norm_df['datetime']).dt.hour
			norm_df['day_of_week'] = pd.to_datetime(norm_df['datetime']).dt.day_name()
			
			# Define peak hours (7-9 AM, 6-9 PM)
			peak_hours = [7, 8, 9, 18, 19, 20, 21]
			norm_df['is_peak'] = norm_df['hour'].isin(peak_hours)
			
			# Energy consumption analysis for all sensors
			energy_cols = [col for col in norm_df.columns if col not in ['datetime', 'hour', 'day_of_week', 'is_peak']]
			
			peak_analysis = []
			for col in energy_cols[:3]:  # Limit to first 3 sensors for space
				if col in norm_df.columns:
					peak_mean = norm_df[norm_df['is_peak'] == True][col].mean()
					off_peak_mean = norm_df[norm_df['is_peak'] == False][col].mean()
					peak_ratio = peak_mean / off_peak_mean if off_peak_mean > 0 else 0
					
					peak_analysis.append([
						col,
						f"{peak_mean:.2f}",
						f"{off_peak_mean:.2f}", 
						f"{peak_ratio:.2f}x"
					])
			
			if peak_analysis:
				peak_table_data = [['Sensor', 'Peak Hours Avg', 'Off-Peak Avg', 'Peak Ratio']] + peak_analysis
				peak_table = Table(peak_table_data, colWidths=[4*cm, 3*cm, 3*cm, 2.5*cm])
				peak_table.setStyle(TableStyle([
					('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
					('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
					('ALIGN', (0, 0), (-1, -1), 'CENTER'),
					('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
					('FONTSIZE', (0, 0), (-1, -1), 9),
					('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
				]))
				elements.append(peak_table)
		
		elements.append(Spacer(1, 0.3*cm))
		
		# SA-01.2: Seasonality Detection
		elements.append(Paragraph("2. Seasonality & Temporal Patterns", subheading_style))
		
		if 'datetime' in norm_df.columns and 'hour' in norm_df.columns:
			# Weekly patterns analysis
			main_sensor = energy_cols[0] if energy_cols else None  # Use first sensor as representative
			if main_sensor and main_sensor in norm_df.columns:
				weekly_stats = norm_df.groupby('day_of_week')[main_sensor].agg(['mean', 'std']).round(2)
				
				# Find peak day
				peak_day = weekly_stats['mean'].idxmax()
				low_day = weekly_stats['mean'].idxmin()
				variability = weekly_stats['std'].mean()
				
				seasonality_text = [
					f"📈 Peak Day: {peak_day} (Avg: {weekly_stats.loc[peak_day, 'mean']:.2f})",
					f"📉 Lowest Day: {low_day} (Avg: {weekly_stats.loc[low_day, 'mean']:.2f})",
					f"📊 Weekly Variability: {variability:.2f} (Standard deviation)",
					f"🔄 Data Coverage: {len(norm_df)} observations across {norm_df['day_of_week'].nunique()} unique days"
				]
				
				for text in seasonality_text:
					elements.append(Paragraph(text, styles['Normal']))
		
		elements.append(Spacer(1, 0.3*cm))
		
		# SA-01.3: Efficiency Metrics
		elements.append(Paragraph("3. Efficiency Metrics & Quality Assessment", subheading_style))
		
		if energy_cols:
			# Data quality metrics
			total_readings = len(norm_df)
			missing_percent = (norm_df[energy_cols].isnull().sum().sum() / (len(energy_cols) * total_readings)) * 100
			
			# Energy efficiency indicators
			avg_consumption = norm_df[energy_cols].mean().mean()
			consumption_stability = 1 - (norm_df[energy_cols].std().mean() / avg_consumption) if avg_consumption > 0 else 0
			
			# Outlier detection (simple IQR method)
			outliers_detected = 0
			for col in energy_cols:
				if col in norm_df.columns:
					Q1 = norm_df[col].quantile(0.25)
					Q3 = norm_df[col].quantile(0.75)
					IQR = Q3 - Q1
					lower_bound = Q1 - 1.5 * IQR
					upper_bound = Q3 + 1.5 * IQR
					outliers_detected += ((norm_df[col] < lower_bound) | (norm_df[col] > upper_bound)).sum()
			
			outlier_rate = (outliers_detected / (len(energy_cols) * total_readings)) * 100
			
			# Quality indicators
			quality_metrics = [
				["📊 Data Completeness", f"{100 - missing_percent:.1f}%", "✅ Excellent" if missing_percent < 1 else "⚠️ Good" if missing_percent < 5 else "❌ Poor"],
				["🎯 Consumption Stability", f"{consumption_stability:.1%}", "✅ Stable" if consumption_stability > 0.8 else "⚠️ Moderate" if consumption_stability > 0.6 else "❌ Volatile"],
				["🔍 Outlier Rate", f"{outlier_rate:.1f}%", "✅ Clean" if outlier_rate < 2 else "⚠️ Acceptable" if outlier_rate < 5 else "❌ High"],
				["📈 Average Consumption", f"{avg_consumption:.2f}", "ℹ️ Baseline"]
			]
			
			quality_table = Table(quality_metrics, colWidths=[4*cm, 3*cm, 4*cm])
			quality_table.setStyle(TableStyle([
				('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
				('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
				('ALIGN', (0, 0), (-1, -1), 'LEFT'),
				('ALIGN', (1, 0), (1, -1), 'CENTER'),
				('ALIGN', (2, 0), (2, -1), 'CENTER'),
				('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
				('FONTSIZE', (0, 0), (-1, -1), 9),
				('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
			]))
			elements.append(quality_table)
		
		elements.append(Spacer(1, 0.4*cm))

	@staticmethod
	def _build_caption(
		results: Dict,
		params: Dict | None,
		device_name: str,
		date_range: str,
		total_points: int,
	) -> str:
		fts_metrics = results.get("fts", {}).get("metrics", {})
		fts_mape = ExportManager._to_float(fts_metrics.get("mape"))

		method = ExportManager._get_param(params, "fts", "partition", default="equal-width")
		method = str(method).strip().lower()
		if method in ["equal frequency", "equal-frequency", "equalfrequency"]:
			method_label = "equal-frequency"
		else:
			method_label = "equal-width"

		n_val = ExportManager._get_param(params, "fts", "interval", default=None)
		if n_val is None:
			n_val = len(results.get("fts", {}).get("artifacts", {}).get("intervals", [])) or "-"
		pad_pct = ExportManager._get_param(params, "fts", "pad_pct", default=None)
		if pad_pct is None:
			pad_pct = ExportManager._get_param(params, "fts", "padPct", default=0.05)

		comp_rows, best_method = ExportManager._collect_comparison_rows(results)
		best_mape = "-"
		for row in comp_rows:
			if row.get("method") == best_method:
				best_mape = ExportManager._fmt_mape(row.get("mape"))

		sens = results.get("sensitivity") or {}
		best_case_id = sens.get("bestCase")
		best_case_label = "N/A"
		for case in sens.get("cases", []):
			if case.get("id") == best_case_id:
				best_case_label = case.get("label", "N/A")
				break
		improvement = ExportManager._to_float(sens.get("improvement", 0.0))
		if improvement < 0:
			sens_text = f"Sensitivity menyarankan {best_case_label} (improve {abs(improvement):.2f}%)."
		else:
			sens_text = "Konfigurasi saat ini sudah optimal."

		return (
			f"Analisis perbandingan FTS Cheng, ANN, dan ARIMA pada {device_name} "
			f"periode {date_range} dengan {total_points} titik data. "
			f"FTS parameter n={n_val}, method={method_label}, pad={float(pad_pct) * 100:.0f}% "
			f"memberi MAPE={ExportManager._fmt_mape(fts_mape)}%. "
			f"Model terbaik: {best_method or 'N/A'} (MAPE={best_mape}%). "
			f"{sens_text}"
		)

	@staticmethod
	def _append_summary_sections(
		elements: list,
		styles,
		heading_style: ParagraphStyle,
		results: Dict,
		params: Dict | None = None,
		raw_df: pd.DataFrame | None = None,
	) -> None:
		full_series = results.get("data", {}).get("full")
		norm_df = ExportManager._normalize_raw_df(raw_df)
		raw_total_points = int(len(norm_df)) if not norm_df.empty else 0
		total_points = raw_total_points if raw_total_points > 0 else int(len(full_series)) if full_series is not None else 0
		device_name = ExportManager._get_device_name(raw_df)
		date_range = ExportManager._get_date_range_from_df(raw_df)
		if date_range == "Unknown":
			date_range = ExportManager._get_date_range_from_series(full_series)

		subheading_style = ParagraphStyle(
			"CustomSubHeading",
			parent=styles["Heading3"],
			fontSize=11,
			textColor=colors.HexColor("#0f172a"),
			spaceAfter=6,
			spaceBefore=6,
		)

		# Dataset Summary
		elements.append(Paragraph("1. Dataset Summary", heading_style))
		start_ts = "-"
		end_ts = "-"
		if not norm_df.empty:
			ts_series = norm_df["timestamp"].dropna()
			if not ts_series.empty:
				start_ts = ExportManager._fmt_ts(ts_series.iloc[0])
				end_ts = ExportManager._fmt_ts(ts_series.iloc[-1])
		elif full_series is not None and len(full_series) > 0:
			start_ts = ExportManager._fmt_ts(full_series.index.min())
			end_ts = ExportManager._fmt_ts(full_series.index.max())
		median_sec = ExportManager._compute_median_interval_seconds(norm_df)
		if median_sec > 0:
			median_str = f"{median_sec:.0f} seconds ({median_sec / 60:.1f} min)"
		else:
			median_str = "N/A"
		data_rows = [
			["Item", "Value"],
			["Device", device_name],
			["Date Range", date_range],
			["Total Rows", f"{total_points:,}"],
			["Start Time", start_ts],
			["End Time", end_ts],
			["Median Interval", median_str],
		]
		if not norm_df.empty and norm_df["synthetic"].notna().any():
			synthetic_count = int(norm_df["synthetic"].fillna(False).astype(bool).sum())
			pct = (synthetic_count / total_points * 100) if total_points else 0.0
			data_rows.append(["Synthetic Points", f"{synthetic_count} ({pct:.1f}%)"])
		data_tbl = Table(data_rows, colWidths=[5 * cm, 9 * cm])
		ExportManager._style_table(data_tbl, align="LEFT", font_size=9)
		elements.append(data_tbl)
		elements.append(Spacer(1, 0.4 * cm))

		# First/Last 10 Rows
		include_synthetic = not norm_df.empty and norm_df["synthetic"].notna().any()
		headers = ["Timestamp", "V (V)", "A (A)", "W (W)", "kWh", "Hz", "PF"]
		col_widths = [4.5 * cm, 2 * cm, 2 * cm, 2 * cm, 2.2 * cm, 1.8 * cm, 1.8 * cm]
		if include_synthetic:
			headers.append("Synthetic")
			col_widths.append(2 * cm)

		def _append_rows_section(title: str, df_slice: pd.DataFrame) -> None:
			elements.append(Paragraph(title, heading_style))
			if df_slice.empty:
				elements.append(Paragraph("No data available.", styles["Normal"]))
				elements.append(Spacer(1, 0.3 * cm))
				return
			row_list = [headers]
			for _, row in df_slice.iterrows():
				row_values = [
					ExportManager._fmt_ts(row.get("timestamp")),
					ExportManager._fmt_number(row.get("voltage"), 2),
					ExportManager._fmt_number(row.get("current"), 3),
					ExportManager._fmt_number(row.get("watt"), 2),
					ExportManager._fmt_number(row.get("energy_kwh"), 4),
					ExportManager._fmt_number(row.get("frequency"), 1),
					ExportManager._fmt_number(row.get("pf"), 3),
				]
				if include_synthetic:
					row_values.append("Yes" if bool(row.get("synthetic")) else "")
				row_list.append(row_values)
			row_tbl = Table(row_list, colWidths=col_widths)
			ExportManager._style_table(row_tbl, font_size=8)
			elements.append(row_tbl)
			elements.append(Spacer(1, 0.4 * cm))

		if not norm_df.empty:
			_append_rows_section("2. First 10 Rows", norm_df.head(10))
			_append_rows_section("3. Last 10 Rows", norm_df.tail(10))
		else:
			_append_rows_section("2. First 10 Rows", pd.DataFrame())
			_append_rows_section("3. Last 10 Rows", pd.DataFrame())

		# Global Resume
		elements.append(Paragraph("4. Global Resume", heading_style))
		if not norm_df.empty:
			overall_chart = ExportManager._build_global_resume_chart(norm_df)
			if overall_chart is not None:
				elements.append(Paragraph("4.0 Overall", subheading_style))
				elements.append(overall_chart)
				elements.append(Spacer(1, 0.25 * cm))
			else:
				elements.append(Paragraph("Grafik overall tidak tersedia.", styles["Normal"]))

			charts_spec = [
				("voltage", "4.1 Tegangan (V)", "#ef4444", "Voltage (V)"),
				("watt", "4.2 Daya (W)", "#f59e0b", "Power (W)"),
				("current", "4.3 Arus (A)", "#06b6d4", "Current (A)"),
				("energy_kwh", "4.4 Energi (kWh)", "#10b981", "Energy (kWh)"),
				("pf", "4.5 Power Factor", "#64748b", "PF"),
			]
			
			# RUN-4: Statistical analysis parameters (exclude PF from statistical tables)
			statistical_params = [
				("voltage", "V", "Tegangan"),
				("watt", "W", "Daya"), 
				("current", "A", "Arus"),
				("energy_kwh", "kWh", "Energi")
			]
			
			for key, title, color, y_label in charts_spec:
				chart = ExportManager._build_single_series_chart(norm_df, key, title, color, y_label)
				if chart is None:
					elements.append(Paragraph(f"{title} tidak tersedia.", styles["Normal"]))
					continue
				elements.append(Paragraph(title, subheading_style))
				elements.append(chart)
				elements.append(Spacer(1, 0.25 * cm))
				
				# RUN-4: Add statistical table and mathematical documentation for main parameters
				param_info = next((p for p in statistical_params if p[0] == key), None)
				if param_info:
					param_key, unit, param_name = param_info
					
					# Generate statistical analysis table
					stat_table = ExportManager._generate_statistical_analysis_table(
						norm_df, param_key, param_name, unit
					)
					
					if stat_table is not None:
						elements.append(Paragraph(f"Analisis Statistik {param_name}:", subheading_style))
						elements.append(stat_table)
						elements.append(Spacer(1, 0.2 * cm))
						
						# Add mathematical process documentation
						ExportManager._generate_mathematical_process_doc(
							elements, styles, param_name
						)
					else:
						elements.append(Paragraph(f"Data statistik {param_name.lower()} tidak tersedia.", styles["Normal"]))
						elements.append(Spacer(1, 0.2 * cm))

			df_current = norm_df.dropna(subset=["current"])
			if not df_current.empty:
				top_n = min(5, len(df_current))
				highest_df = df_current.sort_values("current", ascending=False).head(top_n)
				lowest_df = df_current.sort_values("current", ascending=True).head(top_n)

				def _append_extreme_table(title: str, df_extreme: pd.DataFrame) -> None:
					elements.append(Paragraph(title, subheading_style))
					rows = [["Rank", "Timestamp", "A (A)", "W (W)", "V (V)", "Hz", "kWh", "PF"]]
					for idx, row in enumerate(df_extreme.iterrows(), start=1):
						_, data = row
						rows.append(
							[
								str(idx),
								ExportManager._fmt_ts(data.get("timestamp")),
								ExportManager._fmt_number(data.get("current"), 3),
								ExportManager._fmt_number(data.get("watt"), 2),
								ExportManager._fmt_number(data.get("voltage"), 2),
								ExportManager._fmt_number(data.get("frequency"), 1),
								ExportManager._fmt_number(data.get("energy_kwh"), 4),
								ExportManager._fmt_number(data.get("pf"), 3),
							]
						)
					table = Table(rows, colWidths=[1.2 * cm, 4.2 * cm, 2 * cm, 2 * cm, 2 * cm, 1.6 * cm, 2 * cm, 1.6 * cm])
					ExportManager._style_table(table, font_size=8)
					elements.append(table)
					elements.append(Spacer(1, 0.3 * cm))

				_append_extreme_table("4.6 Highest Current Points (Arus)", highest_df)
				_append_extreme_table("4.7 Lowest Current Points (Arus)", lowest_df)
			else:
				elements.append(Paragraph("Tidak ada data arus untuk resume global.", styles["Normal"]))

			# 4.8 HOME Average summary (referensi Tab HOME Average)
			elements.append(Paragraph("4.8 HOME Average Summary (Rata-rata)", subheading_style))
			if not norm_df.empty:
				ts_series = pd.to_datetime(norm_df["timestamp"], errors="coerce").dropna().sort_values()
				start_date = ExportManager._fmt_date(ts_series.iloc[0]) if not ts_series.empty else "-"
				end_date = ExportManager._fmt_date(ts_series.iloc[-1]) if not ts_series.empty else "-"

				def _mean_or_zero(series: pd.Series) -> float:
					try:
						return float(pd.to_numeric(series, errors="coerce").fillna(0.0).mean())
					except Exception:
						return 0.0

				def _energy_kwh_avg(df: pd.DataFrame) -> tuple[float, str]:
					"""Hitung energi kWh dan anotasi metode: SENSOR_DELTA atau INTEGRATION."""
					try:
						if df is None or df.empty:
							return 0.0, "UNKNOWN"
						energy_vals = pd.to_numeric(df.get("energy_kwh"), errors="coerce").dropna()
						if len(energy_vals) >= 2:
							val = max(0.0, float(energy_vals.iloc[-1] - energy_vals.iloc[0]))
							return val, "SENSOR_DELTA"
						ts = pd.to_datetime(df.get("timestamp"), errors="coerce")
						dt_h = ts.diff().dt.total_seconds().fillna(0) / 3600.0
						watt = pd.to_numeric(df.get("watt"), errors="coerce").fillna(0.0)
						val = max(0.0, float((watt * dt_h).sum() / 1000.0))
						return val, "INTEGRATION"
					except Exception:
						return 0.0, "UNKNOWN"

				avg_rows = int(len(norm_df))
				avg_v = _mean_or_zero(norm_df["voltage"])
				avg_a = _mean_or_zero(norm_df["current"])
				avg_w = _mean_or_zero(norm_df["watt"])
				avg_hz = _mean_or_zero(norm_df["frequency"])
				avg_pf = _mean_or_zero(norm_df["pf"])
				avg_kwh, energy_method = _energy_kwh_avg(norm_df)

				avg_table_rows = [
					["Tanggal Awal", "Tanggal Akhir", "Jumlah Data", "V_avg (V)", "A_avg (A)", "W_avg (W)", "E (kWh)", "Hz_avg", "PF_avg"],
					[
						start_date,
						end_date,
						f"{avg_rows:,}",
						ExportManager._fmt_number(avg_v, 2),
						ExportManager._fmt_number(avg_a, 3),
						ExportManager._fmt_number(avg_w, 2),
						ExportManager._fmt_number(avg_kwh, 4),
						ExportManager._fmt_number(avg_hz, 1),
						ExportManager._fmt_number(avg_pf, 3),
					],
				]
				avg_tbl = Table(
					avg_table_rows,
					colWidths=[2.6 * cm, 2.6 * cm, 2.1 * cm, 1.7 * cm, 1.7 * cm, 1.7 * cm, 1.7 * cm, 1.5 * cm, 1.5 * cm],
				)
				ExportManager._style_table(avg_tbl, font_size=8)
				elements.append(avg_tbl)
				# Run-3: energy method annotation
				elements.append(Paragraph(f"Energy method: <b>{energy_method}</b>", styles["Normal"]))
				elements.append(Spacer(1, 0.3 * cm))
			else:
				elements.append(Paragraph("No data available.", styles["Normal"]))
		else:
			elements.append(Paragraph("No data available.", styles["Normal"]))
		elements.append(Spacer(1, 0.4 * cm))

		# Resume Graphic (FTS/ANN/ARIMA)
		elements.append(Paragraph("5. Resume Graphic (FTS/ANN/ARIMA)", heading_style))
		test_series = results.get("data", {}).get("test")
		if isinstance(test_series, pd.Series) and not test_series.empty:
			# Global comparison chart
			global_map = {"actual": test_series}
			if "fts" in results:
				global_map["fts"] = pd.Series(results["fts"].get("forecast", []), index=test_series.index[: len(results["fts"].get("forecast", []))])
			if "ann" in results:
				global_map["ann"] = pd.Series(results["ann"].get("forecast", []), index=test_series.index[: len(results["ann"].get("forecast", []))])
			if "arima" in results:
				global_map["arima"] = pd.Series(results["arima"].get("forecast", []), index=test_series.index[: len(results["arima"].get("forecast", []))])
			global_chart = ExportManager._build_forecast_chart(global_map, "Global Graphic (FTS/ANN/ARIMA)")
			if global_chart is not None:
				elements.append(Paragraph("5.0 Global Graphic", subheading_style))
				elements.append(global_chart)
				elements.append(Spacer(1, 0.25 * cm))

			# FTS chart
			fts_map = {"actual": test_series}
			if "fts" in results:
				fts_map["fts"] = pd.Series(results["fts"].get("forecast", []), index=test_series.index[: len(results["fts"].get("forecast", []))])
			if "naive" in results:
				fts_map["naive"] = pd.Series(results["naive"].get("forecast", []), index=test_series.index[: len(results["naive"].get("forecast", []))])
			if "ma" in results:
				fts_map["ma"] = pd.Series(results["ma"].get("forecast", []), index=test_series.index[: len(results["ma"].get("forecast", []))])
			fts_chart = ExportManager._build_forecast_chart(fts_map, "FTS Graphic (Aktual, FTS, Naive, MA)")
			if fts_chart is not None:
				elements.append(Paragraph("5.1 FTS Graphic", subheading_style))
				elements.append(fts_chart)
				elements.append(Spacer(1, 0.25 * cm))
				
				# RUN-5: FTS Main Comparison Table (5×4)
				fts_main_table = ExportManager._generate_forecast_comparison_table(
					test_series, results, table_type="main"
				)
				if fts_main_table is not None:
					elements.append(Paragraph("Perbandingan FTS (Aktual, FTS, Naive, Moving Average):", subheading_style))
					elements.append(fts_main_table)
					elements.append(Spacer(1, 0.3 * cm))

				# 5.1.1 Grafik Aktual vs FTS
				if "fts" in results and results["fts"].get("forecast"):
					series_fts = pd.Series(
						results["fts"].get("forecast", []),
						index=test_series.index[: len(results["fts"].get("forecast", []))],
					)
					cmp_map_fts = {"actual": test_series, "fts": series_fts}
					cmp_chart_fts = ExportManager._build_forecast_chart(cmp_map_fts, "Aktual vs FTS")
					if cmp_chart_fts is not None:
						elements.append(Paragraph("5.1.1 Grafik Aktual vs FTS", subheading_style))
						elements.append(cmp_chart_fts)
						elements.append(Spacer(1, 0.25 * cm))
						
						# RUN-5: FTS Sub-Table Aktual vs FTS (5×3)
						fts_sub_table = ExportManager._generate_forecast_comparison_table(
							test_series, results, table_type="fts_sub", models=["FTS"]
						)
						if fts_sub_table is not None:
							elements.append(Paragraph("Perbandingan Detail Aktual vs FTS:", subheading_style))
							elements.append(fts_sub_table)
							elements.append(Spacer(1, 0.25 * cm))

				# 5.1.2 Grafik Aktual vs Naive
				if "naive" in results and results["naive"].get("forecast"):
					series_naive = pd.Series(
						results["naive"].get("forecast", []),
						index=test_series.index[: len(results["naive"].get("forecast", []))],
					)
					cmp_map_naive = {"actual": test_series, "naive": series_naive}
					cmp_chart_naive = ExportManager._build_forecast_chart(cmp_map_naive, "Aktual vs Naive")
					if cmp_chart_naive is not None:
						elements.append(Paragraph("5.1.2 Grafik Aktual vs Naive", subheading_style))
						elements.append(cmp_chart_naive)
						elements.append(Spacer(1, 0.25 * cm))
						
						# RUN-5: FTS Sub-Table Aktual vs Naive (5×3)
						naive_sub_table = ExportManager._generate_forecast_comparison_table(
							test_series, results, table_type="fts_sub", models=["Naive"]
						)
						if naive_sub_table is not None:
							elements.append(Paragraph("Perbandingan Detail Aktual vs Naive:", subheading_style))
							elements.append(naive_sub_table)
							elements.append(Spacer(1, 0.25 * cm))

				# 5.1.3 Grafik Aktual vs Moving Average
				if "ma" in results and results["ma"].get("forecast"):
					series_ma = pd.Series(
						results["ma"].get("forecast", []),
						index=test_series.index[: len(results["ma"].get("forecast", []))],
					)
					cmp_map_ma = {"actual": test_series, "ma": series_ma}
					cmp_chart_ma = ExportManager._build_forecast_chart(cmp_map_ma, "Aktual vs Moving Average")
					if cmp_chart_ma is not None:
						elements.append(Paragraph("5.1.3 Grafik Aktual vs Moving Average", subheading_style))
						elements.append(cmp_chart_ma)
						elements.append(Spacer(1, 0.25 * cm))
						
						# RUN-5: FTS Sub-Table Aktual vs Moving Average (5×3)
						ma_sub_table = ExportManager._generate_forecast_comparison_table(
							test_series, results, table_type="fts_sub", models=["Moving Average"]
						)
						if ma_sub_table is not None:
							elements.append(Paragraph("Perbandingan Detail Aktual vs Moving Average:", subheading_style))
							elements.append(ma_sub_table)
							elements.append(Spacer(1, 0.25 * cm))

			# ANN chart
			ann_map = {"actual": test_series}
			if "ann" in results:
				ann_map["pred"] = pd.Series(results["ann"].get("forecast", []), index=test_series.index[: len(results["ann"].get("forecast", []))])
			ann_chart = ExportManager._build_forecast_chart(ann_map, "ANN Graphic (Aktual, Prediksi)")
			if ann_chart is not None:
				elements.append(Paragraph("5.2 ANN Graphic", subheading_style))
				elements.append(ann_chart)
				elements.append(Spacer(1, 0.25 * cm))
				
				# RUN-5: ANN Comparison Table (5×3)
				ann_comparison_table = ExportManager._generate_forecast_comparison_table(
					test_series, results, table_type="ann"
				)
				if ann_comparison_table is not None:
					elements.append(Paragraph("Perbandingan ANN (Aktual vs Prediksi):", subheading_style))
					elements.append(ann_comparison_table)
					elements.append(Spacer(1, 0.3 * cm))

			# ARIMA chart
			arima_map = {"actual": test_series}
			if "arima" in results:
				arima_map["pred"] = pd.Series(results["arima"].get("forecast", []), index=test_series.index[: len(results["arima"].get("forecast", []))])
			arima_chart = ExportManager._build_forecast_chart(arima_map, "ARIMA Graphic (Aktual, Prediksi)")
			if arima_chart is not None:
				elements.append(Paragraph("5.3 ARIMA Graphic", subheading_style))
				elements.append(arima_chart)
				elements.append(Spacer(1, 0.25 * cm))
				
				# RUN-5: ARIMA Comparison Table (5×3)
				arima_comparison_table = ExportManager._generate_forecast_comparison_table(
					test_series, results, table_type="arima"
				)
				if arima_comparison_table is not None:
					elements.append(Paragraph("Perbandingan ARIMA (Aktual vs Prediksi):", subheading_style))
					elements.append(arima_comparison_table)
					elements.append(Spacer(1, 0.3 * cm))
		else:
			elements.append(Paragraph("Grafik resume belum tersedia.", styles["Normal"]))
		elements.append(Spacer(1, 0.4 * cm))

		# FTS Mathematical Documentation
		elements.append(Paragraph("6. FTS Mathematical Documentation", heading_style))
		ExportManager._append_fts_math_doc(elements, styles, subheading_style, results, params)
		elements.append(Spacer(1, 0.4 * cm))

		# Model Configuration
		elements.append(Paragraph("7. Model Configuration", heading_style))
		fts_cfg = {
			"interval": ExportManager._get_param(params, "fts", "interval"),
			"partition": ExportManager._get_param(params, "fts", "partition"),
			"pad_pct": ExportManager._get_param(params, "fts", "pad_pct"),
			"padPct": ExportManager._get_param(params, "fts", "padPct"),
		}
		pad_val = fts_cfg.get("pad_pct") if fts_cfg.get("pad_pct") is not None else fts_cfg.get("padPct")
		split_ratio = ExportManager._get_param(params, "global", "split_ratio")
		fts_cfg_str = (
			f"n={fts_cfg.get('interval', '-')}, "
			f"method={fts_cfg.get('partition', '-')}, "
			f"pad={ExportManager._to_float(pad_val, 0.05) * 100:.0f}%, "
			f"split={ExportManager._to_float(split_ratio, 0.0) * 100:.0f}%"
		)
		ann_cfg = ExportManager._get_param(params, "ann", default={}) or {}
		ann_cfg_str = (
			f"epoch={ann_cfg.get('epoch', '-')}, "
			f"neuron={ann_cfg.get('neuron', '-')}, "
			f"layers={ann_cfg.get('layers', '-')}, "
			f"lr={ann_cfg.get('lr', '-')}"
		)
		arima_cfg = ExportManager._get_param(params, "arima", default={}) or {}
		arima_cfg_str = (
			f"order=({arima_cfg.get('p', '-')}, {arima_cfg.get('d', '-')}, {arima_cfg.get('q', '-')})"
		)
		if arima_cfg.get("seasonal"):
			arima_cfg_str += f", seasonal=({arima_cfg.get('P', '-')}, {arima_cfg.get('D', '-')}, {arima_cfg.get('Q', '-')}, {arima_cfg.get('s', '-')})"

		cfg_rows = [
			["Model", "Config Summary"],
			["FTS", fts_cfg_str],
			["ANN", ann_cfg_str],
			["ARIMA", arima_cfg_str],
		]
		cfg_tbl = Table(cfg_rows, colWidths=[3 * cm, 11 * cm])
		ExportManager._style_table(cfg_tbl, align="LEFT", font_size=9)
		elements.append(cfg_tbl)
		elements.append(Spacer(1, 0.4 * cm))

		# Performance Results
		elements.append(Paragraph("8. Performance Results", heading_style))
		rows, best_method = ExportManager._collect_comparison_rows(results)
		comp_rows = [["Model", "MAE", "RMSE", "MAPE (%)", "Rank"]]
		best_row_idx = None
		for idx, row in enumerate(rows, start=1):
			if row.get("method") == best_method:
				best_row_idx = idx
			comp_rows.append(
				[
					row.get("method", "-"),
					ExportManager._fmt_metric(row.get("mae")),
					ExportManager._fmt_metric(row.get("rmse")),
					ExportManager._fmt_mape(row.get("mape")),
					str(row.get("rank", "-")),
				]
			)
		comp_tbl = Table(comp_rows, colWidths=[3 * cm, 3 * cm, 3 * cm, 3 * cm, 2 * cm])
		ExportManager._style_table(comp_tbl, font_size=9)
		if best_row_idx is not None:
			comp_tbl.setStyle(
				TableStyle([("BACKGROUND", (0, best_row_idx), (-1, best_row_idx), colors.HexColor("#d1fae5"))])
			)
		elements.append(comp_tbl)
		if best_method:
			elements.append(Paragraph(f"<b>Best Model:</b> {best_method}", styles["Normal"]))
		elements.append(Spacer(1, 0.4 * cm))

		# Sensitivity Analysis
		elements.append(Paragraph("9. Sensitivity Analysis", heading_style))
		sens = results.get("sensitivity") or {}
		cases = sens.get("cases", [])
		if cases:
			sens_rows = [["Case", "MAPE (%)", "Delta (%)"]]
			for case in cases:
				sens_rows.append(
					[
						case.get("label", "-"),
						ExportManager._fmt_mape(case.get("mape")),
						ExportManager._fmt_mape(case.get("delta")),
					]
				)
			sens_tbl = Table(sens_rows, colWidths=[6 * cm, 4 * cm, 4 * cm])
			ExportManager._style_table(sens_tbl, font_size=9)
			elements.append(sens_tbl)
			best_case = sens.get("bestCase")
			if best_case:
				best_label = best_case
				for case in cases:
					if case.get("id") == best_case:
						best_label = case.get("label", best_case)
						break
				elements.append(Paragraph(f"<b>Best Case:</b> {best_label}", styles["Normal"]))
		else:
			elements.append(Paragraph("Sensitivity analysis belum tersedia.", styles["Normal"]))
		elements.append(Spacer(1, 0.4 * cm))

		# Caption
		elements.append(Paragraph("10. Auto-Generated Caption", heading_style))
		caption = ExportManager._build_caption(
			results,
			params,
			device_name,
			date_range,
			total_points,
		)
		elements.append(Paragraph(caption, styles["Normal"]))

	@staticmethod
	def _generate_predictive_insights(
		elements: list,
		styles,
		heading_style: ParagraphStyle,
		results: Dict
	) -> None:
		"""RUN-5 SA-02: Advanced predictive insights with confidence intervals and scenario analysis."""
		
		elements.append(Paragraph("🔮 Predictive Insights & Scenario Analysis", heading_style))
		elements.append(Spacer(1, 0.3*cm))
		
		# Collect model performance data
		comp_rows, best_method = ExportManager._collect_comparison_rows(results)
		
		# SA-02.1: Forecast Confidence Analysis
		subheading_style = ParagraphStyle(
			'InsightSubheading',
			parent=styles['Heading3'],
			fontSize=10,
			textColor=colors.HexColor('#7c3aed'),
			spaceAfter=6
		)
		
		elements.append(Paragraph("1. Forecast Confidence Assessment", subheading_style))
		
		# Calculate confidence levels based on MAPE
		confidence_analysis = []
		for row in comp_rows:
			method = row.get('method', 'Unknown')
			mape = row.get('mape', 0)
			
			# Confidence classification based on MAPE ranges
			if mape <= 5:
				confidence = "Very High (95%+)"
				icon = "🟢"
			elif mape <= 10:
				confidence = "High (85-95%)"
				icon = "🟡"
			elif mape <= 20:
				confidence = "Moderate (70-85%)"
				icon = "🟠"
			else:
				confidence = "Low (<70%)"
				icon = "🔴"
			
			confidence_analysis.append([
				f"{icon} {method}",
				f"{mape:.2f}%",
				confidence
			])
		
		if confidence_analysis:
			conf_table_data = [['Model', 'MAPE', 'Confidence Level']] + confidence_analysis
			conf_table = Table(conf_table_data, colWidths=[4*cm, 2.5*cm, 4.5*cm])
			conf_table.setStyle(TableStyle([
				('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7c3aed')),
				('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
				('ALIGN', (0, 0), (-1, -1), 'CENTER'),
				('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
				('FONTSIZE', (0, 0), (-1, -1), 9),
				('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
			]))
			elements.append(conf_table)
		
		elements.append(Spacer(1, 0.3*cm))
		
		# SA-02.2: Scenario Analysis
		elements.append(Paragraph("2. Scenario Analysis & Business Recommendations", subheading_style))
		
		# Get best and worst models
		mape_values = [row.get('mape', 0) for row in comp_rows]
		if mape_values:
			best_mape = min(mape_values)
			worst_mape = max(mape_values)
			
			best_model = next((row.get('method') for row in comp_rows if row.get('mape') == best_mape), 'Unknown')
			worst_model = next((row.get('method') for row in comp_rows if row.get('mape') == worst_mape), 'Unknown')
			
			# Business scenarios based on performance
			scenarios = [
				f"🎯 **Best Case Scenario ({best_model})**",
				f"   • Accuracy: {best_mape:.2f}% MAPE - Excellent predictive performance",
				f"   • Business Impact: High confidence in demand forecasting",
				f"   • Recommendation: Deploy for production energy planning",
				f"",
				f"⚠️ **Worst Case Scenario ({worst_model})**", 
				f"   • Accuracy: {worst_mape:.2f}% MAPE - Requires improvement",
				f"   • Business Impact: Limited reliability for critical decisions",
				f"   • Recommendation: Use as backup or require manual validation",
				f"",
				f"📊 **Performance Range Analysis**",
				f"   • Accuracy Spread: {worst_mape - best_mape:.2f}% difference between models",
				f"   • Model Consistency: {'High' if (worst_mape - best_mape) < 5 else 'Moderate' if (worst_mape - best_mape) < 10 else 'Low'}",
				f"   • Ensemble Potential: {'Recommended' if len(comp_rows) >= 2 else 'Single model sufficient'}"
			]
			
			for scenario in scenarios:
				if scenario.strip():  # Skip empty lines
					elements.append(Paragraph(scenario, styles['Normal']))
		
		elements.append(Spacer(1, 0.4*cm))

	@staticmethod
	def _enhance_performance_comparison(
		elements: list,
		styles,
		heading_style: ParagraphStyle,
		results: Dict
	) -> None:
		"""RUN-5 SA-04: Advanced model comparison with performance trends and strengths/weaknesses analysis."""
		
		elements.append(Paragraph("⚖️ Advanced Model Performance Comparison", heading_style))
		elements.append(Spacer(1, 0.3*cm))
		
		comp_rows, best_method = ExportManager._collect_comparison_rows(results)
		
		if not comp_rows:
			elements.append(Paragraph("No performance data available for comparison.", styles['Normal']))
			return
		
		subheading_style = ParagraphStyle(
			'PerfSubheading',
			parent=styles['Heading3'],
			fontSize=10,
			textColor=colors.HexColor('#ea580c'),
			spaceAfter=6
		)
		
		# SA-04.1: Performance Strengths & Weaknesses Analysis
		elements.append(Paragraph("1. Model Strengths & Weaknesses Analysis", subheading_style))
		
		# Analyze each model's characteristics
		for row in comp_rows:
			method = row.get('method', 'Unknown')
			mape = row.get('mape', 0)
			mae = row.get('mae', 0)
			rmse = row.get('rmse', 0)
			
			# Determine model characteristics based on performance
			strengths = []
			weaknesses = []
			
			if method.upper() == 'FTS':
				strengths = ["Fast computation", "Good for fuzzy patterns", "Interpretable intervals"]
				if mape <= 10:
					strengths.append("Excellent accuracy")
				else:
					weaknesses.append("Accuracy could be improved")
				weaknesses.append("Sensitive to parameter tuning")
				
			elif method.upper() == 'ANN':
				strengths = ["Learns complex patterns", "Non-linear modeling", "Adaptive learning"]
				if mape <= 8:
					strengths.append("Superior pattern recognition")
				else:
					weaknesses.append("May need more training data")
				weaknesses.extend(["Black box model", "Requires careful tuning"])
				
			elif method.upper() == 'ARIMA':
				strengths = ["Statistical foundation", "Trend modeling", "Seasonality handling"]
				if mape <= 12:
					strengths.append("Good statistical fit")
				else:
					weaknesses.append("May not capture complex patterns")
				weaknesses.append("Assumes linear relationships")
			
			# Performance classification
			perf_icon = "🥇" if method == best_method else "🥈" if mape <= 15 else "🥉"
			perf_class = "Excellent" if mape <= 5 else "Good" if mape <= 10 else "Acceptable" if mape <= 20 else "Needs Improvement"
			
			elements.append(Paragraph(f"{perf_icon} **{method}** - {perf_class} Performance", styles['Heading4']))
			elements.append(Paragraph(f"MAPE: {mape:.2f}% | MAE: {mae:.2f} | RMSE: {rmse:.2f}", styles['Normal']))
			elements.append(Paragraph(f"**Strengths:** {', '.join(strengths)}", styles['Normal']))
			elements.append(Paragraph(f"**Areas for Improvement:** {', '.join(weaknesses)}", styles['Normal']))
			elements.append(Spacer(1, 0.2*cm))
		
		elements.append(Spacer(1, 0.3*cm))
		
		# SA-04.2: Cross-Model Performance Analysis
		elements.append(Paragraph("2. Cross-Model Performance Analysis", subheading_style))
		
		# Calculate performance statistics
		mape_values = [row.get('mape', 0) for row in comp_rows]
		best_mape = min(mape_values) if mape_values else 0
		worst_mape = max(mape_values) if mape_values else 0
		avg_mape = sum(mape_values) / len(mape_values) if mape_values else 0
		mape_range = worst_mape - best_mape
		
		# Performance insights
		insights = [
			f"📊 **Performance Overview**:",
			f"   • Best Model: {best_method} (MAPE: {best_mape:.2f}%)",
			f"   • Average Performance: {avg_mape:.2f}% MAPE",
			f"   • Performance Range: {mape_range:.2f}% spread between models",
			f"",
			f"🎯 **Model Selection Guidance**:"
		]
		
		if mape_range < 3:
			insights.append("   • Models show similar performance - choose based on interpretability needs")
		elif mape_range < 8:
			insights.append("   • Moderate performance difference - best model recommended for production")
		else:
			insights.append("   • Significant performance gap - strongly recommend best performing model")
		
		# Business recommendations
		insights.extend([
			f"",
			f"💼 **Business Recommendations**:",
			f"   • Production Deployment: Use {best_method} for primary forecasting",
			f"   • Backup Strategy: Maintain secondary model for validation",
			f"   • Monitoring: Track performance degradation over time",
			f"   • Update Schedule: {'Monthly' if best_mape > 10 else 'Quarterly'} model retraining recommended"
		])
		
		for insight in insights:
			if insight.strip():  # Skip empty lines
				elements.append(Paragraph(insight, styles['Normal']))
		
		elements.append(Spacer(1, 0.4*cm))

	@staticmethod
	def _assess_data_quality_enhanced(
		elements: list,
		styles,
		heading_style: ParagraphStyle,
		raw_df: pd.DataFrame | None
	) -> None:
		"""RUN-5 SA-03: Enhanced data quality assessment with statistical indicators and recommendations."""
		
		if raw_df is None or raw_df.empty:
			elements.append(Paragraph("⚠️ Data Quality Assessment: No data available", heading_style))
			return
		
		norm_df = ExportManager._normalize_raw_df(raw_df)
		if norm_df.empty:
			elements.append(Paragraph("⚠️ Data Quality Assessment: Unable to process data", heading_style))
			return
		
		elements.append(Paragraph("🔍 Advanced Data Quality Assessment", heading_style))
		elements.append(Spacer(1, 0.3*cm))
		
		subheading_style = ParagraphStyle(
			'QualitySubheading',
			parent=styles['Heading3'],
			fontSize=10,
			textColor=colors.HexColor('#dc2626'),
			spaceAfter=6
		)
		
		# SA-03.1: Missing Data Analysis
		elements.append(Paragraph("1. Missing Data Analysis", subheading_style))
		
		energy_cols = [col for col in norm_df.columns if col not in ['datetime', 'timestamp', 'hour', 'day_of_week', 'is_peak', 'synthetic']]
		missing_analysis = []
		
		for col in energy_cols[:5]:  # Limit to first 5 sensors
			if col in norm_df.columns:
				missing_count = norm_df[col].isnull().sum()
				missing_percent = (missing_count / len(norm_df)) * 100
				status = "✅ Excellent" if missing_percent == 0 else "⚠️ Good" if missing_percent < 5 else "❌ Poor"
				
				missing_analysis.append([
					col,
					str(missing_count),
					f"{missing_percent:.1f}%",
					status
				])
		
		if missing_analysis:
			missing_table_data = [['Sensor', 'Missing Count', 'Missing %', 'Quality Status']] + missing_analysis
			missing_table = Table(missing_table_data, colWidths=[3*cm, 2.5*cm, 2.5*cm, 3*cm])
			missing_table.setStyle(TableStyle([
				('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc2626')),
				('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
				('ALIGN', (0, 0), (-1, -1), 'CENTER'),
				('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
				('FONTSIZE', (0, 0), (-1, -1), 9),
				('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
			]))
			elements.append(missing_table)
		
		elements.append(Spacer(1, 0.3*cm))
		
		# SA-03.2: Outlier Detection & Statistical Consistency
		elements.append(Paragraph("2. Outlier Detection & Statistical Consistency", subheading_style))
		
		outlier_summary = []
		overall_outliers = 0
		total_points = 0
		
		for col in energy_cols[:3]:  # Analyze first 3 sensors
			if col in norm_df.columns and norm_df[col].dtype in ['float64', 'int64']:
				# IQR method for outlier detection
				Q1 = norm_df[col].quantile(0.25)
				Q3 = norm_df[col].quantile(0.75)
				IQR = Q3 - Q1
				lower_bound = Q1 - 1.5 * IQR
				upper_bound = Q3 + 1.5 * IQR
				
				outliers = ((norm_df[col] < lower_bound) | (norm_df[col] > upper_bound)).sum()
				outlier_rate = (outliers / len(norm_df)) * 100
				
				# Statistical measures
				mean_val = norm_df[col].mean()
				std_val = norm_df[col].std()
				cv = (std_val / mean_val) * 100 if mean_val > 0 else 0  # Coefficient of variation
				
				overall_outliers += outliers
				total_points += len(norm_df)
				
				stability_status = "✅ Stable" if cv < 20 else "⚠️ Moderate" if cv < 50 else "❌ Volatile"
				
				outlier_summary.append([
					col,
					f"{outliers}",
					f"{outlier_rate:.1f}%",
					f"{cv:.1f}%",
					stability_status
				])
		
		if outlier_summary:
			outlier_table_data = [['Sensor', 'Outliers', 'Outlier Rate', 'Variability (CV)', 'Stability']] + outlier_summary
			outlier_table = Table(outlier_table_data, colWidths=[2.5*cm, 2*cm, 2.5*cm, 2.5*cm, 2.5*cm])
			outlier_table.setStyle(TableStyle([
				('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc2626')),
				('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
				('ALIGN', (0, 0), (-1, -1), 'CENTER'),
				('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
				('FONTSIZE', (0, 0), (-1, -1), 8),
				('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
			]))
			elements.append(outlier_table)
		
		# SA-03.3: Data Quality Recommendations
		elements.append(Spacer(1, 0.3*cm))
		elements.append(Paragraph("3. Data Quality Recommendations", subheading_style))
		
		overall_outlier_rate = (overall_outliers / total_points) * 100 if total_points > 0 else 0
		total_missing = sum(norm_df[col].isnull().sum() for col in energy_cols if col in norm_df.columns)
		overall_missing_rate = (total_missing / (len(energy_cols) * len(norm_df))) * 100 if len(energy_cols) > 0 else 0
		
		recommendations = [
			f"📊 **Overall Data Quality Score**: {100 - overall_missing_rate - overall_outlier_rate:.1f}/100",
			f"",
			f"🔧 **Immediate Actions Required**:"
		]
		
		if overall_missing_rate > 5:
			recommendations.extend([
				f"   • ❌ High missing data rate ({overall_missing_rate:.1f}%) - Review data collection processes",
				f"   • Implement data validation checks at source"
			])
		elif overall_missing_rate > 1:
			recommendations.append(f"   • ⚠️ Moderate missing data ({overall_missing_rate:.1f}%) - Monitor data collection")
		else:
			recommendations.append(f"   • ✅ Excellent data completeness ({100-overall_missing_rate:.1f}%)")
		
		if overall_outlier_rate > 5:
			recommendations.extend([
				f"   • ❌ High outlier rate ({overall_outlier_rate:.1f}%) - Investigate sensor calibration",
				f"   • Consider data preprocessing with outlier filtering"
			])
		elif overall_outlier_rate > 2:
			recommendations.append(f"   • ⚠️ Moderate outlier rate ({overall_outlier_rate:.1f}%) - Regular sensor maintenance")
		else:
			recommendations.append(f"   • ✅ Low outlier rate ({overall_outlier_rate:.1f}%) - Good sensor stability")
		
		recommendations.extend([
			f"",
			f"💡 **Long-term Improvements**:",
			f"   • Implement real-time data quality monitoring",
			f"   • Setup automated alerts for data anomalies", 
			f"   • Regular sensor calibration schedule",
			f"   • Data preprocessing pipeline optimization"
		])
		
		for rec in recommendations:
			if rec.strip():  # Skip empty lines
				elements.append(Paragraph(rec, styles['Normal']))
		
		elements.append(Spacer(1, 0.4*cm))

	@staticmethod
	def export_to_excel(results: Dict, file_path: str) -> tuple[bool, str]:
		"""Export hasil analisis ke Excel.

		Mengembalikan (success: bool, message: str).
		"""

		try:
			if not results:
				raise ValueError("Tidak ada data hasil analisis untuk diekspor.")

			os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)

			with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
				# Sheet 1: Comparison Metrics
				metrics_rows = []
				for method in ["fts", "ann", "arima"]:
					if method in results:
						m = results[method]["metrics"]
						metrics_rows.append(
							{
								"Method": method.upper(),
								"MAE": m.get("mae", 0.0),
								"RMSE": m.get("rmse", 0.0),
								"MAPE (%)": m.get("mape", 0.0),
							}
						)
				pd.DataFrame(metrics_rows).to_excel(
					writer, sheet_name="Comparison Metrics", index=False
				)

				# Sheet 2: Forecast vs Actual
				test_series = results.get("data", {}).get("test", pd.Series(dtype=float))
				df_forecast = pd.DataFrame(
					{"Timestamp": test_series.index, "Actual (W)": test_series.values}
				)

				for method in ["fts", "ann", "arima"]:
					if method not in results:
						continue
					pred = results[method]["forecast"]
					if len(pred) == len(df_forecast):
						df_forecast[f"{method.upper()} Pred"] = pred
					else:
						# Align sederhana jika panjang berbeda
						series_pred = pd.Series(pred, index=test_series.index[: len(pred)])
						df_forecast[f"{method.upper()} Pred"] = series_pred.values

				df_forecast.to_excel(writer, sheet_name="Forecast Data", index=False)

				# Sheet 3: FTS Details
				if "fts" in results:
					art = results["fts"]["artifacts"]
					pd.DataFrame(art.get("intervals", []), columns=["Min", "Max"]).to_excel(
						writer, sheet_name="FTS_Intervals", index=False
					)
					pd.DataFrame(art.get("flr_table", []), columns=["Relations"]).to_excel(
						writer, sheet_name="FTS_FLR", index=False
					)
					flrg_items = [
						{"Group": k, "Next States": v}
						for k, v in art.get("flrg_table", {}).items()
					]
					pd.DataFrame(flrg_items).to_excel(
						writer, sheet_name="FTS_FLRG", index=False
					)

				# Sheet 4: ANN Details
				if "ann" in results:
					art = results["ann"]["artifacts"]
					pd.DataFrame(art.get("loss_history", []), columns=["Loss"]).to_excel(
						writer, sheet_name="ANN_Loss_History", index=False
					)
					pd.DataFrame([art.get("config_used", {})]).to_excel(
						writer, sheet_name="ANN_Config", index=False
					)

				# Sheet 5: ARIMA Details
				if "arima" in results:
					art = results["arima"]["artifacts"]
					stats_rows = [
						{"Metric": "AIC", "Value": art.get("aic", 0.0)},
						{"Metric": "BIC", "Value": art.get("bic", 0.0)},
					]
					pd.DataFrame(stats_rows).to_excel(
						writer, sheet_name="ARIMA_Stats", index=False
					)

			return True, f"Export berhasil disimpan ke: {file_path}"
		except Exception as e:  # pragma: no cover - report singkat
			return False, str(e)

	@staticmethod
	def export_to_pdf(
		results: Dict,
		file_path: str,
		logger=None,
		params: Dict | None = None,
		raw_df: pd.DataFrame | None = None,
	) -> tuple[bool, str]:
		"""Generate comprehensive PDF report dari hasil analisis.
		
		Args:
			results: dict hasil analisis dari CalculationWorker
			file_path: Path output PDF file
			logger: AppLogger instance (optional)
		
		Returns:
			tuple: (success: bool, message: str)
		"""
		try:
			if not results:
				raise ValueError("Tidak ada data hasil analisis untuk diekspor.")

			if logger:
				base_name = os.path.basename(file_path)
				logger.log_event(
					lvl1="INIT",
					lvl2="RESUME",
					lvl3="CAL",
					lvl4="GENERAL",
					evt=EVT.EXPORT_START,
					route_to=["RESUME"],
					fields=[f"type=PDF", f"file={base_name}"],
				)
				logger.log_event(
					lvl1="GEN",
					lvl2="RESUME",
					lvl3="CAL",
					lvl4="GENERAL",
					evt=EVT.RPT_BUILD_START,
					route_to=["RESUME"],
					fields=[f"type=PDF", f"file={base_name}"],
				)
				# Harmonize GLOBAL headers: START framing
				logger.log(
					"INIT",
					f"===== START Export | TYPE=PDF | FILE={base_name} =====",
					lvl2="RESUME",
					lvl3="CAL",
					lvl4="GENERAL",
				)
			
			# Create PDF document
			doc = SimpleDocTemplate(
				file_path,
				pagesize=A4,
				rightMargin=2*cm,
				leftMargin=2*cm,
				topMargin=2.5*cm,
				bottomMargin=2.5*cm
			)
			
			# Container for elements
			elements = []
			
			# Styles
			styles = getSampleStyleSheet()
			heading_style = ParagraphStyle(
				'CustomHeading',
				parent=styles['Heading2'],
				fontSize=14,
				textColor=colors.HexColor('#2563eb'),
				spaceAfter=12,
				spaceBefore=12
			)
			
			# ==================== RUN-1: TITLE PAGE ====================
			ExportManager._generate_title_page(elements, styles, params)
			
			# ==================== RUN-1: TABLE OF CONTENTS ====================
			ExportManager._generate_table_of_contents(elements, styles, results)

			# ==================== EXECUTIVE SUMMARY ====================
			ExportManager._append_executive_summary(
				elements,
				styles,
				title_style,
				heading_style,
				results,
				params=params,
				raw_df=raw_df,
			)

			ExportManager._append_summary_sections(
				elements,
				styles,
				heading_style,
				results,
				params=params,
				raw_df=raw_df,
			)
			
			# ==================== RUN-5: STATISTICAL ANALYSIS & ADVANCED ANALYTICS ====================
			elements.append(PageBreak())
			
			# SA-01: Statistical Summary with consumption patterns, seasonality, efficiency metrics
			ExportManager._generate_statistical_summary(
				elements,
				styles,
				heading_style,
				raw_df,
				results
			)
			elements.append(PageBreak())
			
			# SA-02: Predictive insights with confidence intervals and scenario analysis
			ExportManager._generate_predictive_insights(
				elements,
				styles,
				heading_style,
				results
			)
			elements.append(PageBreak())
			
			# SA-03: Enhanced data quality assessment with statistical indicators
			ExportManager._assess_data_quality_enhanced(
				elements,
				styles,
				heading_style,
				raw_df
			)
			elements.append(PageBreak())
			
			# SA-04: Advanced model comparison with performance trends analysis
			ExportManager._enhance_performance_comparison(
				elements,
				styles,
				heading_style,
				results
			)
			
			elements.append(PageBreak())
			elements.append(Paragraph("Appendix A. Technical Details", heading_style))
			
			# ==================== SECTION 2: FTS DETAILS ====================
			if 'fts' in results:
				elements.append(Paragraph("A.1 Detail Fuzzy Time Series (Cheng)", heading_style))
				elements.append(Spacer(1, 0.5*cm))
				
				fts_art = results['fts']['artifacts']
				
				# UoD
				if 'uod' in fts_art and fts_art['uod']:
					uod_min, uod_max = fts_art['uod']
					elements.append(Paragraph(
						f"<b>Universe of Discourse (UoD):</b> [{uod_min:.2f}, {uod_max:.2f}]",
						styles['Normal']
					))
					elements.append(Spacer(1, 0.3*cm))
				
				# Intervals
				if 'intervals' in fts_art and fts_art['intervals']:
					elements.append(Paragraph("<b>Partisi Interval:</b>", styles['Normal']))
					interval_data = [['Label', 'Batas Bawah', 'Batas Atas']]
					for idx, (low, high) in enumerate(fts_art['intervals'][:10], 1):  # Limit 10 for space
						interval_data.append([f"A{idx}", f"{low:.2f}", f"{high:.2f}"])
					
					interval_table = Table(interval_data, colWidths=[3*cm, 4*cm, 4*cm])
					interval_table.setStyle(TableStyle([
						('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
						('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
						('ALIGN', (0, 0), (-1, -1), 'CENTER'),
						('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
						('GRID', (0, 0), (-1, -1), 1, colors.grey)
					]))
					elements.append(interval_table)
					elements.append(Spacer(1, 0.5*cm))
				
				# FLRG Summary
				if 'flrg_table' in fts_art and fts_art['flrg_table']:
					elements.append(Paragraph(
						f"<b>Fuzzy Logical Relationship Groups (FLRG):</b> {len(fts_art['flrg_table'])} groups",
						styles['Normal']
					))
				
				elements.append(PageBreak())
			
			# ==================== SECTION 3: ANN DETAILS ====================
			if 'ann' in results:
				elements.append(Paragraph("A.2 Detail Artificial Neural Network", heading_style))
				elements.append(Spacer(1, 0.5*cm))
				
				ann_art = results['ann']['artifacts']
				
				# Mathematical Documentation for ANN
				elements.append(Paragraph("A.2.1 Mathematical Formulation", heading_style))
				elements.append(Paragraph(
					"Forward propagation: z = W * x + b, a = σ(z)",
					styles['Normal']
				))
				
				# LaTeX formulas for ANN
				ann_formulas = [
					r"z^{(l)} = W^{(l)} \cdot a^{(l-1)} + b^{(l)}",
					r"a^{(l)} = \sigma(z^{(l)})",
					r"\sigma(x) = \frac{1}{1 + e^{-x}} \text{ (sigmoid)}",
					r"\text{Loss: } J = \frac{1}{2m}\sum_{i=1}^{m}(y^{(i)} - \hat{y}^{(i)})^2",
					r"\frac{\partial J}{\partial W} = \frac{1}{m} \sum_{i=1}^{m} (\hat{y}^{(i)} - y^{(i)}) \cdot a^{(i)}"
				]
				ExportManager._append_latex_images(elements, ann_formulas)
				
				# Config
				if 'config_used' in ann_art:
					config = ann_art['config_used']
					elements.append(Paragraph(
						f"<b>Konfigurasi:</b> Neurons={config.get('neuron', 'N/A')}, "
						f"Layers={config.get('layers', 'N/A')}, "
						f"Epochs={config.get('epoch', 'N/A')}, "
						f"Learning Rate={config.get('lr', 'N/A')}",
						styles['Normal']
					))
					
					# LaTeX calculation for network architecture
					arch_latex = [
						f"\\text{{Input layer: }} x \\in \\mathbb{{R}}^{{1}}",
						f"\\text{{Hidden layer: }} h \\in \\mathbb{{R}}^{{{config.get('neuron', 'n')}}}",
						f"\\text{{Output layer: }} \\hat{{y}} \\in \\mathbb{{R}}^{{1}}",
						f"\\text{{Total epochs: }} {config.get('epoch', 'N/A')}",
						f"\\text{{Learning rate: }} \\alpha = {config.get('lr', 'N/A')}"
					]
					elements.append(Paragraph("<b>LaTeX Network Architecture:</b>", styles['Normal']))
					ExportManager._append_latex_images(elements, arch_latex)
					elements.append(Spacer(1, 0.3*cm))
				
				# Final Loss
				if 'final_loss' in ann_art:
					elements.append(Paragraph(
						f"<b>Final Training Loss:</b> {ann_art['final_loss']:.6f}",
						styles['Normal']
					))
					# LaTeX calculation for final loss
					loss_latex = [
						f"J_{{final}} = {ann_art['final_loss']:.6f}",
						"\\text{(Mean Squared Error after training)}"
					]
					elements.append(Paragraph("<b>LaTeX Loss Calculation:</b>", styles['Normal']))
					ExportManager._append_latex_images(elements, loss_latex)
					elements.append(Spacer(1, 0.5*cm))
				
				# Loss History Chart
				if 'loss_history' in ann_art and len(ann_art['loss_history']) > 0:
					elements.append(Paragraph("<b>Grafik Loss History:</b>", styles['Normal']))
					
					# RUN-2: Professional styling setup
					ExportManager._setup_matplotlib_style()
					
					# Generate matplotlib chart
					fig, ax = plt.subplots(figsize=(6, 3))
					
					# RUN-2: Enhanced line styling
					ax.plot(ann_art['loss_history'], color=CHART_CONFIG['colors']['methods']['ann'], 
							linewidth=2.5, alpha=0.9, marker='o', markersize=3, markerfacecolor='white',
							markeredgecolor=CHART_CONFIG['colors']['methods']['ann'], markeredgewidth=1.5)
					
					# RUN-2: Apply professional styling
					ExportManager._apply_professional_styling(ax, 
						title='Training Loss per Epoch',
						xlabel='Epoch', 
						ylabel='Loss (MSE)')
					
					plt.tight_layout()
					
					# Save to BytesIO
					img_buffer = io.BytesIO()
					# RUN-2: Enhanced DPI
					plt.savefig(img_buffer, format='png', dpi=CHART_CONFIG['dpi'], bbox_inches='tight')
					img_buffer.seek(0)
					plt.close(fig)
					
					# Add to PDF
					img = Image(img_buffer, width=12*cm, height=6*cm)
					elements.append(img)
				
				elements.append(PageBreak())
			
			# ==================== SECTION 4: ARIMA DETAILS ====================
			if 'arima' in results:
				elements.append(Paragraph("A.3 Detail ARIMA/SARIMA", heading_style))
				elements.append(Spacer(1, 0.5*cm))
				
				arima_art = results['arima']['artifacts']
				
				# Mathematical Documentation for ARIMA
				elements.append(Paragraph("A.3.1 Mathematical Formulation", heading_style))
				elements.append(Paragraph(
					"ARIMA(p,d,q): Autoregressive Integrated Moving Average",
					styles['Normal']
				))
				
				# LaTeX formulas for ARIMA
				arima_formulas = [
					r"(1 - \phi_1 L - \phi_2 L^2 - \cdots - \phi_p L^p)(1-L)^d y_t = (1 + \theta_1 L + \theta_2 L^2 + \cdots + \theta_q L^q)\epsilon_t",
					r"\text{AR part: } \phi_1 y_{t-1} + \phi_2 y_{t-2} + \cdots + \phi_p y_{t-p}",
					r"\text{I part: } (1-L)^d y_t = y_t - y_{t-1} \text{ (differencing)}",
					r"\text{MA part: } \theta_1 \epsilon_{t-1} + \theta_2 \epsilon_{t-2} + \cdots + \theta_q \epsilon_{t-q}",
					r"\text{where } \epsilon_t \sim N(0, \sigma^2)"
				]
				ExportManager._append_latex_images(elements, arima_formulas)
				
				# Get ARIMA order from params or artifacts
				order_p = ExportManager._get_param(params, 'arima', 'p', default='?')
				order_d = ExportManager._get_param(params, 'arima', 'd', default='?')
				order_q = ExportManager._get_param(params, 'arima', 'q', default='?')
				
				# LaTeX calculation for ARIMA specification
				arima_spec_latex = [
					f"\\text{{ARIMA order: }} (p,d,q) = ({order_p},{order_d},{order_q})",
					f"\\text{{AR parameters: }} p = {order_p} \\text{{ (autoregressive terms)}}",
					f"\\text{{I parameters: }} d = {order_d} \\text{{ (differencing order)}}",
					f"\\text{{MA parameters: }} q = {order_q} \\text{{ (moving average terms)}}"
				]
				elements.append(Paragraph("<b>LaTeX Model Specification:</b>", styles['Normal']))
				ExportManager._append_latex_images(elements, arima_spec_latex)
				
				# AIC & BIC
				elements.append(Paragraph(
					f"<b>Akaike Information Criterion (AIC):</b> {arima_art.get('aic', 'N/A'):.2f}",
					styles['Normal']
				))
				elements.append(Paragraph(
					f"<b>Bayesian Information Criterion (BIC):</b> {arima_art.get('bic', 'N/A'):.2f}",
					styles['Normal']
				))
				
				# LaTeX calculation for information criteria
				if 'aic' in arima_art and 'bic' in arima_art:
					aic_val = arima_art.get('aic', 0)
					bic_val = arima_art.get('bic', 0)
					info_criteria_latex = [
						r"AIC = -2 \ln(L) + 2k",
						r"BIC = -2 \ln(L) + k \ln(n)",
						f"AIC = {aic_val:.2f}",
						f"BIC = {bic_val:.2f}",
						"\\text{where } L \\text{ = likelihood, } k \\text{ = parameters, } n \\text{ = observations}"
					]
					elements.append(Paragraph("<b>LaTeX Information Criteria:</b>", styles['Normal']))
					ExportManager._append_latex_images(elements, info_criteria_latex)
				elements.append(Spacer(1, 0.5*cm))
				
				# Model Summary (truncate if too long)
				if 'summary_text' in arima_art:
					summary_text = arima_art['summary_text'][:500] + "..." if len(arima_art['summary_text']) > 500 else arima_art['summary_text']
					elements.append(Paragraph("<b>Model Summary (excerpt):</b>", styles['Normal']))
					elements.append(Paragraph(
						f"<font face='Courier' size='8'>{summary_text}</font>",
						styles['Normal']
					))
			
			elements.append(PageBreak())
			
			# ==================== SECTION 5: FORECAST COMPARISON ====================
			elements.append(Paragraph("A.4 Perbandingan Hasil Prediksi", heading_style))
			elements.append(Spacer(1, 0.5*cm))
			
			# Get test data actual
			test_series = results.get('data', {}).get('test', None)
			
			if test_series is not None and len(test_series) > 0:
				# Build forecast table (first 10 rows)
				forecast_data = [['Index', 'Actual'] + [m.upper() for m in ['fts', 'ann', 'arima'] if m in results]]
				
				for i in range(min(10, len(test_series))):
					row = [str(i+1), f"{test_series.iloc[i]:.2f}"]
					for method in ['fts', 'ann', 'arima']:
						if method in results and len(results[method]['forecast']) > i:
							pred_val = results[method]['forecast'][i]
							try:
								row.append(f"{float(pred_val):.2f}")
							except (TypeError, ValueError):
								row.append("-")
						else:
							row.append("-")
					forecast_data.append(row)
				
				forecast_table = Table(forecast_data, colWidths=[2*cm] + [3*cm] * (len(forecast_data[0]) - 1))
				forecast_table.setStyle(TableStyle([
					('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
					('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
					('ALIGN', (0, 0), (-1, -1), 'CENTER'),
					('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
					('GRID', (0, 0), (-1, -1), 1, colors.black),
					('FONTSIZE', (0, 0), (-1, -1), 9)
				]))
				elements.append(forecast_table)
				elements.append(Paragraph("<i>(Menampilkan 10 data pertama dari hasil prediksi)</i>", styles['Italic']))
			
			# RUN-2 FIX: Better page estimation system 
			def create_footer_with_pages(label: str, is_title: bool = False):
				"""Create footer function with better total page estimation."""
				def footer_func(canvas, doc_obj):
					# Use current page + small buffer, minimum 20 pages
					current = canvas.getPageNumber()
					estimated_total = max(current + 2, 20)
					ExportManager._draw_enhanced_footer(canvas, doc_obj, label, estimated_total, is_title)
				return footer_func
			
			doc.build(
				elements,
				onFirstPage=create_footer_with_pages("PPDL Resume Report", True),
				onLaterPages=create_footer_with_pages("PPDL Resume Report", False)
			)

			if logger:
				base_name = os.path.basename(file_path)
				logger.log_event(
					lvl1="INFO",
					lvl2="RESUME",
					lvl3="RPT",
					lvl4="GENERAL",
					evt=EVT.RPT_BUILD_DONE,
					route_to=["RESUME"],
					fields=[f"type=PDF", f"file={base_name}"],
					result="status=OK",
				)
				logger.log_event(
					lvl1="SUCCESS",
					lvl2="RESUME",
					lvl3="RPT",
					lvl4="GENERAL",
					evt=EVT.EXPORT_DONE,
					route_to=["RESUME"],
					fields=[f"type=PDF", f"file={base_name}"],
					result="status=OK",
				)
				# Harmonize GLOBAL headers: END framing
				logger.log(
					"SUCCESS",
					f"===== END Export | TYPE=PDF | FILE={base_name} | STATUS=OK =====",
					lvl2="RESUME",
					lvl3="RPT",
					lvl4="GENERAL",
				)

				# RUN-2: Append metadata tail to GLOBAL & SUMMARY
				try:
					paths = getattr(logger, "get_run_log_paths", lambda: {})()
					guid = getattr(logger, "get_run_guid", lambda: None)()
					app_ver = getattr(getattr(logger, "_run_ctx", None), "app_version", None)
					if not app_ver:
						gp = paths.get("global")
						if gp and os.path.exists(gp):
							try:
								with open(gp, "r", encoding="utf-8") as rf:
									for _ in range(6):
										line = rf.readline()
										if not line:
											break
										line = line.strip()
										if line.startswith("APP_VERSION="):
											app_ver = line.split("=", 1)[1]
											break
							except Exception:
								app_ver = None

					meta_lines = [
						"----- METADATA TAIL -----",
						f"RUN_GUID={guid}",
						"APP_NAME=PPDL",
						f"APP_VERSION={app_ver or '1.0'}",
						f"OUTPUT_PATH={file_path}",
					]
					for key in ("global", "summary"):
						p = paths.get(key)
						if p:
							with open(p, "a", encoding="utf-8") as f:
								f.write("\n" + "\n".join(meta_lines) + "\n")
				except Exception:
					pass
			return True, f"PDF report berhasil disimpan ke:\n{file_path}"

		except Exception as e:
			if logger:
				base_name = os.path.basename(file_path)
				logger.log_event(
					lvl1="ERROR",
					lvl2="RESUME",
					lvl3="RPT",
					lvl4="GENERAL",
					evt=EVT.EXPORT_DONE,
					route_to=["RESUME"],
					fields=[f"type=PDF", f"file={base_name}"],
					cause=f"exception={type(e).__name__}",
					result="status=FAILED",
				)
				# Harmonize GLOBAL headers: END framing with failure
				logger.log(
					"ERROR",
					f"===== END Export | TYPE=PDF | FILE={base_name} | STATUS=FAILED =====",
					lvl2="RESUME",
					lvl3="RPT",
					lvl4="GENERAL",
				)
				# RUN-2: Append metadata tail with FAILED status
				try:
					paths = getattr(logger, "get_run_log_paths", lambda: {})()
					guid = getattr(logger, "get_run_guid", lambda: None)()
					app_ver = getattr(getattr(logger, "_run_ctx", None), "app_version", None)
					if not app_ver:
						gp = paths.get("global")
						if gp and os.path.exists(gp):
							try:
								with open(gp, "r", encoding="utf-8") as rf:
									for _ in range(6):
										line = rf.readline()
										if not line:
											break
										line = line.strip()
										if line.startswith("APP_VERSION="):
											app_ver = line.split("=", 1)[1]
											break
							except Exception:
								app_ver = None
					meta_lines = [
						"----- METADATA TAIL -----",
						f"RUN_GUID={guid}",
						"APP_NAME=PPDL",
						f"APP_VERSION={app_ver or '1.0'}",
						f"OUTPUT_PATH={file_path}",
					]
					for key in ("global", "summary"):
						p = paths.get(key)
						if p:
							with open(p, "a", encoding="utf-8") as f:
								f.write("\n" + "\n".join(meta_lines) + "\n")
				except Exception:
					pass
			return False, str(e)

	@staticmethod
	def export_resume_report(
		results: Dict,
		raw_df: pd.DataFrame,
		params: Dict,
		file_path: str,
		logger=None,
		progress_cb=None,
	) -> tuple[bool, str]:
		"""Generate Resume PDF sesuai struktur export tab."""
		try:
			if not results:
				raise ValueError("Tidak ada data hasil analisis untuk diekspor.")

			def _progress(val: int, msg: str) -> None:
				if progress_cb is not None:
					progress_cb(val, msg)
				if logger:
					base_name = os.path.basename(file_path)
					if val < 100:
						logger.log_event(
							lvl1="GEN",
							lvl2="RESUME",
							lvl3="CAL",
							lvl4="GENERAL",
							evt=EVT.RPT_BUILD_START,
							route_to=["RESUME"],
							fields=[f"type=RESUME", f"file={base_name}", f"progress={val}%", f"stage={msg}"],
						)
					else:
						logger.log_event(
							lvl1="INFO",
							lvl2="RESUME",
							lvl3="RPT",
							lvl4="GENERAL",
							evt=EVT.RPT_BUILD_DONE,
							route_to=["RESUME"],
							fields=[f"type=RESUME", f"file={base_name}", f"progress={val}%", f"stage={msg}"],
							result="status=OK",
						)

			if logger:
				base_name = os.path.basename(file_path)
				logger.log_event(
					lvl1="INIT",
					lvl2="RESUME",
					lvl3="CAL",
					lvl4="GENERAL",
					evt=EVT.EXPORT_START,
					route_to=["RESUME"],
					fields=[f"type=RESUME", f"file={base_name}"],
				)
				# Harmonize GLOBAL headers: START framing
				logger.log(
					"INIT",
					f"===== START Export | TYPE=RESUME | FILE={base_name} =====",
					lvl2="RESUME",
					lvl3="CAL",
					lvl4="GENERAL",
				)

			_progress(5, "Preparing")

			doc = SimpleDocTemplate(
				file_path,
				pagesize=A4,
				rightMargin=2 * cm,
				leftMargin=2 * cm,
				topMargin=2 * cm,
				bottomMargin=2 * cm,
			)
			elements = []
			styles = getSampleStyleSheet()
			title_style = ParagraphStyle(
				"CustomTitle",
				parent=styles["Heading1"],
				fontSize=16,
				textColor=colors.HexColor("#1f4e79"),
				spaceAfter=20,
				alignment=TA_CENTER,
				fontName=_get_font_name('heading')  # RUN-3: Bahnschrift-Bold
			)
			heading_style = ParagraphStyle(
				"CustomHeading",
				parent=styles["Heading2"],
				fontSize=12,
				textColor=colors.HexColor("#1f4e79"),
				spaceAfter=10,
				spaceBefore=10,
				fontName=_get_font_name('heading-regular')  # RUN-3: Bahnschrift
			)

			# Add professional title page and TOC (RUN-1 & RUN-2)
			_progress(25, "Creating Title Page")
			ExportManager._generate_title_page(elements, styles, params)
			
			_progress(27, "Creating Table of Contents")
			ExportManager._generate_table_of_contents(elements, styles, results)

			_progress(30, "Summary Report")
			ExportManager._append_summary_sections(
				elements,
				styles,
				heading_style,
				results,
				params=params,
				raw_df=raw_df,
			)

			# RUN-2 FIX: Enhanced dynamic page numbering for second export
			class PageCallbackSecond:
				def __init__(self):
					self.total_pages = 0
				
				def on_first_page(self, canvas, doc_obj):
					if self.total_pages == 0:
						self.total_pages = self._estimate_pages(elements)
					ExportManager._draw_enhanced_footer(canvas, doc_obj, "PPDL Resume Report", 
													   self.total_pages, is_title_page=True)
				
				def on_later_pages(self, canvas, doc_obj):
					if self.total_pages == 0:
						self.total_pages = self._estimate_pages(elements)
					ExportManager._draw_enhanced_footer(canvas, doc_obj, "PPDL Resume Report", 
													   self.total_pages, is_title_page=False)
				
				def _estimate_pages(self, elements_list):
					page_breaks = sum(1 for elem in elements_list if isinstance(elem, PageBreak))
					content_estimate = len([e for e in elements_list if isinstance(e, (Table, Paragraph))]) // 12
					return max(page_breaks + content_estimate + 1, 15)
			
			callback2 = PageCallbackSecond()
			doc.build(elements, onFirstPage=callback2.on_first_page, onLaterPages=callback2.on_later_pages)
			_progress(100, "Done")
			if logger:
				base_name = os.path.basename(file_path)
				logger.log_event(
					lvl1="SUCCESS",
					lvl2="RESUME",
					lvl3="RPT",
					lvl4="GENERAL",
					evt=EVT.EXPORT_DONE,
					route_to=["RESUME"],
					fields=[f"type=RESUME", f"file={base_name}"],
					result="status=OK",
				)
				# Harmonize GLOBAL headers: END framing
				logger.log(
					"SUCCESS",
					f"===== END Export | TYPE=RESUME | FILE={base_name} | STATUS=OK =====",
					lvl2="RESUME",
					lvl3="RPT",
					lvl4="GENERAL",
				)
				# RUN-2: Append metadata tail to GLOBAL & SUMMARY
				try:
					paths = getattr(logger, "get_run_log_paths", lambda: {})()
					guid = getattr(logger, "get_run_guid", lambda: None)()
					app_ver = getattr(getattr(logger, "_run_ctx", None), "app_version", None)
					if not app_ver:
						gp = paths.get("global")
						if gp and os.path.exists(gp):
							try:
								with open(gp, "r", encoding="utf-8") as rf:
									for _ in range(6):
										line = rf.readline()
										if not line:
											break
										line = line.strip()
										if line.startswith("APP_VERSION="):
											app_ver = line.split("=", 1)[1]
											break
							except Exception:
								app_ver = None
					meta_lines = [
						"----- METADATA TAIL -----",
						f"RUN_GUID={guid}",
						"APP_NAME=PPDL",
						f"APP_VERSION={app_ver or '1.0'}",
						f"OUTPUT_PATH={file_path}",
					]
					for key in ("global", "summary"):
						p = paths.get(key)
						if p:
							with open(p, "a", encoding="utf-8") as f:
								f.write("\n" + "\n".join(meta_lines) + "\n")
				except Exception:
					pass
			return True, f"Export berhasil disimpan ke:\n{file_path}"
		except Exception as e:
			if logger:
				base_name = os.path.basename(file_path)
				logger.log_event(
					lvl1="ERROR",
					lvl2="RESUME",
					lvl3="RPT",
					lvl4="GENERAL",
					evt=EVT.EXPORT_DONE,
					route_to=["RESUME"],
					fields=[f"type=RESUME", f"file={base_name}"],
					cause=f"exception={type(e).__name__}",
					result="status=FAILED",
				)
				# Harmonize GLOBAL headers: END framing with failure
				logger.log(
					"ERROR",
					f"===== END Export | TYPE=RESUME | FILE={base_name} | STATUS=FAILED =====",
					lvl2="RESUME",
					lvl3="RPT",
					lvl4="GENERAL",
				)
				# RUN-2: Append metadata tail with FAILED status
				try:
					paths = getattr(logger, "get_run_log_paths", lambda: {})()
					guid = getattr(logger, "get_run_guid", lambda: None)()
					meta_lines = [
						"----- METADATA TAIL -----",
						f"RUN_GUID={guid}",
						"APP_NAME=PPDL",
						"APP_VERSION=V1.0",
						f"OUTPUT_PATH={file_path}",
					]
					for key in ("global", "summary"):
						p = paths.get(key)
						if p:
							with open(p, "a", encoding="utf-8") as f:
								f.write("\n" + "\n".join(meta_lines) + "\n")
				except Exception:
					pass
			return False, str(e)

	@staticmethod
	def export_academic_artifacts_run3(
		*,
		logger,
		raw_df: pd.DataFrame | None,
		params: Dict,
		output_dir: str | None = None,
		include_csv: bool = True,
	) -> tuple[bool, str]:
		"""RUN-3 Ex_Plan-6: Export ZIP 3 log + snapshot params + snapshot dataset.

		Output file naming mengikuti kontrak Doc_for_Ex_Plan-6 (GUID identik).
		"""

		if logger is None:
			return False, "Logger tidak tersedia."

		run_guid = getattr(logger, "get_run_guid", lambda: None)()
		run_logs = getattr(logger, "get_run_log_paths", lambda: {})()
		run_dir = getattr(logger, "get_run_dir", lambda: None)()

		if not run_guid or not run_logs or not run_dir:
			return False, "Run GUID/log belum tersedia. Jalankan Start Analysis terlebih dahulu."

		out_dir = output_dir or run_dir

		try:
			logger.log_event(
				lvl1="INIT",
				lvl2="RESUME",
				lvl3="CAL",
				lvl4="GENERAL",
				evt=EVT.EXPORT_START,
				route_to=["RESUME"],
				fields=[f"type=LOG_ZIP", f"guid={run_guid}", f"out_dir={out_dir}"],
			)
			# Harmonize GLOBAL headers: START framing
			logger.log(
				"INIT",
				f"===== START Export | TYPE=LOG_ZIP | GUID={run_guid} | OUT={out_dir} =====",
				lvl2="RESUME",
				lvl3="CAL",
				lvl4="GENERAL",
			)
		except Exception:
			pass

		res = export_academic_artifacts(
			out_dir=out_dir,
			guid=run_guid,
			log_paths=run_logs,
			params=dict(params or {}),
			raw_df=raw_df,
			include_csv=bool(include_csv),
		)

		if res.ok:
			try:
				logger.log_event(
					lvl1="SUCCESS",
					lvl2="RESUME",
					lvl3="RPT",
					lvl4="GENERAL",
					evt=EVT.EXPORT_DONE,
					route_to=["RESUME"],
					fields=[f"type=LOG_ZIP", f"guid={run_guid}", f"zip={os.path.basename(res.paths.get('log_zip',''))}"],
					result="status=OK",
				)
				# Harmonize GLOBAL headers: END framing
				logger.log(
					"SUCCESS",
					f"===== END Export | TYPE=LOG_ZIP | GUID={run_guid} | STATUS=OK =====",
					lvl2="RESUME",
					lvl3="RPT",
					lvl4="GENERAL",
				)
			except Exception:
				pass
			# RUN-2: Append metadata tail to GLOBAL & SUMMARY for LOG_ZIP
			try:
				paths = getattr(logger, "get_run_log_paths", lambda: {})()
				guid = getattr(logger, "get_run_guid", lambda: None)()
				zip_path = res.paths.get("log_zip", "")
				app_ver = getattr(getattr(logger, "_run_ctx", None), "app_version", None)
				if not app_ver:
					paths2 = getattr(logger, "get_run_log_paths", lambda: {})()
					gp = paths2.get("global")
					if gp and os.path.exists(gp):
						try:
							with open(gp, "r", encoding="utf-8") as rf:
								for _ in range(6):
									line = rf.readline()
									if not line:
										break
									line = line.strip()
									if line.startswith("APP_VERSION="):
										app_ver = line.split("=", 1)[1]
										break
						except Exception:
							app_ver = None
				meta_lines = [
					"----- METADATA TAIL -----",
					f"RUN_GUID={guid}",
					"APP_NAME=PPDL",
					f"APP_VERSION={app_ver or '1.0'}",
					f"OUTPUT_PATH={os.path.join(out_dir, zip_path) if zip_path else out_dir}",
				]
				for key in ("global", "summary"):
					p = paths.get(key)
					if p:
						with open(p, "a", encoding="utf-8") as f:
							f.write("\n" + "\n".join(meta_lines) + "\n")
			except Exception:
				pass
			msg = "Artefak akademik berhasil dibuat:\n" + "\n".join(f"- {k}: {v}" for k, v in res.paths.items())
			return True, msg

		try:
			logger.log_event(
				lvl1="ERROR",
				lvl2="RESUME",
				lvl3="RPT",
				lvl4="GENERAL",
				evt=EVT.EXPORT_DONE,
				route_to=["RESUME"],
				fields=[f"type=LOG_ZIP", f"guid={run_guid}"],
				cause=f"exception={res.message}",
				result="status=FAILED",
			)
			# Harmonize GLOBAL headers: END framing with failure
			logger.log(
				"ERROR",
				f"===== END Export | TYPE=LOG_ZIP | GUID={run_guid} | STATUS=FAILED =====",
				lvl2="RESUME",
				lvl3="RPT",
				lvl4="GENERAL",
			)
		except Exception:
			pass
		# RUN-2: Append metadata tail with FAILED status for LOG_ZIP
		try:
			paths = getattr(logger, "get_run_log_paths", lambda: {})()
			guid = getattr(logger, "get_run_guid", lambda: None)()
			app_ver = getattr(getattr(logger, "_run_ctx", None), "app_version", None)
			if not app_ver:
				try:
					paths = getattr(logger, "get_run_log_paths", lambda: {})()
					gp = paths.get("global")
					if gp and os.path.exists(gp):
						with open(gp, "r", encoding="utf-8") as rf:
							for _ in range(6):
								line = rf.readline()
								if not line:
									break
								line = line.strip()
								if line.startswith("APP_VERSION="):
									app_ver = line.split("=", 1)[1]
									break
				except Exception:
					app_ver = None
			meta_lines = [
				"----- METADATA TAIL -----",
				f"RUN_GUID={guid}",
				"APP_NAME=PPDL",
				f"APP_VERSION={app_ver or '1.0'}",
				f"OUTPUT_PATH={out_dir}",
			]
			for key in ("global", "summary"):
				p = paths.get(key)
				if p:
					with open(p, "a", encoding="utf-8") as f:
						f.write("\n" + "\n".join(meta_lines) + "\n")
		except Exception:
			pass
		return False, f"Export artefak akademik gagal: {res.message}"
