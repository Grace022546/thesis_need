
---

# 一、設計亮點 (Design Highlights)

## 1 26-bit Internal Datapath 提升精度

本設計將 CORDIC 的內部資料路徑由傳統 16-bit 擴展至 **26-bit fixed-point**，以降低迭代過程中的量化誤差。

優點：

* 減少 **rounding error**
* 降低 **truncation error**
* 提升 rotation / vectoring 計算精度

經 Python 模擬結果：

| metric                | value     |
| --------------------- | --------- |
| Rotation RMSE         | ~8×10⁻⁵   |
| Vector magnitude RMSE | ~2.7×10⁻⁵ |
| Magnitude SNR         | ~88 dB    |
| Mean ULP error        | <1        |

說明內部寬度足以支撐 **16-bit output precision**。

---

## 2 Integer Headroom 保護數值範圍

本設計並未將所有新增位元用於 fractional precision，而是保留 **integer headroom**：

```
input  Q1.15
internal ≈ Q7.18
```

目的：

* 避免 CORDIC 迭代過程中的 **intermediate overflow**
* 支援 vectoring mode 中 magnitude growth

這比單純增加 fractional bits 更穩定。

---

## 3 Symmetric Rounding 減少偏差

一般 CORDIC 實作常使用：

```
+ 0.5 LSB
```

這對 **負數會產生 bias**。

本設計採用：

```
positive : +0.5 LSB
negative : −0.5 LSB
```

即 **symmetric rounding**

優點：

* 減少 fixed-point bias
* 降低 angle / magnitude estimation error

---

## 4 Saturation 防止 Overflow

最終輸出採用 **saturation arithmetic**：

```
> +32767 → clamp to +32767
< -32768 → clamp to -32768
```

避免：

* wrap-around overflow
* 符號翻轉

這在 fixed-point DSP 系統中非常重要。

---

## 5 完整 Pipeline 設計

CORDIC pipeline 分為：

| Stage  | Function                   |
| ------ | -------------------------- |
| 0      | quadrant preprocessing     |
| 1–ITER | CORDIC microrotation       |
| ITER   | gain compensation multiply |
| ITER+1 | rounding                   |
| ITER+2 | saturation & output        |

總 latency：

```
ITER + 3 cycles
= 18 cycles
```

優點：

* 高 throughput
* timing friendly
* 適合 FPGA / ASIC pipeline

---

## 6 Rotation / Vectoring Unified Datapath

設計使用同一 datapath 支援：

```
state = 010 → rotation mode
state = 011 → vectoring mode
```

差異僅在 direction control：

Rotation

```
sign(z)
```

Vectoring

```
sign(y)
```

優點：

* hardware reuse
* area efficient

---

## 7 Python Bit-Accurate Model 驗證

建立 **RTL-like Python model**：

特性：

* sign-extend
* fixed-point wrap
* CORDIC iteration
* gain compensation
* identical atan table

並進行 sweep：

```
WIDTH ∈ {18,20,22,24,26}
WIDTH_OUT ∈ {16,18}
ITER = 15
```

評估：

* RMSE
* SNR
* ULP error

確保 RTL 設計具備可預測數值精度。

---

# 二、設計考量 (Design Considerations)

## 1 Internal Width vs Hardware Cost

增加 datapath width 可提升精度，但也會增加：

* area
* power
* routing complexity

模擬結果顯示：

```
WIDTH ≥ 24
```

即可滿足 16-bit output precision。

因此：

| width | 評價   |
| ----- | ---- |
| 20    | 可用   |
| 24    | 建議   |
| 26    | 保守設計 |

---

## 2 Iteration Count

CORDIC accuracy roughly follows：

```
error ≈ 2^(-ITER)
```

ITER=15 對應：

```
~3×10⁻⁵ rad
```

符合 Q1.15 precision。

減少 iteration 雖可降低 latency，但會增加 angle error。

---

## 3 Fixed-Point Scaling

輸入採用：

```
Q1.15
```

角度採用：

```
180° = 32768
```

內部 scaling 需注意：

* CORDIC gain
* shift precision
* angle wrap

---

## 4 CORDIC Gain Compensation

CORDIC iteration 會產生 gain：

```
K ≈ 0.607252
```

本設計使用：

```
K⁻¹ ≈ 19899 / 2¹⁵
```

於 pipeline stage 進行補償。

---

## 5 Pipeline Latency vs Throughput

增加 pipeline stage：

優點

* 提高 clock frequency
* 減少 critical path

缺點

* latency 增加

本設計選擇：

```
ITER + 3 pipeline stages
```

以優化 timing。

---

# 三、整體設計結論

本設計提出一個 **26-bit internal fixed-point CORDIC architecture**，具有：

* integer headroom 保護
* symmetric rounding
* saturation arithmetic
* unified rotation/vectoring datapath
* pipeline friendly implementation

Python bit-accurate simulation 顯示：

```
Magnitude SNR ≈ 88 dB
Mean ULP < 1
RMSE ≈ 10⁻⁵
```

證明此設計能在 **16-bit output precision** 下維持高精度與穩定數值特性。

---

<img width="1536" height="1024" alt="38e03ced-4659-4aed-9b34-c07fdd9370a6" src="https://github.com/user-attachments/assets/a8286841-d7e4-4857-8b31-1c08b28cdf84" />
<img width="1536" height="1024" alt="ChatGPT Image Mar 13, 2026, 11_51_42 AM" src="https://github.com/user-attachments/assets/31f5a243-f337-4255-bb30-8c053e429aa0" />
<img width="1536" height="1024" alt="ChatGPT Image Mar 13, 2026, 11_51_37 AM" src="https://github.com/user-attachments/assets/736acbc1-60e6-4b34-94be-f170266cf3cb" />

