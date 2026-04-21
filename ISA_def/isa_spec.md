# ISA Specification

## 1. Overview
This project uses a two-level control model:
1. Cluster-level IR (`ClusterIR_Op`) for kernel orchestration, memory movement, exchange, and synchronization.
2. Local PE ISA (`LocalPEInst24`) for PE-local computation and intra-cluster communication.

## 2. ISA Layers

### 2.1 Cluster-level IR
Role:
- kernel launch/configuration
- memory movement
- local/ring exchange
- synchronization
- macro compute operations

Main opcodes:
- CFG, LOAD, LOAD_SM, MOVE_SM_TO_PE, BROADCAST_SM_TO_PE
- STORE, STORE_SCALAR, LOAD_PE_GROUP, STORE_PE_GROUP
- EXCHANGE_LOCAL, EXCHANGE_RING
- CLUSTER_FFT8, CLUSTER_MM4X8_K8, CLUSTER_FIR8_4OUT, CLUSTER_QR_ROWPAIR
- QR_VEC, QR_ROT
- WAIT, HALT

### 2.2 Local PE ISA
Role:
- PE-local datapath execution
- RF/ACC updates
- P2P / broadcast communication
- local commit

## 3. Local Instruction Format

`LocalPEInst24 = {fmt[1:0], op[3:0], en[0], dst[2:0], src0[2:0], src1[2:0], res[2:0], imm[4:0]}`

Bit layout:
- [23:22] fmt
- [21:18] op
- [17] en
- [16:14] dst
- [13:11] src0
- [10:8] src1
- [7:5] res
- [4:0] imm

### 3.1 Field Definitions
- `fmt`: instruction class
  - 0 = control
  - 1 = move
  - 2 = compute
  - 3 = reserved
- `op`: local opcode
- `en`: execute enable
- `dst`: destination namespace
- `src0`: source namespace 0
- `src1`: source namespace 1
- `res`: bound execution/communication resource
- `imm`: immediate / stage index / route tag / lane metadata

## 4. Dispatch Format

`DispatchPacket = {cluster_id, pe_mask, local_inst}`

- `cluster_id`: target cluster
- `pe_mask`: target PE mask within the cluster
- `local_inst`: 24-bit local PE instruction payload

## 5. Local Namespace Encoding

- 0 = NONE
- 1 = RF0
- 2 = RF1
- 3 = ACC
- 4 = IN_P2P
- 5 = IN_BCAST
- 6 = SW
- 7 = IMM

## 6. Local Resource Encoding

- 0 = ALU_MAC
- 1 = FFT_PATH
- 2 = MM_FIR_PATH
- 3 = CORDIC_PATH
- 4 = OUT_P2P
- 5 = OUT_BCAST
- 6 = SW_FABRIC
- 7 = RESERVED

## 7. Local Opcode Definitions

### 7.1 Basic / Control
- `NOP`
- `MOV`
- `ACC_CLR`
- `ALU_MAC`

### 7.2 FFT
- `FFT_STEP`
- `FFT_SHUF`

### 7.3 MM / FIR
- `MM_MAC`
- `FIR_MAC`
- `FIR_REDUCE`

### 7.4 QR / CORDIC
- `QR_VEC`
- `QR_ROT`

### 7.5 Communication / Commit
- `OUT_COMMIT`
- `SEND_P2P`
- `RECV_P2P`
- `SEND_BCAST`
- `RECV_BCAST`

## 8. Execution Semantics

### 8.1 Architectural State
Each PE maintains:
- RF0
- RF1
- ACC
- IN_P2P
- IN_BCAST
- OUT_COMMIT
- busy
- last_inst

### 8.2 General Execution Rule
A local instruction may execute only when:
- target PE is not busy
- required source operands are available
- communication endpoints are ready
- output/commit channel can accept data

### 8.3 Example Semantics
- `MOV`: write `src0` to `dst`
- `ACC_CLR`: clear accumulator
- `MM_MAC`: `ACC <- ACC + src0 * src1`
- `FIR_REDUCE`: `dst <- ACC`
- `QR_VEC`: vectoring update on CORDIC path
- `QR_ROT`: rotation update on CORDIC path
- `SEND_P2P`: send data to target PE indicated by `imm`
- `RECV_P2P`: receive from local P2P input
- `SEND_BCAST`: inject token/data into cluster broadcast fabric
- `RECV_BCAST`: consume broadcast input
- `OUT_COMMIT`: publish local result to commit/output channel

## 9. Cluster IR Role

Cluster IR is responsible for:
- orchestration
- buffer movement
- exchange control
- synchronization
- macro compute issue

Cluster IR is not the final PE execution format; selected macro-ops are lowered into local PE dispatch streams.

## 10. Lowering Overview
Examples:
- `CLUSTER_FFT8` -> `FFT_STEP` sequence
- `CLUSTER_MM4X8_K8` -> `ACC_CLR` + `MM_MAC` + optional `OUT_COMMIT`
- `CLUSTER_FIR8_4OUT` -> `FIR_MAC` + optional `FIR_REDUCE` + `OUT_COMMIT`
- `QR_VEC` -> `QR_VEC`
- `QR_ROT` -> `QR_ROT`
- `BROADCAST_SM_TO_PE` -> `SEND_BCAST` + `RECV_BCAST`
- `EXCHANGE_LOCAL` -> `SEND_P2P` + `RECV_P2P`

## 11. Current Modeling Scope
Already localized:
- major compute path
- QR queue path
- intra-cluster broadcast
- intra-cluster local exchange

Still modeled at higher level:
- SM ingress (`MOVE_SM_TO_PE`)
- inter-cluster ring transfer (`EXCHANGE_RING`)
- some higher-level QR macro orchestration

## 12. Notes
This ISA should be treated as the frozen functional specification for:
- lowering rules
- golden trace generation
- RTL interface definition
- testbench construction
