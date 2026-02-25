`timescale 1ns/1ps

module tb_PE_CORDIC;

    localparam int LANES = 8;
    // ====== DUT signals ======
    reg clk, rst_n;
    reg in_valid;
    reg signed [31:0] in [0:LANES-1];
    reg [1:0] mode;
    shortint signed mmA_flat [0:63];   // 8x8 Matrix A
    shortint signed mmB_flat [0:63];   // 8x8 Matrix B
    int signed mmC_flat [0:63];   // 8x8 Matrix C (Golden)

    int signed fft_in_flat  [0:4095];
    int signed fft_out_flat [0:4095];
    int fft_in_words;
    int fft_out_words;

    integer i;
    integer watchdog;
    reg call_mem_d;
    wire call_mem_pulse;


    wire signed [31:0] out_to_exchange [0:LANES-1];
    wire cordic_valid;
    wire call_mem;
    integer wd;
    int fft_max_err_re, fft_max_err_im;
    int fft_sum_abs_err_re, fft_sum_abs_err_im;
    int fft_checked_points;
    
    string fft_in_path;
    string fft_out_path;
    int case_idx;


    // ====== TV paths ======
    localparam string MM_A_FILE   = "/home/2024_summer/2024train_04/DSP_TEST/00_TESTBED/mm_tv/matA_q15.memh";
    localparam string MM_B_FILE   = "/home/2024_summer/2024train_04/DSP_TEST/00_TESTBED/mm_tv/matB_q15.memh";
    localparam string MM_CG_FILE  = "/home/2024_summer/2024train_04/DSP_TEST/00_TESTBED/mm_tv/matC_gold.memh";
    
    task automatic run_full_fft_suite(input int num_cases);
        for (case_idx = 0; case_idx < num_cases; case_idx++) begin
            $display("\n========================================");
            $display("      RUNNING FFT CASE: %03d", case_idx);
            $display("========================================");

            // 動態產生路徑 (假設你的檔案名格式是 in_case000.memh)
            $sformat(fft_in_path,  "/home/2024_summer/2024train_04/DSP_TEST/00_TESTBED/fft8_tv_dut/in_case%03d.memh", case_idx);
            $sformat(fft_out_path, "/home/2024_summer/2024train_04/DSP_TEST/00_TESTBED/fft8_tv_dut/out_case%03d.memh", case_idx);

            // 讀取該 Case 的資料
            read_memh_32_var(fft_in_path,  fft_in_flat,  fft_in_words);
            read_memh_32_var(fft_out_path, fft_out_flat, fft_out_words);

            // 執行原本的 FFT 運算與比對任務
            run_fft_case(); 

            // 每一組跑完稍微停一下，方便在 Waveform 區分
            repeat(10) @(posedge clk);
        end
    endtask

    
    // ====== instantiate DUT ======
    global_top dut (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(in_valid),
        .in(in),
        .mode(mode),
        .out_to_exchange(out_to_exchange),
        .call_mem(call_mem),
        .cordic_valid(cordic_valid)
    );

    // ===== clock =====
    always #5 clk = ~clk;

    // ============================================================
    // Memory buffers
    // ============================================================

    // 偵測 call_mem 上升緣
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) call_mem_d <= 1'b0;
        else        call_mem_d <= call_mem;
    end
    assign call_mem_pulse = call_mem & ~call_mem_d;

    // ============================================================
    // Helpers
    // ============================================================
    function automatic int signed sext16_to32(input int unsigned x);
        int unsigned y;
    begin
        y = x & 16'hFFFF;
        if (y[15]) sext16_to32 = int'(y | 32'hFFFF0000);
        else       sext16_to32 = int'(y);
    end
    endfunction

    function automatic int signed sext32(input int unsigned x);
        int unsigned y;
    begin
        y = x & 32'hFFFFFFFF;
        if (y[31]) sext32 = int'(y);
        else       sext32 = int'(y);
    end
    endfunction
        function automatic shortint signed q15_div8_round_sat(input int signed x);
        int signed xr;
    begin
        // 四捨五入到 /8（signed）
        // 正數 +4，負數 -4，比較接近二補數對稱 rounding
        if (x >= 0) xr = (x + 4) >>> 3;
        else        xr = (x - 4) >>> 3;

        // 飽和到 Q15
        if (xr > 32767)       q15_div8_round_sat = 16'sh7FFF;
        else if (xr < -32768) q15_div8_round_sat = 16'sh8000;
        else                  q15_div8_round_sat = xr[15:0];
    end
    endfunction

    // ============================================================
    // File Readers
    // ============================================================
    task automatic read_memh_16_flat(
        input  string filename,
        output shortint signed flat [0:63]
    );
        int fd;
        string line;
        int unsigned w;
        int idx, n;
    begin
        fd = $fopen(filename, "r");
        if (fd == 0) begin
            $display("[TB][FATAL] Cannot open: %s", filename);
            $fatal;
        end
        idx = 0;
        while (!$feof(fd) && idx < 64) begin
            line = "";
            void'($fgets(line, fd));
            if (line.len() == 0) continue;
            if (line.tolower().substr(0,0) == "#") continue;
            if (line.tolower().substr(0,1) == "//") continue;
            n = $sscanf(line, "%h", w);
            if (n == 1) begin
                flat[idx] = shortint'(w & 16'hFFFF);
                idx++;
            end
        end
        $fclose(fd);
        if (idx != 64) begin
            $display("[TB][FATAL] %s loaded %0d words, expected 64", filename, idx);
            $fatal;
        end
        $display("[TB] Loaded 64x16b from %s", filename);
    end
    endtask

    task automatic read_memh_32_var(
        input  string filename,
        output int signed flat [0:4095],
        output int words
    );
        int fd;
        string line;
        int unsigned w;
        int idx, n;
    begin
        fd = $fopen(filename, "r");
        if (fd == 0) begin
            $display("[TB][FATAL] Cannot open: %s", filename);
            $fatal;
        end
        idx = 0;
        while (!$feof(fd) && idx < 4096) begin
            line = "";
            void'($fgets(line, fd));
            if (line.len() == 0) continue;
            if (line.tolower().substr(0,0) == "#") continue;
            if (line.tolower().substr(0,1) == "//") continue;
            n = $sscanf(line, "%h", w);
            if (n == 1) begin
                flat[idx] = sext32(w);
                idx++;
            end
        end
        $fclose(fd);
        words = idx;
        $display("[TB] Loaded %0d x 32b from %s", words, filename);
    end
    endtask

    // ============================================================
    // FFT Task: Drive rows based on call_mem pulse
    // ============================================================
    task automatic drive_rows_on_call_mem(
        input string tag,
        input int signed data_flat [0:4095], 
        input int total_rows
    );
        int row;
        int wd;
        int k, base;
    begin
        row = 0;
        wd  = 0;

        // Init input
        for (k = 0; k < LANES; k++) in[k] = '0;

        while (row < total_rows) begin
            @(posedge clk);
            wd++;

            if (wd > 50000) begin
                $display("[TB][FATAL] %s wait call_mem timeout. row=%0d/%0d", tag, row, total_rows);
                $fatal;
            end

            if (call_mem_pulse) begin
                base = row * LANES;
                for (k = 0; k < LANES; k++) begin
                    in[k] = data_flat[base + k];
                end
                // Debug msg
                // $display("[TB][%s] Driven row %0d", tag, row);
                row++;
                wd = 0;
            end
        end

        // Clear after done
        @(posedge clk);
        for (k = 0; k < LANES; k++) in[k] = '0;
        $display("[TB][%s] Driven all %0d rows.", tag, total_rows);
    end
    endtask

    // ============================================================
    // FFT Comparison Task
    // ============================================================
    
    task automatic run_fft_case;
        int rows_in;
        int rows_out;
        int row;
        int mismatch;
        int cordic_cnt;
    begin
        mismatch = 0;

        // ===== reset FFT error stats =====
        fft_max_err_re     = 0;
        fft_max_err_im     = 0;
        fft_sum_abs_err_re = 0;
        fft_sum_abs_err_im = 0;
        fft_checked_points = 0;

        if (fft_in_words % LANES != 0) $fatal;
        // rows_in  = fft_in_words  / LANES;
        // rows_out = fft_out_words / LANES;
        rows_in  = 1;
        rows_out = 1;

        mode = 2'b01; // FFT
        $display("\n=== RUN FFT (rows=%0d) ===", rows_in);

        // (1) Pulse in_valid to kick FSM to WAIT_CORDIC and start CORDIC
        @(negedge clk); in_valid = 1;
        @(negedge clk); in_valid = 0;

        // (2) Wait 4 cordic_valid pulses
        cordic_cnt = 0;
        watchdog   = 0;
        while (cordic_cnt < 4 && watchdog < 2000) begin
            @(posedge clk);
            if (cordic_valid) cordic_cnt = cordic_cnt + 1;
            watchdog++;
        end
        if (cordic_cnt < 4) begin
            $display("[TB][FATAL] FFT cordic_valid failed.");
            $finish;
        end

        @(posedge clk);

        // (3) Drive Data
        drive_rows_on_call_mem("FFT_IN", fft_in_flat, rows_in);

        // (4) Wait Latency
        wd = 0;
        while (!dut.u_PE.ready) begin
            @(posedge clk);
            wd++;
            if (wd > 2000) $fatal("[TB] FFT Timeout waiting for ready!");
        end
        mode = 2'b00;

        // (5) Compare
        for (row = 0; row < rows_out; row++) begin
            @(posedge clk);
            compare_out_row("FFT", row, fft_out_flat, mismatch);
        end

        $display("[TB][FFT] max_abs_err_re=%0d, max_abs_err_im=%0d", fft_max_err_re, fft_max_err_im);

        if (fft_checked_points > 0) begin
            $display("[TB][FFT] mean_abs_err_re=%0f, mean_abs_err_im=%0f",
                (1.0 * fft_sum_abs_err_re) / fft_checked_points,
                (1.0 * fft_sum_abs_err_im) / fft_checked_points);
        end

        $display("[TB][FFT] Done. mismatches=%0d\n", mismatch);
    end
    endtask
    function automatic int abs_int(input int x);
    begin
        abs_int = (x < 0) ? -x : x;
    end
    endfunction
    task automatic compare_out_row(
        input string tag,
        input int out_row_idx,
        input int signed gold_flat [0:4095],
        inout int mismatch_cnt
    );
        int k, base;
        int signed dutv, goldv;
        int signed err_re, err_im;
        int tol_re, tol_im;

        shortint signed dut_re, dut_im;
        shortint signed gold_re, gold_im;
        shortint signed gold_re_cmp, gold_im_cmp;  // 比對用（FFT會縮放）
    begin
        base = out_row_idx * LANES;

        // FFT 容差 (LSB)
        tol_re = (tag == "FFT") ? 256 : 0;
        tol_im = (tag == "FFT") ? 256 : 0;
        $display("[TB][FFT] tolerance_re=%0d, tolerance_im=%0d", tol_re, tol_im);

        for (k = 0; k < LANES; k++) begin
            dutv  = out_to_exchange[k];
            goldv = gold_flat[base + k];

            dut_re  = $signed(dutv[31:16]);
            dut_im  = $signed(dutv[15:0]);
            gold_re = $signed(goldv[31:16]);
            gold_im = $signed(goldv[15:0]);

            // 預設直接比（MM）
            gold_re_cmp = gold_re;
            gold_im_cmp = gold_im;


            err_re = dut_re - gold_re_cmp;
            err_im = dut_im - gold_im_cmp;

            if (tag == "FFT") begin
                // ===== 統計 =====
                if (abs_int(err_re) > fft_max_err_re) fft_max_err_re = abs_int(err_re);
                if (abs_int(err_im) > fft_max_err_im) fft_max_err_im = abs_int(err_im);

                fft_sum_abs_err_re = fft_sum_abs_err_re + abs_int(err_re);
                fft_sum_abs_err_im = fft_sum_abs_err_im + abs_int(err_im);
                fft_checked_points = fft_checked_points + 1;

                // ===== FFT 容差比對 =====
                if ((abs_int(err_re) > tol_re) || (abs_int(err_im) > tol_im)) begin
                    mismatch_cnt++;
                    $display("[MIS] %s row=%0d lane=%0d | DUT=(%0d,%0d) GOLDcmp=(%0d,%0d) ORIG_GOLD=(%0d,%0d) | ERR=(%0d,%0d)",
                        tag, out_row_idx, k,
                        dut_re, dut_im,
                        gold_re_cmp, gold_im_cmp,
                        gold_re, gold_im,
                        err_re, err_im);
                end
            end
            else begin
                // MM 還是 bit-exact
                if (dutv !== goldv) begin
                    mismatch_cnt++;
                    $display("[MIS] %s row=%0d lane=%0d | DUT=%0d GOLD=%0d",
                        tag, out_row_idx, k, dutv, goldv);
                end
            end
        end
    end
    endtask
    // ============================================================
    // MATMUL Helpers (修正版: 記憶體串流送法)
    // ============================================================
// 核心數據準備邏輯：對應 A 固定一排，B 滾動 8 排
task automatic prepare_mm_parallel(input int row_a_idx, input int step_k);
    int lane;
    shortint signed a_val, b_val;
begin
    // 【修改重點】: A 矩陣在這一整組 (8 cycles) 運算中固定抓取特定的 Row
    // 我們讓 step_k 決定在這一排中取哪一個元素，並廣播給 8 個 Lane
   
    for (lane = 0; lane < 8; lane++) begin
        a_val = mmA_flat[row_a_idx * 8 + lane]; // 固定 Row，Column 由 step_k 決定

        // B 矩陣則維持原樣：每一拍取 B 的一整排，每個 Lane 負責一個 Column
        b_val = mmB_flat[step_k * 8 + lane];

        // 所有的 Lane 在這一拍都拿到同一個 a_val，但拿到不同的 b_val
        in[lane] = {a_val, b_val};
    end
end
endtask
task automatic run_mm;
    int mismatch;
    int r_a, k;
    int wd;
begin
    mismatch = 0;
    mode = 2'b10; // Matmul 模式
    $display("\n=== START MATMUL: Continuous Burst Mode ===");

    // 啟動 FSM
    @(negedge clk); in_valid <= 1'b1;
    @(negedge clk); in_valid <= 0;

    // 外層迴圈：計算 C 的每一排 (Row 0 ~ 7)
    for (r_a = 0; r_a < 8; r_a++) begin
        
        // --- 1. 等待 call_mem 拉高 ---
        while (call_mem !== 1'b1) @(posedge clk);
        
        // --- 2. 連續讀取模式 (Burst) ---
        // 當 call_mem 為高，每一拍給出一個 k，不間斷
        for (k = 0; k < 8; k++) begin
            prepare_mm_parallel(r_a, k); 
            @(posedge clk); // 資料在這一拍被 PE 鎖存
        end

        // 傳輸完畢，清空輸入避免干擾
        for (int l = 0; l < 8; l++) in[l] <= '0;

        // --- 3. 等待 PE 運算完成 (Ready) ---
        wd = 0;
        while (!dut.u_PE.ready) begin
            @(posedge clk);
            wd++;
            if (wd > 2000) $fatal("[TB] Timeout! PE ready not found for Row %0d", r_a);
        end

        // --- 4. 數值驗證 (原本的驗證邏輯) ---
        #0.1; 
        $display("[TB] Verifying Row %0d...", r_a);
        for (int lane = 0; lane < 8; lane++) begin
            int signed dut_res = out_to_exchange[lane];
            int signed gold_res = mmC_flat[r_a * 8 + lane];

            if (dut_res !== gold_res) begin
                mismatch++;
                $display("  [MISMATCH] Col %0d | DUT: %d | GOLD: %d", lane, dut_res, gold_res);
            end else begin
                $display("  [MATCH]    Col %0d | Val: %d", lane, dut_res);
            end
        end
        
        // 確保 ready 訊號結束後再進入下一排計算
        while (dut.u_PE.ready) @(posedge clk);
    end

    if (mismatch == 0)
        $display("\n*** ALL TEST CASES PASSED (8x8 Matrix) ***\n");
    else
        $display("\n*** TEST FAILED: Total Mismatches = %0d ***\n", mismatch);
    
end
endtask
    // ============================================================
    // MAIN
    // ============================================================
    initial begin
        $fsdbDumpfile("global_top_vs_golden.fsdb");
        $fsdbDumpvars(0, "+mda");

        clk = 0;
        rst_n = 0;
        in_valid = 0;
        mode = 0;

        for (i = 0; i < LANES; i++) in[i] = 0;

        // Load TVs
        read_memh_16_flat(MM_A_FILE, mmA_flat);
        read_memh_16_flat(MM_B_FILE, mmB_flat);

        // Load MM Golden
        begin : load_mmC
            int tmp_words;
            int signed tmp32 [0:4095];
            read_memh_32_var(MM_CG_FILE, tmp32, tmp_words);
            if (tmp_words != 64) begin
                $display("[TB][FATAL] %s loaded %0d words, expected 64", MM_CG_FILE, tmp_words);
                $fatal;
            end
            for (i = 0; i < 64; i++) mmC_flat[i] = tmp32[i];
        end

       
        // Reset
        #20 rst_n = 1;
        repeat(5) @(posedge clk);
        
        // Start
        // in_valid = 1;
        // @(posedge clk);
        // in_valid = 0;

        // ========================================================
        // RUN MATMUL
        // ========================================================
        run_mm();

        repeat(20) @(posedge clk);
       

        // ========================================================
        // RUN MULTI-CASE FFT (跑 100 組)
        // ========================================================
        run_full_fft_suite(10); 

        $display("\n[TB] All FFT Test Suites Finished.");
        @(posedge clk); 
        mode = 2'b00;
        repeat(20) @(posedge clk);
        $finish;
    end

endmodule
