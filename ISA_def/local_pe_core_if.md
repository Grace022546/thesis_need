# local_pe_core Interface Specification

## 1. Module Purpose
`local_pe_core` is the phase-1 RTL execution engine for one processing element (PE).

Its role is to:
- accept one 24-bit local instruction (`LocalPEInst24`)
- update PE-local architectural state
- execute PE-local arithmetic operations
- handle local input channels
- generate local commit output

This module is the RTL realization of the local PE ISA layer, not the outer cluster-level IR. The reference instruction format is `LocalPEInst24 = {fmt, op, en, dst, src0, src1, res, imm}` and the architectural state model currently includes `RF0`, `RF1`, `ACC`, local input channels, commit channel, and `busy`. :contentReference[oaicite:0]{index=0}

---

## 2. Top-Level Ports

### 2.1 Clock / Reset
| Port | Dir | Width | Description |
|---|---|---:|---|
| `clk` | input | 1 | System clock |
| `rst_n` | input | 1 | Active-low reset |

### 2.2 Instruction Input
| Port | Dir | Width | Description |
|---|---|---:|---|
| `inst_valid` | input | 1 | Local instruction valid |
| `inst_ready` | output | 1 | PE can accept a new instruction |
| `inst` | input | 24 | Encoded `LocalPEInst24` |

### 2.3 Local Input Channels
| Port | Dir | Width | Description |
|---|---|---:|---|
| `in_p2p_valid` | input | 1 | P2P input valid |
| `in_p2p_ready` | output | 1 | PE ready to accept P2P input |
| `in_p2p_data` | input | DATA_W | P2P input payload |
| `in_bcast_valid` | input | 1 | Broadcast input valid |
| `in_bcast_ready` | output | 1 | PE ready to accept broadcast input |
| `in_bcast_data` | input | DATA_W | Broadcast input payload |

### 2.4 Local Output Channels
| Port | Dir | Width | Description |
|---|---|---:|---|
| `out_commit_valid` | output | 1 | Commit/output valid |
| `out_commit_ready` | input | 1 | Downstream can accept commit data |
| `out_commit_data` | output | ACC_W or DATA_W | Commit payload |
| `send_p2p_valid` | output | 1 | P2P send valid |
| `send_p2p_ready` | input | 1 | P2P destination/fabric ready |
| `send_p2p_data` | output | DATA_W | P2P send payload |
| `send_p2p_dst` | output | PID_W | P2P destination PE ID |
| `send_bcast_valid` | output | 1 | Broadcast send valid |
| `send_bcast_ready` | input | 1 | Broadcast fabric ready |
| `send_bcast_data` | output | DATA_W | Broadcast payload |

### 2.5 Debug / Observation Ports
| Port | Dir | Width | Description |
|---|---|---:|---|
| `dbg_rf0` | output | DATA_W | Current RF0 value |
| `dbg_rf1` | output | DATA_W | Current RF1 value |
| `dbg_acc` | output | ACC_W | Current ACC value |
| `dbg_busy` | output | BUSY_W | Remaining busy cycles |
| `dbg_last_inst` | output | 24 | Last accepted instruction |

---

## 3. Parameter Recommendation
| Parameter | Suggested value | Description |
|---|---:|---|
| `DATA_W` | 16 or 32 | PE data-path width |
| `ACC_W` | 32 or wider | Accumulator width |
| `PID_W` | 2 | Enough for 4 PEs per cluster |
| `BUSY_W` | 5 | Enough to represent max local-op latency |

---

## 4. Architectural State
The PE maintains the following architectural state:
- `RF0`
- `RF1`
- `ACC`
- `busy`
- `last_inst`
- local input status for P2P
- local input status for broadcast
- local output/commit status

This matches the current software architectural model used in the simulator. :contentReference[oaicite:1]{index=1}

---

## 5. Phase-1 Supported Opcodes
Phase-1 RTL only implements the minimum arithmetic/commit subset needed to validate the local PE execution model.

### 5.1 Required opcodes
| Opcode | Function |
|---|---|
| `MOV` | Move `src0` to `dst` |
| `ACC_CLR` | Clear accumulator |
| `MM_MAC` | `ACC <- ACC + src0 * src1` |
| `FIR_MAC` | `ACC <- ACC + src0 * src1` |
| `FIR_REDUCE` | `dst <- ACC` |
| `QR_VEC` | QR vectoring update on CORDIC path |
| `QR_ROT` | QR rotation update on CORDIC path |
| `OUT_COMMIT` | Publish local result to output channel |

### 5.2 Deferred to later phase
| Opcode | Reason deferred |
|---|---|
| `NOP` | trivial, can be added later |
| `ALU_MAC` | not required for first trace bring-up |
| `FFT_STEP` | current simulator model is still abstract |
| `FFT_SHUF` | not critical for phase-1 PE bring-up |
| `SEND_P2P` | communication phase |
| `RECV_P2P` | communication phase |
| `SEND_BCAST` | communication phase |
| `RECV_BCAST` | communication phase |

The local opcode set and instruction encoding come from the current `LocalPEOp` and `LocalPEInst24` definitions. :contentReference[oaicite:2]{index=2}

---

## 6. Instruction Acceptance Rule
A new instruction is accepted only when:

- `inst_valid == 1`
- `inst_ready == 1`

The instruction is considered issued on the cycle where both are high.

### 6.1 `inst_ready` rule
For phase-1:
- `inst_ready = 1` only when `busy == 0`
- if `busy > 0`, the PE cannot accept a new instruction

This matches the current simulator rule that a PE cannot fire a new local instruction while `busy > 0`. :contentReference[oaicite:3]{index=3}

---

## 7. Operand Read Rule
After instruction acceptance, operands are interpreted by `dst/src0/src1` namespace encoding.

For phase-1, the following source namespaces must be supported:
- `RF0`
- `RF1`
- `ACC`
- `IMM`

For later communication phase:
- `IN_P2P`
- `IN_BCAST`

The namespace encoding is currently:
- `RF0 = 1`
- `RF1 = 2`
- `ACC = 3`
- `IN_P2P = 4`
- `IN_BCAST = 5`
- `IMM = 7` :contentReference[oaicite:4]{index=4}

---

## 8. Handshake Rules

## 8.1 Instruction Handshake
Instruction issue uses standard ready/valid semantics:
- issue occurs on `inst_valid && inst_ready`
- once accepted, the PE enters the corresponding busy period
- the accepted instruction becomes `dbg_last_inst`

## 8.2 Commit Handshake
For `OUT_COMMIT`:
- PE raises `out_commit_valid`
- `out_commit_data` holds the selected source value
- transfer completes on `out_commit_valid && out_commit_ready`
- until completion, commit state remains pending

This matches the simulator notion that `OUT_COMMIT` writes to a local commit channel and waits until it can be retired. :contentReference[oaicite:5]{index=5}

## 8.3 P2P Input Handshake
For the later communication phase:
- incoming P2P data is accepted when `in_p2p_valid && in_p2p_ready`
- `RECV_P2P` may only execute when P2P input is valid

## 8.4 Broadcast Input Handshake
For the later communication phase:
- incoming broadcast data is accepted when `in_bcast_valid && in_bcast_ready`
- `RECV_BCAST` may only execute when broadcast input is valid

## 8.5 P2P / Broadcast Output Handshake
For the later communication phase:
- `SEND_P2P` completes only when destination/fabric is ready
- `SEND_BCAST` completes only when broadcast fabric is ready

---

## 9. Busy-Time Rule
Each accepted instruction loads a `busy` counter according to the local-op latency table.

Current software model latencies include:
- `MOV = 1`
- `ACC_CLR = 1`
- `MM_MAC = 11`
- `FIR_MAC = 12`
- `FIR_REDUCE = 2`
- `QR_VEC = 18`
- `QR_ROT = 18`
- `OUT_COMMIT = 1` :contentReference[oaicite:6]{index=6}

For phase-1 RTL, the same latency contract should be preserved unless explicitly redefined.

---

## 10. Golden Reference
The phase-1 RTL must match:
1. the `LocalPEInst24` encoding
2. the local opcode semantics
3. the architectural state transition model
4. the dispatch traces generated from the current golden trace flow

The intended golden reference artifacts are:
- `golden_traces/*.dispatch.txt`
- local instruction encoding (`hex` / `bin`)
- the simulator-side `_fire_local_inst()` semantics model. 

---

## 11. Phase-1 Verification Scope
Minimum testbench objectives:
- decode and accept a 24-bit instruction
- verify `RF0`, `RF1`, `ACC` update correctly
- verify `busy` timing behavior
- verify `OUT_COMMIT` handshake
- compare selected instruction traces against generated golden dispatch files

---

## 12. Out of Scope for Phase-1
The following are intentionally excluded from phase-1:
- full cluster dispatch logic
- `pe_mask` handling across multiple PEs
- local broadcast fabric
- local P2P routing fabric
- outer `ClusterIR_Op` controller
- memory/ring exchange integration
