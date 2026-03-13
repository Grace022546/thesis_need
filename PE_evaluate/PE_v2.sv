module PE(
    input clk,
    input rst_n,
    input signed [31:0] in [0:7],  
    input signed [31:0] angle [0:7], // angle (theta) for CORDIC
    input [2:0] state, // 0: FFT, 1: Matrix Multiply
    input [2:0] next_state,
    output reg signed [31:0] out [0:7],
    output reg call_mem,
    output reg ready
);
    reg signed [31:0] switch_out[0:7];
    reg signed [15:0] mulin1[0:15],mulin2[0:15]; 
    reg signed [31:0] mul_out1[0:15];
    reg signed [31:0] addin1_re[0:7],addin1_im[0:7],addin2_re[0:7],addin2_im[0:7];
    reg signed [34:0] addout_re[0:7], addout_im[0:7];
    reg [5:0] counter;
    integer i;


    reg signed [15:0] fft_re_q15[0:7];
    reg signed [15:0] fft_im_q15[0:7];
    reg signed [15:0] mm_q15[0:7];
    reg signed [15:0] fft_stage_re[0:7];
    reg signed [15:0] fft_stage_im[0:7];

    reg [3:0] pivot;
    reg [3:0] row;
    reg [3:0] row_cnt;


    
    parameter  IDLE = 3'b000,
               WAIT_MODE = 3'b001,
               WAIT_ROT = 3'b010,
               WAIT_VEC = 3'b011,
               FFT_PROCESS_8 = 3'b100,
               MM_PROCESS_8_8 = 3'b101,
               QR_PROCESS_8_8 = 3'b110;
               //update_QR_pivot = 3'b111;


    //========================================================
    // counter
    //========================================================
    always@(posedge clk or negedge rst_n) begin
        if(!rst_n ) counter <= 6'd0;
        // else if(state==FFT_PROCESS_8) counter <= counter + 1;
        // else if(state==MM_PROCESS_8_8) begin
        //     if(counter==12) counter <= 0;
        //     else counter <= counter + 1;
        // end
        else if(state == QR_PROCESS_8_8) begin 
            if(counter==12) counter <= 0;
            else counter <= counter + 1;
        end
        // else if(state == WAIT_VEC) counter <= counter + 1;
        else if(next_state != state) counter <=0;// Reset counter on state change
        else counter <= counter +1;
    end

    //========================================================
    // input register with switchbox
    //========================================================

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < 8; i = i + 1) begin
                switch_out[i] <= 32'd0;
            end

        end 
        else if (state == FFT_PROCESS_8) begin
            // 直接處理輸入數據與 Shuffle 邏輯
            case (counter)
                6'd2: begin
                    // Stage 1: Bit-reversal Permutation (直接取 in 訊號)
                    switch_out[0] <= in[0]; // {in[0][31:16], in[0][15:0]}
                    switch_out[1] <= in[4];
                    switch_out[2] <= in[2];
                    switch_out[3] <= in[6];
                    switch_out[4] <= in[1];
                    switch_out[5] <= in[5];
                    switch_out[6] <= in[3];
                    switch_out[7] <= in[7];
                    $display("\n[DEBUG] --- Stage 1 Input (Bit-Reversed) ---");
                end
                6'd7: begin
                    // Stage 2: 根據上一級運算結果 (fft_q15) 進行 Shuffle
                    switch_out[0] <= {fft_stage_re[0], fft_stage_im[0]};
                    switch_out[1] <= {fft_stage_re[2], fft_stage_im[2]};
                    switch_out[2] <= {fft_stage_re[1], fft_stage_im[1]};
                    switch_out[3] <= {fft_stage_re[3], fft_stage_im[3]};
                    switch_out[4] <= {fft_stage_re[4], fft_stage_im[4]};
                    switch_out[5] <= {fft_stage_re[6], fft_stage_im[6]};
                    switch_out[6] <= {fft_stage_re[5], fft_stage_im[5]};
                    switch_out[7] <= {fft_stage_re[7], fft_stage_im[7]};
                    //$display("\n[DEBUG] --- Stage 1 Output / Stage 2 Input ---");for(i=0; i<8; i=i+1) $display("lane[%d] = (re:%d, im:%d)", i, $signed(fft_stage_re[i]), $signed(fft_stage_im[i]));
                end
                6'd12: begin
                    switch_out[0] <= {fft_stage_re[0], fft_stage_im[0]};
                    switch_out[1] <= {fft_stage_re[4], fft_stage_im[4]}; // 0 跟 4 配
                    switch_out[2] <= {fft_stage_re[1], fft_stage_im[1]};
                    switch_out[3] <= {fft_stage_re[5], fft_stage_im[5]}; // 1 跟 5 配
                    switch_out[4] <= {fft_stage_re[2], fft_stage_im[2]};
                    switch_out[5] <= {fft_stage_re[6], fft_stage_im[6]}; // 2 跟 6 配
                    switch_out[6] <= {fft_stage_re[3], fft_stage_im[3]};
                    switch_out[7] <= {fft_stage_re[7], fft_stage_im[7]}; // 3 跟 7 配
                    //$display("\n[DEBUG] --- Stage 2 Output / Stage 3 Input ---");for(i=0; i<8; i=i+1) $display("lane[%d] = (re:%d, im:%d)", i, $signed(fft_stage_re[i]), $signed(fft_stage_im[i]));
                end
                
            endcase
        end
        else if (state == MM_PROCESS_8_8) begin
                if(counter==2) begin
                    for (i = 0; i < 8; i = i + 1) begin
                        switch_out[i] <= in[i];
                    end
                end
                else begin//3-10
                    for (i = 0; i < 7; i = i + 1) begin
                        switch_out[i][15:0]  <= in[i][15:0];
                        switch_out[i][31:16] <= switch_out[i+1][31:16];
                        end

                        // 再處理 index 7
                        switch_out[7][15:0]  <= in[7][15:0];
                        switch_out[7][31:16] <= switch_out[0][31:16];
                    end
        end
        //pivot row全部更新，其他是存0(或者消掉的結果)
        // else if (state == WAIT_VEC ) begin
        //     if(counter==19) begin
        //         for (i = 0; i < 7; i = i + 1) begin
        //             if(i<pivot) switch_out[i][15:0] <= 0;
        //             else switch_out[i][15:0] <= switch_out[i+1][15:0];
        //         end
        //         switch_out[7][15:0] <= in[0][15:0];//save pivot
        //         for(i=0; i<8; i=i+1) switch_out[i][31:16] <= in[i][31:16];
        //     end
           
        // end
        else if (state == QR_PROCESS_8_8) begin
           for (i = 0; i < 8; i = i + 1) switch_out[i]<= in[i];
        end
        else if (state == WAIT_MODE) begin
            for (i = 0; i < 8; i = i + 1) begin
                switch_out[i] <= 32'd0; 
            end

        end
    end

    //========================================================
    // mult-in
    //========================================================
    always@(*) begin
        for(i=0;i<16;i=i+1) begin
            mulin1[i] = 16'd0; mulin2[i] = 16'd0;
        end

        if(state == FFT_PROCESS_8) begin
            case(counter)
                6'd3: begin
                    mulin1[0] = switch_out[1][31:16]; mulin2[0] = angle[0][31:16];
                    mulin1[1] = switch_out[1][15:0];  mulin2[1] = angle[0][15:0];
                    mulin1[2] = switch_out[1][31:16]; mulin2[2] = angle[0][15:0];
                    mulin1[3] = switch_out[1][15:0];  mulin2[3] = angle[0][31:16];
                    mulin1[4] = switch_out[3][31:16]; mulin2[4] = angle[0][31:16];
                    mulin1[5] = switch_out[3][15:0];  mulin2[5] = angle[0][15:0];
                    mulin1[6] = switch_out[3][31:16]; mulin2[6] = angle[0][15:0];
                    mulin1[7] = switch_out[3][15:0];  mulin2[7] = angle[0][31:16];
                    mulin1[8] = switch_out[5][31:16]; mulin2[8] = angle[0][31:16];
                    mulin1[9] = switch_out[5][15:0];  mulin2[9] = angle[0][15:0];
                    mulin1[10] = switch_out[5][31:16]; mulin2[10] = angle[0][15:0];
                    mulin1[11] = switch_out[5][15:0];  mulin2[11] = angle[0][31:16];
                    mulin1[12] = switch_out[7][31:16]; mulin2[12] = angle[0][31:16];
                    mulin1[13] = switch_out[7][15:0];  mulin2[13] = angle[0][15:0];
                    mulin1[14] = switch_out[7][31:16]; mulin2[14] = angle[0][15:0];
                    mulin1[15] = switch_out[7][15:0];  mulin2[15] = angle[0][31:16];
                    // $display("\n[DEBUG] --- Stage 1 mult-in (Twiddle Factors) ---");
                    // $display("W8^0 used: (re:%d, im:%d)", $signed(angle[0][31:16]), $signed(angle[0][15:0]));
                end
                6'd8: begin
                    mulin1[0] = switch_out[1][31:16]; mulin2[0] = angle[0][31:16];
                    mulin1[1] = switch_out[1][15:0];  mulin2[1] = angle[0][15:0];
                    mulin1[2] = switch_out[1][31:16]; mulin2[2] = angle[0][15:0];
                    mulin1[3] = switch_out[1][15:0];  mulin2[3] = angle[0][31:16];
                    mulin1[4] = switch_out[3][31:16]; mulin2[4] = angle[2][31:16];
                    mulin1[5] = switch_out[3][15:0];  mulin2[5] = angle[2][15:0];
                    mulin1[6] = switch_out[3][31:16]; mulin2[6] = angle[2][15:0];
                    mulin1[7] = switch_out[3][15:0];  mulin2[7] = angle[2][31:16];
                    mulin1[8] = switch_out[5][31:16]; mulin2[8] = angle[0][31:16];
                    mulin1[9] = switch_out[5][15:0];  mulin2[9] = angle[0][15:0];
                    mulin1[10] = switch_out[5][31:16]; mulin2[10] = angle[0][15:0];
                    mulin1[11] = switch_out[5][15:0];  mulin2[11] = angle[0][31:16];
                    mulin1[12] = switch_out[7][31:16]; mulin2[12] = angle[2][31:16];
                    mulin1[13] = switch_out[7][15:0];  mulin2[13] = angle[2][15:0];
                    mulin1[14] = switch_out[7][31:16]; mulin2[14] = angle[2][15:0];
                    mulin1[15] = switch_out[7][15:0];  mulin2[15] = angle[2][31:16];
                    // $display("\n[DEBUG] --- Stage 2 mult-in (Twiddle Factors) ---");
                    // $display("W8^0 used: (re:%d, im:%d)", $signed(angle[0][31:16]), $signed(angle[0][15:0]));
                    // $display("W8^2 used: (re:%d, im:%d)", $signed(angle[2][31:16]), $signed(angle[2][15:0]));
                end
                6'd13: begin
                    // pair0: switch_out[0] with switch_out[1], twiddle W8^0 on [1]
                    mulin1[0]  = switch_out[1][31:16]; mulin2[0]  = angle[0][31:16];
                    mulin1[1]  = switch_out[1][15:0];  mulin2[1]  = angle[0][15:0];
                    mulin1[2]  = switch_out[1][31:16]; mulin2[2]  = angle[0][15:0];
                    mulin1[3]  = switch_out[1][15:0];  mulin2[3]  = angle[0][31:16];

                    // pair1: switch_out[2] with switch_out[3], twiddle W8^1 on [3]
                    mulin1[4]  = switch_out[3][31:16]; mulin2[4]  = angle[1][31:16];
                    mulin1[5]  = switch_out[3][15:0];  mulin2[5]  = angle[1][15:0];
                    mulin1[6]  = switch_out[3][31:16]; mulin2[6]  = angle[1][15:0];
                    mulin1[7]  = switch_out[3][15:0];  mulin2[7]  = angle[1][31:16];

                    // pair2: switch_out[4] with switch_out[5], twiddle W8^2 on [5]
                    mulin1[8]  = switch_out[5][31:16]; mulin2[8]  = angle[2][31:16];
                    mulin1[9]  = switch_out[5][15:0];  mulin2[9]  = angle[2][15:0];
                    mulin1[10] = switch_out[5][31:16]; mulin2[10] = angle[2][15:0];
                    mulin1[11] = switch_out[5][15:0];  mulin2[11] = angle[2][31:16];

                    // pair3: switch_out[6] with switch_out[7], twiddle W8^3 on [7]
                    mulin1[12] = switch_out[7][31:16]; mulin2[12] = angle[3][31:16];
                    mulin1[13] = switch_out[7][15:0];  mulin2[13] = angle[3][15:0];
                    mulin1[14] = switch_out[7][31:16]; mulin2[14] = angle[3][15:0];
                    mulin1[15] = switch_out[7][15:0];  mulin2[15] = angle[3][31:16];


                    // $display("\n[DEBUG] --- Stage 3 mult-in (Twiddle Factors) ---");
                    // $display("[ST3 SRC] g0 src switch_out[1]=(%0d,%0d)", $signed(switch_out[1][31:16]), $signed(switch_out[1][15:0]));
                    // $display("[ST3 SRC] g0 src switch_out[4]=(%0d,%0d)", $signed(switch_out[4][31:16]), $signed(switch_out[4][15:0]));
                    // $display("W8^0: (re:%d, im:%d)", $signed(angle[0][31:16]), $signed(angle[0][15:0]));
                    // $display("W8^1: (re:%d, im:%d)", $signed(angle[1][31:16]), $signed(angle[1][15:0]));
                    // $display("W8^2: (re:%d, im:%d)", $signed(angle[2][31:16]), $signed(angle[2][15:0]));
                    // $display("W8^3: (re:%d, im:%d)", $signed(angle[3][31:16]), $signed(angle[3][15:0]));
                end
            endcase
        end
        else if(state == MM_PROCESS_8_8) begin
            
                mulin1[0] = switch_out[0][31:16]; mulin2[0] = switch_out[0][15:0]; // Term 0
                mulin1[1] = switch_out[0][31:16]; mulin2[1] = switch_out[1][15:0]; // Term 1
                mulin1[2] = switch_out[0][31:16]; mulin2[2] = switch_out[2][15:0]; // Term 2
                mulin1[3] = switch_out[0][31:16]; mulin2[3] = switch_out[3][15:0]; // Term 3
                mulin1[4] = switch_out[0][31:16]; mulin2[4] = switch_out[4][15:0]; // Term 4
                mulin1[5] = switch_out[0][31:16]; mulin2[5] = switch_out[5][15:0]; // Term 5
                mulin1[6] = switch_out[0][31:16]; mulin2[6] = switch_out[6][15:0]; // Term 6
                mulin1[7] = switch_out[0][31:16]; mulin2[7] = switch_out[7][15:0]; // Term 7
        end
        else if (state == QR_PROCESS_8_8) begin
            for(i=0;i<16;i=i+2) begin
                mulin2[i] = angle[0][31:16];
                mulin2[i+1] = angle[0][15:0];
            end
            if(counter[0]==0) begin
                mulin1[0] = switch_out[0][31:16]; mulin1[1] = switch_out[0][15:0];mulin1[2] = -switch_out[0][31:16]; mulin1[3] = switch_out[0][15:0]; 
                mulin1[4] = switch_out[1][31:16];mulin1[5] = switch_out[1][15:0];mulin1[6] = -switch_out[1][31:16];mulin1[7] = switch_out[1][15:0];
                mulin1[8] = switch_out[2][31:16];mulin1[9] = switch_out[2][15:0];mulin1[10] = -switch_out[2][31:16];mulin1[11] = switch_out[2][15:0];
                mulin1[12] = switch_out[3][31:16];mulin1[13] = switch_out[3][15:0];mulin1[14] = -switch_out[3][31:16];mulin1[15] = switch_out[3][15:0];
            end
            else if(counter[0]==1) begin
                mulin1[0] = switch_out[4][31:16]; mulin1[1] = switch_out[4][15:0];mulin1[2] = -switch_out[4][31:16]; mulin1[3] = switch_out[4][15:0]; 
                mulin1[4] = switch_out[5][31:16];mulin1[5] = switch_out[5][15:0];mulin1[6] = -switch_out[5][31:16];mulin1[7] = switch_out[5][15:0];
                mulin1[8] = switch_out[6][31:16];mulin1[9] = switch_out[6][15:0];mulin1[10] = -switch_out[6][31:16];mulin1[11] = switch_out[6][15:0];
                mulin1[12] = switch_out[7][31:16];mulin1[13] = switch_out[7][15:0];mulin1[14] = -switch_out[7][31:16];mulin1[15] = switch_out[7][15:0]; 
            end
        end
    end

    //========================================================
    // multiplier
    //========================================================
    always@(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            for(i=0;i<16;i=i+1) begin
                mul_out1[i] <= 0;
            end
        end
        else begin
            for(i=0;i<16;i=i+1) begin
                mul_out1[i] <= mulin1[i] * mulin2[i];
            end
        end
    end

    //========================================================
    // adder-in (Pipeline Logic Corrected)
    //========================================================
    always@(*) begin
        for(i=0;i<8;i=i+1) begin
            addin1_re[i] = 32'd0; addin2_re[i] = 32'd0;
            addin1_im[i] = 32'd0; addin2_im[i] = 32'd0;
        end

        if(state == FFT_PROCESS_8) begin
            case(counter)
                6'd4,6'd9,6'd14: begin
                    addin1_re[0] = mul_out1[0]; addin2_re[0] = -mul_out1[1];
                    addin1_im[0] = mul_out1[2]; addin2_im[0] = mul_out1[3];
                    addin1_re[1] = mul_out1[4]; addin2_re[1] = -mul_out1[5];
                    addin1_im[1] = mul_out1[6]; addin2_im[1] = mul_out1[7];
                    addin1_re[2] = mul_out1[8]; addin2_re[2] = -mul_out1[9];
                    addin1_im[2] = mul_out1[10]; addin2_im[2] = mul_out1[11];
                    addin1_re[3] = mul_out1[12]; addin2_re[3] = -mul_out1[13];
                    addin1_im[3] = mul_out1[14]; addin2_im[3] = mul_out1[15];
                    // $display("[CMUL COMB] g0=(%0d,%0d) g1=(%0d,%0d) g2=(%0d,%0d) g3=(%0d,%0d)",
                    // $signed(($signed(addin1_re[0]) + $signed(addin2_re[0])) >>> 15),
                    // $signed(($signed(addin1_im[0]) + $signed(addin2_im[0])) >>> 15),
                    // $signed(($signed(addin1_re[1]) + $signed(addin2_re[1])) >>> 15),
                    // $signed(($signed(addin1_im[1]) + $signed(addin2_im[1])) >>> 15),
                    // $signed(($signed(addin1_re[2]) + $signed(addin2_re[2])) >>> 15),
                    // $signed(($signed(addin1_im[2]) + $signed(addin2_im[2])) >>> 15),
                    // $signed(($signed(addin1_re[3]) + $signed(addin2_re[3])) >>> 15),
                    // $signed(($signed(addin1_im[3]) + $signed(addin2_im[3])) >>> 15));
                   end
                6'd5, 6'd10, 6'd15: begin
                for (i = 0; i < 4; i = i + 1) begin
                    // --- Real Part ---
                    // 手動將 16-bit 擴展到 32-bit: { {16{sign_bit}}, value }
                    // 這裡我們左移 15 位，所以高位需要 1 位的符號擴展 (假設 addin1 是 32-bit)
                    addin1_re[2*i]   = $signed({ {1{switch_out[2*i][31]}}, switch_out[2*i][31:16], 15'd0 });
                    addin1_re[2*i+1] = $signed({ {1{switch_out[2*i][31]}}, switch_out[2*i][31:16], 15'd0 });
                    
                    // --- Imaginary Part ---
                    addin1_im[2*i]   = $signed({ {1{switch_out[2*i][15]}}, switch_out[2*i][15:0],  15'd0 });
                    addin1_im[2*i+1] = $signed({ {1{switch_out[2*i][15]}}, switch_out[2*i][15:0],  15'd0 });

                    // B 部分 (注意要確保 addin2 的寬度與 addin1 一致)
                    addin2_re[2*i]   = $signed(addout_re[i]);
                    addin2_im[2*i]   = $signed(addout_im[i]);
                    
                    // 減法改用加負值的方式最安全
                    addin2_re[2*i+1] = -$signed(addout_re[i]);
                    addin2_im[2*i+1] = -$signed(addout_im[i]);
                    // $display("Index %d (Add): A=%h, B=%h", 2*i,   addin1_re[2*i],   addin2_re[2*i]);
                    // $display("Index %d (Sub): A=%h, B=%h", 2*i+1, addin1_re[2*i+1], addin2_re[2*i+1]);
                    end
            end
            endcase
        end
        else if(state == MM_PROCESS_8_8) begin
            if(counter==0) begin
                for(i=0;i<8;i=i+1) begin
                    addin1_re[i] = 0; addin2_re[i] = 0;
                    addin1_im[i] = 0; addin2_im[i] = 0;
                end
            end
            else begin
                for(i=0;i<8;i=i+1) begin
                    addin1_re[i] = mul_out1[i]; addin2_re[i] = addout_re[i];
                    addin1_im[i] = 32'd0; addin2_im[i] = 32'd0;
                end
            end
        end
        else if (state == QR_PROCESS_8_8) begin
            // if((counter>=1)&&(counter[0]==1 ||counter[0]==0)) begin
                addin1_re[0] = mul_out1[0]; addin2_re[0] = mul_out1[1];
                addin1_im[0] = mul_out1[2]; addin2_im[0] = mul_out1[3];
                addin1_re[1] = mul_out1[4]; addin2_re[1] = mul_out1[5];
                addin1_im[1] = mul_out1[6]; addin2_im[1] = mul_out1[7];
                addin1_re[2] = mul_out1[8]; addin2_re[2] = mul_out1[9];
                addin1_im[2] = mul_out1[10]; addin2_im[2] = mul_out1[11];
                addin1_re[3] = mul_out1[12]; addin2_re[3] = mul_out1[13];
                addin1_im[3] = mul_out1[14]; addin2_im[3] = mul_out1[15];
           // end
        end
    end

    //========================================================
    // adder
    //========================================================
    always@(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            for(i=0;i<8;i=i+1) begin
                addout_re[i] <= 35'd0; addout_im[i] <= 35'd0;
            end
        end
        else begin
            for(i=0;i<8;i=i+1) begin
                addout_re[i] <= $signed(addin1_re[i]) + $signed(addin2_re[i]);
                addout_im[i] <= $signed(addin1_im[i]) + $signed(addin2_im[i]);
            end
        end
    end

    //=================================================
    // Truncation
    //=================================================
    always @(*) begin
        for (i=0; i<8; i=i+1) begin
            fft_re_q15[i] = 16'sd0; fft_im_q15[i] = 16'sd0; mm_q15[i] = 16'sd0;
            if (state == FFT_PROCESS_8) begin
                fft_re_q15[i] = q15_round_sat_from_q30(addout_re[i],16);
                fft_im_q15[i] = q15_round_sat_from_q30(addout_im[i],16);
            end
            else if(state == MM_PROCESS_8_8) begin
                mm_q15[i] = q15_round_sat_from_q30(addout_re[i],15);
            end
            // else if(state == QR_PROCESS_8_8) begin
            //     // QR 的輸出也是 q15，跟 FFT 一樣的 truncation 就好
            //     mm_q15[i] = q15_round_sat_from_q30(addout_re[i], 16);
            // end
        end
    end

   

    //======================================
    // call memory (Corrected for FFT)
    //======================================
    always@(posedge clk or negedge rst_n) begin
        if(!rst_n) call_mem <= 1'b0;
        else if(state==MM_PROCESS_8_8 && (counter<8)) call_mem <= 1'b1;
        else if(state==FFT_PROCESS_8 && counter==0) call_mem <= 1'b1; // Added for FFT
        else if(state==WAIT_VEC && counter==0) call_mem <= 1'b1; // Added for QR
        //else if(state==QR_PROCESS_8_8  && ready && pivot < 7) call_mem <= 1'b1; // Added for QR
        else call_mem <= 1'b0;
    end

    //========================================================
    // output buffer
    //========================================================
    always@(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            for(i=0;i<8;i=i+1) out[i] <= 32'd0;
        end
        else if(state==FFT_PROCESS_8 && counter==6'd17) begin
            for(i=0;i<8;i=i+1) out[i] <= {fft_stage_re[i], fft_stage_im[i] };
        end
        else if(state==MM_PROCESS_8_8 ) begin
                for (int i = 0; i < 8; i++) begin
                    out[i] <= mm_q15[i];
                end
        end
        else if(state==QR_PROCESS_8_8 ) begin
            if(counter>=4)begin
                if(counter[0]==0) begin
                    for(i=0;i<4;i=i+1) out[i] <= {q15_round_sat_from_q30(addout_re[i], 15),q15_round_sat_from_q30(addout_im[i], 15)}; 
                end
                else begin
                    for(i=0;i<4;i=i+1) out[i+4] <= {q15_round_sat_from_q30(addout_im[i], 15),q15_round_sat_from_q30(addout_im[i], 15)};
                end
            end
            end
        else begin
            for(i=0;i<8;i=i+1) out[i] <= 32'd0;
        end
    end

    //========================================================
    // ready
    //========================================================
    always@(posedge clk or negedge rst_n) begin
        if(!rst_n) ready <= 1'b0;
        else if((state==FFT_PROCESS_8 && counter==6'd17) || (state==MM_PROCESS_8_8 && counter==6'd12)) ready <= 1'b1;
        else if(state==QR_PROCESS_8_8 && counter==6'd12) ready <= 1'b1;
        else ready <= 1'b0;
    end
    function automatic signed [15:0] q15_round_sat_from_q30;
        input signed [34:0] x_q30;
        input int shift;
        reg signed [34:0] x_round;
        begin
            // 統一加 0.5LSB (16384) 進行二補數捨入，不分正負
            x_round = x_q30 + 35'sd16384; 
            
            // 算術右移 (必須確保 x_round 是 signed)
            x_round = x_round >>> shift;//mm15 //fft16
            
            // 飽和處理
            if (x_round > 32767)       q15_round_sat_from_q30 = 16'sh7FFF;
            else if (x_round < -32768) q15_round_sat_from_q30 = 16'sh8000;
            else                       q15_round_sat_from_q30 = x_round[15:0];
        end
    endfunction
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < 8; i = i + 1) begin
                fft_stage_re[i] <= 16'sd0;
                fft_stage_im[i] <= 16'sd0;
            end
        end
        else if (state == FFT_PROCESS_8) begin
            // 在 butterfly 完成那拍後，把 q15 結果鎖進 stage buffer
            // 你的時序是:
            // cmul @ 4/8/12 -> butterfly @ 5/9/13 -> addout更新後 q15穩定於同拍之後
            // 下一拍拿來shuffle最穩，所以在 5/9/13 鎖
            
            if (counter == 6'd6 || counter == 6'd11 || counter == 6'd16) begin
                for (i = 0; i < 8; i = i + 1) begin
                    fft_stage_re[i] <= fft_re_q15[i];
                    fft_stage_im[i] <= fft_im_q15[i];
                end
            end
            
        end
    end



endmodule
