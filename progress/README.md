. 新FFT mapping：dynamic-owner streaming

原本：

input DMA
→ butterfly
→ RU/WBQ
→ output scatter DMA回固定owner
→ barrier
→ 下一stage

改成：

Stage s source ping-pong region
        │
        ├─ local input直接讀
        └─ 缺少的remote input由DMA預取
                    ↓
              Input Buffer A/B
                    ↓
ParamRF Bank A/B → 4-PE butterfly
                    ↓
              2-entry Result FIFO
                    ↓
                 RU/WBQ
                    ↓
Stage s+1 destination ping-pong region

核心規則：

每個stage重新決定butterfly compute owner。
優先選擇已持有其中一個input的cluster。
兩個output直接留在compute cluster。
下一stage只搬缺少的那一個input。
完全取消output scatter DMA。
每stage只保留一次global visibility barrier。
初始資料採contiguous block distribution。
仍然只有原本的一套DMA engine／cluster。
新增的硬體假設

沒有增加CORDIC數量，也沒有加第二套DMA。

新增單元	規格
Twiddle Expansion Unit	每cluster 2個complex multipliers，3-cycle latency
Input buffer	2組，支援compute／prefetch ping-pong
Result FIFO	2 entries
Streaming controller	管理stage-dependent owner與batch狀態
ParamRF	沿用原本2×8，改成真正跨batch temporal ping-pong
CORDIC	沿用既有18-stage registered版本

TEU的用途是：

CORDIC產生一個twiddle seed
→ TEU以recurrence展開同一batch需要的4組twiddle
→ 寫入下一個ParamRF bank

因此不再讓PE1～PE3花三次17-cycle CMUL串行產生twiddle，四顆PE可以主要用在butterfly運算。
