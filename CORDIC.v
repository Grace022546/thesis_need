module CORDIC #(
    parameter WIDTH = 16,
    parameter ITER = 15
)(
    input clk,
    input rst_n,
    input in_valid,
    input signed [WIDTH-1:0] theta,
    output reg signed [WIDTH-1:0] cos_out,
    output reg signed [WIDTH-1:0] sin_out,
    output reg out_valid
);

    reg signed [WIDTH-1:0] atan_table [0:ITER-1];

    initial begin
        atan_table[0]  = 16'sd25735;
        atan_table[1]  = 16'sd15192;
        atan_table[2]  = 16'sd8027;
        atan_table[3]  = 16'sd4074;
        atan_table[4]  = 16'sd2045;
        atan_table[5]  = 16'sd1023;
        atan_table[6]  = 16'sd512;
        atan_table[7]  = 16'sd256;
        atan_table[8]  = 16'sd128;
        atan_table[9]  = 16'sd64;
        atan_table[10] = 16'sd32;
        atan_table[11] = 16'sd16;
        atan_table[12] = 16'sd8;
        atan_table[13] = 16'sd4;
        atan_table[14] = 16'sd2;
    end

    reg signed [WIDTH-1:0] x[0:ITER];
    reg signed [WIDTH-1:0] y[0:ITER];
    reg signed [WIDTH-1:0] z[0:ITER];

    localparam signed [WIDTH-1:0] K = 16'sd19899;

    integer i;

    // -------------------------------
    // out_valid pipeline
    // -------------------------------
    reg [ITER:0] valid_pipe;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            valid_pipe <= 0;
        else
            valid_pipe <= {valid_pipe[ITER-1:0], in_valid};
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            out_valid <= 0;
        else
            out_valid <= valid_pipe[ITER];
    end

    // -------------------------------
    // main CORDIC pipeline
    // -------------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cos_out <= 0;
            sin_out <= 0;
        end else begin
            if (in_valid) begin
                x[0] <= K;
                y[0] <= 0;
                z[0] <= theta;
            end

            for (i = 0; i < ITER; i = i + 1) begin
                if (z[i][WIDTH-1] == 0) begin
                    x[i+1] <= x[i] - (y[i] >>> i);
                    y[i+1] <= y[i] + (x[i] >>> i);
                    z[i+1] <= z[i] - atan_table[i];
                end else begin
                    x[i+1] <= x[i] + (y[i] >>> i);
                    y[i+1] <= y[i] - (x[i] >>> i);
                    z[i+1] <= z[i] + atan_table[i];
                end
            end

            cos_out <= x[ITER];
            sin_out <= y[ITER];
        end
    end

endmodule
