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
BigQuery Data Downloader

Version: 1.0.1
Created: December 2025
"""

import os
import json
import time
from google.cloud import bigquery
from google.oauth2 import service_account

class BigQueryDownloader:
    def __init__(self):
        # 1. Setup Path Relative
        # Script ini diasumsikan ada di dalam folder 'database/'
        # Structure:
        # project_root/
        #   ├── config/
        #   │   └── ppdl-c7949-7536faac87ba.json
        #   ├── database/
        #   │   └── bq_downloader.py (FILE INI)
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        
        # SETTING 1: Lokasi File Kunci (Sesuai nama file kamu)
        self.cred_path = os.path.join(project_root, 'config', 'ppdl-c7949-7536faac87ba.json')
        
        # SETTING 2: Folder untuk hasil download - gunakan system default Downloads
        self.download_dir = os.path.join(os.path.expanduser("~"), "Downloads")

        # Cek apakah file credential benar-benar ada
        if not os.path.exists(self.cred_path):
            raise FileNotFoundError(f"CRITICAL: File kunci tidak ditemukan di: {self.cred_path}")
            
        # Init Client BigQuery dengan Credential tersebut
        try:
            self.credentials = service_account.Credentials.from_service_account_file(self.cred_path)
            self.client = bigquery.Client(credentials=self.credentials, project=self.credentials.project_id)
        except Exception as e:
            raise ConnectionError(f"Gagal inisialisasi BigQuery Client: {e}")
            
        # SETTING 3: Target Table ID (Sesuai Cloud Function yang sudah jalan)
        self.table_id = "ppdl-c7949.valid_dataset_PPDL.valid_sensor_data_PPDL"

    def download_data(self, filename=None, limit=1000):
        """
        Download data dari BigQuery dan convert ke format JSON Firebase (Nested).
        Output disimpan otomatis ke folder 'downloads/'.
        
        Returns:
            tuple: (success: bool, result_path_or_error: str)
        """
        # 1. Pastikan folder 'downloads' ada
        if not os.path.exists(self.download_dir):
            try:
                os.makedirs(self.download_dir)
                print(f"📁 Folder 'downloads' dibuat di: {self.download_dir}")
            except OSError as e:
                return False, f"Gagal membuat folder download: {e}"
            
        # 2. Generate nama file otomatis jika tidak ada request nama khusus
        if filename is None:
            # Format: data_bq_TAHUNBULANTANGGAL_JAMMENITDETIK.json
            timestamp_str = time.strftime("%Y%m%d_%H%M%S")
            filename = f"data_bq_{timestamp_str}.json"
            
        output_path = os.path.join(self.download_dir, filename)

        print(f"🔄 Menghubungkan ke BigQuery: {self.table_id}...")

        # 3. Query SQL
        # Mengambil data terbaru berdasarkan ts_epoch
        # Note: 'current' adalah reserved word di BigQuery, jadi dibungkus dengan backticks
        query = f"""
            SELECT 
                ts_epoch, 
                voltage, 
                `current`, 
                power, 
                energy, 
                frequency, 
                pf 
            FROM `{self.table_id}`
            ORDER BY ts_epoch DESC
            LIMIT {limit}
        """

        try:
            query_job = self.client.query(query)
            results = query_job.result()  # Eksekusi dan tunggu hasil (Blocking)

            # 4. Transformasi Data (Table -> JSON Tree)
            # Format Firebase: { "timestamp_key": { ...data... }, ... }
            firebase_structure = {}
            count = 0

            print("🔄 Mentransformasi data Table ke JSON Structure...")
            
            for row in results:
                # Gunakan ts_epoch sebagai Key Utama (node ID)
                # Pastikan di-cast ke string agar valid sebagai JSON Key
                node_key = str(row.ts_epoch) 
                
                # MAPPING BALIK: Kolom BQ -> Key JSON Lama
                # Menggunakan .get atau if/else untuk handle nilai NULL dari database
                firebase_structure[node_key] = {
                    "ts_server_ms": row.ts_epoch,
                    "V": row.voltage if row.voltage is not None else 0.0,
                    "A": row.current if row.current is not None else 0.0,
                    "W": row.power if row.power is not None else 0.0,
                    "kWh": row.energy if row.energy is not None else 0.0,
                    "F": row.frequency if row.frequency is not None else 0.0,
                    "pf": row.pf if row.pf is not None else 0.0
                }
                count += 1

            # 5. Simpan ke file JSON fisik
            with open(output_path, 'w') as f:
                json.dump(firebase_structure, f, indent=4)
            
            print(f"✅ Berhasil! {count} data tersimpan di: {output_path}")
            
            # Return True dan Path file agar UI bisa langsung baca/tampilkan
            return True, output_path

        except Exception as e:
            error_msg = f"Gagal saat proses download/save: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

# --- BAGIAN TESTING (Bisa dijalankan langsung via Terminal) ---
if __name__ == "__main__":
    print("--- MULAI TESTING BIGQUERY DOWNLOADER ---")
    try:
        downloader = BigQueryDownloader()
        # Test download 5 data saja untuk verifikasi
        success, msg = downloader.download_data(filename="test_run_manual.json", limit=5)
        
        print(f"Status Sukses: {success}")
        print(f"Output Info: {msg}")
        
    except Exception as e:
        print(f"CRITICAL ERROR INIT: {e}")