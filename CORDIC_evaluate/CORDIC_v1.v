module CORDIC #(
    parameter WIDTH = 16,
    parameter ITER = 15
)(
    input clk,
    input rst_n,
    input [2:0] state,
    input angle_valid,
    input signed [WIDTH-1:0] theta,
    output reg signed [WIDTH-1:0] cos_out,
    output reg signed [WIDTH-1:0] sin_out,
    output reg out_valid
);

    // atan_table: 25735 = 45度
    reg signed [WIDTH-1:0] atan_table [0:ITER-1];
    initial begin
        // 標尺基準：180度 = 32768, 則 45度 = 8192
        atan_table[0]  = 16'sd8192;   // atan(2^0) = 45.000 deg
        atan_table[1]  = 16'sd4836;   // atan(2^-1) = 26.565 deg
        atan_table[2]  = 16'sd2555;   // atan(2^-2) = 14.036 deg
        atan_table[3]  = 16'sd1297;   // atan(2^-3) = 7.125 deg
        atan_table[4]  = 16'sd651;    // atan(2^-4) = 3.576 deg
        atan_table[5]  = 16'sd326;    // atan(2^-5) = 1.790 deg
        atan_table[6]  = 16'sd163;    // atan(2^-6) = 0.895 deg
        atan_table[7]  = 16'sd81;     // atan(2^-7) = 0.448 deg
        atan_table[8]  = 16'sd41;     // atan(2^-8) = 0.224 deg
        atan_table[9]  = 16'sd20;     // atan(2^-9) = 0.112 deg
        atan_table[10] = 16'sd10;    // atan(2^-10) = 0.056 deg
        atan_table[11] = 16'sd5;     // atan(2^-11) = 0.028 deg
        atan_table[12] = 16'sd3;     // atan(2^-12) = 0.014 deg
        atan_table[13] = 16'sd1;     // atan(2^-13) = 0.007 deg
        atan_table[14] = 16'sd1;     // atan(2^-14) = 0.003 deg
    end

    // 增加一個 pipeline 階段來存放象限標記，以便最後校正正負號
    reg [ITER:0] is_quadrant_23; 
    
    reg signed [WIDTH-1:0] x[0:ITER];
    reg signed [WIDTH-1:0] y[0:ITER];
    reg signed [WIDTH-1:0] z[0:ITER];

    localparam signed [WIDTH-1:0] K = 16'sd19899;
    localparam signed [WIDTH-1:0] ANG_90 = 16'sd51470; // 這裡要注意溢位問題

    integer i;
    reg [ITER:0] valid_pipe;

    // -------------------------------
    // 象限預處理與 Pipeline 邏輯
    // -------------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            valid_pipe <= 0;
            is_quadrant_23 <= 0;
            for (i = 0; i <= ITER; i = i + 1) begin
                x[i] <= 0; y[i] <= 0; z[i] <= 0;
            end
            cos_out <= 0; sin_out <= 0;
        end
        else begin
            valid_pipe <= {valid_pipe[ITER-1:0], angle_valid}; // 將 angle_valid 推入 pipeline

            // --- Stage 0: 象限判斷 (Quadrant Mapping) ---
            if (angle_valid) begin
                // 如果角度大於 90 度 (25735*2) 或小於 -90 度
                // 這裡假設輸入 theta 是廣義角，我們做簡單的對稱處理
                if (theta > 16'sd16384) begin 
                    x[0] <= -K;           // 翻轉到第二三象限，初始 X 設為負
                    y[0] <= 0;
                    z[0] <= theta - 16'sd32768; // 減去 180度 (這裡標尺要對齊)
                    is_quadrant_23[0] <= 1;
                end 
                else if (theta <= -16'sd16384) begin
                    x[0] <= -K; 
                    y[0] <= 0;
                    z[0] <= theta + 16'sd32768; // 加上 180度 (這裡標尺要對齊)
                    is_quadrant_23[0] <= 1;
                end
                else begin
                    x[0] <= K;
                    y[0] <= 0;
                    z[0] <= theta;
                    is_quadrant_23[0] <= 0;
                end
            end

            // --- Stage 1 to ITER: CORDIC 旋轉 ---
            for (i = 0; i < ITER; i = i + 1) begin
                is_quadrant_23[i+1] <= is_quadrant_23[i]; // 傳遞象限標記
                if (z[i][WIDTH-1] == 0) begin
                    x[i+1] <= x[i] - (y[i] >>> i);
                    y[i+1] <= y[i] + (x[i] >>> i);
                    z[i+1] <= z[i] - atan_table[i];
                end
                else begin
                    x[i+1] <= x[i] + (y[i] >>> i);
                    y[i+1] <= y[i] - (x[i] >>> i);
                    z[i+1] <= z[i] + atan_table[i];
                end
            end

            // --- Final Stage: 輸出 ---
            // 這裡如果是二三象限，x[ITER] 和 y[ITER] 理論上已經在初始 x[0]=-K 時修正過了
            cos_out <= x[ITER];
            sin_out <= y[ITER];
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) out_valid <= 0;
        else        out_valid <= valid_pipe[ITER];
    end

endmodule
