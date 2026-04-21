# Lowering Table

## 1. Purpose
This document defines how cluster-level macro operations are lowered into local PE ISA dispatch streams.

---

## 2. Dispatch Rule

A lowered local instruction is always wrapped as:

`DispatchPacket = {cluster_id, pe_mask, local_inst}`

Where:
- `cluster_id` = target cluster
- `pe_mask` = active PE mask
- `local_inst` = 24-bit local instruction

---

## 3. Macro-op to Local-op Mapping

| Cluster IR op | Condition | Lowered Local PE Ops | Notes |
|---|---|---|---|
| `CLUSTER_FFT8` | `stage_count = 1` | `FFT_STEP(stage0)` | one radix-stage group |
| `CLUSTER_FFT8` | `stage_count = 2` | `FFT_STEP(stage0), FFT_STEP(stage1)` | two-stage grouped FFT |
| `CLUSTER_FFT8` | `stage_count = 3` | `FFT_STEP(stage0), FFT_STEP(stage1), FFT_STEP(stage2)` | full local FFT8 group |
| `CLUSTER_MM4X8_K8` | `first_k = 1, last_k = 0` | `ACC_CLR, MM_MAC` | initialize psum |
| `CLUSTER_MM4X8_K8` | `first_k = 0, last_k = 0` | `MM_MAC` | middle accumulation step |
| `CLUSTER_MM4X8_K8` | `first_k = 0, last_k = 1` | `MM_MAC, OUT_COMMIT` | final psum commit |
| `CLUSTER_MM4X8_K8` | `first_k = 1, last_k = 1` | `ACC_CLR, MM_MAC, OUT_COMMIT` | single-k reduced case |
| `CLUSTER_FIR8_4OUT` | `words_out = 0` | `FIR_MAC` | non-final tap chunk |
| `CLUSTER_FIR8_4OUT` | `words_out > 0` | `FIR_MAC, FIR_REDUCE, OUT_COMMIT` | final tap chunk |
| `QR_VEC` | always | `QR_VEC` | vectoring stage |
| `QR_ROT` | angle ready | `QR_ROT` | rotation stage |
| `BROADCAST_SM_TO_PE` | cluster-local | `SEND_BCAST, RECV_BCAST` | one sender, masked receivers |
| `EXCHANGE_LOCAL` | cluster-local | `SEND_P2P, RECV_P2P` | chained local handoff |

---

## 4. Lowering Details by Workload

### 4.1 FFT
Outer op:
- `CLUSTER_FFT8`

Lowering:
- generate `stage_count` dispatch packets
- each packet contains one `FFT_STEP`
- `imm = stage index`
- `dst = RF0`
- `src0 = RF0`
- `src1 = RF1`
- `res = FFT_PATH`

---

### 4.2 MM
Outer op:
- `CLUSTER_MM4X8_K8`

Lowering:
- if `first_k`, emit `ACC_CLR`
- emit `MM_MAC`
- if `last_k`, emit `OUT_COMMIT`

Resource binding:
- `ACC_CLR` -> `ALU_MAC`
- `MM_MAC` -> `MM_FIR_PATH`
- `OUT_COMMIT` -> `OUT_BCAST`

---

### 4.3 FIR
Outer op:
- `CLUSTER_FIR8_4OUT`

Lowering:
- always emit `FIR_MAC`
- if final chunk (`words_out > 0`), emit `FIR_REDUCE`
- then emit `OUT_COMMIT`

Resource binding:
- `FIR_MAC` -> `MM_FIR_PATH`
- `FIR_REDUCE` -> `MM_FIR_PATH`
- `OUT_COMMIT` -> `OUT_BCAST`

---

### 4.4 QR
Outer ops:
- `QR_VEC`
- `QR_ROT`

Lowering:
- `QR_VEC` -> one `QR_VEC`
- `QR_ROT` -> one `QR_ROT`

Resource binding:
- both use `CORDIC_PATH`

---

### 4.5 Broadcast
Outer op:
- `BROADCAST_SM_TO_PE`

Lowering:
- emit one `SEND_BCAST` from PE0
- emit one masked `RECV_BCAST` packet for active PEs

---

### 4.6 Local Exchange
Outer op:
- `EXCHANGE_LOCAL`

Lowering:
- build P2P chain across active PEs
- each edge emits:
  - `SEND_P2P`
  - `RECV_P2P`

Example for 4 PEs:
- `PE0 -> PE1`
- `PE1 -> PE2`
- `PE2 -> PE3`

---

## 5. Not Yet Fully Lowered

These operations are still modeled at a higher abstraction level:
- `MOVE_SM_TO_PE`
- `EXCHANGE_RING`
- parts of higher-level QR orchestration such as `CLUSTER_QR_ROWPAIR`

---

## 6. Output of Lowering
The output of lowering is:
1. a sequence of `DispatchPacket`
2. each packet contains:
   - target cluster
   - target PE mask
   - encoded 24-bit local instruction

This lowered sequence is the golden reference for:
- simulator execution
- RTL dispatch interface
- local PE testbench input
