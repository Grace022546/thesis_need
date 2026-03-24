import math
import csv
from dataclasses import dataclass
from typing import Dict, List, Tuple, Callable

import numpy as np


# =========================================================
# fixed-point helpers
# =========================================================

def sign_extend(val: int, bits: int) -> int:
    mask = (1 << bits) - 1
    val &= mask
    if val & (1 << (bits - 1)):
        val -= (1 << bits)
    return val


def sat_to_bits(val: int, bits: int) -> int:
    qmin = -(1 << (bits - 1))
    qmax = (1 << (bits - 1)) - 1
    return min(max(val, qmin), qmax)


def q15_to_float(x: int) -> float:
    return sign_extend(x, 16) / float(1 << 15)


def float_to_q15(x: float) -> int:
    raw = int(np.round(x * (1 << 15)))
    return sat_to_bits(raw, 16)


def rmse(ref: np.ndarray, est: np.ndarray) -> float:
    ref = np.asarray(ref, dtype=np.float64)
    est = np.asarray(est, dtype=np.float64)
    return float(np.sqrt(np.mean((ref - est) ** 2)))


def rel_rmse(ref: np.ndarray, est: np.ndarray, eps: float = 1e-12) -> float:
    ref = np.asarray(ref, dtype=np.float64)
    est = np.asarray(est, dtype=np.float64)
    num = np.sqrt(np.mean((ref - est) ** 2))
    den = np.sqrt(np.mean(ref ** 2)) + eps
    return float(num / den)


def snr_db(ref: np.ndarray, err: np.ndarray, eps: float = 1e-15) -> float:
    ref = np.asarray(ref, dtype=np.float64)
    err = np.asarray(err, dtype=np.float64)
    ps = np.mean(ref ** 2)
    pe = np.mean(err ** 2) + eps
    return float(10.0 * np.log10((ps + eps) / pe))


def bit_growth_sum(num_terms: int) -> int:
    if num_terms <= 1:
        return 0
    return int(math.ceil(math.log2(num_terms)))


# =========================================================
# configurable quantizer
# =========================================================

@dataclass
class QuantResult:
    value: int
    sat: bool
    pre_shift: int
    post_shift: int


def q15_quantize(
    x_q30: int,
    shift: int,
    rounding_mode: str = "rtl_bias",
    acc_bits: int = 35
) -> QuantResult:
    """
    rounding_mode:
        rtl_bias   -> x + 16384
        symmetric  -> positive:+16384, negative:-16384
        trunc      -> no rounding
    """
    x_q30 = sign_extend(x_q30, acc_bits)

    if rounding_mode == "rtl_bias":
        x_round = x_q30 + (1 << 14)

    elif rounding_mode == "symmetric":
        if x_q30 >= 0:
            x_round = x_q30 + (1 << 14)
        else:
            x_round = x_q30 - (1 << 14)

    elif rounding_mode == "trunc":
        x_round = x_q30

    else:
        raise ValueError(f"Unsupported rounding mode: {rounding_mode}")

    x_shift = sign_extend(x_round >> shift, acc_bits)

    sat = False
    if x_shift > 32767:
        sat = True
        out = 32767
    elif x_shift < -32768:
        sat = True
        out = -32768
    else:
        out = x_shift

    return QuantResult(
        value=sign_extend(out, 16),
        sat=sat,
        pre_shift=x_q30,
        post_shift=x_shift
    )


# =========================================================
# arithmetic
# =========================================================

def q15_mul_q30(a_q15: int, b_q15: int) -> int:
    a = sign_extend(a_q15, 16)
    b = sign_extend(b_q15, 16)
    return a * b


def dot_q15_config(
    a_q15: np.ndarray,
    b_q15: np.ndarray,
    shift: int = 15,
    rounding_mode: str = "rtl_bias",
    acc_bits: int = 35
) -> Tuple[int, Dict]:
    assert len(a_q15) == len(b_q15)

    acc = 0
    max_abs_acc = 0
    sat_internal = False

    full_acc = 0
    max_acc_limit = (1 << (acc_bits - 1)) - 1
    min_acc_limit = -(1 << (acc_bits - 1))

    for aa, bb in zip(a_q15, b_q15):
        prod = q15_mul_q30(int(aa), int(bb))
        full_acc += prod

        if full_acc > max_acc_limit or full_acc < min_acc_limit:
            sat_internal = True

        acc = sign_extend(full_acc, acc_bits)
        max_abs_acc = max(max_abs_acc, abs(full_acc))

    q = q15_quantize(acc, shift=shift, rounding_mode=rounding_mode, acc_bits=acc_bits)

    return q.value, {
        "acc_full_precision": full_acc,
        "acc_max_abs": max_abs_acc,
        "acc_internal_overflow": sat_internal,
        "sat_final": q.sat
    }


def risk_level(sat_cnt_avg: float, rel_err: float, snr: float) -> str:
    if sat_cnt_avg > 10 or snr < 20 or rel_err > 0.1:
        return "FAIL"
    elif sat_cnt_avg > 0.1 or snr < 40 or rel_err > 0.01:
        return "WARNING"
    return "SAFE"


# =========================================================
# MM
# =========================================================

def mm_q15_eval(
    n: int,
    trials: int = 100,
    seed: int = 0,
    rounding_mode: str = "rtl_bias",
    acc_bits: int = 35,
    pre_scale_bits: int = 0
) -> Dict:
    rng = np.random.default_rng(seed)
    rmses, rels, snrs = [], [], []
    sat_cnts, internal_of = [], []

    for _ in range(trials):
        A = rng.uniform(-0.8, 0.8, size=(n, n))
        B = rng.uniform(-0.8, 0.8, size=(n, n))

        A_q = np.array([[float_to_q15(v / (2 ** pre_scale_bits)) for v in row] for row in A], dtype=np.int64)
        B_q = np.array([[float_to_q15(v / (2 ** pre_scale_bits)) for v in row] for row in B], dtype=np.int64)

        C_est = np.zeros((n, n), dtype=np.float64)
        sat_cnt = 0
        int_of = 0

        for i in range(n):
            for j in range(n):
                q15_out, info = dot_q15_config(
                    A_q[i, :], B_q[:, j],
                    shift=15,
                    rounding_mode=rounding_mode,
                    acc_bits=acc_bits
                )
                C_est[i, j] = q15_to_float(q15_out) * (2 ** (2 * pre_scale_bits))
                sat_cnt += int(info["sat_final"])
                int_of += int(info["acc_internal_overflow"])

        C_ref = A @ B
        err = C_est - C_ref

        rmses.append(rmse(C_ref, C_est))
        rels.append(rel_rmse(C_ref, C_est))
        snrs.append(snr_db(C_ref, err))
        sat_cnts.append(sat_cnt)
        internal_of.append(int_of)

    return {
        "kernel": "MM",
        "size": f"{n}x{n}",
        "dot_depth": n,
        "growth_bits": bit_growth_sum(n),
        "rounding_mode": rounding_mode,
        "acc_bits": acc_bits,
        "pre_scale_bits": pre_scale_bits,
        "rmse": float(np.mean(rmses)),
        "rel_rmse": float(np.mean(rels)),
        "snr_db": float(np.mean(snrs)),
        "sat_count_avg": float(np.mean(sat_cnts)),
        "internal_overflow_avg": float(np.mean(internal_of)),
        "risk": risk_level(float(np.mean(sat_cnts)), float(np.mean(rels)), float(np.mean(snrs)))
    }


# =========================================================
# FIR
# =========================================================

def fir_q15_eval(
    taps: int,
    signal_len: int = 2048,
    trials: int = 50,
    seed: int = 1,
    rounding_mode: str = "rtl_bias",
    acc_bits: int = 35,
    pre_scale_bits: int = 0
) -> Dict:
    rng = np.random.default_rng(seed)

    rmses, rels, snrs = [], [], []
    sat_cnts, internal_of = [], []

    for _ in range(trials):
        x = rng.uniform(-0.9, 0.9, size=signal_len)
        h = rng.uniform(-0.2, 0.2, size=taps)

        x_q = np.array([float_to_q15(v / (2 ** pre_scale_bits)) for v in x], dtype=np.int64)
        h_q = np.array([float_to_q15(v / (2 ** pre_scale_bits)) for v in h], dtype=np.int64)

        y_est = []
        sat_cnt = 0
        int_of = 0

        for n in range(taps - 1, len(x_q)):
            xx = x_q[n - taps + 1:n + 1][::-1]
            q15_out, info = dot_q15_config(
                xx, h_q,
                shift=15,
                rounding_mode=rounding_mode,
                acc_bits=acc_bits
            )
            y_est.append(q15_to_float(q15_out) * (2 ** (2 * pre_scale_bits)))
            sat_cnt += int(info["sat_final"])
            int_of += int(info["acc_internal_overflow"])

        y_est = np.array(y_est, dtype=np.float64)
        y_ref = np.convolve(x, h, mode="valid")
        err = y_est - y_ref

        rmses.append(rmse(y_ref, y_est))
        rels.append(rel_rmse(y_ref, y_est))
        snrs.append(snr_db(y_ref, err))
        sat_cnts.append(sat_cnt)
        internal_of.append(int_of)

    return {
        "kernel": "FIR",
        "size": taps,
        "mac_depth": taps,
        "growth_bits": bit_growth_sum(taps),
        "rounding_mode": rounding_mode,
        "acc_bits": acc_bits,
        "pre_scale_bits": pre_scale_bits,
        "rmse": float(np.mean(rmses)),
        "rel_rmse": float(np.mean(rels)),
        "snr_db": float(np.mean(snrs)),
        "sat_count_avg": float(np.mean(sat_cnts)),
        "internal_overflow_avg": float(np.mean(internal_of)),
        "risk": risk_level(float(np.mean(sat_cnts)), float(np.mean(rels)), float(np.mean(snrs)))
    }


# =========================================================
# CONV2D (with channels)
# =========================================================

def conv2d_q15_eval(
    img_hw=(32, 32),
    kernel_hw=(3, 3),
    in_channels: int = 1,
    trials: int = 30,
    seed: int = 2,
    rounding_mode: str = "rtl_bias",
    acc_bits: int = 35,
    pre_scale_bits: int = 0
) -> Dict:
    rng = np.random.default_rng(seed)
    H, W = img_hw
    KH, KW = kernel_hw
    mac_depth = KH * KW * in_channels

    rmses, rels, snrs = [], [], []
    sat_cnts, internal_of = [], []

    for _ in range(trials):
        img = rng.uniform(-0.9, 0.9, size=(in_channels, H, W))
        ker = rng.uniform(-0.2, 0.2, size=(in_channels, KH, KW))

        img_q = np.array(
            [[[float_to_q15(v / (2 ** pre_scale_bits)) for v in row] for row in ch] for ch in img],
            dtype=np.int64
        )
        ker_q = np.array(
            [[[float_to_q15(v / (2 ** pre_scale_bits)) for v in row] for row in ch] for ch in ker],
            dtype=np.int64
        )

        OH = H - KH + 1
        OW = W - KW + 1

        y_est = np.zeros((OH, OW), dtype=np.float64)
        y_ref = np.zeros((OH, OW), dtype=np.float64)

        sat_cnt = 0
        int_of = 0

        for r in range(OH):
            for c in range(OW):
                patch = img_q[:, r:r+KH, c:c+KW].flatten()
                filt = ker_q.flatten()

                q15_out, info = dot_q15_config(
                    patch, filt,
                    shift=15,
                    rounding_mode=rounding_mode,
                    acc_bits=acc_bits
                )
                y_est[r, c] = q15_to_float(q15_out) * (2 ** (2 * pre_scale_bits))
                sat_cnt += int(info["sat_final"])
                int_of += int(info["acc_internal_overflow"])

                y_ref[r, c] = np.sum(img[:, r:r+KH, c:c+KW] * ker)

        err = y_est - y_ref
        rmses.append(rmse(y_ref, y_est))
        rels.append(rel_rmse(y_ref, y_est))
        snrs.append(snr_db(y_ref, err))
        sat_cnts.append(sat_cnt)
        internal_of.append(int_of)

    return {
        "kernel": "CONV2D",
        "size": f"{H}x{W}, K={KH}x{KW}, Cin={in_channels}",
        "mac_depth": mac_depth,
        "growth_bits": bit_growth_sum(mac_depth),
        "rounding_mode": rounding_mode,
        "acc_bits": acc_bits,
        "pre_scale_bits": pre_scale_bits,
        "rmse": float(np.mean(rmses)),
        "rel_rmse": float(np.mean(rels)),
        "snr_db": float(np.mean(snrs)),
        "sat_count_avg": float(np.mean(sat_cnts)),
        "internal_overflow_avg": float(np.mean(internal_of)),
        "risk": risk_level(float(np.mean(sat_cnts)), float(np.mean(rels)), float(np.mean(snrs)))
    }


# =========================================================
# experiment helpers
# =========================================================

def annotate_row(row: Dict, exp_name: str, compare_group: str) -> Dict:
    row = dict(row)
    row["exp_name"] = exp_name
    row["compare_group"] = compare_group
    return row


def run_suite(
    eval_fn: Callable,
    eval_arg,
    exp_name: str,
    compare_group: str,
    rounding_mode: str,
    acc_bits: int,
    pre_scale_bits: int
) -> Dict:
    row = eval_fn(
        eval_arg,
        rounding_mode=rounding_mode,
        acc_bits=acc_bits,
        pre_scale_bits=pre_scale_bits
    )
    return annotate_row(row, exp_name=exp_name, compare_group=compare_group)


def run_conv_suite(
    img_hw,
    ker_hw,
    cin: int,
    exp_name: str,
    compare_group: str,
    rounding_mode: str,
    acc_bits: int,
    pre_scale_bits: int
) -> Dict:
    row = conv2d_q15_eval(
        img_hw=img_hw,
        kernel_hw=ker_hw,
        in_channels=cin,
        rounding_mode=rounding_mode,
        acc_bits=acc_bits,
        pre_scale_bits=pre_scale_bits
    )
    return annotate_row(row, exp_name=exp_name, compare_group=compare_group)


# =========================================================
# save / run
# =========================================================

def save_csv(rows: List[Dict], path: str):
    keys = sorted(set().union(*[r.keys() for r in rows]))
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def main():
    rows = []

    mm_sizes = [8, 16, 32, 64]
    fir_taps = [128, 256]
    test_convs = [
        ((32, 32), (3, 3), 1),
        ((32, 32), (5, 5), 1),
        ((32, 32), (3, 3), 16),
        ((32, 32), (5, 5), 16),
    ]

    # =====================================================
    # Group A: fair accumulator-width comparison
    # fixed rounding = symmetric, fixed pre_scale = 0
    # =====================================================
    for n in mm_sizes:
        rows.append(run_suite(
            mm_q15_eval, n,
            exp_name="fair_acc_cmp_35b",
            compare_group=f"MM_{n}x{n}_acc_only",
            rounding_mode="symmetric", acc_bits=35, pre_scale_bits=0
        ))
        rows.append(run_suite(
            mm_q15_eval, n,
            exp_name="fair_acc_cmp_40b",
            compare_group=f"MM_{n}x{n}_acc_only",
            rounding_mode="symmetric", acc_bits=40, pre_scale_bits=0
        ))

    for taps in fir_taps:
        rows.append(run_suite(
            fir_q15_eval, taps,
            exp_name="fair_acc_cmp_35b",
            compare_group=f"FIR_{taps}_acc_only",
            rounding_mode="symmetric", acc_bits=35, pre_scale_bits=0
        ))
        rows.append(run_suite(
            fir_q15_eval, taps,
            exp_name="fair_acc_cmp_40b",
            compare_group=f"FIR_{taps}_acc_only",
            rounding_mode="symmetric", acc_bits=40, pre_scale_bits=0
        ))

    for img_hw, ker_hw, cin in test_convs:
        tag = f"CONV_{img_hw[0]}x{img_hw[1]}_K{ker_hw[0]}x{ker_hw[1]}_Cin{cin}_acc_only"
        rows.append(run_conv_suite(
            img_hw, ker_hw, cin,
            exp_name="fair_acc_cmp_35b",
            compare_group=tag,
            rounding_mode="symmetric", acc_bits=35, pre_scale_bits=0
        ))
        rows.append(run_conv_suite(
            img_hw, ker_hw, cin,
            exp_name="fair_acc_cmp_40b",
            compare_group=tag,
            rounding_mode="symmetric", acc_bits=40, pre_scale_bits=0
        ))

    # =====================================================
    # Group B: fair pre-scale comparison
    # fixed acc_bits = 40, fixed rounding = symmetric
    # =====================================================
    for n in mm_sizes:
        rows.append(run_suite(
            mm_q15_eval, n,
            exp_name="prescale_cmp_ps0",
            compare_group=f"MM_{n}x{n}_prescale_only",
            rounding_mode="symmetric", acc_bits=40, pre_scale_bits=0
        ))
        rows.append(run_suite(
            mm_q15_eval, n,
            exp_name="prescale_cmp_ps1",
            compare_group=f"MM_{n}x{n}_prescale_only",
            rounding_mode="symmetric", acc_bits=40, pre_scale_bits=1
        ))

    for taps in fir_taps:
        rows.append(run_suite(
            fir_q15_eval, taps,
            exp_name="prescale_cmp_ps0",
            compare_group=f"FIR_{taps}_prescale_only",
            rounding_mode="symmetric", acc_bits=40, pre_scale_bits=0
        ))
        rows.append(run_suite(
            fir_q15_eval, taps,
            exp_name="prescale_cmp_ps1",
            compare_group=f"FIR_{taps}_prescale_only",
            rounding_mode="symmetric", acc_bits=40, pre_scale_bits=1
        ))

    for img_hw, ker_hw, cin in test_convs:
        tag = f"CONV_{img_hw[0]}x{img_hw[1]}_K{ker_hw[0]}x{ker_hw[1]}_Cin{cin}_prescale_only"
        rows.append(run_conv_suite(
            img_hw, ker_hw, cin,
            exp_name="prescale_cmp_ps0",
            compare_group=tag,
            rounding_mode="symmetric", acc_bits=40, pre_scale_bits=0
        ))
        rows.append(run_conv_suite(
            img_hw, ker_hw, cin,
            exp_name="prescale_cmp_ps1",
            compare_group=tag,
            rounding_mode="symmetric", acc_bits=40, pre_scale_bits=1
        ))

    # =====================================================
    # Group C: optional rounding comparison
    # fixed acc_bits = 35, fixed pre_scale = 0
    # =====================================================
    for n in mm_sizes:
        rows.append(run_suite(
            mm_q15_eval, n,
            exp_name="rounding_cmp_rtl_bias",
            compare_group=f"MM_{n}x{n}_rounding_only",
            rounding_mode="rtl_bias", acc_bits=35, pre_scale_bits=0
        ))
        rows.append(run_suite(
            mm_q15_eval, n,
            exp_name="rounding_cmp_symmetric",
            compare_group=f"MM_{n}x{n}_rounding_only",
            rounding_mode="symmetric", acc_bits=35, pre_scale_bits=0
        ))

    for taps in fir_taps:
        rows.append(run_suite(
            fir_q15_eval, taps,
            exp_name="rounding_cmp_rtl_bias",
            compare_group=f"FIR_{taps}_rounding_only",
            rounding_mode="rtl_bias", acc_bits=35, pre_scale_bits=0
        ))
        rows.append(run_suite(
            fir_q15_eval, taps,
            exp_name="rounding_cmp_symmetric",
            compare_group=f"FIR_{taps}_rounding_only",
            rounding_mode="symmetric", acc_bits=35, pre_scale_bits=0
        ))

    for img_hw, ker_hw, cin in test_convs:
        tag = f"CONV_{img_hw[0]}x{img_hw[1]}_K{ker_hw[0]}x{ker_hw[1]}_Cin{cin}_rounding_only"
        rows.append(run_conv_suite(
            img_hw, ker_hw, cin,
            exp_name="rounding_cmp_rtl_bias",
            compare_group=tag,
            rounding_mode="rtl_bias", acc_bits=35, pre_scale_bits=0
        ))
        rows.append(run_conv_suite(
            img_hw, ker_hw, cin,
            exp_name="rounding_cmp_symmetric",
            compare_group=tag,
            rounding_mode="symmetric", acc_bits=35, pre_scale_bits=0
        ))

    save_csv(rows, "pe_scaling_report_fair_compare.csv")

    print("\n===== SUMMARY =====")
    for r in rows:
        print(r)

    print("\nSaved to pe_scaling_report_fair_compare.csv")


if __name__ == "__main__":
    main()
