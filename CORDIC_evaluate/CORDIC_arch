```mermaid
graph TD
    classDef reg fill:#f9f,stroke:#333,stroke-width:2px;
    classDef logic fill:#bbf,stroke:#333,stroke-width:2px;
    classDef lut fill:#bfb,stroke:#333,stroke-width:2px;

    subgraph Inputs
        XIN[x_in 16-bit]
        YIN[y_in 16-bit]
        TIN[theta 16-bit]
    end

    subgraph Stage_0 [Stage 0: Pre-process & Padding]
        MUX_Q[Quadrant Correction & Padding MUX]:::logic
        REG0_X[FF: x0]:::reg
        REG0_Y[FF: y0]:::reg
        REG0_Z[FF: z0]:::reg
        
        XIN --> MUX_Q
        YIN --> MUX_Q
        TIN --> MUX_Q
        MUX_Q --> REG0_X
        MUX_Q --> REG0_Y
        MUX_Q --> REG0_Z
    end

    subgraph Stage_i [Stage i: CORDIC Unrolled Pipeline x 15]
        DIR[Direction logic: sign z/y]:::logic
        SH_X[Shifter: x >> i]:::logic
        SH_Y[Shifter: y >> i]:::logic
        ATAN[LUT: atan_table_i]:::lut
        
        ADD_X[Adder/Subtractor]:::logic
        ADD_Y[Adder/Subtractor]:::logic
        ADD_Z[Adder/Subtractor]:::logic
        
        REG_Xi[FF: x_i+1]:::reg
        REG_Yi[FF: y_i+1]:::reg
        REG_Zi[FF: z_i+1]:::reg

        REG0_X -.-> SH_X & ADD_X & ADD_Y
        REG0_Y -.-> SH_Y & ADD_Y & ADD_X
        REG0_Z -.-> DIR & ADD_Z
        
        DIR -->|+/- control| ADD_X & ADD_Y & ADD_Z
        SH_X --> ADD_Y
        SH_Y --> ADD_X
        ATAN --> ADD_Z
        
        ADD_X --> REG_Xi
        ADD_Y --> REG_Yi
        ADD_Z --> REG_Zi
    end

    subgraph Stage_ITER [Stage 15: Multiply & Delay]
        MUL_X[Multiplier: x * K]:::logic
        MUL_Y[Multiplier: y * K]:::logic
        REG_MULX[FF: x_mul]:::reg
        REG_MULY[FF: y_mul]:::reg
        REG_ZDEL[FF: z_stage]:::reg
        
        REG_Xi -.-> MUL_X
        REG_Yi -.-> MUL_Y
        REG_Zi -.-> REG_ZDEL
        
        MUL_X --> REG_MULX
        MUL_Y --> REG_MULY
    end

    subgraph Stage_ITER_1 [Stage 16: Rounding]
        RND_X[round_shift_xy]:::logic
        RND_Y[round_shift_xy]:::logic
        RND_Z[round_shift_z]:::logic
        REG_RNDX[FF: x_rnd]:::reg
        REG_RNDY[FF: y_rnd]:::reg
        REG_RNDZ[FF: z_rnd]:::reg
        
        REG_MULX --> RND_X --> REG_RNDX
        REG_MULY --> RND_Y --> REG_RNDY
        REG_ZDEL --> RND_Z --> REG_RNDZ
    end

    subgraph Stage_ITER_2 [Stage 17: Saturation & Output]
        SAT_X[sat16 logic]:::logic
        SAT_Y[sat16 logic]:::logic
        SAT_Z[sat16 logic]:::logic
        OUT_X[x_out 16-bit]:::reg
        OUT_Y[y_out 16-bit]:::reg
        OUT_Z[z_out 16-bit]:::reg
        
        REG_RNDX --> SAT_X --> OUT_X
        REG_RNDY --> SAT_Y --> OUT_Y
        REG_RNDZ --> SAT_Z --> OUT_Z
    end
