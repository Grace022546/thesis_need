import os
import math
import glob
import csv
import numpy as np
import zipfile
import os

zip_path = "/mnt/data/dsp_tv_bundle.zip"
extract_dir = "/mnt/data/dsp_tv_bundle"

if not os.path.exists(extract_dir):
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(extract_dir)

BASE = "/mnt/data/dsp_tv_bundle"

MM_A_FILE   = BASE + "/mm_tv/matA_q15.memh"
MM_B_FILE   = BASE + "/mm_tv/matB_q15.memh"
MM_CG_FILE  = BASE + "/mm_tv/matC_gold.memh"

QR_IN_FILE     = BASE + "/pattern_8x8_qr/input_A.hex"
QR_GOLD_R_FILE = BASE + "/pattern_8x8_qr/golden_R.hex"
QR_GOLD_Q_FILE = BASE + "/pattern_8x8_qr/golden_Q.hex"

FFT_DIR = BASE + "/fft8_tv_dut"

# =========================================================
# 基本 fixed-point helper
# =========================================================
class QSpec(object):
    def __init__(self, total_bits, frac_bits):
        self.total_bits = total_bits
        self.frac_bits = frac_bits
        self.qmin = -(1 << (total_bits - 1))
        self.qmax = (1 << (total_bits - 1)) - 1
        self.scale = 1 << frac_bits

    def quantize(self, x):
        raw = int(np.round(x * self.scale))
        ovf = (raw < self.qmin) or (raw > self.qmax)
        raw = min(max(raw, self.qmin), self.qmax)
        return raw / float(self.scale), ovf

    def wrap_to_bits(self, raw_int):
        mask = (1 << self.total_bits) - 1
        raw_int &= mask
        if raw_int & (1 << (self.total_bits - 1)):
            raw_int -= (1 << self.total_bits)
        return raw_int

    def saturate_int(self, raw_int):
        return min(max(raw_int, self.qmin), self.qmax)

def sign_extend(val, from_bits):
    mask = (1 << from_bits) - 1
    val &= mask
    if val & (1 << (from_bits - 1)):
        val -= (1 << from_bits)
    return val

def q15_to_float(x):
    return float(sign_extend(x, 16)) / (1 << 15)

def float_to_q(value, frac_bits):
    return int(np.round(value * (1 << frac_bits)))

def abs_rel_err(ref, est, eps=1e-12):
    return float(np.linalg.norm(ref - est) / (np.linalg.norm(ref) + eps))

def rmse_rel(ref, est, eps=1e-12):
    num = np.sqrt(np.mean(np.abs(ref - est) ** 2))
    den = np.sqrt(np.mean(np.abs(ref) ** 2)) + eps
    return float(num / den)

# =========================================================
# 讀檔 helper
# =========================================================
def read_hex_lines(filename):
    vals = []
    with open(filename, "r") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            if s.startswith("#") or s.startswith("//"):
                continue
            vals.append(int(s, 16))
    return vals

def read_memh_16_signed(filename, expected=None):
    vals = read_hex_lines(filename)
    vals = [sign_extend(v, 16) for v in vals]
    if expected is not None and len(vals) != expected:
        raise ValueError("File {} loaded {}, expected {}".format(filename, len(vals), expected))
    return np.array(vals, dtype=np.int64)

def read_memh_32_signed(filename):
    vals = read_hex_lines(filename)
    vals = [sign_extend(v, 32) for v in vals]
    return np.array(vals, dtype=np.int64)

def load_mm_real_tv():
    A = read_memh_16_signed(MM_A_FILE, expected=64).reshape(8, 8)
    B = read_memh_16_signed(MM_B_FILE, expected=64).reshape(8, 8)
    Cg = read_memh_32_signed(MM_CG_FILE).reshape(8, 8)
    return A, B, Cg

def load_qr_real_tv():
    A = read_memh_16_signed(QR_IN_FILE, expected=64).reshape(8, 8)
    Rg = read_memh_16_signed(QR_GOLD_R_FILE, expected=64).reshape(8, 8)
    Qg = read_memh_16_signed(QR_GOLD_Q_FILE, expected=64).reshape(8, 8)
    return A, Rg, Qg

def load_fft_cases(limit_cases=None):
    in_files = sorted(glob.glob(os.path.join(FFT_DIR, "in_case*.memh")))
    cases = []
    for inf in in_files:
        base = os.path.basename(inf)
        idx = base.replace("in_case", "").replace(".memh", "")
        outf = os.path.join(FFT_DIR, "out_case{}.memh".format(idx))
        if not os.path.exists(outf):
            continue
        xin = read_memh_32_signed(inf)
        ygold = read_memh_32_signed(outf)
        cases.append((inf, outf, xin, ygold))
    if limit_cases is not None:
        cases = cases[:limit_cases]
    return cases

# =========================================================
# 你的 RTL CORDIC model
# state 3'b010 : rotation mode
# state 3'b011 : vectoring mode
# =========================================================
class RTL_CORDIC_Model(object):
    def __init__(self, width=18, width_out=16, iter_n=15):
        self.WIDTH = width
        self.WIDTH_OUT = width_out
        self.ITER = iter_n

        self.atan_table = [
            8192, 4836, 2555, 1297, 651,
            326, 163, 81, 41, 20,
            10, 5, 3, 1, 1
        ]
        self.K = 19899  # same as RTL
        self.qw = QSpec(width, 15)       # internal interpreted as Q?.15 angle/data style
        self.qw_out = QSpec(width_out, 15)

    def trunc_width(self, val, bits):
        mask = (1 << bits) - 1
        val &= mask
        if val & (1 << (bits - 1)):
            val -= (1 << bits)
        return val

    def arshift(self, val, sh, bits):
        val = self.trunc_width(val, bits)
        if sh <= 0:
            return val
        return self.trunc_width(val >> sh, bits)

    def run_rotation(self, theta_in):
        """
        RTL-like rotation mode
        input theta_in: signed int, WIDTH_OUT bits
        return x_out, y_out, z_out as signed ints of WIDTH_OUT bits
        """
        theta = self.trunc_width(theta_in, self.WIDTH_OUT)

        # stage0
        if theta > 16384:
            x = -self.K
            y = 0
            z = theta - 32768
        elif theta <= -16384:
            x = -self.K
            y = 0
            z = theta + 32768
        else:
            x = self.K
            y = 0
            z = theta

        x = self.trunc_width(x, self.WIDTH)
        y = self.trunc_width(y, self.WIDTH)
        z = self.trunc_width(z, self.WIDTH)

        for i in range(self.ITER):
            if z >= 0:
                xn = x - self.arshift(y, i, self.WIDTH)
                yn = y + self.arshift(x, i, self.WIDTH)
                zn = z - self.atan_table[i]
            else:
                xn = x + self.arshift(y, i, self.WIDTH)
                yn = y - self.arshift(x, i, self.WIDTH)
                zn = z + self.atan_table[i]
            x, y, z = map(lambda v: self.trunc_width(v, self.WIDTH), (xn, yn, zn))

        # final gain compensation
        xo = self.trunc_width((x * 19899) >> 15, self.WIDTH_OUT)
        yo = self.trunc_width((y * 19899) >> 15, self.WIDTH_OUT)
        zo = self.trunc_width(z, self.WIDTH_OUT)
        return xo, yo, zo

    def run_vectoring(self, x_in, y_in):
        """
        RTL-like vectoring mode
        input x_in/y_in: signed int WIDTH_OUT bits
        return x_out, y_out, z_out as signed ints WIDTH_OUT bits
        """
        x0 = self.trunc_width(x_in, self.WIDTH_OUT)
        y0 = self.trunc_width(y_in, self.WIDTH_OUT)

        if x0 < 0:
            x = -x0
            y = -y0
            z = 32768
        else:
            x = x0
            y = y0
            z = 0

        x = self.trunc_width(x, self.WIDTH)
        y = self.trunc_width(y, self.WIDTH)
        z = self.trunc_width(z, self.WIDTH)

        for i in range(self.ITER):
            if y < 0:
                xn = x - self.arshift(y, i, self.WIDTH)
                yn = y + self.arshift(x, i, self.WIDTH)
                zn = z - self.atan_table[i]
            else:
                xn = x + self.arshift(y, i, self.WIDTH)
                yn = y - self.arshift(x, i, self.WIDTH)
                zn = z + self.atan_table[i]
            x, y, z = map(lambda v: self.trunc_width(v, self.WIDTH), (xn, yn, zn))

        xo = self.trunc_width((x * 19899) >> 15, self.WIDTH_OUT)
        yo = self.trunc_width((y * 19899) >> 15, self.WIDTH_OUT)
        zo = self.trunc_width(z, self.WIDTH_OUT)
        return xo, yo, zo


# =========================================================
# FFT 8-point with real TV
# 這裡先做和 golden 檔比對的相對誤差
# 注意：若你要完全一比一 RTL FFT datapath，要再更細拆
# =========================================================
def eval_fft_real_tv(cases, qspec_data, limit_cases=None):
    errs = []
    max_abs = 0.0
    ovf_cnt = 0

    use_cases = cases if limit_cases is None else cases[:limit_cases]
    for _, _, xin32, ygold32 in use_cases:
        # 轉成 complex float
        x = []
        yg = []
        for v in xin32:
            re = sign_extend((int(v) >> 16) & 0xFFFF, 16) / float(1 << 15)
            im = sign_extend(int(v) & 0xFFFF, 16) / float(1 << 15)
            x.append(re + 1j * im)
        for v in ygold32:
            re = sign_extend((int(v) >> 16) & 0xFFFF, 16) / float(1 << 15)
            im = sign_extend(int(v) & 0xFFFF, 16) / float(1 << 15)
            yg.append(re + 1j * im)

        x = np.array(x, dtype=np.complex128)
        yg = np.array(yg, dtype=np.complex128)

        # system-level approximation: FFT + stage scaling
        y = np.fft.fft(x) / 8.0

        # quantize output to target qspec
        yr = []
        for vv in y:
            r, ov1 = qspec_data.quantize(np.real(vv))
            ii, ov2 = qspec_data.quantize(np.imag(vv))
            ovf_cnt += int(ov1) + int(ov2)
            yr.append(r + 1j * ii)
        yr = np.array(yr, dtype=np.complex128)

        errs.append(rmse_rel(yg, yr))
        max_abs = max(max_abs, float(np.max(np.abs(yr))))

    return float(np.max(errs)) if errs else 0.0, ovf_cnt, max_abs


# =========================================================
# MM real TV
# =========================================================
def eval_mm_real_tv(Ai, Bi, Cg, qspec_data):
    # Ai/Bi are int16 q15
    A = Ai.astype(np.float64) / (1 << 15)
    B = Bi.astype(np.float64) / (1 << 15)

    # golden in matC_gold.memh 看起來是 int32
    # 你 RTL mm_q15 是 q15_round_sat_from_q30(...,15)
    # 所以 golden 這裡先假設是 same scale output integer -> /2^15
    Cgold = Cg.astype(np.float64) / (1 << 15)

    C = np.zeros((8, 8), dtype=np.float64)
    ovf_cnt = 0
    max_abs = 0.0

    for i in range(8):
        for j in range(8):
            acc = 0.0
            for k in range(8):
                prod = A[i, k] * B[k, j]
                p, ovp = qspec_data.quantize(prod)
                ovf_cnt += int(ovp)
                acc += p
                acc, ova = qspec_data.quantize(acc)
                ovf_cnt += int(ova)
                max_abs = max(max_abs, abs(acc))
            C[i, j] = acc

    err = abs_rel_err(Cgold, C)
    return err, ovf_cnt, max_abs


# =========================================================
# QR real TV + RTL-like CORDIC vectoring
# 這裡不是完整模擬你的 global_top/PE/FSM
# 但把 vectoring CORDIC 合進消第一欄/逐步 Givens 的數值核心
# =========================================================
def eval_qr_real_tv(Ai, Rgold_i, qspec_data, cordic_model):
    A = Ai.astype(np.float64) / (1 << 15)
    Rgold = Rgold_i.astype(np.float64) / (1 << 15)

    R = A.copy()
    Q = np.eye(8, dtype=np.float64)

    ovf_cnt = 0
    max_abs = float(np.max(np.abs(R)))

    for col in range(8):
        for row in range(7, col, -1):
            x = R[col, col]
            y = R[row, col]

            # convert to WIDTH_OUT input format for RTL CORDIC
            xin_raw = int(np.round(x * (1 << 15)))
            yin_raw = int(np.round(y * (1 << 15)))

            # saturate to WIDTH_OUT signed range
            xin_raw = min(max(xin_raw, -(1 << (cordic_model.WIDTH_OUT - 1))),
                          (1 << (cordic_model.WIDTH_OUT - 1)) - 1)
            yin_raw = min(max(yin_raw, -(1 << (cordic_model.WIDTH_OUT - 1))),
                          (1 << (cordic_model.WIDTH_OUT - 1)) - 1)

            xo, yo, zo = cordic_model.run_vectoring(xin_raw, yin_raw)

            # c,s from angle output via RTL rotation mode
            co, so, _ = cordic_model.run_rotation(zo)

            c = sign_extend(co, cordic_model.WIDTH_OUT) / float(1 << 15)
            s = sign_extend(so, cordic_model.WIDTH_OUT) / float(1 << 15)

            # row update
            rc = R[col, :].copy()
            rr = R[row, :].copy()
            for k in range(8):
                nx = c * rc[k] - s * rr[k]
                ny = s * rc[k] + c * rr[k]

                nx, ov1 = qspec_data.quantize(nx)
                ny, ov2 = qspec_data.quantize(ny)
                ovf_cnt += int(ov1) + int(ov2)

                R[col, k] = nx
                R[row, k] = ny
                max_abs = max(max_abs, abs(nx), abs(ny))

            # Q update
            qc = Q[:, col].copy()
            qr = Q[:, row].copy()
            for k in range(8):
                nx = c * qc[k] - s * qr[k]
                ny = s * qc[k] + c * qr[k]
                nx, ov1 = qspec_data.quantize(nx)
                ny, ov2 = qspec_data.quantize(ny)
                ovf_cnt += int(ov1) + int(ov2)
                Q[k, col] = nx
                Q[k, row] = ny
                max_abs = max(max_abs, abs(nx), abs(ny))

    rec = abs_rel_err(Rgold, R)
    orth = float(np.linalg.norm(Q.T @ Q - np.eye(8), ord='fro'))
    return rec, orth, ovf_cnt, max_abs


# =========================================================
# FIR / CONV realistic range version
# 這裡先用你論文常見 normalized 範圍，但 kernel 範圍可調
# =========================================================
def gen_fir_coeff_realistic(rng, taps, coeff_abs_sum_target=0.9):
    h = rng.uniform(-0.25, 0.25, taps).astype(np.float64)
    s = np.sum(np.abs(h))
    if s > 1e-12:
        h = h * (coeff_abs_sum_target / s)
    return h

def eval_fir_realistic(qspec_data, trials=20, lengths=(128, 256, 512), taps_list=(8, 16, 32, 64), seed=42):
    rng = np.random.default_rng(seed)
    errs = []
    ovf_cnt = 0
    max_abs = 0.0

    for _ in range(trials):
        L = int(rng.choice(lengths))
        T = int(rng.choice(taps_list))
        x = rng.uniform(-0.8, 0.8, L).astype(np.float64)
        h = gen_fir_coeff_realistic(rng, T)

        ref = np.convolve(x, h, mode='full')[:L]
        y = np.zeros(L, dtype=np.float64)
        for i in range(L):
            acc = 0.0
            for k in range(T):
                if i - k < 0:
                    continue
                prod = x[i - k] * h[k]
                prod, ov1 = qspec_data.quantize(prod)
                ovf_cnt += int(ov1)
                acc += prod
                acc, ov2 = qspec_data.quantize(acc)
                ovf_cnt += int(ov2)
                max_abs = max(max_abs, abs(acc))
            y[i] = acc
        errs.append(rmse_rel(ref, y))

    return float(np.max(errs)), ovf_cnt, max_abs

def gen_conv_kernel_realistic(rng, kh, kw, coeff_abs_sum_target=0.9):
    k = rng.uniform(-0.2, 0.2, (kh, kw)).astype(np.float64)
    s = np.sum(np.abs(k))
    if s > 1e-12:
        k = k * (coeff_abs_sum_target / s)
    return k

def eval_conv_realistic(qspec_data, trials=12, img_shapes=((16,16),(32,32),(64,64)), kernels=((3,3),(5,5)), seed=42):
    rng = np.random.default_rng(seed)
    errs = []
    ovf_cnt = 0
    max_abs = 0.0

    for _ in range(trials):
        H, W = img_shapes[int(rng.integers(0, len(img_shapes)))]
        KH, KW = kernels[int(rng.integers(0, len(kernels)))]
        img = rng.uniform(-0.8, 0.8, (H, W)).astype(np.float64)
        ker = gen_conv_kernel_realistic(rng, KH, KW)

        OH, OW = H-KH+1, W-KW+1
        ref = np.zeros((OH, OW), dtype=np.float64)
        out = np.zeros((OH, OW), dtype=np.float64)

        for i in range(OH):
            for j in range(OW):
                ref[i, j] = np.sum(img[i:i+KH, j:j+KW] * ker)
                acc = 0.0
                for ki in range(KH):
                    for kj in range(KW):
                        prod = img[i+ki, j+kj] * ker[ki, kj]
                        prod, ov1 = qspec_data.quantize(prod)
                        ovf_cnt += int(ov1)
                        acc += prod
                        acc, ov2 = qspec_data.quantize(acc)
                        ovf_cnt += int(ov2)
                        max_abs = max(max_abs, abs(acc))
                out[i, j] = acc

        errs.append(rmse_rel(ref, out))

    return float(np.max(errs)), ovf_cnt, max_abs


# =========================================================
# 主 sweep
# =========================================================
def evaluate_config(total_bits, frac_bits, cordic_width, cordic_width_out,
                    fft_cases, mm_tv, qr_tv):
    qspec = QSpec(total_bits, frac_bits)
    cordic = RTL_CORDIC_Model(width=cordic_width, width_out=cordic_width_out, iter_n=15)

    # FFT
    fft_err, fft_ovf, fft_max = eval_fft_real_tv(fft_cases, qspec, limit_cases=20)

    # MM
    A_mm, B_mm, Cg_mm = mm_tv
    mm_err, mm_ovf, mm_max = eval_mm_real_tv(A_mm, B_mm, Cg_mm, qspec)

    # QR
    A_qr, Rg_qr, Qg_qr = qr_tv
    qr_rec, qr_orth, qr_ovf, qr_max = eval_qr_real_tv(A_qr, Rg_qr, qspec, cordic)

    # FIR
    fir_err, fir_ovf, fir_max = eval_fir_realistic(qspec, trials=20)

    # CONV
    conv_err, conv_ovf, conv_max = eval_conv_realistic(qspec, trials=12)

    ovf_cnt = fft_ovf + mm_ovf + qr_ovf + fir_ovf + conv_ovf
    overflow_any = ovf_cnt > 0
    max_internal = max(fft_max, mm_max, qr_max, fir_max, conv_max)

    return {
        "TB": total_bits,
        "FB": frac_bits,
        "IB": total_bits - frac_bits,
        "CORDIC_W": cordic_width,
        "CORDIC_WO": cordic_width_out,
        "OVF": overflow_any,
        "OVF_CNT": ovf_cnt,
        "MAX_INT": max_internal,
        "FFT": fft_err,
        "MM": mm_err,
        "QR_REC": qr_rec,
        "QR_ORTH": qr_orth,
        "FIR": fir_err,
        "CONV": conv_err,
    }


def passed_threshold(res):
    return (
        (not res["OVF"]) and
        (res["FFT"] <= 0.03) and
        (res["MM"] <= 0.02) and
        (res["QR_REC"] <= 0.03) and
        (res["QR_ORTH"] <= 0.03) and
        (res["FIR"] <= 0.02) and
        (res["CONV"] <= 0.02)
    )


def main():
    mm_tv = load_mm_real_tv()
    qr_tv = load_qr_real_tv()
    fft_cases = load_fft_cases(limit_cases=20)

    results = []

    # 你現在最在意的是 WIDTH=18 / WIDTH_OUT=16 夠不夠
    # 所以先把這幾組掃掉
    total_bits_list = [16, 18, 20, 22]
    frac_bits_list  = [12, 13, 14, 15]
    cordic_settings = [
        (18, 16),
        (18, 18),
        (20, 16),
        (20, 18),
    ]

    for cw, cwo in cordic_settings:
        for tb in total_bits_list:
            for fb in frac_bits_list:
                if fb >= tb:
                    continue
                res = evaluate_config(tb, fb, cw, cwo, fft_cases, mm_tv, qr_tv)
                res["PASS"] = passed_threshold(res)
                results.append(res)

    # print
    print("{:>4} {:>4} {:>4} {:>8} {:>9} {:>6} {:>8} {:>10} {:>10} {:>10} {:>10} {:>10} {:>10} {:>6}".format(
        "TB", "FB", "IB", "CORDIC_W", "CORDIC_WO", "OVF", "OVF_CNT",
        "FFT", "MM", "QR_REC", "QR_ORTH", "FIR", "CONV", "PASS"
    ))
    for r in results:
        print("{:>4} {:>4} {:>4} {:>8} {:>9} {:>6} {:>8} {:>10.5f} {:>10.5f} {:>10.5f} {:>10.5f} {:>10.5f} {:>10.5f} {:>6}".format(
            r["TB"], r["FB"], r["IB"], r["CORDIC_W"], r["CORDIC_WO"],
            str(r["OVF"]), r["OVF_CNT"], r["FFT"], r["MM"], r["QR_REC"],
            r["QR_ORTH"], r["FIR"], r["CONV"], str(r["PASS"])
        ))

    with open("real_tv_cordic_qformat_eval.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    passed = [r for r in results if r["PASS"]]
    passed = sorted(passed, key=lambda r: (
        r["TB"], -r["FB"], r["CORDIC_W"], r["CORDIC_WO"],
        r["FFT"] + r["MM"] + r["QR_REC"] + r["QR_ORTH"] + r["FIR"] + r["CONV"]
    ))

    print("\n=== RECOMMENDED ===")
    if not passed:
        print("No config passed. Try increasing TB or CORDIC widths.")
    else:
        for r in passed[:10]:
            print(r)

if __name__ == "__main__":
    main()
