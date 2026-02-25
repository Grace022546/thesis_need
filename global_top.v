module global_top(
    input clk,
    input rst_n,
    input in_valid,

    input signed [31:0] in [0:7],  

    input [1:0] mode, // 0: FFT, 1: Matrix Multiply

    // rename output to Z_*
    output reg signed [31:0] out_to_exchange [0:7],
    output reg call_mem,

    output cordic_valid
);


    wire signed [15:0] cos_out;
    wire signed [15:0] sin_out;
    reg [6:0] counter;
    reg signed [15:0] angle_cos_reg [0:7];
    reg signed [15:0] angle_sin_reg [0:7];
  
    integer i;
    wire ready;

    //========================================================
    // FSM 
    //========================================================
    reg [2:0] state, next_state; 
    parameter  IDLE = 3'b000,
               WAIT_MODE = 3'b001,
               WAIT_CORDIC = 3'b010,
               FFT_PROCESS = 3'b011,
               MM_PROCESS = 3'b100;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) state <= IDLE;
        else state <= next_state;
    end
    always @(*) begin
        case(state)
            IDLE: begin
                if(in_valid) next_state = WAIT_MODE;
                else next_state = IDLE;
            end
            WAIT_MODE: begin
                if(mode==1) next_state = WAIT_CORDIC;
                else if(mode==2) next_state = MM_PROCESS;
                else next_state = WAIT_MODE;
            end
            WAIT_CORDIC: begin
                if(counter==3 && cordic_valid) next_state = FFT_PROCESS;
                else next_state = WAIT_CORDIC;
            end
            FFT_PROCESS: begin
                if(ready) next_state = WAIT_MODE;
                else next_state = FFT_PROCESS;
            end
            MM_PROCESS: begin
                //if(counter==64) next_state = WAIT_MODE;
                if(counter==12) next_state = WAIT_MODE;
                else next_state = MM_PROCESS;
            end
            default: next_state = WAIT_MODE;
        endcase
    end

    //========================================================
    // counter 
    //========================================================
    
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) counter <= 0;
        else if(state != next_state)counter <= 0;
        else if(state==WAIT_CORDIC) begin
            if (cordic_valid) counter <= counter + 1;
            else counter <= counter;
        end
        else counter <= counter+1;
        
    end

reg angle_valid;

always@(posedge clk or negedge rst_n) begin
    if(!rst_n) angle_valid <= 0;
    else if((state==WAIT_CORDIC && cordic_valid && counter<3)||(next_state==WAIT_CORDIC && state!=WAIT_CORDIC)) angle_valid <= 1;
    else angle_valid <= 0;
end

reg signed [15:0] theta;
always@(*) begin
    if(state==WAIT_CORDIC) begin
        case(counter)
            0: theta = 16'sd0;
            1: theta = -16'sd8192;   // -pi/4
            2: theta = -16'sd16384;  // -pi/2
            3: theta = -16'sd24576;  // -3pi/4
            default: theta = 16'sd0;
        endcase
    end
    else theta = 16'sd0;
end
    
CORDIC cordic_u (.clk(clk),.rst_n(rst_n),.state(state),.theta(theta),.cos_out(cos_out),.sin_out(sin_out),.out_valid(cordic_valid),.angle_valid(angle_valid));

always@(posedge clk or negedge rst_n) begin
    if(!rst_n) begin
        for(i=0;i<8;i=i+1) begin
            angle_cos_reg[i] <= 0;
            angle_sin_reg[i] <= 0;
        end
    end
    else begin
        if(cordic_valid) begin
            for(i=0; i<3; i=i+1) begin
                angle_cos_reg[i] <= angle_cos_reg[i+1];
                angle_sin_reg[i] <= angle_sin_reg[i+1];
            end
            angle_cos_reg[3] <= cos_out;
            angle_sin_reg[3] <= sin_out;
        end
    end
end
// always@(posedge clk or negedge rst_n) begin
//     if(!rst_n) begin
//         for(i=0;i<8;i=i+1) begin
//             angle_cos_reg[i] <= 0;
//             angle_sin_reg[i] <= 0;
//         end
//     end
//     else begin
//         angle_cos_reg[0] <= 32767;
//         angle_sin_reg[0] <= 0;
//         angle_cos_reg[1] <= 23170;;
//         angle_sin_reg[1] <= -23170;
//         angle_cos_reg[2] <= 0;
//         angle_sin_reg[2] <= -32768;
//         angle_cos_reg[3] <= -23170;
//         angle_sin_reg[3] <= -23170;
//     end
// end



reg signed [31:0] pe_in [0:7];
reg signed [31:0] angle [0:7];
wire signed [31:0] out [0:7];
integer p;
always @(*) begin
  for (p=0; p<8; p=p+1) begin
    pe_in[p] = in[p];
    angle[p] = {angle_cos_reg[p],angle_sin_reg[p]  };
  end
  
end

PE u_PE(
    .clk(clk),
    .rst_n(rst_n),
    .in(pe_in), 
    .angle(angle),
    .state(state), // 0: FFT, 1: Matrix Multiply
    .out(out),
    .call_mem(call_mem),
    .ready(ready)
);
//========================================================
// output register
//========================================================
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for(i=0;i<8;i=i+1) begin
                out_to_exchange[i] <= 0;
            end
        end 
        else begin
            if(ready) begin
                for(i=0;i<8;i=i+1) begin
                    out_to_exchange[i] <= out[i];
                end
            end
        end
    end
   

endmodule
