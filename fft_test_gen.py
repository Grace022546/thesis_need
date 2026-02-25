#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DUT-compatible 8-point complex FFT test-vector generator (for your PE)

This generator matches the PE fixed-point behavior:
- 8-point 1D FFT (NOT 2D)
- Q1.15 input/output
- Twiddles are Q1.15 constants:
    W8^0 = ( 32767,     0)
    W8^1 = ( 23170,-23170)
    W8^2 = (     0,-32768)
    W8^3 = (-23170,-23170)
- Bit-reversal input order: [0,4,2,6,1,5,3,7]
- Stage-by-stage butterfly with scaling /2 at EACH stage
- Rounding/saturation matches DUT q15_round_sat_from_q30:
    x_round = x_q30 + 16384
    x_round = x_round >>> 15
    saturate to [-32768, 32767]

Output format:
- in_caseXXX.memh : 8 lines, each 32-bit hex {re16, im16}
- out_caseXXX.memh: 8 lines, each 32-bit hex {re16, im16}
- all_cases_q15.csv
"""

import argparse
import csv
import os
import numpy as np

N = 8

# ------------------------------------------------------------
# DUT-compatible fixed-point helpers
# ------------------------------------------------------------
def sat16(x: int) -> int:
    if x > 32767:
        return 32767
    if x < -32768:
        return -32768
    return int(x)

def q15_from_float_dut(x: float) -> int:
    """
    Float -> Q1.15 int16 using DUT-like rule:
      q = sat( floor(x*32768 + 0.5) ) for positive-ish,
    but implemented exactly as:
      x_q30 = round?  No. For input quantization we still need a choice.
    Since DUT input arrives already quantized, we quantize here with nearest.
    """
    q = int(np.round(x * (1 << 15)))
    return sat16(q)

def q15_pack_word(re_i16: int, im_i16: int) -> str:
    re_u16 = np.uint16(np.int16(re_i16))
    im_u16 = np.uint16(np.int16(im_i16))
    w = (np.uint32(re_u16) << 16) | np.uint32(im_u16)
    return f"{int(w):08X}"

def q15_round_sat_from_q30_dut(x_q30: int) -> int:
    """
    Match Verilog:
      x_round = x_q30 + 16384
      x_round = x_round >>> 15
      sat to int16
    """
    x_round = int(x_q30) + 16384
    # Python >> is arithmetic for int
    y = x_round >> 15
    return sat16(y)

def cmul_q15_dut(a_re: int, a_im: int, w_re: int, w_im: int):
    """
    Complex multiply in Q1.15:
      (a_re + j a_im) * (w_re + j w_im)
    Intermediate is q30:
      re_q30 = a_re*w_re - a_im*w_im
      im_q30 = a_re*w_im + a_im*w_re
    Then DUT q30->q15 rounding/saturation.
    """
    re_q30 = int(a_re) * int(w_re) - int(a_im) * int(w_im)
    im_q30 = int(a_re) * int(w_im) + int(a_im) * int(w_re)
    re_q15 = q15_round_sat_from_q30_dut(re_q30)
    im_q15 = q15_round_sat_from_q30_dut(im_q30)
    return re_q15, im_q15

def bfly_scale2_dut(a_re: int, a_im: int, b_re: int, b_im: int):
    """
    Butterfly with per-stage /2 scaling to match your DUT behavior.
    Compute in q30 by shifting q15 inputs left 15, then q30->q15 convert.
    """
    # add
    add_re_q30 = ((int(a_re) + int(b_re)) << 15)
    add_im_q30 = ((int(a_im) + int(b_im)) << 15)
    # sub
    sub_re_q30 = ((int(a_re) - int(b_re)) << 15)
    sub_im_q30 = ((int(a_im) - int(b_im)) << 15)

    # divide by 2 at each stage (your current PE behavior)
    add_re_q30 >>= 1
    add_im_q30 >>= 1
    sub_re_q30 >>= 1
    sub_im_q30 >>= 1

    y0_re = q15_round_sat_from_q30_dut(add_re_q30)
    y0_im = q15_round_sat_from_q30_dut(add_im_q30)
    y1_re = q15_round_sat_from_q30_dut(sub_re_q30)
    y1_im = q15_round_sat_from_q30_dut(sub_im_q30)
    return (y0_re, y0_im), (y1_re, y1_im)

# ------------------------------------------------------------
# Twiddles (Q1.15, match your PE angle[] constants)
# ------------------------------------------------------------
W8 = [
    ( 32767,     0),   # W8^0
    ( 23170,-23170),   # W8^1
    (     0,-32768),   # W8^2
    (-23170,-23170),   # W8^3
]

# ------------------------------------------------------------
# DUT-compatible FFT8
# ------------------------------------------------------------
def fft8_dut_q15(in_re_q15, in_im_q15):
    """
    Input:  length-8 int arrays (Q1.15)
    Output: length-8 int arrays (Q1.15), DUT-compatible
    """

    # Bit-reversal order used in your PE stage1 switchbox
    br = [0, 4, 2, 6, 1, 5, 3, 7]
    x_re = [int(in_re_q15[i]) for i in br]
    x_im = [int(in_im_q15[i]) for i in br]

    # ---------------- Stage 1 ----------------
    # Pairs: (0,1),(2,3),(4,5),(6,7), twiddle all W0 on odd index
    s1_re = [0] * 8
    s1_im = [0] * 8
    for p in range(0, 8, 2):
        t_re, t_im = cmul_q15_dut(x_re[p+1], x_im[p+1], *W8[0])
        (y0_re, y0_im), (y1_re, y1_im) = bfly_scale2_dut(x_re[p], x_im[p], t_re, t_im)
        s1_re[p],   s1_im[p]   = y0_re, y0_im
        s1_re[p+1], s1_im[p+1] = y1_re, y1_im

    # Your PE stage2 shuffle:
    # [0,2,1,3,4,6,5,7]
    idx2 = [0, 2, 1, 3, 4, 6, 5, 7]
    x2_re = [s1_re[i] for i in idx2]
    x2_im = [s1_im[i] for i in idx2]

    # ---------------- Stage 2 ----------------
    # Pairs: (0,1)->W0, (2,3)->W2, (4,5)->W0, (6,7)->W2
    s2_re = [0] * 8
    s2_im = [0] * 8
    tw_stage2 = [0, 2, 0, 2]
    for g in range(4):
        p = 2 * g
        tw = tw_stage2[g]
        t_re, t_im = cmul_q15_dut(x2_re[p+1], x2_im[p+1], *W8[tw])
        (y0_re, y0_im), (y1_re, y1_im) = bfly_scale2_dut(x2_re[p], x2_im[p], t_re, t_im)
        s2_re[p],   s2_im[p]   = y0_re, y0_im
        s2_re[p+1], s2_im[p+1] = y1_re, y1_im

    # Your PE stage3 shuffle:
    # [0,4,1,5,2,6,3,7]
    idx3 = [0, 4, 1, 5, 2, 6, 3, 7]
    x3_re = [s2_re[i] for i in idx3]
    x3_im = [s2_im[i] for i in idx3]

    # ---------------- Stage 3 ----------------
    # Pairs: (0,1)->W0, (2,3)->W1, (4,5)->W2, (6,7)->W3
    out_re = [0] * 8
    out_im = [0] * 8
    tw_stage3 = [0, 1, 2, 3]
    for g in range(4):
        p = 2 * g
        tw = tw_stage3[g]
        t_re, t_im = cmul_q15_dut(x3_re[p+1], x3_im[p+1], *W8[tw])
        (y0_re, y0_im), (y1_re, y1_im) = bfly_scale2_dut(x3_re[p], x3_im[p], t_re, t_im)
        out_re[p],   out_im[p]   = y0_re, y0_im
        out_re[p+1], out_im[p+1] = y1_re, y1_im

    return np.array(out_re, dtype=np.int16), np.array(out_im, dtype=np.int16)

# ------------------------------------------------------------
# Pattern generators (8-point only)
# ------------------------------------------------------------
def gen_random_8(rng, amp=0.8):
    re = rng.uniform(-amp, amp, size=(N,))
    im = rng.uniform(-amp, amp, size=(N,))
    return re + 1j * im

def gen_impulse_8(pos=0, val=1+0j):
    x = np.zeros((N,), dtype=np.complex128)
    x[pos % N] = val
    return x

def gen_dc_8(val=0.5+0j):
    return np.full((N,), val, dtype=np.complex128)

def gen_tone_8(k=1, amp=0.8, phase=0.0):
    n = np.arange(N)
    ang = 2 * np.pi * k * n / N + phase
    return amp * np.exp(1j * ang)

# ------------------------------------------------------------
# IO
# ------------------------------------------------------------
def ensure_dir(d):
    os.makedirs(d, exist_ok=True)

def write_memh(path, words_hex):
    with open(path, "w", encoding="utf-8") as f:
        for w in words_hex:
            f.write(w + "\n")

def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["case", "idx", "in_re_i16", "in_im_i16", "out_re_i16", "out_im_i16"])
        for r in rows:
            w.writerow(r)

# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", type=str, default="fft8_tv_dut")
    ap.add_argument("--cases", type=int, default=10)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--mode", type=str, default="random",
                    choices=["random", "impulse", "dc", "tone", "mixed"])
    ap.add_argument("--amp", type=float, default=0.8)
    ap.add_argument("--tone_k", type=int, default=1)
    ap.add_argument("--tone_phase", type=float, default=0.0)
    ap.add_argument("--imp_idx", type=int, default=0)
    ap.add_argument("--imp_re", type=float, default=1.0)
    ap.add_argument("--imp_im", type=float, default=0.0)
    ap.add_argument("--dc_re", type=float, default=0.5)
    ap.add_argument("--dc_im", type=float, default=0.0)
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    ensure_dir(args.outdir)

    csv_rows = []
    case_id = 0

    if args.mode == "mixed":
        patterns = [
            gen_dc_8(0.5 + 0.25j),
            gen_impulse_8(0, 1 + 0j),
            gen_impulse_8(3, 0.7 - 0.2j),
            gen_tone_8(1, amp=0.7, phase=0.3),
            gen_tone_8(2, amp=0.6, phase=0.1),
            gen_random_8(rng, amp=0.8),
            gen_random_8(rng, amp=0.3),
        ]
    else:
        patterns = []
        for _ in range(args.cases):
            if args.mode == "random":
                x = gen_random_8(rng, amp=args.amp)
            elif args.mode == "impulse":
                x = gen_impulse_8(args.imp_idx, complex(args.imp_re, args.imp_im))
            elif args.mode == "dc":
                x = gen_dc_8(complex(args.dc_re, args.dc_im))
            elif args.mode == "tone":
                x = gen_tone_8(args.tone_k, amp=args.amp, phase=args.tone_phase)
            else:
                raise RuntimeError("unreachable")
            patterns.append(x)

    for x in patterns:
        # Input quantization (Q1.15)
        in_re = np.array([q15_from_float_dut(v) for v in np.real(x)], dtype=np.int16)
        in_im = np.array([q15_from_float_dut(v) for v in np.imag(x)], dtype=np.int16)

        # DUT-compatible golden
        out_re, out_im = fft8_dut_q15(in_re, in_im)

        # Write memh (8 words only, one row)
        in_hex = [q15_pack_word(int(in_re[i]), int(in_im[i])) for i in range(N)]
        out_hex = [q15_pack_word(int(out_re[i]), int(out_im[i])) for i in range(N)]

        write_memh(os.path.join(args.outdir, f"in_case{case_id:03d}.memh"), in_hex)
        write_memh(os.path.join(args.outdir, f"out_case{case_id:03d}.memh"), out_hex)

        for i in range(N):
            csv_rows.append([case_id, i, int(in_re[i]), int(in_im[i]), int(out_re[i]), int(out_im[i])])

        case_id += 1

    write_csv(os.path.join(args.outdir, "all_cases_q15.csv"), csv_rows)

    with open(os.path.join(args.outdir, "README.txt"), "w", encoding="utf-8") as f:
        f.write("DUT-compatible 8-point FFT vectors\n")
        f.write("Format: each line is 32-bit hex = {real[15:0], imag[15:0]} (two's complement)\n")
        f.write("Length per case: 8 lines (one FFT row)\n")
        f.write("Flow matches PE: bit-reversal + 3 stages + per-stage /2 + DUT q30->q15 rounding\n")
        f.write("Twiddles: Q1.15 fixed constants from PE angle[]\n")

    print(f"Generated {case_id} case(s) in {args.outdir}")
    print("Files: in_caseXXX.memh, out_caseXXX.memh, all_cases_q15.csv, README.txt")

if __name__ == "__main__":
    main()
