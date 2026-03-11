已開始執行
Initializing environment
Installing packages
Running code
SyntaxError: invalid syntax (<exec>, line 473)

import os
import math
import csv
import zipfile
import numpy as np

# =========================================================
# unzip tv bundle
# =========================================================
zip_path = "/mnt/data/dsp_tv_bundle.zip"
extract_dir = "/mnt/data/dsp_tv_bundle"

if os.path.exists(zip_path) and not os.path.exists(extract_dir):
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_dir)

BASE = "/mnt/data/dsp_tv_bundle"

# 確保路徑存在，否則後續讀取會失敗
MM_A_FILE   = BASE + "/mm_tv/matA_q15.memh"
MM_B_FILE   = BASE + "/mm_tv/matB_q15.memh"
MM_CG_FILE  = BASE + "/mm_tv/matC_gold.memh"

# =========================================================
# helpers
# =========================================================
def sign_extend(val, bits):
    mask = (1 << bits) - 1
    val &= mask
    if val & (1 << (bits - 1)):
        val -= (1 << bits)
    return val

def rmse_rel(ref, est, eps=1e-12):
    ref = np.asarray(ref, dtype=np.float64)
    est = np.asarray(est, dtype=np.float64)
    num = np.sqrt(np.mean((ref - est) ** 2))
    den = np.sqrt(np.mean(ref ** 2)) + eps
    return float(num / den)

def abs_rel_err(ref, est, eps=1e-12):
    ref = np.asarray(ref, dtype=np.float64)
    est = np.asarray(est, dtype=np.float64)
    return float(np.linalg.norm(ref - est) / (np.linalg.norm(ref) + eps))

def read_hex_lines(filename):
    vals = []
    if not os.path.exists(filename):
        print(f"Warning: {filename} not found.")
        return []
    with open(filename, "r") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#") or s.startswith("//"):
                continue
            vals.append(int(s, 16))
    return vals

def read_memh_16_signed(filename, expected=None):
    vals = [sign_extend(v, 16) for v in read_hex_lines(filename)]
    if expected is not None and len(vals) != expected:
        raise ValueError("File {} loaded {}, expected {}".format(filename, len(vals), expected))
    return np.array(vals, dtype=np.int64)

def read_memh_32_signed(filename, expected=None):
    vals = [sign_extend(v, 32) for v in read_hex_lines(filename)]
    if expected is not None and len(vals) != expected:
        raise ValueError("File {} loaded {}, expected {}".format(filename, len(vals), expected))
    return np.array(vals, dtype=np.int64)

# =========================================================
# q format
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

# =========================================================
# MM real TV
# =========================================================
def load_mm_real_tv():
    A = read_memh_16_signed(MM_A_FILE, expected=64).reshape(8, 8)
    B = read_memh_16_signed(MM_B_FILE, expected=64).reshape(8, 8)
    Cg = read_memh_32_signed(MM_CG_FILE, expected=64).reshape(8, 8)
    return A, B, Cg

def eval_mm_real_tv(Ai, Bi, Cg, qspec):
    A = Ai.astype(np.float64) / (1 << 15)
    B = Bi.astype(np.float64) / (1 << 15)
    Cgold = Cg.astype(np.float64) / (1 << 15)

    C = np.zeros((8, 8), dtype=np.float64)
    ovf_cnt = 0
    max_abs = 0.0

    for i in range(8):
        for j in range(8):
            acc = 0.0
            for k in range(8):
                prod = A[i, k] * B[k, j]
                prod, ov1 = qspec.quantize(prod)
                ovf_cnt += int(ov1)

                acc += prod
                acc, ov2 = qspec.quantize(acc)
                ovf_cnt += int(ov2)

                max_abs = max(max_abs, abs(acc))
            C[i, j] = acc

    err = abs_rel_err(Cgold, C)
    return err, ovf_cnt, max_abs

# =========================================================
# FIR realistic
# =========================================================
def gen_fir_coeff_realistic(rng, taps, coeff_abs_sum_target=0.9):
    h = rng.uniform(-0.25, 0.25, taps).astype(np.float64)
    s = np.sum(np.abs(h))
    if s > 1e-12:
        h = h * (coeff_abs_sum_target / s)
    return h

def eval_fir_realistic(qspec, trials=12, lengths=(128, 256, 512), taps_list=(8, 16, 32, 64), seed=42):
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
                prod, ov1 = qspec.quantize(prod)
                ovf_cnt += int(ov1)

                acc += prod
                acc, ov2 = qspec.quantize(acc)
                ovf_cnt += int(ov2)

                max_abs = max(max_abs, abs(acc))
            y[i] = acc

        errs.append(rmse_rel(ref, y))

    return float(np.max(errs)), ovf_cnt, max_abs

# =========================================================
# CONV realistic
# =========================================================
def gen_conv_kernel_realistic(rng, kh, kw, coeff_abs_sum_target=0.9):
    k = rng.uniform(-0.2, 0.2, (kh, kw)).astype(np.float64)
    s = np.sum(np.abs(k))
    if s > 1e-12:
        k = k * (coeff_abs_sum_target / s)
    return k

def eval_conv_realistic(qspec, trials=8, img_shapes=((16,16),(32,32)), kernels=((3,3),(5,5)), seed=42):
    rng = np.random.default_rng(seed)
    errs = []
    ovf_cnt = 0
    max_abs = 0.0

    for _ in range(trials):
        H, W = img_shapes[int(rng.integers(0, len(img_shapes)))]
        KH, KW = kernels[int(rng.integers(0, len(kernels)))]
        img = rng.uniform(-0.8, 0.8, (H, W)).astype(np.float64)
        ker = gen_conv_kernel_realistic(rng, KH, KW)

        OH, OW = H - KH + 1, W - KW + 1
        ref = np.zeros((OH, OW), dtype=np.float64)
        out = np.zeros((OH, OW), dtype=np.float64)

        for i in range(OH):
            for j in range(OW):
                ref[i, j] = np.sum(img[i:i+KH, j:j+KW] * ker)
                acc = 0.0
                for ki in range(KH):
                    for kj in range(KW):
                        prod = img[i+ki, j+kj] * ker[ki, kj]
                        prod, ov1 = qspec.quantize(prod)
                        ovf_cnt += int(ov1)

                        acc += prod
                        acc, ov2 = qspec.quantize(acc)
                        ovf_cnt += int(ov2)

                        max_abs = max(max_abs, abs(acc))
                out[i, j] = acc

        errs.append(rmse_rel(ref, out))

    return float(np.max(errs)), ovf_cnt, max_abs

# =========================================================
# CORDIC standalone
# =========================================================
def theta_q15_to_rad(theta_q15):
    return sign_extend(theta_q15, 16) * math.pi / 32768.0

def deg_to_theta_q15(deg):
    return int(np.round(deg / 180.0 * 32768.0))

def float_to_q15(x):
    raw = int(np.round(x * (1 << 15)))
    raw = min(max(raw, -(1 << 15)), (1 << 15) - 1)
    return raw

class RTL_CORDIC_Model(object):
    def __init__(self, width=18, width_out=16, iter_n=15):
        self.WIDTH = width
        self.WIDTH_OUT = width_out
        self.ITER = iter_n
        self.atan_table = [8192,4836,2555,1297,651,326,163,81,41,20,10,5,3,1,1]
        self.K = 19899

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

    def run_vectoring(self, x_in, y_in):
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
            x, y, z = self.trunc_width(xn, self.WIDTH), self.trunc_width(yn, self.WIDTH), self.trunc_width(zn, self.WIDTH)

        xo = self.trunc_width((x * 19899) >> 15, self.WIDTH_OUT)
        yo = self.trunc_width((y * 19899) >> 15, self.WIDTH_OUT)
        zo = self.trunc_width(z, self.WIDTH_OUT)
        return xo, yo, zo

def eval_cordic_vectoring(width, width_out, iter_n=15, num_samples=3000, seed=42):
    rng = np.random.default_rng(seed)
    model = RTL_CORDIC_Model(width=width, width_out=width_out, iter_n=iter_n)

    ref_mag = []
    est_mag = []
    ang_errs = []

    max_abs = 0.0

    for _ in range(num_samples):
        x = rng.uniform(-0.999, 0.999)
        y = rng.uniform(-0.999, 0.999)

        xin = float_to_q15(x)
        yin = float_to_q15(y)

        xo, yo, zo = model.run_vectoring(xin, yin)

        xo_f = sign_extend(xo, width_out) / float(1 << 15)
        zo_f = theta_q15_to_rad(zo)

        ref_mag.append(math.sqrt(x*x + y*y))
        est_mag.append(abs(xo_f))

        ref_ang = math.atan2(y, x)
        diff = zo_f - ref_ang
        while diff > math.pi:
            diff -= 2 * math.pi
        while diff < -math.pi:
            diff += 2 * math.pi
        ang_errs.append(diff)

        max_abs = max(max_abs, abs(xo_f))

    # 修正此處的函數名稱從 rel_rmse 改為 rmse_rel
    return {
        "vec_mag_rmse": rmse_rel(np.array(ref_mag), np.array(est_mag)),
        "vec_ang_rmse": float(np.sqrt(np.mean(np.array(ang_errs) ** 2))),
        "vec_ang_max": float(np.max(np.abs(np.array(ang_errs)))),
        "vec_max_abs": max_abs,
    }

# =========================================================
# main sweep
# =========================================================
def pass_datapath(mm_err, fir_err, conv_err, ovf):
    return (not ovf) and (mm_err <= 0.02) and (fir_err <= 0.02) and (conv_err <= 0.02)

def pass_cordic(vec_mag_rmse, vec_ang_rmse):
    return (vec_mag_rmse <= 0.01) and (vec_ang_rmse <= 0.02)

def main():
    try:
        A_mm, B_mm, Cg_mm = load_mm_real_tv()
    except Exception as e:
        print(f"Error loading files: {e}")
        return

    datapath_results = []
    cordic_results = []

    # Part A: shared datapath q-format
    for tb in [16, 18, 20, 22]:
        for fb in [10, 12, 13, 14, 15]:
            if fb >= tb:
                continue
            q = QSpec(tb, fb)

            mm_err, mm_ovf, mm_max = eval_mm_real_tv(A_mm, B_mm, Cg_mm, q)
            fir_err, fir_ovf, fir_max = eval_fir_realistic(q, trials=12)
            conv_err, conv_ovf, conv_max = eval_conv_realistic(q, trials=8)

            ovf_cnt = mm_ovf + fir_ovf + conv_ovf
            ovf = ovf_cnt > 0
            max_int = max(mm_max, fir_max, conv_max)

            datapath_results.append({
                "TB": tb, "FB": fb, "IB": tb - fb, "OVF": ovf,
                "OVF_CNT": ovf_cnt, "MAX_INT": max_int, "MM": mm_err,
                "FIR": fir_err, "CONV": conv_err,
                "PASS": pass_datapath(mm_err, fir_err, conv_err, ovf)
            })

    # Part B: CORDIC width sweep
    for w, wo in [(18,16), (18,18), (20,16), (20,18), (20,20)]:
        r = eval_cordic_vectoring(w, wo, iter_n=15, num_samples=3000)
        cordic_results.append({
            "WIDTH": w, "WIDTH_OUT": wo, "ITER": 15,
            "VEC_MAG_RMSE": r["vec_mag_rmse"], "VEC_ANG_RMSE": r["vec_ang_rmse"],
            "VEC_ANG_MAX": r["vec_ang_max"], "MAX_OUT": r["vec_max_abs"],
            "PASS": pass_cordic(r["vec_mag_rmse"], r["vec_ang_rmse"])
        })

    # Print results
    print("\n=== DATAPATH QFORMAT SWEEP ===")
    for r in datapath_results:
        print(r)

    print("\n=== CORDIC SWEEP ===")
    for r in cordic_results:
        print(r)

if __name__ == "__main__":
    main()幫我執行這段程式
