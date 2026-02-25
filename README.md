<img width="884" height="527" alt="image" src="https://github.com/user-attachments/assets/a0f58fdf-25e0-49e6-b516-99fc051633a1" />
<img width="879" height="512" alt="image" src="https://github.com/user-attachments/assets/738ebde8-f802-4b72-9d4b-66c0f20a7acd" />

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

