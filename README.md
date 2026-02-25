<img width="884" height="527" alt="image" src="https://github.com/user-attachments/assets/a0f58fdf-25e0-49e6-b516-99fc051633a1" />
<img width="879" height="512" alt="image" src="https://github.com/user-attachments/assets/738ebde8-f802-4b72-9d4b-66c0f20a7acd" />


# 🚀 DSP Accelerator Hardware Verification

![Status](https://img.shields.io/badge/Status-All%20Tests%20Passed-brightgreen)
![Data Type](https://img.shields.io/badge/Data%20Format-Fixed--Point%20Q15-blue)
![Mode](https://img.shields.io/badge/Mode-Continuous%20Burst-orange)

本專案實現並驗證了基於 Verilog 的 DSP 加速器核心，包含 **8x8 矩陣乘法 (MatMul)** 與 **8 點快速傅立葉變換 (FFT)**。所有運算皆通過 Golden Model 100% 比對驗證。

---

```markdown
# 🚀 DSP Accelerator Hardware Verification

![Status](https://img.shields.io/badge/Status-All%20Tests%20Passed-brightgreen)
![Data Type](https://img.shields.io/badge/Data%20Format-Fixed--Point%20Q15-blue)
![Mode](https://img.shields.io/badge/Mode-Continuous%20Burst-orange)

本專案實現並驗證了基於 Verilog 的 DSP 加速器核心，包含 **8x8 矩陣乘法 (MatMul)** 與 **8 點快速傅立葉變換 (FFT)**。所有運算皆通過 Golden Model 100% 比對驗證。

---

## 🟦 Part 1: Matrix Multiplication (8x8)
### 驗證狀態：`PASSED`
採用連續噴發模式 (Continuous Burst Mode) 運算，下表為各 Row 驗證結果與輸出數值：

| Row | Status | Column 0 ~ 3 (Values) | Column 4 ~ 7 (Values) |
| :--- | :---: | :--- | :--- |
| **Row 0** | ✅ | 19584, -1536, -768, 2944 | 17280, 7936, -3840, -2816 |
| **Row 1** | ✅ | 12160, -4352, -21120, 4096 | 3968, -4608, -4992, -2560 |
| **Row 2** | ✅ | 5632, -4864, -18048, -2560 | 17024, 3968, -9088, -5632 |
| **Row 3** | ✅ | -12416, 24320, 29056, 896 | -4224, 18816, -5504, 13440 |
| **Row 4** | ✅ | -11008, 10240, 9856, 18944 | -14208, 2944, -2176, -7808 |
| **Row 5** | ✅ | -8064, -1280, 12288, 24192 | -14976, 15104, -1280, -8576 |
| **Row 6** | ✅ | 6912, 17408, 9344, 14720 | 6272, 8576, -10752, -9728 |
| **Row 7** | ✅ | 5248, 10368, -27648, -11776 | 20608, -15616, -896, -4352 |

```diff
+ *** ALL TEST CASES PASSED (8x8 Matrix) ***

```

---

## 🟨 Part 2: FFT 8-Point Analysis

### 驗證狀態：`PASSED`

針對 10 組獨立測試案例進行精度分析。容許誤差 (Tolerance) 設定為 `256`。

| Case ID | Max Abs Error (Re/Im) | Mean Abs Error (Re/Im) | Result |
| --- | --- | --- | --- |
| **Case 000** | 182 / 119 | 50.25 / 52.00 | ✅ Pass |
| **Case 001** | 93 / 85 | 44.00 / 28.25 | ✅ Pass |
| **Case 002** | 62 / 87 | 23.00 / 26.88 | ✅ Pass |
| **Case 003** | 108 / 125 | 40.38 / 46.75 | ✅ Pass |
| **Case 004** | 123 / 87 | 46.75 / 42.75 | ✅ Pass |
| **Case 005** | 208 / 140 | 76.38 / 59.25 | ✅ Pass |
| **Case 006** | 138 / 144 | 48.88 / 49.88 | ✅ Pass |
| **Case 007** | 113 / 205 | 47.50 / 53.63 | ✅ Pass |
| **Case 008** | 112 / 72 | 33.75 / 24.75 | ✅ Pass |
| **Case 009** | 125 / 141 | 37.88 / 45.88 | ✅ Pass |

---

## 📄 Raw Simulation Logs

若需查看原始測試路徑與加載過程，請點開下方摺疊選單：

<details>
<summary>點擊展開原始 Log 詳細內容</summary>

```text

[TB] Loaded 64x16b from /home/2024_summer/2024train_04/DSP_TEST/00_TESTBED/mm_tv/matA_q15.memh
[TB] Loaded 64x16b from /home/2024_summer/2024train_04/DSP_TEST/00_TESTBED/mm_tv/matB_q15.memh
[TB] Loaded 64 x 32b from /home/2024_summer/2024train_04/DSP_TEST/00_TESTBED/mm_tv/matC_gold.memh

=== START MATMUL: Continuous Burst Mode ===
[TB] Verifying Row 0...
  [MATCH]    Col 0 | Val:       19584
  [MATCH]    Col 1 | Val:       -1536
  [MATCH]    Col 2 | Val:        -768
  [MATCH]    Col 3 | Val:        2944
  [MATCH]    Col 4 | Val:       17280
  [MATCH]    Col 5 | Val:        7936
  [MATCH]    Col 6 | Val:       -3840
  [MATCH]    Col 7 | Val:       -2816
[TB] Verifying Row 1...
  [MATCH]    Col 0 | Val:       12160
  [MATCH]    Col 1 | Val:       -4352
  [MATCH]    Col 2 | Val:      -21120
  [MATCH]    Col 3 | Val:        4096
  [MATCH]    Col 4 | Val:        3968
  [MATCH]    Col 5 | Val:       -4608
  [MATCH]    Col 6 | Val:       -4992
  [MATCH]    Col 7 | Val:       -2560
[TB] Verifying Row 2...
  [MATCH]    Col 0 | Val:        5632
  [MATCH]    Col 1 | Val:       -4864
  [MATCH]    Col 2 | Val:      -18048
  [MATCH]    Col 3 | Val:       -2560
  [MATCH]    Col 4 | Val:       17024
  [MATCH]    Col 5 | Val:        3968
  [MATCH]    Col 6 | Val:       -9088
  [MATCH]    Col 7 | Val:       -5632
[TB] Verifying Row 3...
  [MATCH]    Col 0 | Val:      -12416
  [MATCH]    Col 1 | Val:       24320
  [MATCH]    Col 2 | Val:       29056
  [MATCH]    Col 3 | Val:         896
  [MATCH]    Col 4 | Val:       -4224
  [MATCH]    Col 5 | Val:       18816
  [MATCH]    Col 6 | Val:       -5504
  [MATCH]    Col 7 | Val:       13440
[TB] Verifying Row 4...
  [MATCH]    Col 0 | Val:      -11008
  [MATCH]    Col 1 | Val:       10240
  [MATCH]    Col 2 | Val:        9856
  [MATCH]    Col 3 | Val:       18944
  [MATCH]    Col 4 | Val:      -14208
  [MATCH]    Col 5 | Val:        2944
  [MATCH]    Col 6 | Val:       -2176
  [MATCH]    Col 7 | Val:       -7808
[TB] Verifying Row 5...
  [MATCH]    Col 0 | Val:       -8064
  [MATCH]    Col 1 | Val:       -1280
  [MATCH]    Col 2 | Val:       12288
  [MATCH]    Col 3 | Val:       24192
  [MATCH]    Col 4 | Val:      -14976
  [MATCH]    Col 5 | Val:       15104
  [MATCH]    Col 6 | Val:       -1280
  [MATCH]    Col 7 | Val:       -8576
[TB] Verifying Row 6...
  [MATCH]    Col 0 | Val:        6912
  [MATCH]    Col 1 | Val:       17408
  [MATCH]    Col 2 | Val:        9344
  [MATCH]    Col 3 | Val:       14720
  [MATCH]    Col 4 | Val:        6272
  [MATCH]    Col 5 | Val:        8576
  [MATCH]    Col 6 | Val:      -10752
  [MATCH]    Col 7 | Val:       -9728
[TB] Verifying Row 7...
  [MATCH]    Col 0 | Val:        5248
  [MATCH]    Col 1 | Val:       10368
  [MATCH]    Col 2 | Val:      -27648
  [MATCH]    Col 3 | Val:      -11776
  [MATCH]    Col 4 | Val:       20608
  [MATCH]    Col 5 | Val:      -15616
  [MATCH]    Col 6 | Val:        -896
  [MATCH]    Col 7 | Val:       -4352

*** ALL TEST CASES PASSED (8x8 Matrix) ***


========================================
      RUNNING FFT CASE: 000
========================================
[TB] Loaded 8 x 32b from /home/2024_summer/2024train_04/DSP_TEST/00_TESTBED/fft8_tv_dut/in_case000.memh
[TB] Loaded 8 x 32b from /home/2024_summer/2024train_04/DSP_TEST/00_TESTBED/fft8_tv_dut/out_case000.memh

=== RUN FFT (rows=1) ===
[TB][FFT_IN] Driven all 1 rows.

[DEBUG] --- Stage 1 Input (Bit-Reversed) ---
[TB][FFT] tolerance_re=256, tolerance_im=256
[TB][FFT] max_abs_err_re=182, max_abs_err_im=119
[TB][FFT] mean_abs_err_re=50.250000, mean_abs_err_im=52.000000
[TB][FFT] Done. mismatches=0


========================================
      RUNNING FFT CASE: 001
========================================
[TB] Loaded 8 x 32b from /home/2024_summer/2024train_04/DSP_TEST/00_TESTBED/fft8_tv_dut/in_case001.memh
[TB] Loaded 8 x 32b from /home/2024_summer/2024train_04/DSP_TEST/00_TESTBED/fft8_tv_dut/out_case001.memh

=== RUN FFT (rows=1) ===
[TB][FFT_IN] Driven all 1 rows.

[DEBUG] --- Stage 1 Input (Bit-Reversed) ---
[TB][FFT] tolerance_re=256, tolerance_im=256
[TB][FFT] max_abs_err_re=93, max_abs_err_im=85
[TB][FFT] mean_abs_err_re=44.000000, mean_abs_err_im=28.250000
[TB][FFT] Done. mismatches=0


========================================
      RUNNING FFT CASE: 002
========================================
[TB] Loaded 8 x 32b from /home/2024_summer/2024train_04/DSP_TEST/00_TESTBED/fft8_tv_dut/in_case002.memh
[TB] Loaded 8 x 32b from /home/2024_summer/2024train_04/DSP_TEST/00_TESTBED/fft8_tv_dut/out_case002.memh

=== RUN FFT (rows=1) ===
[TB][FFT_IN] Driven all 1 rows.

[DEBUG] --- Stage 1 Input (Bit-Reversed) ---
[TB][FFT] tolerance_re=256, tolerance_im=256
[TB][FFT] max_abs_err_re=62, max_abs_err_im=87
[TB][FFT] mean_abs_err_re=23.000000, mean_abs_err_im=26.875000
[TB][FFT] Done. mismatches=0


========================================
      RUNNING FFT CASE: 003
========================================
[TB] Loaded 8 x 32b from /home/2024_summer/2024train_04/DSP_TEST/00_TESTBED/fft8_tv_dut/in_case003.memh
[TB] Loaded 8 x 32b from /home/2024_summer/2024train_04/DSP_TEST/00_TESTBED/fft8_tv_dut/out_case003.memh

=== RUN FFT (rows=1) ===
[TB][FFT_IN] Driven all 1 rows.

[DEBUG] --- Stage 1 Input (Bit-Reversed) ---
[TB][FFT] tolerance_re=256, tolerance_im=256
[TB][FFT] max_abs_err_re=108, max_abs_err_im=125
[TB][FFT] mean_abs_err_re=40.375000, mean_abs_err_im=46.750000
[TB][FFT] Done. mismatches=0


========================================
      RUNNING FFT CASE: 004
========================================
[TB] Loaded 8 x 32b from /home/2024_summer/2024train_04/DSP_TEST/00_TESTBED/fft8_tv_dut/in_case004.memh
[TB] Loaded 8 x 32b from /home/2024_summer/2024train_04/DSP_TEST/00_TESTBED/fft8_tv_dut/out_case004.memh

=== RUN FFT (rows=1) ===
[TB][FFT_IN] Driven all 1 rows.

[DEBUG] --- Stage 1 Input (Bit-Reversed) ---
[TB][FFT] tolerance_re=256, tolerance_im=256
[TB][FFT] max_abs_err_re=123, max_abs_err_im=87
[TB][FFT] mean_abs_err_re=46.750000, mean_abs_err_im=42.750000
[TB][FFT] Done. mismatches=0


========================================
      RUNNING FFT CASE: 005
========================================
[TB] Loaded 8 x 32b from /home/2024_summer/2024train_04/DSP_TEST/00_TESTBED/fft8_tv_dut/in_case005.memh
[TB] Loaded 8 x 32b from /home/2024_summer/2024train_04/DSP_TEST/00_TESTBED/fft8_tv_dut/out_case005.memh

=== RUN FFT (rows=1) ===
[TB][FFT_IN] Driven all 1 rows.

[DEBUG] --- Stage 1 Input (Bit-Reversed) ---
[TB][FFT] tolerance_re=256, tolerance_im=256
[TB][FFT] max_abs_err_re=208, max_abs_err_im=140
[TB][FFT] mean_abs_err_re=76.375000, mean_abs_err_im=59.250000
[TB][FFT] Done. mismatches=0


========================================
      RUNNING FFT CASE: 006
========================================
[TB] Loaded 8 x 32b from /home/2024_summer/2024train_04/DSP_TEST/00_TESTBED/fft8_tv_dut/in_case006.memh
[TB] Loaded 8 x 32b from /home/2024_summer/2024train_04/DSP_TEST/00_TESTBED/fft8_tv_dut/out_case006.memh

=== RUN FFT (rows=1) ===
[TB][FFT_IN] Driven all 1 rows.

[DEBUG] --- Stage 1 Input (Bit-Reversed) ---
[TB][FFT] tolerance_re=256, tolerance_im=256
[TB][FFT] max_abs_err_re=138, max_abs_err_im=144
[TB][FFT] mean_abs_err_re=48.875000, mean_abs_err_im=49.875000
[TB][FFT] Done. mismatches=0


========================================
      RUNNING FFT CASE: 007
========================================
[TB] Loaded 8 x 32b from /home/2024_summer/2024train_04/DSP_TEST/00_TESTBED/fft8_tv_dut/in_case007.memh
[TB] Loaded 8 x 32b from /home/2024_summer/2024train_04/DSP_TEST/00_TESTBED/fft8_tv_dut/out_case007.memh

=== RUN FFT (rows=1) ===
[TB][FFT_IN] Driven all 1 rows.

[DEBUG] --- Stage 1 Input (Bit-Reversed) ---
[TB][FFT] tolerance_re=256, tolerance_im=256
[TB][FFT] max_abs_err_re=113, max_abs_err_im=205
[TB][FFT] mean_abs_err_re=47.500000, mean_abs_err_im=53.625000
[TB][FFT] Done. mismatches=0


========================================
      RUNNING FFT CASE: 008
========================================
[TB] Loaded 8 x 32b from /home/2024_summer/2024train_04/DSP_TEST/00_TESTBED/fft8_tv_dut/in_case008.memh
[TB] Loaded 8 x 32b from /home/2024_summer/2024train_04/DSP_TEST/00_TESTBED/fft8_tv_dut/out_case008.memh

=== RUN FFT (rows=1) ===
[TB][FFT_IN] Driven all 1 rows.

[DEBUG] --- Stage 1 Input (Bit-Reversed) ---
[TB][FFT] tolerance_re=256, tolerance_im=256
[TB][FFT] max_abs_err_re=112, max_abs_err_im=72
[TB][FFT] mean_abs_err_re=33.750000, mean_abs_err_im=24.750000
[TB][FFT] Done. mismatches=0


========================================
      RUNNING FFT CASE: 009
========================================
[TB] Loaded 8 x 32b from /home/2024_summer/2024train_04/DSP_TEST/00_TESTBED/fft8_tv_dut/in_case009.memh
[TB] Loaded 8 x 32b from /home/2024_summer/2024train_04/DSP_TEST/00_TESTBED/fft8_tv_dut/out_case009.memh

=== RUN FFT (rows=1) ===
[TB][FFT_IN] Driven all 1 rows.

[DEBUG] --- Stage 1 Input (Bit-Reversed) ---
[TB][FFT] tolerance_re=256, tolerance_im=256
[TB][FFT] max_abs_err_re=125, max_abs_err_im=141
[TB][FFT] mean_abs_err_re=37.875000, mean_abs_err_im=45.875000
[TB][FFT] Done. mismatches=0


[TB] All FFT Test Suites Finished.
```

</details>

---

```


```
