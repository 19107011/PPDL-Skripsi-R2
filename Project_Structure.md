# Project Structure

- Target: `D:\0.0.SKRIPSI-ALMA\JANUARY 2026\Aplikasi\ppdl-app`
- Ignored: `.git, .idea, .venv, .vscode, __pycache__, build, dist, logs, node_modules, output, venv`
- Folders: **34**
- Files: **216**
- Generated: `2026-01-16 05:15:36`

```text
ppdl-app/
├─ config/
│  ├─ __init__.py
│  ├─ app_config.json
│  ├─ config_manager.py
│  ├─ constants.py
│  └─ ppdl-c7949-7536faac87ba.json
├─ database/
│  ├─ __init__.py
│  ├─ bq_downloader.py
│  ├─ db_manager.py
│  ├─ importer.py
│  └─ storage.db
├─ docs/
│  ├─ image/
│  │  └─ Report_CODEX-R0/
│  │     └─ 1767903988169.png
│  ├─ Audit_Report_Cache_Cleanup_R0.md
│  ├─ Audit_Report_Compliance_R1.md
│  ├─ Audit_Report_ExportLogs-R3.md
│  ├─ Audit_Report_for_BQ-Integration_R0.md
│  ├─ Audit_Report_PDF_Export_R2.md
│  ├─ Audit_Report_Target_Variable_R0.md
│  ├─ CATATAN.md
│  ├─ Doc_for_Ex_Plan-5.md
│  ├─ Doc_for_Ex_Plan-6.md
│  ├─ Ex_plan-1.md
│  ├─ Ex_plan-2.md
│  ├─ Ex_Plan-3.1.md
│  ├─ Ex_Plan-3.2.md
│  ├─ Ex_Plan-4.md
│  ├─ Ex_Plan-5.md
│  ├─ Ex_Plan-6.1.md
│  ├─ Ex_Plan-6.2.md
│  ├─ Ex_Plan-6.3.md
│  ├─ Ex_Plan-6.md
│  ├─ Ex_Plan-7.md
│  ├─ Ex_Plan-8.md
│  ├─ Ex_Plan-9.md
│  ├─ FIX_Flow_end_to_end-Contract.yaml
│  ├─ FIX_Flow_end_to_end.yaml
│  ├─ Flow_end_to_end.yaml.bak
│  ├─ Flowchart_System_Existing.mmd
│  ├─ Flowchart_System_Existing.puml
│  ├─ FTS_EqualWidth_Frequency_Fix_Report.md
│  ├─ R4_Design_Review.md
│  ├─ Ref-0.md
│  ├─ Ref-1.md
│  ├─ Ref-2.md
│  ├─ Ref-3.md
│  ├─ Ref-4.md
│  ├─ Ref-5.md
│  ├─ Ref-6.md
│  ├─ Ref-7.md
│  ├─ Ref-8.md
│  ├─ Ref-9.md
│  ├─ Report_Analisis_Export_Format_R5.md
│  ├─ Report_Claude-R1.md
│  ├─ Report_Claude.md
│  ├─ Report_CODEX-R0.md
│  ├─ Report_Event_ALL.md
│  ├─ Report_FORMULA_EVENTS-R1.md
│  ├─ Report_LOG_EVENTS-R1.md
│  ├─ Report_RUN-C.md
│  ├─ ResourceManager_Enhancement_Guide.md
│  ├─ Respon Todolist 3.md
│  ├─ RUN-1_COMPLETION_REPORT.md
│  ├─ RUN-2_COMPLETION_REPORT.md
│  ├─ RUN-3_COMPLETION_REPORT.md
│  ├─ RUN-4_COMPLETION_REPORT.md
│  ├─ RUN-5_COMPLETION_REPORT.md
│  ├─ smoke_guide.md
│  ├─ Struktur aplikasi.md
│  ├─ To_do_list-1.md
│  ├─ To_do_list-2.md
│  ├─ To_do_list-3.md
│  ├─ To_do_list_of_polishment-Export.txt
│  └─ UI_Redesign_Guide.md
├─ internal/
│  ├─ model/
│  ├─ repository/
│  └─ service/
├─ logic/
│  ├─ __init__.py
│  ├─ ann_model.py
│  ├─ arima_model.py
│  ├─ baseline.py
│  ├─ fts_chen.py
│  ├─ metrics.py
│  ├─ preprocessing.py
│  └─ sensitivity.py
├─ sample_data/
│  ├─ NEW Data result - R0/
│  │  ├─ PPDL_LOG_NLGZ6JSFTH/
│  │  │  ├─ [calc]_[detail]_NLGZ6JSFTH.log
│  │  │  ├─ [global]_[view]_NLGZ6JSFTH.log
│  │  │  ├─ [summary]_[view]_NLGZ6JSFTH.log
│  │  │  └─ Log_di_ui.log
│  │  ├─ dataset_range_NLGZ6JSFTH.json
│  │  ├─ dataset_schema_NLGZ6JSFTH.json
│  │  ├─ dataset_snapshot_NLGZ6JSFTH.csv
│  │  ├─ dataset_snapshot_NLGZ6JSFTH.meta.json
│  │  ├─ params_NLGZ6JSFTH.json
│  │  ├─ PPDL_LOG_NLGZ6JSFTH.zip
│  │  └─ resume_export_20260110_162247.pdf
│  ├─ NEW Data result - R1/
│  │  ├─ PPDL_LOG_Y11TAPZ82T/
│  │  │  ├─ [calc]_[detail]_Y11TAPZ82T.log
│  │  │  ├─ [global]_[view]_Y11TAPZ82T.log
│  │  │  ├─ [summary]_[view]_Y11TAPZ82T.log
│  │  │  └─ [ui]_[summary]_Y11TAPZ82T.log
│  │  ├─ dataset_range_Y11TAPZ82T.json
│  │  ├─ dataset_schema_Y11TAPZ82T.json
│  │  ├─ dataset_snapshot_Y11TAPZ82T.csv
│  │  ├─ dataset_snapshot_Y11TAPZ82T.meta.json
│  │  ├─ params_Y11TAPZ82T.json
│  │  ├─ PPDL_LOG_Y11TAPZ82T.zip
│  │  └─ resume_export_20260110_171931.pdf
│  ├─ New Data Result - R2/
│  │  ├─ log ui.log
│  │  ├─ ppdl_db_export_20260110_180820.csv
│  │  └─ resume_export_20260110_180648.pdf
│  ├─ New Data Result - R3/
│  │  ├─ PPDL_LOG_XSKLJKDKBN/
│  │  │  ├─ [calc]_[detail]_XSKLJKDKBN.log
│  │  │  ├─ [global]_[view]_XSKLJKDKBN.log
│  │  │  └─ [summary]_[view]_XSKLJKDKBN.log
│  │  ├─ dataset_range_XSKLJKDKBN.json
│  │  ├─ dataset_schema_XSKLJKDKBN.json
│  │  ├─ dataset_snapshot_XSKLJKDKBN.csv
│  │  ├─ dataset_snapshot_XSKLJKDKBN.meta.json
│  │  ├─ Log Ui.log
│  │  ├─ params_XSKLJKDKBN.json
│  │  ├─ ppdl_db_export_20260110_212203.csv
│  │  ├─ PPDL_LOG_XSKLJKDKBN.zip
│  │  └─ resume_export_20260110_212252.pdf
│  ├─ New Data Result - R4/
│  │  ├─ PPDL_DATASET_2Z2HKY06MO/
│  │  │  ├─ dataset_range_2Z2HKY06MO.json
│  │  │  ├─ dataset_schema_2Z2HKY06MO.json
│  │  │  ├─ dataset_snapshot_2Z2HKY06MO.csv
│  │  │  └─ dataset_snapshot_2Z2HKY06MO.meta.json
│  │  ├─ PPDL_LOG_2Z2HKY06MO/
│  │  │  ├─ [calc]_[detail]_2Z2HKY06MO.log
│  │  │  ├─ [global]_[view]_2Z2HKY06MO.log
│  │  │  ├─ [summary]_[view]_2Z2HKY06MO.log
│  │  │  └─ [ui]_[log]_2Z2HKY06MO.log
│  │  ├─ params_2Z2HKY06MO.json
│  │  ├─ PPDL_LOG_2Z2HKY06MO.zip
│  │  └─ resume_export_20260111_204207.pdf
│  ├─ New Data Result - R5/
│  │  ├─ PPDL_DATASET_GRWIS2G1Y6/
│  │  │  ├─ dataset_range_GRWIS2G1Y6.json
│  │  │  ├─ dataset_schema_GRWIS2G1Y6.json
│  │  │  ├─ dataset_snapshot_GRWIS2G1Y6.csv
│  │  │  └─ dataset_snapshot_GRWIS2G1Y6.meta.json
│  │  ├─ PPDL_LOG_GRWIS2G1Y6/
│  │  │  ├─ [calc]_[detail]_GRWIS2G1Y6.log
│  │  │  ├─ [global]_[view]_GRWIS2G1Y6.log
│  │  │  ├─ [summary]_[view]_GRWIS2G1Y6.log
│  │  │  └─ [ui]_[log]_GRWIS2G1Y6.txt
│  │  ├─ Resume Export in PNG/
│  │  │  ├─ resume_export_20260112_035310_Page1.png
│  │  │  ├─ resume_export_20260112_035310_Page10.png
│  │  │  ├─ resume_export_20260112_035310_Page11.png
│  │  │  ├─ resume_export_20260112_035310_Page12.png
│  │  │  ├─ resume_export_20260112_035310_Page2.png
│  │  │  ├─ resume_export_20260112_035310_Page3.png
│  │  │  ├─ resume_export_20260112_035310_Page4.png
│  │  │  ├─ resume_export_20260112_035310_Page5.png
│  │  │  ├─ resume_export_20260112_035310_Page6.png
│  │  │  ├─ resume_export_20260112_035310_Page7.png
│  │  │  ├─ resume_export_20260112_035310_Page8.png
│  │  │  └─ resume_export_20260112_035310_Page9.png
│  │  ├─ params_GRWIS2G1Y6.json
│  │  ├─ PPDL_LOG_GRWIS2G1Y6.zip
│  │  └─ resume_export_20260112_035310.pdf
│  ├─ PERCOBAAN/
│  │  ├─ dataset_range_90DD6726QV.json
│  │  ├─ dataset_schema_90DD6726QV.json
│  │  ├─ dataset_snapshot_90DD6726QV.csv
│  │  ├─ dataset_snapshot_90DD6726QV.meta.json
│  │  ├─ params_90DD6726QV.json
│  │  ├─ PPDL_LOG_90DD6726QV.zip
│  │  └─ resume_export_20260116_032327.pdf
│  ├─ PPDL_LOG_W9Z7NUQ99V/
│  │  ├─ [calc]_[detail]_W9Z7NUQ99V.log
│  │  ├─ [global]_[view]_W9Z7NUQ99V.log
│  │  └─ [summary]_[view]_W9Z7NUQ99V.log
│  ├─ Coba EXPORT.pdf
│  ├─ datapembacaan_26_desember_2025_sampai_04_januari_2026.json
│  ├─ dataset_range_W9Z7NUQ99V.json
│  ├─ dataset_schema_W9Z7NUQ99V.json
│  ├─ dataset_snapshot_W9Z7NUQ99V.meta.json
│  ├─ format-1.png
│  ├─ format-2.png
│  ├─ format-3.png
│  ├─ logo-trilogi-clean.png
│  └─ logo-trilogi.png
├─ smoke/
│  ├─ __init__.py
│  ├─ Report_SMOKE.md
│  └─ smoke_backend.py
├─ temp/
│  ├─ test_report.pdf
│  └─ test_resume_report.pdf
├─ tools/
│  ├─ log_audit.py
│  ├─ png_logo_cleaner.py
│  └─ png_requirements.txt
├─ ui/
│  ├─ assets/
│  │  └─ Logo_Trilogi.png
│  ├─ __init__.py
│  ├─ export_manager.py
│  ├─ main_window.py
│  ├─ main_window_ui.py
│  ├─ main_window_ui_R4.py
│  ├─ progress_dialog.py
│  ├─ R3-design-ui.ui
│  ├─ R3-design-ui.ui.backup
│  └─ R4-design-ui.ui
├─ utils/
│  ├─ __init__.py
│  ├─ app_logger.py
│  ├─ artifact_exporter.py
│  ├─ logging_events.py
│  ├─ logging_spec.py
│  ├─ resource_manager.py
│  └─ run_context.py
├─ workers/
│  ├─ __init__.py
│  └─ calc_thread.py
├─ .gitignore
├─ 4.0.7
├─ Backup-ppdl-app_10 januari 2026-R0_ok minor perbaikan polishment.zip
├─ Backup-ppdl-app_10 januari 2026-R1_ok minor perbaikan polishment.zip
├─ Backup-ppdl-app_9 januari 2026-sebelum rumus dibenerin.zip
├─ fix_syntax_error.py
├─ format_docstring.md
├─ main.py
├─ manual_finish_run_1_2.py
├─ project_tree.py
├─ README_EN.md
├─ README_ID.md
├─ requirements.txt
├─ test_cache_cleanup.py
├─ test_run1.py
├─ test_run_1_2_implementation.py
├─ test_tex.png
└─ test_tex.py
```

_Elapsed: 0.05s_