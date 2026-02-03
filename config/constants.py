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
Application Constants

Version: 1.0.1
Created: December 2025
"""

import os


# Base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SQLite database path
DB_PATH = os.path.join(BASE_DIR, "database", "storage.db")

# Konfigurasi aplikasi (JSON)
CONFIG_PATH = os.path.join(BASE_DIR, "config", "app_config.json")

# Default export directory (boleh di-override via UI nanti)
EXPORT_PATH = os.path.join(BASE_DIR, "exports")


# Database table names
TBL_RAW = "raw_telemetry"
TBL_EXP_LOG = "experiment_log"
TBL_EXP_RES = "experiment_results"


# Default values
DEFAULT_INTERVAL_FTS = 7
DEFAULT_SPLIT_RATIO = 0.8
DEFAULT_FORECAST_HORIZON = 1
