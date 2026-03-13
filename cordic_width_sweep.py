
import math
import csv
import numpy as np
import pandas as pd
from dataclasses import dataclass

def wrap_to_bits(val, bits):
    mask = (1 << bits) - 1
    val &= mask
    if val & (1 << (bits - 1)):
        val -= (1 << bits)
    return val

def sat_to_bits(val, bits):
    qmin = -(1 << (bits - 1))
    qmax = (1 << (bits - 1)) - 1
    return min(max(int(val), qmin), qmax)

def q_to_float(x, frac_bits, bits):
    return wrap_to_bits(int(x), bits) / float(1 << frac_bits)

def float_to_q(x, frac_bits, bits):
    raw = int(np.round(x * (1 << frac_bits)))
    return sat_to_bits(raw, bits)

def deg_to_theta_q15(deg):
    return wrap_to_bits(int(np.round(deg / 180.0 * 32768.0)), 16)

def theta_q15_to_rad(theta_q15):
    return wrap_to_bits(theta_q15, 16) * math.pi / 32768.0

def wrap_pm_pi(x):
    while x > math.pi:
        x -= 2 * math.pi
    while x < -math.pi:
        x += 2 * math.pi
    return x

def rmse(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    return float(np.sqrt(np.mean((a - b) ** 2)))

def snr_db(ref, est, eps=1e-30):
    ref = np.asarray(ref, dtype=float)
    est = np.asarray(est, dtype=float)
    sig = np.mean(ref ** 2)
    err = np.mean((ref - est) ** 2)
    return float(10 * np.log10((sig + eps) / (err + eps)))

@dataclass
class CordicCfg:
    width: int
    width_out: int
    iter_n: int = 15
    xy_frac_in: int = 15
    xy_frac_int: int = 18

class CordicRTLModel:
    def __init__(self, cfg: CordicCfg):
        self.cfg = cfg
        self.W = cfg.width
        self.WO = cfg.width_out
        self.I = cfg.iter_n
        self.XY_SHIFT = cfg.xy_frac_int - cfg.xy_frac_in
        self.Z_SHIFT = cfg.width - cfg.width_out
        self.K_INV_Q15 = 19899
        base = [8192, 4836, 2555, 1297, 651, 326, 163, 81, 41, 20, 10, 5, 3, 1, 1]
        self.atan = [wrap_to_bits(v << self.Z_SHIFT, self.W) for v in base[:self.I]]

    def tw(self, v):
        return wrap_to_bits(v, self.W)

    def two(self, v):
        return wrap_to_bits(v, self.WO)

    def a_shr(self, v, sh):
        v = self.tw(v)
        return self.tw(v >> sh) if sh > 0 else v

    def round_shift_xy(self, din, sh):
        if sh == 0:
            return din
        bias = 1 << (sh - 1)
        if din < 0:
            bias = -bias
        return (din + bias) >> sh

    def round_shift_z(self, din, sh):
        if sh == 0:
            return din
        bias = 1 << (sh - 1)
        if din < 0:
            bias = -bias
        return (din + bias) >> sh

    def run_rotation(self, theta_in, x_in=None, y_in=None):
        if x_in is None:
            x_in = (1 << 15) - 1
        if y_in is None:
            y_in = 0

        theta = self.two(theta_in)
        x0 = self.two(x_in)
        y0 = self.two(y_in)

        if theta > 16384:
            x = -(x0 << self.XY_SHIFT)
            y = -(y0 << self.XY_SHIFT)
            z = (theta << self.Z_SHIFT) - (32768 << self.Z_SHIFT)
        elif theta < -16384:
            x = -(x0 << self.XY_SHIFT)
            y = -(y0 << self.XY_SHIFT)
            z = (theta << self.Z_SHIFT) + (32768 << self.Z_SHIFT)
        else:
            x = x0 << self.XY_SHIFT
            y = y0 << self.XY_SHIFT
            z = theta << self.Z_SHIFT

        x, y, z = self.tw(x), self.tw(y), self.tw(z)

        for i in range(self.I):
            if z < 0:
                xn = x + self.a_shr(y, i)
                yn = y - self.a_shr(x, i)
                zn = z + self.atan[i]
            else:
                xn = x - self.a_shr(y, i)
                yn = y + self.a_shr(x, i)
                zn = z - self.atan[i]
            x, y, z = self.tw(xn), self.tw(yn), self.tw(zn)

        x_mul = x * self.K_INV_Q15
        y_mul = y * self.K_INV_Q15
        x_rnd = self.round_shift_xy(x_mul, self.cfg.xy_frac_int)
        y_rnd = self.round_shift_xy(y_mul, self.cfg.xy_frac_int)
        z_rnd = self.round_shift_z(z, self.Z_SHIFT)

        xo = sat_to_bits(x_rnd, self.WO)
        yo = sat_to_bits(y_rnd, self.WO)
        zo = sat_to_bits(z_rnd, self.WO)
        return xo, yo, zo

    def run_vectoring(self, x_in, y_in):
        x0 = self.two(x_in)
        y0 = self.two(y_in)

        if x0 < 0:
            x = -(x0 << self.XY_SHIFT)
            y = -(y0 << self.XY_SHIFT)
            z = (32768 << self.Z_SHIFT) if y0 > 0 else -(32768 << self.Z_SHIFT)
        else:
            x = x0 << self.XY_SHIFT
            y = y0 << self.XY_SHIFT
            z = 0

        x, y, z = self.tw(x), self.tw(y), self.tw(z)

        for i in range(self.I):
            if y >= 0:
                xn = x + self.a_shr(y, i)
                yn = y - self.a_shr(x, i)
                zn = z + self.atan[i]
            else:
                xn = x - self.a_shr(y, i)
                yn = y + self.a_shr(x, i)
                zn = z - self.atan[i]
            x, y, z = self.tw(xn), self.tw(yn), self.tw(zn)

        x_mul = x * self.K_INV_Q15
        y_mul = y * self.K_INV_Q15
        x_rnd = self.round_shift_xy(x_mul, self.cfg.xy_frac_int)
        y_rnd = self.round_shift_xy(y_mul, self.cfg.xy_frac_int)
        z_rnd = self.round_shift_z(z, self.Z_SHIFT)

        xo = sat_to_bits(x_rnd, self.WO)
        yo = sat_to_bits(y_rnd, self.WO)
        zo = sat_to_bits(z_rnd, self.WO)
        return xo, yo, zo

def eval_model(cfg, num_angles=721, num_vec=10000, seed=0):
    m = CordicRTLModel(cfg)

    xamp = ((1 << 15) - 1) / (1 << 15)
    angles_deg = np.linspace(-179.5, 179.5, num_angles)

    ref_cos, est_cos, ref_sin, est_sin = [], [], [], []
    cos_ulp, sin_ulp, z_resid_rad = [], [], []
    sat_rot_cnt = 0

    for deg in angles_deg:
        tq = deg_to_theta_q15(deg)
        xo, yo, zo = m.run_rotation(tq)

        xo_f = q_to_float(xo, 15, cfg.width_out)
        yo_f = q_to_float(yo, 15, cfg.width_out)

        rc = xamp * math.cos(math.radians(deg))
        rs = xamp * math.sin(math.radians(deg))

        rq_c = float_to_q(rc, 15, cfg.width_out)
        rq_s = float_to_q(rs, 15, cfg.width_out)

        ref_cos.append(rc)
        est_cos.append(xo_f)
        ref_sin.append(rs)
        est_sin.append(yo_f)

        cos_ulp.append(abs(int(xo) - int(rq_c)))
        sin_ulp.append(abs(int(yo) - int(rq_s)))
        z_resid_rad.append(abs(theta_q15_to_rad(zo)))

        if abs(rq_c) == (1 << (cfg.width_out - 1)) - 1 or abs(rq_s) == (1 << (cfg.width_out - 1)) - 1:
            sat_rot_cnt += 1

    rng = np.random.default_rng(seed)
    ref_mag, est_mag, mag_ulp = [], [], []
    ref_ang, est_ang, yo_res = [], [], []
    sat_vec_cnt = 0

    for _ in range(num_vec):
        r = math.sqrt(rng.uniform(0, 0.999 ** 2))
        phi = rng.uniform(-math.pi, math.pi)
        x = r * math.cos(phi)
        y = r * math.sin(phi)

        xin = float_to_q(x, 15, cfg.width_out)
        yin = float_to_q(y, 15, cfg.width_out)

        xo, yo, zo = m.run_vectoring(xin, yin)

        xo_f = q_to_float(xo, 15, cfg.width_out)
        mag = math.hypot(x, y)
        mag_ref_q = float_to_q(mag, 15, cfg.width_out)

        ref_mag.append(mag)
        est_mag.append(abs(xo_f))
        mag_ulp.append(abs(int(xo) - int(mag_ref_q)))

        ang_ref = math.atan2(y, x)
        ang_est = theta_q15_to_rad(zo)
        d = wrap_pm_pi(ang_est - ang_ref)

        ref_ang.append(0.0)
        est_ang.append(d)
        yo_res.append(abs(q_to_float(yo, 15, cfg.width_out)))

        if abs(mag_ref_q) == (1 << (cfg.width_out - 1)) - 1:
            sat_vec_cnt += 1

    return {
        "WIDTH": cfg.width,
        "WIDTH_OUT": cfg.width_out,
        "ITER": cfg.iter_n,
        "XY_FRAC_INT": cfg.xy_frac_int,
        "rot_cos_rmse": rmse(ref_cos, est_cos),
        "rot_cos_snr_db": snr_db(ref_cos, est_cos),
        "rot_cos_ulp_mean": float(np.mean(cos_ulp)),
        "rot_cos_ulp_max": int(np.max(cos_ulp)),
        "rot_sin_rmse": rmse(ref_sin, est_sin),
        "rot_sin_snr_db": snr_db(ref_sin, est_sin),
        "rot_sin_ulp_mean": float(np.mean(sin_ulp)),
        "rot_sin_ulp_max": int(np.max(sin_ulp)),
        "rot_z_resid_max_rad": float(np.max(z_resid_rad)),
        "vec_mag_rmse": rmse(ref_mag, est_mag),
        "vec_mag_snr_db": snr_db(ref_mag, est_mag),
        "vec_mag_ulp_mean": float(np.mean(mag_ulp)),
        "vec_mag_ulp_max": int(np.max(mag_ulp)),
        "vec_ang_rmse_rad": rmse(ref_ang, est_ang),
        "vec_ang_max_rad": float(np.max(np.abs(est_ang))),
        "vec_y_resid_mean": float(np.mean(yo_res)),
        "vec_y_resid_max": float(np.max(yo_res)),
        "rot_ref_sat_cnt": sat_rot_cnt,
        "vec_ref_sat_cnt": sat_vec_cnt,
    }

def main():
    configs = [
        CordicCfg(18, 16, 15, 15, 16),
        CordicCfg(20, 16, 15, 15, 17),
        CordicCfg(22, 16, 15, 15, 17),
        CordicCfg(24, 16, 15, 15, 18),
        CordicCfg(26, 16, 15, 15, 18),
        CordicCfg(26, 18, 15, 15, 18),
    ]
    results = [eval_model(c) for c in configs]
    df = pd.DataFrame(results)
    print(df.to_string(index=False))
    df.to_csv("cordic_error_sweep.csv", index=False)

if __name__ == "__main__":
    main()
