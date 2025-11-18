`timescale 1ns/1ps

module tb_pe_cordic;

// ---------------------
// 1. Clock & reset
// ---------------------
reg clk = 0;
reg rst_n = 0;

always #5 clk = ~clk;  // 100MHz clock


// ---------------------
// 2. CORDIC Interface
// ---------------------
reg in_valid;
reg signed [15:0] theta;

wire signed [15:0] cos_wire;
wire signed [15:0] sin_wire;
wire cordic_valid;

CORDIC cordic_u(
    .clk(clk),
    .rst_n(rst_n),
    .in_valid(in_valid),
    .theta(theta),
    .cos_out(cos_wire),
    .sin_out(sin_wire),
    .out_valid(cordic_valid)
);

// Twiddle factor from CORDIC
wire signed [15:0] tw_re = cos_wire;
wire signed [15:0] tw_im = -sin_wire;  // FFT twiddle = cos - j sin


// ---------------------
// 3. PE Interface
// ---------------------
reg signed [15:0] in1_re [0:7];
reg signed [15:0] in1_im [0:7];
reg signed [15:0] in2_re [0:7]; // twiddle re
reg signed [15:0] in2_im [0:7]; // twiddle im

wire signed [15:0] out_re [0:7];
wire signed [15:0] out_im [0:7];

PE pe_u(
    .clk(clk),
    .rst_n(rst_n),
    .in1_re(in1_re),
    .in1_im(in1_im),
    .in2_re(in2_re),
    .in2_im(in2_im),
    .out_re(out_re),
    .out_im(out_im)
);


// ======================================================================
// 4. Test flow control
// ======================================================================
integer i;

// Precomputed Q1.15 angles (rad * 32768)
// 0°, -45°, -90°, -135°
localparam signed [15:0] ANGLES [0:3] = '{
    16'sd0,
    -16'sd11585,   // -45° = -π/4 * 32768 = -0.785398 * 32768
    -16'sd23170,   // -90° = -π/2
    -16'sd34755    // -135° = -3π/4
};


// ======================================================================
// 5. Test procedure
// ======================================================================
initial begin
    // Dump wave
    $fsdbDumpfile("pe_cordic.fsdb");
	$fsdbDumpvars(0,"+mda");
    $fsdbDumpvars();
    // Reset
    rst_n = 0;
    in_valid = 0;
    #40;
    rst_n = 1;
    #20;

    // Loop through four twiddle angles
    for (i = 0; i < 4; i = i + 1) begin
        run_one_twiddle(ANGLES[i]);
    end
    
    #200;
    $finish;
end


// ======================================================================
// 6. TASK: Run one twiddle & feed into PE
// ======================================================================
task run_one_twiddle(input signed [15:0] ang);
integer k;
begin
    $display("\n==============================================");
    $display(" Testing Twiddle Angle: %d", ang);
    $display("==============================================");

    // Send angle into CORDIC
    theta = ang;
    in_valid = 1;
    #10;
    in_valid = 0;

    // Wait for CORDIC
    @(posedge cordic_valid);

    $display("[CORDIC] cos = %d, sin = %d → tw_re=%d, tw_im=%d",
             cos_wire, sin_wire, tw_re, tw_im);

    // Feed twiddle to all PE channels
    for (k = 0; k < 8; k = k + 1) begin
        in2_re[k] = tw_re;
        in2_im[k] = tw_im;
    end

    // Feed test samples (complex ramp)
    for (k = 0; k < 8; k = k + 1) begin
        in1_re[k] = k * 100;
        in1_im[k] = k * 50;
    end

    // Wait for PE to compute (depends on your PE pipelining)
    #50;

    // Print output
    for (k = 0; k < 8; k = k + 1) begin
        $display("PE[%0d] = %d + j%d", k, out_re[k], out_im[k]);
    end
end
endtask

endmodule
