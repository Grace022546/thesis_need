#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
8x8 Real Matrix Multiply test-vector generator (Q1.15 int16)

A, B : int16 (Q1.15), real-only
C    : int32, golden computed as:
       C[i][j] = sum_k( (A[i][k] * B[k][j]) >> 15 )

Outputs (row-major, 64 lines each):
- matA_q15.memh : 16-bit hex per line
- matB_q15.memh : 16-bit hex per line
- matC_gold.memh: 32-bit hex per line (two's complement)

Modes:
- random   : float uniform(-0.9, 0.9) then quantize to Q1.15
- ramp     : deterministic ramp (scaled)
- identity : A = I (0x7FFF diag), B random
- zeros    : all zeros
- digit    : generate "single-digit" integers in [-digit_max, digit_max],
             then shift-left by digit_shift to keep Q1.15 bitwidth but simple values.
             Default digit_shift=11 => real value = digit / 16.

Examples:
  python3 mm_test_gen.py --outdir mm_tv --seed 0 --mode random
  python3 mm_test_gen.py --mode ramp
  python3 mm_test_gen.py --mode identity
  python3 mm_test_gen.py --mode digit --digit_max 9 --digit_shift 11
"""

from __future__ import print_function
import argparse
import os
import numpy as np

N = 8
Q = 15
INT16_MIN = -(1 << 15)
INT16_MAX = (1 << 15) - 1


def sat_int16(x):
    return np.clip(x, INT16_MIN, INT16_MAX).astype(np.int16)


def float_to_q15(x):
    # x expected in [-1, 1)
    q = np.round(x * (1 << Q))
    return sat_int16(q)


def pack_u16_hex(v):
    # v: int16 array -> list of 4-hex-digit strings
    u = v.astype(np.uint16)
    flat = u.flatten()
    return ["{0:04X}".format(int(x)) for x in flat]


def pack_u32_hex_from_i32(v):
    # v: int32 array -> list of 8-hex-digit strings
    u = v.astype(np.uint32)
    flat = u.flatten()
    return ["{0:08X}".format(int(x)) for x in flat]


def gen_A_B(mode, rng, digit_max=9, digit_shift=11):
    if mode == "random":
        Af = rng.uniform(-0.9, 0.9, size=(N, N))
        Bf = rng.uniform(-0.9, 0.9, size=(N, N))
        A = float_to_q15(Af)
        B = float_to_q15(Bf)
        return A, B

    if mode == "ramp":
        A_int = np.arange(N * N, dtype=np.int32).reshape(N, N) - 32
        B_int = (np.arange(N * N, dtype=np.int32).reshape(N, N) - 16) * 2
        A = sat_int16(A_int * 256)
        B = sat_int16(B_int * 256)
        return A, B

    if mode == "identity":
        A = np.zeros((N, N), dtype=np.int16)
        for i in range(N):
            A[i, i] = np.int16(INT16_MAX)  # Q1.15 "1.0" approx
        Bf = rng.uniform(-0.9, 0.9, size=(N, N))
        B = float_to_q15(Bf)
        return A, B

    if mode == "zeros":
        A = np.zeros((N, N), dtype=np.int16)
        B = np.zeros((N, N), dtype=np.int16)
        return A, B

    if mode == "digit":
        # Step 1: small "single-digit" integers
        A_d = rng.randint(-digit_max, digit_max + 1, size=(N, N), dtype=np.int32)
        B_d = rng.randint(-digit_max, digit_max + 1, size=(N, N), dtype=np.int32)

        # Step 2: shift into Q1.15 domain (still int16)
        # value = digit << digit_shift  => real = digit / 2^(Q-digit_shift)
        A = sat_int16(A_d << digit_shift)
        B = sat_int16(B_d << digit_shift)
        return A, B

    raise ValueError("mode must be one of: random, ramp, identity, zeros, digit")


def golden_matmul_q15(A, B):
    # A,B are int16; do mult in int64 to be safe
    A64 = A.astype(np.int64)
    B64 = B.astype(np.int64)

    C = np.zeros((N, N), dtype=np.int64)
    for i in range(N):
        for j in range(N):
            acc = 0
            for k in range(N):
                prod = A64[i, k] * B64[k, j]  # Q30
                acc += (prod >> Q)            # back to Q15-ish (matches your spec)
            C[i, j] = acc

    return C.astype(np.int32)


def write_lines(path, lines):
    with open(path, "w") as f:
        for s in lines:
            f.write(s + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", type=str, default="mm_tv")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--mode", type=str, default="random",
                    choices=["random", "ramp", "identity", "zeros", "digit"])

    # For "digit" mode
    ap.add_argument("--digit_max", type=int, default=9,
                    help="max absolute digit for mode=digit (default 9 => -9..9)")
    ap.add_argument("--digit_shift", type=int, default=11,
                    help="left shift for mode=digit (default 11 => real=digit/16)")

    args = ap.parse_args()

    if not os.path.isdir(args.outdir):
        os.makedirs(args.outdir)

    rng = np.random.RandomState(args.seed)  # compatible with older numpy

    A, B = gen_A_B(args.mode, rng, digit_max=args.digit_max, digit_shift=args.digit_shift)
    C = golden_matmul_q15(A, B)

    write_lines(os.path.join(args.outdir, "matA_q15.memh"), pack_u16_hex(A))
    write_lines(os.path.join(args.outdir, "matB_q15.memh"), pack_u16_hex(B))
    write_lines(os.path.join(args.outdir, "matC_gold.memh"), pack_u32_hex_from_i32(C))

    print("[OK] Generated 8x8 real Q15 matmul vectors in:", args.outdir)
    print("     matA_q15.memh (64 lines, 16-bit hex, row-major)")
    print("     matB_q15.memh (64 lines, 16-bit hex, row-major)")
    print("     matC_gold.memh (64 lines, 32-bit hex, row-major)")
    if args.mode == "digit":
        denom = (1 << (Q - args.digit_shift)) if (Q - args.digit_shift) >= 0 else None
        real_info = ("real=digit/{0}".format(denom) if denom is not None else "real scaling depends on shift")
        print("     mode=digit, digit_max={0}, digit_shift={1} ({2})".format(
            args.digit_max, args.digit_shift, real_info))
    else:
        print("     mode={0}, seed={1}".format(args.mode, args.seed))


if __name__ == "__main__":
    main()
