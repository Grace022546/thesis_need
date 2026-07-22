```mermaid
graph TD
    %% 定義外觀風格
    classDef memory fill:#f9f9f9,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5;
    classDef compute fill:#ffe6cc,stroke:#d79b00,stroke-width:2px;
    classDef buffer fill:#dae8fc,stroke:#6c8ebf,stroke-width:2px;

    subgraph Stage_S [Stage s Source Region]
        L_IN[Local Input<br/>(Direct Read)]
        R_IN[Remote Input<br/>(DMA Prefetch)]
    end

    subgraph PingPong_In [Input Ping-Pong Buffer]
        BUF_A[Buffer A]
        BUF_B[Buffer B]
    end

    subgraph Param_Bank [ParamRF]
        PRF_A[Bank A]
        PRF_B[Bank B]
    end

    PE[4-PE Butterfly Unit]:::compute

    FIFO[2-entry Result FIFO]:::buffer
    RU_WBQ[RU / WBQ]:::buffer
    
    Stage_S1[Stage s+1 Destination Ping-Pong Region]:::memory

    %% 資料流連線
    L_IN -->|Data| BUF_A
    R_IN -->|Prefetch| BUF_B
    
    BUF_A ==>|Data Bus| PE
    BUF_B ==>|Data Bus| PE
    
    PRF_A -.->|Twiddle/Weight| PE
    PRF_B -.->|Twiddle/Weight| PE

    PE ==>|Output| FIFO
    FIFO ==> RU_WBQ
    RU_WBQ ==>|Write Back| Stage_S1
```
