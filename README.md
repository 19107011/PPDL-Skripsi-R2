# 📈 PPDL - Prediksi Pemakaian Daya Listrik

> **Judul Proyek Akademik:**
> Prediksi Pemakaian Daya Listrik Pada Rumah Tangga di Jakarta Berbasis IoT dengan Menggunakan Metode Fuzzy Time Series
> *Prediction of Household Electrical Power Consumption in Jakarta Using the Fuzzy Time Series Method*

---

**🎓 Institusi Akademik:**
Universitas Trilogi | Teknik Informatika | Program Sarjana (Strata 1)
Trilogi University | Informatics Engineering | Bachelor Degree

**👤 Penulis:** Alma Zannuba Arifah | 19107011

**👥 Pembimbing:**

- Ir. Yaddarabulah, M.Kom., Ph.D.
- Opitasari, S.Si., M.Kom.

**📅 Versi:** 1.0.1 | **Dibuat:** December 2025

---

**Power Prediction and Data Logger (PPDL)** - Aplikasi desktop canggih untuk prediksi konsumsi daya listrik menggunakan berbagai model machine learning dan analisis data komprehensif.

## 📋 Ikhtisar

PPDL V1.0 adalah aplikasi desktop sophisticated yang dibangun dengan PyQt6 untuk prediksi dan analisis konsumsi daya listrik. Aplikasi ini mengintegrasikan berbagai model forecasting termasuk Fuzzy Time Series (FTS Chen), Artificial Neural Networks (ANN), dan model ARIMA untuk memberikan analisis prediksi daya yang komprehensif.

### ✨ Fitur Utama

- 🔥 **Multi-Model Forecasting**: Model FTS Chen, ANN, ARIMA
- 📊 **Pemrosesan Data Lanjutan**: Import JSON, preprocessing, dan transformasi
- 🌐 **Integrasi BigQuery**: Download data langsung dari Google Cloud BigQuery
- 📈 **Visualisasi Interaktif**: Chart real-time dan analisis data
- 📄 **Generasi Laporan**: Export PDF dengan hasil analisis komprehensif
- 🧪 **Analisis Sensitivitas**: Optimasi parameter model
- 📋 **Kemampuan Export**: Export ke Excel, CSV, dan PDF
- 🎯 **Manajemen Cache Enhanced**: Cleanup dan resource management yang intelligent
- 📝 **Logging Komprehensif**: Aplikasi dan error logging yang detail

## 🛠 Stack Teknologi

- **Framework**: PyQt6 (Desktop GUI)
- **Backend**: Python 3.10.11
- **ML Libraries**: TensorFlow, scikit-learn, statsmodels
- **Pemrosesan Data**: pandas, NumPy
- **Visualisasi**: matplotlib
- **Integrasi Cloud**: Google Cloud BigQuery
- **Generasi Laporan**: ReportLab, PyMuPDF
- **File Handling**: openpyxl untuk operasi Excel

## 📦 Instalasi

### 📋 Prasyarat

- Python 3.10.11 atau lebih tinggi
- pip package manager
- Virtual environment (direkomendasikan)

### 🚀 Langkah-Langkah Setup

1. **📁 Clone repository**

   ```bash
   cd "D:\0.0.SKRIPSI-ALMA\JANUARY 2026\Aplikasi\ppdl-app"
   ```
2. **🔧 Buat dan aktifkan virtual environment**

   ```bash
   python -m venv venv
   venv\Scripts\activate  # Pada Windows
   # source venv/bin/activate  # Pada macOS/Linux
   ```
3. **📚 Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```
4. **🔑 Konfigurasi Google Cloud credentials** (untuk integrasi BigQuery)

   ```bash
   # Letakkan service account key file di root project
   # Update config/app_config.json jika diperlukan
   ```
5. **▶️ Jalankan aplikasi**

   ```bash
   python main.py
   ```

## 🚀 Cara Penggunaan

### ⚡ Quick Start

1. **🎯 Launch Aplikasi**: Jalankan `python main.py`
2. **📥 Import Data**:
   - Navigasi ke tab Main → Browse Folder → Pilih folder data JSON
   - Klik "Initiate Data" untuk import dan validasi data konsumsi daya
3. **⚙️ Konfigurasi Parameter** (Semua harus di-lock sebelum analisis):
   - **Tab Initial - General**: Set target variable, train/test split, forecasting horizon → Submit
   - **Tab Initial - FTS**: Konfigurasi interval, partition method, sensitivity → Submit
   - **Tab Initial - ANN**: Set epochs, neurons, layers, learning rate → Submit
   - **Tab Initial - ARIMA**: Konfigurasi parameter p,d,q, seasonal settings → Submit
4. **🔬 Jalankan Analisis**: Klik "Start Analysis" ketika semua parameter sudah terkunci
5. **👀 Monitor Progress**: Pantau pemrosesan real-time melalui tahap FTS → ANN → ARIMA
6. **📊 Lihat Hasil**: Analisis dashboard charts, metrik, dan prediksi
7. **💾 Export Laporan**: Generate laporan PDF, export Excel, atau dump database SQL

### 🔄 Alur Sistem Overview

Aplikasi mengikuti **sistem parameter locking** yang ketat dimana:

- Semua parameter model harus di-submit dan dikunci sebelum analisis
- Sistem memvalidasi ketersediaan data dan kelengkapan parameter
- Analisis berjalan melalui tahap sequential: Baseline → FTS → ANN → ARIMA
- Real-time logging menyediakan progress dan informasi debugging yang detail
- Hasil otomatis disimpan dalam database dan ditampilkan di dashboard

## 📁 Struktur Project

```
ppdl-app/
├── 🐍 main.py                 # Entry point aplikasi
├── 📄 requirements.txt        # Dependencies Python
├── 📖 README.md              # File ini
├── 📂 config/                # File konfigurasi
│   ├── 🔧 app_config.json    # Parameter model
│   ├── ⚙️ config_manager.py  # Manajemen konfigurasi
│   └── 📊 constants.py       # Konstanta aplikasi
├── 📂 database/              # Manajemen data
│   ├── 🗄️ db_manager.py      # Operasi database SQLite
│   ├── 📥 importer.py        # Import data JSON
│   └── ☁️ bq_downloader.py   # Integrasi BigQuery
├── 📂 logic/                 # Algoritma inti
│   ├── 🔮 fts_chen.py        # Implementasi Fuzzy Time Series
│   ├── 🧠 ann_model.py       # Model Neural Network
│   ├── 📈 arima_model.py     # Implementasi ARIMA
│   ├── 🛠️ preprocessing.py   # Preprocessing data
│   ├── 📏 metrics.py         # Metrik performa
│   └── 🧪 sensitivity.py    # Analisis sensitivitas
├── 📂 ui/                    # User interface
│   ├── 🖥️ main_window.py     # Window aplikasi utama
│   ├── 🎨 main_window_ui.py  # Definisi layout UI
│   ├── ⏳ progress_dialog.py # Dialog progress
│   └── 💾 export_manager.py  # Fungsionalitas export
├── 📂 utils/                 # Modul utilitas
│   ├── 📝 app_logger.py      # Application logging
│   ├── 🗂️ resource_manager.py # Manajemen cache
│   └── 🎯 run_context.py     # Konteks eksekusi
├── 📂 workers/               # Background tasks
│   └── [worker modules]   # Threading untuk operasi panjang
├── 📂 docs/                  # Dokumentasi
│   ├── 📋 Ex_Plan-*.md       # Execution plans
│   ├── 🔍 Audit_Report_*.md  # Audit reports
│   └── 📚 *.md               # Dokumentasi lainnya
├── 📂 sample_data/           # Dataset sample
└── 📂 temp/                  # File temporary
```

## 🎯 Detail Fitur

### 🔄 Pipeline Pemrosesan Data

Berdasarkan flowchart sistem, aplikasi PPDL mengikuti proses komprehensif berikut:

#### 1. **🚀 Fase Startup**

- **A0**: Peluncuran aplikasi dengan startup cache reset
- **A1**: Inisialisasi UI, loading config, koneksi signal
- **A2**: Loading data initial dari database (jika ada)
- **A3**: Refresh home dashboard (jika data tersedia)

#### 2. **📥 Fase Import Data**

- **B1**: Browse dan pilih folder JSON yang berisi data power
- **B2**: Inisiasi import data dengan validasi dan bulk insert
- **B3**: Penyimpanan database dengan logging komprehensif
- **B4**: Sinkronisasi dan refresh dashboard

#### 3. **⚙️ Konfigurasi Parameter**

- **C1**: **Parameter General** - Target variable, train/test split ratio, forecasting horizon
- **C2**: **Parameter FTS** - Interval count, partition method, validasi sensitivity
- **C3**: **Parameter ANN** - Epochs, layers, neurons, learning rate, batch size
- **C4**: **Parameter ARIMA** - p,d,q orders, konfigurasi seasonal/non-seasonal
- **C5**: **Readiness Gate** - Semua parameter harus dikunci sebelum analisis

#### 4. **🔬 Pipeline Analisis**

- **D1**: Start analisis dengan parameter yang terkunci
- **D2**: **Preprocessing Worker** - Resampling data, train/test splitting
- **D3**: **Metrik Baseline** - Benchmark Naive dan Moving Average
- **D4**: **Tahap FTS** - Modeling dan evaluasi Fuzzy Time Series
- **D5**: **Tahap ANN** - Training Neural Network dan prediksi
- **D6**: **Tahap ARIMA** - Statistical modeling dan forecasting
- **D7**: **Processing Hasil** - Update UI dan penyimpanan database
- **D8**: **Error Handling** - Manajemen failure dan cancellation yang graceful

#### 5. **💾 Export dan Output**

- **E1**: **Generasi Laporan PDF** - Laporan analisis komprehensif
- **E2**: **Resume Export** - Data summary dan metrik
- **E3**: **Log Export** - Complete application logs
- **E4**: **Database Export** - Ekstraksi data SQL

#### 6. **🔧 Fitur Tambahan**

- **F1**: **Integrasi BigQuery** - Kemampuan download data real-time
- **F2**: **Manajemen Log** - Limit display log yang configurable
- **H1-H2**: **Interaksi Dashboard** - Seleksi range dan date yang dinamis

### 📏 Metrik Performa

Sistem menghitung dan log metrik evaluasi komprehensif untuk setiap model:

- **MAE**: Mean Absolute Error - `mean(|y - yhat|)`
- **MSE**: Mean Squared Error - `mean((y - yhat)^2)`
- **RMSE**: Root Mean Squared Error - `sqrt(mean((y - yhat)^2))`
- **MAPE**: Mean Absolute Percentage Error - `mean(|(y - yhat)/y|)*100`
- **Perbandingan Baseline**: Benchmark Naive dan Moving Average (MA)
- **Model-Specific**: AIC/BIC untuk ARIMA, training loss untuk ANN, FLRG groups untuk FTS

#### 🔍 Proses Evaluasi

1. **Kalkulasi Baseline**: Metrik Naive dan MA(N) untuk perbandingan
2. **Evaluasi Model Sequential**: FTS → ANN → ARIMA dengan logging individual
3. **Analisis Komparatif**: Perbandingan performa side-by-side
4. **Validasi Statistik**: Formula logging untuk transparansi dan verifikasi

### 🗂️ Manajemen Cache

- **🧹 Intelligent Cleanup**: Manajemen file temp otomatis
- **🔍 Deteksi Orphaned Cache**: Startup cleanup untuk session lama
- **📊 Monitoring Resource**: Statistik penggunaan cache real-time
- **🔄 Error Recovery**: Cleanup yang robust dengan retry mechanism

### 💾 Opsi Export

- **📄 Laporan PDF**: Analisis komprehensif dengan chart
- **📊 File Excel**: Data detail dan metrik
- **📋 CSV Export**: Data mentah dan prediksi
- **🖼️ Image Export**: Chart dan visualisasi

## 📊 Opsi Import Data

### 📁 JSON Import

- Import file JSON lokal dengan data konsumsi daya
- Validasi dan preprocessing data otomatis
- Support untuk berbagai format timestamp

### ☁️ Integrasi BigQuery

- Koneksi langsung ke Google Cloud BigQuery (via panel Perbarui Data)
- Download data real-time dengan tracking progress
- Deteksi schema otomatis dan konversi
- **Catatan**: Workflow utama menggunakan JSON import; BigQuery sebagai sumber data alternatif

### 🔄 Konfigurasi Model

#### 🔮 Fuzzy Time Series (FTS Chen)

- **Interval**: Jumlah fuzzy sets (default: 9)
- **Sensitivity**: Parameter sensitivitas model (default: 1.0)
- **Partition**: Metode partisi data (Equal Width/Frequency)

#### 🧠 Artificial Neural Network (ANN)

- **Epochs**: Iterasi training (default: 90)
- **Neurons**: Neuron hidden layer (default: 10)
- **Layers**: Jumlah hidden layers (default: 1)
- **Learning Rate**: Rate optimasi (default: 0.01)

#### 📈 ARIMA Model

- **p, d, q**: Parameter non-seasonal (default: 1,1,1)
- **P, D, Q, s**: Parameter seasonal (configurable)
- **Seasonal**: Enable/disable seasonal modeling

## ⚙️ Konfigurasi

### 🔧 Pengaturan Aplikasi

Edit `config/app_config.json` untuk kustomisasi:

```json
{
    "global": {
        "split_ratio": 0.8,
        "forecast_horizon": 1,
        "resample_method": "mean"
    },
    "fts": {
        "interval": 9,
        "sensitivity": 1.0,
        "partition": "Equal Width"
    },
    "ann": {
        "epoch": 90,
        "neuron": 10,
        "layers": 1,
        "lr": 0.01
    },
    "arima": {
        "p": 1, "d": 1, "q": 1,
        "seasonal": false
    }
}
```

### 🔑 Setup BigQuery

1. Buat service account di Google Cloud Console
2. Download service account key (JSON)
3. Letakkan key file di root project
4. Konfigurasi table ID di BigQuery downloader

### 📝 Konfigurasi Logging

- **Session Logs**: Tracking operasi detail
- **Error Logs**: Laporan exception dan error
- **Performance Logs**: Monitoring waktu eksekusi

## 🧪 Testing

### 🔬 Unit Tests

```bash
# Jalankan cache cleanup tests
python test_cache_cleanup.py

# Jalankan test spesifik
python -m unittest test_cache_cleanup.TestCacheCleanup.test_normal_cleanup
```

### 🔗 Integration Testing

```bash
# Built-in integration test
python -c "from utils.resource_manager import ResourceManager; ResourceManager.integration_test()"
```

### 💨 Smoke Testing

```bash
# Jalankan smoke tests
python smoke/smoke_backend.py
```

## 🐛 Troubleshooting

### ⚠️ Masalah Umum

1. **🔌 Error Koneksi BigQuery**

   - Verifikasi service account credentials
   - Cek konektivitas network
   - Validasi format table ID
2. **❌ Import Errors**

   - Pastikan Python 3.10.11+ terinstall
   - Verifikasi semua dependencies di requirements.txt
   - Cek aktivasi virtual environment
3. **🧠 Masalah Memory**

   - Monitor penggunaan cache dengan `ResourceManager.get_cleanup_stats()`
   - Jalankan manual cleanup: `ResourceManager.cleanup()`
   - Kurangi ukuran dataset untuk testing
4. **🔒 UI Freezing**

   - Cek implementasi worker thread
   - Monitor progress dialogs
   - Review eksekusi background task

### 🔍 Debug Mode

Aktifkan logging detail dengan memodifikasi pengaturan logger di `utils/app_logger.py`.

## 📚 Dokumentasi

- **📋 Execution Plans**: `docs/Ex_Plan-*.md` - Strategi implementasi
- **🔍 Audit Reports**: `docs/Audit_Report_*.md` - Analisis sistem
- **📖 API Documentation**: Inline docstrings dan dokumentasi method
- **🛠️ Enhancement Guides**: `docs/*_Guide.md` - Dokumentasi fitur

## 🤝 Kontribusi

### 🔄 Development Workflow

1. Buat feature branch dari main
2. Ikuti style code dan pattern yang ada
3. Tambahkan docstring dan komentar yang komprehensif
4. Test menyeluruh dengan sample data
5. Update dokumentasi sesuai kebutuhan

### 📝 Code Style

- Ikuti konvensi PEP 8
- Gunakan type hints dimana sesuai
- Maintain comprehensive error handling
- Dokumentasikan algoritma complex dan business logic

## 📄 Lisensi

Project ini adalah bagian dari penelitian akademik (Skripsi). Silakan hubungi tim development untuk izin penggunaan dan informasi lisensi.

---

## 📞 Support

For technical support, bug reports, or feature requests:

- **Project Execution**: `Jakarta`
- **Documentation**: Check `docs/` folder for detailed guides
- **Logs**: Review application logs for debugging information

  ***FOR FURTHER CONTACT REACH ME By :  `alma.zannuba@trilogi.ac.id`***

  ---

**🔖 Versi**: 1.0.1
**📅 Last Updated**: 16 Januari 2026
**🐍 Python Version**: 3.10.11+
**🎓 Proyek Akademik**: Universitas Trilogi
**🚀 Status Development**: Production Ready
