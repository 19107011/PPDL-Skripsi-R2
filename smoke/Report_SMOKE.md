# Smoke Backend Report

Timestamp: 2026-01-09 15:16:08
Status: PASS

## Summary
- Project root: `D:\0.0.SKRIPSI-ALMA\JANUARY 2026\Aplikasi\ppdl-app`
- Sample JSON: `D:\0.0.SKRIPSI-ALMA\JANUARY 2026\Aplikasi\ppdl-app\sample_data\datapembacaan_26_desember_2025_sampai_04_januari_2026.json`
- Raw rows: 2817
- Train size: 2275
- Test size: 569

## Preprocess (Resample)
| Method | Resampled | Missing Filled |
| --- | --- | --- |
| mean | 2844 | 27 |
| ffill | 2844 | 1 |
| linear | 2844 | 0 |

## Metrics (Test Window)
| Model | MAE | RMSE | MAPE (%) | Ignored Zero |
| --- | --- | --- | --- | --- |
| FTS (equal-width) | 3.5731 | 5.1358 | 31.22 | 0 |
| FTS (equal-frequency) | 3.4517 | 5.7381 | 28.08 | 0 |
| Naive | 2.5435 | 5.0561 | 21.33 | 0 |
| MA(w=7) | 4.9225 | 6.6880 | 46.22 | 0 |
| ANN | 2.9035 | 4.7649 | 26.15 | 0 |
| ARIMA | 9.8170 | 11.9099 | 51.30 | 0 |

## Sensitivity Analysis
- Baseline MAPE: 31.22%
- Best case: case2
- Improvement: -3.14%

| Case | MAPE (%) | Delta (%) |
| --- | --- | --- |
| method = equal-frequency | 28.08 | -3.14 |
| n = 9 | 28.95 | -2.27 |
| pad = 10% | 31.15 | -0.07 |

## Checks
- PASS: DB fetch non-empty - rows=2817
- PASS: Resample method mean - resampled=2844
- PASS: Resample method ffill - resampled=2844
- PASS: Resample method linear - resampled=2844
- PASS: FTS UoD padding span-based - uod=(-2.5850000000000004, 54.285000000000004)
- PASS: FTS alignment (t-1 -> t) - forecast[0]=None
- PASS: FTS clamp within UoD
- PASS: FTS FLRG support (%)
- PASS: FTS equal-frequency intervals - intervals=7
- PASS: Baseline Naive first NaN
- PASS: Baseline MA first NaN
- PASS: MAPE skip zero actual - ignored=1
- PASS: Sensitivity 3 cases

Report file: `D:\0.0.SKRIPSI-ALMA\JANUARY 2026\Aplikasi\ppdl-app\smoke\Report_SMOKE.md`