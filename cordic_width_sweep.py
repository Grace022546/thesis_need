import math
import csv
import numpy as np


# =========================================================
# fixed-point helper
# =========================================================
def sign_extend(val, bits):
    mask = (1 << bits) - 1
    val &= mask
    if val & (1 << (bits - 1)):
        val -= (1 << bits)
    return val


def wrap_to_bits(val, bits):
    mask = (1 << bits) - 1
    val &= mask
    if val & (1 << (bits - 1)):
        val -= (1 << bits)
    return val


def sat_to_bits(val, bits):
    qmin = -(1 << (bits - 1))
    qmax = (1 << (bits - 1)) - 1
    return min(max(val, qmin), qmax)


def q15_to_float(x):
    return sign_extend(int(x), 16) / float(1 << 15)


def float_to_q15(x):
    raw = int(np.round(x * (1 << 15)))
    raw = sat_to_bits(raw, 16)
    return raw


def deg_to_theta_q15(deg):
    # 180 deg -> 32768
    return int(np.round(deg / 180.0 * 32768.0))


def theta_q15_to_rad(theta_q15):
    return sign_extend(theta_q15, 16) * math.pi / 32768.0


def rel_rmse(ref, est, eps=1e-12):
    ref = np.asarray(ref, dtype=np.float64)
    est = np.asarray(est, dtype=np.float64)
    num = np.sqrt(np.mean((ref - est) ** 2))
    den = np.sqrt(np.mean(ref ** 2)) + eps
    return float(num / den)


# =========================================================
# RTL-like CORDIC model
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

    def trunc_width(self, val, bits):
        return wrap_to_bits(val, bits)

    def arshift(self, val, sh, bits):
        val = self.trunc_width(val, bits)
        if sh <= 0:
            return val
        return self.trunc_width(val >> sh, bits)

    def run_rotation(self, theta_in):
        """
        input theta_in : signed integer in WIDTH_OUT bits
        return x_out, y_out, z_out : signed integer in WIDTH_OUT bits
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
            x, y, z = (
                self.trunc_width(xn, self.WIDTH),
                self.trunc_width(yn, self.WIDTH),
                self.trunc_width(zn, self.WIDTH),
            )

        # final gain compensation
        xo = self.trunc_width((x * 19899) >> 15, self.WIDTH_OUT)
        yo = self.trunc_width((y * 19899) >> 15, self.WIDTH_OUT)
        zo = self.trunc_width(z, self.WIDTH_OUT)
        return xo, yo, zo

    def run_vectoring(self, x_in, y_in):
        """
        input x_in/y_in : signed integer in WIDTH_OUT bits
        return x_out, y_out, z_out : signed integer in WIDTH_OUT bits
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

            x, y, z = (
                self.trunc_width(xn, self.WIDTH),
                self.trunc_width(yn, self.WIDTH),
                self.trunc_width(zn, self.WIDTH),
            )

        xo = self.trunc_width((x * 19899) >> 15, self.WIDTH_OUT)
        yo = self.trunc_width((y * 19899) >> 15, self.WIDTH_OUT)
        zo = self.trunc_width(z, self.WIDTH_OUT)
        return xo, yo, zo


# =========================================================
# rotation mode evaluation
# =========================================================
def eval_rotation_mode(model, num_angles=721):
    # 掃 -180 ~ 180 deg
    angles_deg = np.linspace(-179.5, 179.5, num_angles)

    ref_cos = []
    ref_sin = []
    est_cos = []
    est_sin = []
    est_ang_err = []

    max_abs_out = 0.0

    for deg in angles_deg:
        theta_q = deg_to_theta_q15(deg)
        xo, yo, zo = model.run_rotation(theta_q)

        xo_f = sign_extend(xo, model.WIDTH_OUT) / float(1 << 15)
        yo_f = sign_extend(yo, model.WIDTH_OUT) / float(1 << 15)

        ref_cos.append(math.cos(math.radians(deg)))
        ref_sin.append(math.sin(math.radians(deg)))
        est_cos.append(xo_f)
        est_sin.append(yo_f)

        # angle residual
        z_res_rad = theta_q15_to_rad(zo)
        est_ang_err.append(abs(z_res_rad))

        max_abs_out = max(max_abs_out, abs(xo_f), abs(yo_f))

    cos_err = rel_rmse(np.array(ref_cos), np.array(est_cos))
    sin_err = rel_rmse(np.array(ref_sin), np.array(est_sin))
    ang_resid = float(np.max(est_ang_err))

    return {
        "rot_cos_rmse": cos_err,
        "rot_sin_rmse": sin_err,
        "rot_ang_resid_max_rad": ang_resid,
        "rot_max_abs_out": max_abs_out,
    }


# =========================================================
# vectoring mode evaluation
# =========================================================
def eval_vectoring_mode(model, num_samples=5000, seed=42):
    rng = np.random.default_rng(seed)

    ref_mag = []
    est_mag = []
    ref_ang = []
    est_ang = []

    max_abs_out = 0.0
    overflow_in_cnt = 0

    for _ in range(num_samples):
        # 在 unit circle 附近測，也留一些偏大的點
        x = rng.uniform(-0.999, 0.999)
        y = rng.uniform(-0.999, 0.999)

        xin = float_to_q15(x)
        yin = float_to_q15(y)

        # 若你想測更大動態範圍，可把這裡改成更寬格式
        if xin == 32767 or xin == -32768 or yin == 32767 or yin == -32768:
            overflow_in_cnt += 1

        xo, yo, zo = model.run_vectoring(xin, yin)

        xo_f = sign_extend(xo, model.WIDTH_OUT) / float(1 << 15)
        zo_i = sign_extend(zo, model.WIDTH_OUT)

        ref_mag.append(math.sqrt(x * x + y * y))
        est_mag.append(abs(xo_f))

        ref_ang_val = math.atan2(y, x)
        est_ang_val = theta_q15_to_rad(zo_i)

        # wrap 到 [-pi, pi]
        diff = est_ang_val - ref_ang_val
        while diff > math.pi:
            diff -= 2 * math.pi
        while diff < -math.pi:
            diff += 2 * math.pi

        ref_ang.append(0.0)
        est_ang.append(diff)

        max_abs_out = max(max_abs_out, abs(xo_f))

    mag_err = rel_rmse(np.array(ref_mag), np.array(est_mag))
    ang_rmse = float(np.sqrt(np.mean(np.array(est_ang) ** 2)))
    ang_max = float(np.max(np.abs(np.array(est_ang))))

    return {
        "vec_mag_rmse": mag_err,
        "vec_ang_rmse_rad": ang_rmse,
        "vec_ang_max_rad": ang_max,
        "vec_max_abs_out": max_abs_out,
        "input_sat_cnt": overflow_in_cnt,
    }


# =========================================================
# sweep
# =========================================================
def evaluate_one(width, width_out, iter_n=15):
    model = RTL_CORDIC_Model(width=width, width_out=width_out, iter_n=iter_n)

    rot = eval_rotation_mode(model, num_angles=721)
    vec = eval_vectoring_mode(model, num_samples=5000, seed=42)

    out = {
        "WIDTH": width,
        "WIDTH_OUT": width_out,
        "ITER": iter_n,
    }
    out.update(rot)
    out.update(vec)

    # 簡單 pass criteria，可自己改
    out["PASS"] = (
        out["rot_cos_rmse"] <= 0.01 and
        out["rot_sin_rmse"] <= 0.01 and
        out["vec_mag_rmse"] <= 0.01 and
        out["vec_ang_rmse_rad"] <= 0.02
    )
    return out


def main():
    settings = [
        (18, 16),
        (18, 18),
        (20, 16),
        (20, 18),
        (20, 20),
    ]

    results = []
    for w, wo in settings:
        results.append(evaluate_one(w, wo, iter_n=15))

    print(
        "{:>6} {:>10} {:>8} {:>12} {:>12} {:>14} {:>12} {:>14} {:>14} {:>10} {:>6}".format(
            "W", "W_OUT", "ITER",
            "ROT_COS", "ROT_SIN", "ROT_ANG_MAX",
            "VEC_MAG", "VEC_ANG_RMSE", "VEC_ANG_MAX",
            "MAX_OUT", "PASS"
        )
    )

    for r in results:
        print(
            "{:>6} {:>10} {:>8} {:>12.6f} {:>12.6f} {:>14.6f} {:>12.6f} {:>14.6f} {:>14.6f} {:>10.6f} {:>6}".format(
                r["WIDTH"], r["WIDTH_OUT"], r["ITER"],
                r["rot_cos_rmse"], r["rot_sin_rmse"], r["rot_ang_resid_max_rad"],
                r["vec_mag_rmse"], r["vec_ang_rmse_rad"], r["vec_ang_max_rad"],
                max(r["rot_max_abs_out"], r["vec_max_abs_out"]),
                str(r["PASS"])
            )
        )

    with open("cordic_width_sweep.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    print("\n=== RECOMMENDED ===")
    passed = [r for r in results if r["PASS"]]
    if not passed:
        print("No config passed. Try WIDTH_OUT >= 18 or WIDTH >= 20.")
    else:
        passed = sorted(
            passed,
            key=lambda r: (
                r["WIDTH"],
                r["WIDTH_OUT"],
                r["rot_cos_rmse"] + r["rot_sin_rmse"] + r["vec_mag_rmse"] + r["vec_ang_rmse_rad"]
            )
        )
        for r in passed:
            print(r)


if __name__ == "__main__":
    main()
