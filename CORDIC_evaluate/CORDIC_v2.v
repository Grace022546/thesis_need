module CORDIC #(
    parameter WIDTH_OUT = 16,
    parameter WIDTH     = 26,
    parameter ITER      = 15,

    // x/y fixed-point format
    parameter XY_FRAC_IN  = 15,
    parameter XY_FRAC_INT = 18
)(
    input clk,
    input rst_n,
    input [2:0] state,
    input angle_valid,

    input  signed [WIDTH_OUT-1:0] x_in,
    input  signed [WIDTH_OUT-1:0] y_in,
    input  signed [WIDTH_OUT-1:0] theta,

    output reg signed [WIDTH_OUT-1:0] x_out,
    output reg signed [WIDTH_OUT-1:0] y_out,
    output reg signed [WIDTH_OUT-1:0] z_out,
    output reg out_valid
);

    localparam XY_SHIFT = XY_FRAC_INT - XY_FRAC_IN;
    localparam Z_SHIFT  = WIDTH - WIDTH_OUT;

    localparam integer K_W     = 16;
    localparam integer PROD_W  = WIDTH + K_W;
    localparam integer ROUND_W = PROD_W + 1;

    localparam signed [K_W-1:0] K_INV_Q15 = 16'sd19899;

    reg [ITER+2:0] valid_pipe;

    reg signed [WIDTH-1:0] x [0:ITER];
    reg signed [WIDTH-1:0] y [0:ITER];
    reg signed [WIDTH-1:0] z [0:ITER];

    reg signed [PROD_W-1:0]  x_mul, y_mul;
    reg signed [ROUND_W-1:0] x_rnd, y_rnd, z_rnd;

    reg signed [WIDTH-1:0] z_stage;

    integer i;

    ////////////////////////////////////////////////////////////
    //// atan table
    ////////////////////////////////////////////////////////////

    wire signed [WIDTH-1:0] atan_table [0:ITER-1];

    assign atan_table[0]  = 26'sd8192 <<< Z_SHIFT;
    assign atan_table[1]  = 26'sd4836 <<< Z_SHIFT;
    assign atan_table[2]  = 26'sd2555 <<< Z_SHIFT;
    assign atan_table[3]  = 26'sd1297 <<< Z_SHIFT;
    assign atan_table[4]  = 26'sd651  <<< Z_SHIFT;
    assign atan_table[5]  = 26'sd326  <<< Z_SHIFT;
    assign atan_table[6]  = 26'sd163  <<< Z_SHIFT;
    assign atan_table[7]  = 26'sd81   <<< Z_SHIFT;
    assign atan_table[8]  = 26'sd41   <<< Z_SHIFT;
    assign atan_table[9]  = 26'sd20   <<< Z_SHIFT;
    assign atan_table[10] = 26'sd10   <<< Z_SHIFT;
    assign atan_table[11] = 26'sd5    <<< Z_SHIFT;
    assign atan_table[12] = 26'sd3    <<< Z_SHIFT;
    assign atan_table[13] = 26'sd1    <<< Z_SHIFT;
    assign atan_table[14] = 26'sd1    <<< Z_SHIFT;

    ////////////////////////////////////////////////////////////
    //// Saturation
    ////////////////////////////////////////////////////////////

    function signed [WIDTH_OUT-1:0] sat16;
        input signed [ROUND_W-1:0] din;
    begin
        if (din > 32767)
            sat16 = 16'sd32767;
        else if (din < -32768)
            sat16 = -16'sd32768;
        else
            sat16 = din[WIDTH_OUT-1:0];
    end
    endfunction

    ////////////////////////////////////////////////////////////
    //// symmetric rounding
    ////////////////////////////////////////////////////////////

    function signed [ROUND_W-1:0] round_shift_xy;
        input signed [ROUND_W-1:0] din;
        input integer sh;
        reg signed [ROUND_W-1:0] bias;
    begin
        if (sh == 0)
            round_shift_xy = din;
        else begin
            bias = (din >= 0) ?
                   ({{(ROUND_W-1){1'b0}},1'b1} <<< (sh-1)) :
                  -({{(ROUND_W-1){1'b0}},1'b1} <<< (sh-1));

            round_shift_xy = (din + bias) >>> sh;
        end
    end
    endfunction


    function signed [ROUND_W-1:0] round_shift_z;
        input signed [WIDTH-1:0] din;
        input integer sh;

        reg signed [WIDTH-1:0] bias;
        reg signed [WIDTH-1:0] tmp;
    begin
        if (sh == 0)
            tmp = din;
        else begin
            bias = (din >= 0) ?
                   ({{(WIDTH-1){1'b0}},1'b1} <<< (sh-1)) :
                  -({{(WIDTH-1){1'b0}},1'b1} <<< (sh-1));

            tmp = (din + bias) >>> sh;
        end

        round_shift_z = {{(ROUND_W-WIDTH){tmp[WIDTH-1]}},tmp};
    end
    endfunction


    ////////////////////////////////////////////////////////////
    //// Main sequential logic
    ////////////////////////////////////////////////////////////

    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            valid_pipe <= 0;

            for(i=0; i<=ITER; i=i+1) begin
                x[i] <= 0;
                y[i] <= 0;
                z[i] <= 0;
            end

            x_mul <= 0;
            y_mul <= 0;
            x_rnd <= 0;
            y_rnd <= 0;
            z_rnd <= 0;

            z_stage <= 0;

            x_out <= 0;
            y_out <= 0;
            z_out <= 0;

            out_valid <= 0;
        end
        else begin

            ////////////////////////////////////////////////////////////
            //// valid pipe
            ////////////////////////////////////////////////////////////
            valid_pipe <= {valid_pipe[ITER+1:0], angle_valid};
            out_valid  <= valid_pipe[ITER+2];

            ////////////////////////////////////////////////////////////
            //// stage0 preprocess
            ////////////////////////////////////////////////////////////
            if(angle_valid) begin
                if(state == 3'b010) begin
                    if(theta > 16'sd16384) begin
                        x[0] <= -($signed(x_in) <<< XY_SHIFT);
                        y[0] <= -($signed(y_in) <<< XY_SHIFT);
                        z[0] <= ($signed(theta) <<< Z_SHIFT) - (26'sd32768 <<< Z_SHIFT);
                    end
                    else if(theta < -16'sd16384) begin
                        x[0] <= -($signed(x_in) <<< XY_SHIFT);
                        y[0] <= -($signed(y_in) <<< XY_SHIFT);
                        z[0] <= ($signed(theta) <<< Z_SHIFT) + (26'sd32768 <<< Z_SHIFT);
                    end
                    else begin
                        x[0] <= $signed(x_in) <<< XY_SHIFT;
                        y[0] <= $signed(y_in) <<< XY_SHIFT;
                        z[0] <= $signed(theta) <<< Z_SHIFT;
                    end
                end
                else if(state == 3'b011) begin
                    if(x_in < 0) begin
                        x[0] <= -($signed(x_in) <<< XY_SHIFT);
                        y[0] <= -($signed(y_in) <<< XY_SHIFT);
                        z[0] <= (y_in > 0) ? (26'sd32768 <<< Z_SHIFT) : -(26'sd32768 <<< Z_SHIFT);
                    end
                    else begin
                        x[0] <= $signed(x_in) <<< XY_SHIFT;
                        y[0] <= $signed(y_in) <<< XY_SHIFT;
                        z[0] <= 0;
                    end
                end
            end
            else begin
                x[0] <= 0;
                y[0] <= 0;
                z[0] <= 0;
            end

            ////////////////////////////////////////////////////////////
            //// CORDIC iteration
            ////////////////////////////////////////////////////////////
            for(i=0; i<ITER; i=i+1) begin
                if(valid_pipe[i]) begin
                    if((state == 3'b011 && y[i] >= 0) || (state == 3'b010 && z[i] < 0)) begin
                        x[i+1] <= x[i] + (y[i] >>> i);
                        y[i+1] <= y[i] - (x[i] >>> i);
                        z[i+1] <= z[i] + atan_table[i];
                    end
                    else begin
                        x[i+1] <= x[i] - (y[i] >>> i);
                        y[i+1] <= y[i] + (x[i] >>> i);
                        z[i+1] <= z[i] - atan_table[i];
                    end
                end
                else begin
                    x[i+1] <= 0;
                    y[i+1] <= 0;
                    z[i+1] <= 0;
                end
            end

            ////////////////////////////////////////////////////////////
            //// stage ITER  : multiply
            ////////////////////////////////////////////////////////////
            if(valid_pipe[ITER]) begin
                x_mul <= x[ITER] * K_INV_Q15;
                y_mul <= y[ITER] * K_INV_Q15;
                z_stage <= z[ITER];
            end
            else begin
                x_mul <= 0;
                y_mul <= 0;
                z_stage <= 0;
            end

            ////////////////////////////////////////////////////////////
            //// stage ITER+1 : rounding
            ////////////////////////////////////////////////////////////
            if(valid_pipe[ITER+1]) begin
                // Fixed unsigned concatenation bug here using $signed()
                x_rnd <= round_shift_xy($signed({x_mul[PROD_W-1], x_mul}), XY_FRAC_INT);
                y_rnd <= round_shift_xy($signed({y_mul[PROD_W-1], y_mul}), XY_FRAC_INT);
                z_rnd <= round_shift_z(z_stage, Z_SHIFT);
            end
            else begin
                x_rnd <= 0;
                y_rnd <= 0;
                z_rnd <= 0;
            end

            ////////////////////////////////////////////////////////////
            //// stage ITER+2 : saturation + output
            ////////////////////////////////////////////////////////////
            if(valid_pipe[ITER+2]) begin
                x_out <= sat16(x_rnd);
                y_out <= sat16(y_rnd);
                z_out <= sat16(z_rnd);
            end
            else begin
                x_out <= 0;
                y_out <= 0;
                z_out <= 0;
            end

        end
    end

endmodule
