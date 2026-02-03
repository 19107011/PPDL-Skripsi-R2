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
Application Configuration Manager

Version: 1.0.1
Created: December 2025
"""

import json
import os

from .constants import CONFIG_PATH, DEFAULT_INTERVAL_FTS, DEFAULT_SPLIT_RATIO


class ConfigManager:
    """Mengelola konfigurasi aplikasi (User Settings) untuk PPDL V1.0.

    Bersifat stateless (hanya kumpulan staticmethod) dan menyimpan
    konfigurasi ke file JSON di lokasi CONFIG_PATH.
    """

    _default_config = {
        "fts": {"interval": DEFAULT_INTERVAL_FTS, "method": "chen"},
        "ann": {"epoch": 200, "neuron": 10, "layers": 1, "lr": 0.01},
        "arima": {"p": 1, "d": 1, "q": 1, "seasonal": False, "s": 12},
        "global": {
            "split_ratio": DEFAULT_SPLIT_RATIO,
            "last_export_dir": "",
            "reset_on_startup": True,
        },
    }

    @staticmethod
    def load_config() -> dict:
        """Memuat konfigurasi dari file JSON.

        Jika file belum ada atau korup, akan mengembalikan default
        dan menulis ulang file default tersebut.
        """

        config_dir = os.path.dirname(CONFIG_PATH)
        os.makedirs(config_dir, exist_ok=True)

        if not os.path.exists(CONFIG_PATH):
            ConfigManager.save_config(ConfigManager._default_config)
            return dict(ConfigManager._default_config)

        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            # Jika gagal baca/parse, reset ke default
            ConfigManager.save_config(ConfigManager._default_config)
            return dict(ConfigManager._default_config)

        # Merge dengan default agar key baru tetap ada
        merged = dict(ConfigManager._default_config)
        merged.update(data)
        return merged

    @staticmethod
    def save_config(config_data: dict) -> None:
        """Menyimpan konfigurasi ke file JSON dalam format rapi (indent=4)."""

        config_dir = os.path.dirname(CONFIG_PATH)
        os.makedirs(config_dir, exist_ok=True)

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)
