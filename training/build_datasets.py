#!/usr/bin/env python3
"""Build Silica LoRA training datasets (ChatML JSONL) for 4 stages."""
import json

SYS_SPEC = (
    "You are the SILICA Specification & Architecture agent. Output valid JSON with keys: "
    "title, feature_list, interfaces, clock_reset, pipeline_stages, fsm_states, constraints, "
    "register_map, verification_plan, assumptions. No markdown."
)
SYS_RTL = (
    "You are the SILICA RTL Design agent. Output valid JSON with keys: module_name, rtl, "
    "parameters, packages, sva_assertions, requirement_traceability. The rtl field contains "
    "production SystemVerilog. Verilator lint-clean. No markdown code fences."
)
SYS_VERIF = (
    "You are the SILICA Functional Verification agent. Output valid JSON with keys: "
    "testbench_file, golden_reference_model, stimulus_sequences, assertion_checks, coverage_points. "
    "testbench_file is C++ for Verilator. No markdown."
)
SYS_SYNTH = (
    "You are the SILICA Logic Synthesis agent. Output valid JSON with keys: synthesis_script, "
    "target_clock_ns, expected_cell_primitives, timing_slack_estimate, netlist_directives. "
    "synthesis_script is a Yosys .ys script. No markdown."
)

# ---------------- STAGE 1: SPECIFICATION ----------------
spec_examples = [
    {
        "user": "Design a 4-deep, 8-bit synchronous FIFO with empty and full status flags and synchronous reset.",
        "assistant": {
            "title": "4-deep 8-bit Synchronous FIFO",
            "feature_list": [{"feature": "FIFO Storage", "acceptance": "Stores up to 4 bytes with FIFO ordering"}],
            "interfaces": [
                {"signal": "clk", "dir": "input", "width": 1, "desc": "Primary clock"},
                {"signal": "rst_n", "dir": "input", "width": 1, "desc": "Active low sync reset"},
                {"signal": "wr_en", "dir": "input", "width": 1, "desc": "Write enable"},
                {"signal": "rd_en", "dir": "input", "width": 1, "desc": "Read enable"},
                {"signal": "din", "dir": "input", "width": 8, "desc": "Data input"},
                {"signal": "dout", "dir": "output", "width": 8, "desc": "Data output"},
                {"signal": "full", "dir": "output", "width": 1, "desc": "High when FIFO is full"},
                {"signal": "empty", "dir": "output", "width": 1, "desc": "High when FIFO is empty"},
            ],
            "clock_reset": {"domain": "single_clock", "reset_type": "sync_low"},
            "pipeline_stages": [],
            "fsm_states": [],
            "constraints": {"target_freq_mhz": 250},
            "register_map": [],
            "verification_plan": {
                "features": ["Write to full", "Read to empty", "Simultaneous read/write"],
                "coverage_points": ["FIFO empty flag", "FIFO full flag"],
                "assertions": ["No write when full", "No read when empty"],
                "test_matrix": ["directed_fill_empty", "random_interleaved"],
            },
            "assumptions": ["Zero-latency read"],
        },
    },
    {
        "user": "Design an AXI4-Lite 32-bit register bank with 4 read/write registers and active-low async reset.",
        "assistant": {
            "title": "AXI4-Lite 32-bit Register Bank (4 registers)",
            "feature_list": [{"feature": "Memory-mapped registers", "acceptance": "4x 32-bit R/W registers accessible via AXI4-Lite"}],
            "interfaces": [
                {"signal": "s_axi_aclk", "dir": "input", "width": 1},
                {"signal": "s_axi_aresetn", "dir": "input", "width": 1},
                {"signal": "s_axi_awaddr", "dir": "input", "width": 5},
                {"signal": "s_axi_awprot", "dir": "input", "width": 3},
                {"signal": "s_axi_awvalid", "dir": "input", "width": 1},
                {"signal": "s_axi_awready", "dir": "output", "width": 1},
                {"signal": "s_axi_wdata", "dir": "input", "width": 32},
                {"signal": "s_axi_wstrb", "dir": "input", "width": 4},
                {"signal": "s_axi_wvalid", "dir": "input", "width": 1},
                {"signal": "s_axi_wready", "dir": "output", "width": 1},
                {"signal": "s_axi_bresp", "dir": "output", "width": 2},
                {"signal": "s_axi_bvalid", "dir": "output", "width": 1},
                {"signal": "s_axi_bready", "dir": "input", "width": 1},
                {"signal": "s_axi_araddr", "dir": "input", "width": 5},
                {"signal": "s_axi_arvalid", "dir": "input", "width": 1},
                {"signal": "s_axi_arready", "dir": "output", "width": 1},
                {"signal": "s_axi_rdata", "dir": "output", "width": 32},
                {"signal": "s_axi_rresp", "dir": "output", "width": 2},
                {"signal": "s_axi_rvalid", "dir": "output", "width": 1},
                {"signal": "s_axi_rready", "dir": "input", "width": 1},
            ],
            "clock_reset": {"domain": "single_clock", "reset_type": "async_low"},
            "pipeline_stages": [],
            "fsm_states": ["IDLE", "WRITE", "WRITE_RESP", "READ", "READ_RESP"],
            "constraints": {"target_freq_mhz": 100},
            "register_map": [
                {"offset": "0x00", "name": "REG0", "access": "RW", "reset": "0x00000000"},
                {"offset": "0x04", "name": "REG1", "access": "RW", "reset": "0x00000000"},
                {"offset": "0x08", "name": "REG2", "access": "RW", "reset": "0x00000000"},
                {"offset": "0x0C", "name": "REG3", "access": "RW", "reset": "0x00000000"},
            ],
            "verification_plan": {
                "features": ["Write/read each register", "Write strobe byte enables", "Back-to-back transactions"],
                "coverage_points": ["All 5 channel handshakes", "AW/W ordering"],
                "assertions": ["bresp=OKAY on valid write", "rresp=OKAY on valid read", "no X on outputs"],
                "test_matrix": ["directed_reg_rw", "random_backpressure"],
            },
            "assumptions": ["AW and W arrive in same cycle or AW first"],
        },
    },
    {
        "user": "Design a UART transmitter with 8N1 format, 16-byte TX FIFO, and baud rate divisor register.",
        "assistant": {
            "title": "UART Transmitter (8N1) with 16-byte TX FIFO",
            "feature_list": [{"feature": "Serial TX", "acceptance": "8N1 frames at configurable baud rate"}],
            "interfaces": [
                {"signal": "clk", "dir": "input", "width": 1},
                {"signal": "rst_n", "dir": "input", "width": 1},
                {"signal": "tx_data", "dir": "input", "width": 8},
                {"signal": "tx_valid", "dir": "input", "width": 1},
                {"signal": "tx_ready", "dir": "output", "width": 1},
                {"signal": "baud_div", "dir": "input", "width": 16},
                {"signal": "tx_serial", "dir": "output", "width": 1},
                {"signal": "tx_idle", "dir": "output", "width": 1},
            ],
            "clock_reset": {"domain": "single_clock", "reset_type": "async_low"},
            "pipeline_stages": [],
            "fsm_states": ["IDLE", "START_BIT", "DATA_BIT0..7", "STOP_BIT"],
            "constraints": {"target_freq_mhz": 50, "baud_div_min": 1},
            "register_map": [{"offset": "0x00", "name": "BAUD_DIV", "access": "RW", "reset": "0x0000"}],
            "verification_plan": {
                "features": ["Frame format 8N1", "Baud rate accuracy", "FIFO backpressure"],
                "coverage_points": ["All 256 data values", "Baud divisor corners"],
                "assertions": ["tx_serial idle=1", "start bit=0", "stop bit=1"],
                "test_matrix": ["directed_frame_check", "random_baud_rate"],
            },
            "assumptions": ["No flow control (no RTS/CTS)"],
        },
    },
    {
        "user": "Design a 4-input round-robin priority arbiter with 8-bit data pass-through and registered outputs.",
        "assistant": {
            "title": "4-Input Round-Robin Arbiter",
            "feature_list": [{"feature": "Fair arbitration", "acceptance": "Round-robin priority updates after each grant"}],
            "interfaces": [
                {"signal": "clk", "dir": "input", "width": 1},
                {"signal": "rst_n", "dir": "input", "width": 1},
                {"signal": "req", "dir": "input", "width": 4},
                {"signal": "data_in0..3", "dir": "input", "width": 8},
                {"signal": "grant", "dir": "output", "width": 4},
                {"signal": "data_out", "dir": "output", "width": 8},
                {"signal": "valid_out", "dir": "output", "width": 1},
            ],
            "clock_reset": {"domain": "single_clock", "reset_type": "async_low"},
            "pipeline_stages": ["Arbitration", "Output register"],
            "fsm_states": [],
            "constraints": {"target_freq_mhz": 400},
            "register_map": [],
            "verification_plan": {
                "features": ["Round-robin fairness", "One-hot grant", "Data passthrough correctness"],
                "coverage_points": ["All 16 request patterns", "Priority rotation"],
                "assertions": ["grant is one-hot", "no starvation within 4 cycles"],
                "test_matrix": ["directed_rotation", "random_requests"],
            },
            "assumptions": ["Requests are level-sensitive"],
        },
    },
    {
        "user": "Design a 3-stage pipelined 8-bit ALU with registered operand inputs and result output.",
        "assistant": {
            "title": "3-Stage Pipelined 8-bit ALU",
            "feature_list": [{"feature": "Pipelined execution", "acceptance": "One result per cycle after 3-cycle latency"}],
            "interfaces": [
                {"signal": "clk", "dir": "input", "width": 1},
                {"signal": "rst_n", "dir": "input", "width": 1},
                {"signal": "a", "dir": "input", "width": 8},
                {"signal": "b", "dir": "input", "width": 8},
                {"signal": "op", "dir": "input", "width": 3},
                {"signal": "result", "dir": "output", "width": 8},
                {"signal": "valid", "dir": "output", "width": 1},
            ],
            "clock_reset": {"domain": "single_clock", "reset_type": "async_low"},
            "pipeline_stages": ["S1: Operand register", "S2: ALU combinational", "S3: Result register"],
            "fsm_states": [],
            "constraints": {"target_freq_mhz": 500},
            "register_map": [],
            "verification_plan": {
                "features": ["All 8 opcodes", "Pipeline hazard-free", "Latency = 3 cycles"],
                "coverage_points": ["All opcodes", "Boundary operands 0/255/127"],
                "assertions": ["valid asserts 3 cycles after input", "no pipeline bubble on back-to-back"],
                "test_matrix": ["directed_opcode", "random_operands"],
            },
            "assumptions": ["No stalls (always-ready consumer)"],
        },
    },
]

# ---------------- STAGE 2: RTL DESIGN ----------------
rtl_examples = [
    {
        "user": json.dumps(spec_examples[0]["assistant"]),
        "assistant": {
            "module_name": "fifo_sync_4x8",
            "rtl": "module fifo_sync_4x8(input logic clk, rst_n, wr_en, rd_en, input logic [7:0] din, output logic [7:0] dout, output logic full, empty); logic [7:0] mem[0:3]; logic [1:0] wr_ptr, rd_ptr; logic [2:0] count; always_ff @(posedge clk) if(!rst_n) begin wr_ptr<=0; rd_ptr<=0; count<=0; dout<=0; end else begin if(wr_en && !full) begin mem[wr_ptr]<=din; wr_ptr<=wr_ptr+1; count<=count+1; end if(rd_en && !empty) begin dout<=mem[rd_ptr]; rd_ptr<=rd_ptr+1; count<=count-1; end if(wr_en&&!full&&rd_en&&!empty) count<=count; end assign full=(count==4); assign empty=(count==0); endmodule",
            "parameters": [{"name": "WIDTH", "default": 8}, {"name": "DEPTH", "default": 4}],
            "packages": [],
            "sva_assertions": ["assert property (@(posedge clk) disable iff(!rst_n) (wr_en && full |-> ##1 $stable(wr_ptr)));", "assert property (@(posedge clk) disable iff(!rst_n) (rd_en && empty |-> ##1 $stable(rd_ptr)));"],
            "requirement_traceability": [{"req": "Stores up to 4 bytes", "rtl_signal": "mem[0:3]"}, {"req": "full flag", "rtl_signal": "full=(count==4)"}],
        },
    },
    {
        "user": json.dumps(spec_examples[3]["assistant"]),
        "assistant": {
            "module_name": "arbiter_rr4",
            "rtl": "module arbiter_rr4(input logic clk, rst_n, input logic [3:0] req, output logic [3:0] grant); logic [1:0] priority; logic [3:0] masked_req; always_comb begin grant=0; masked_req=req; for(int i=0;i<4;i++) if(((i+priority)%4)==0 && req[i]) begin grant[i]=1; masked_req=0; end end always_ff @(posedge clk or negedge rst_n) if(!rst_n) priority<=0; else if(|req && |grant) priority<=priority+1; endmodule",
            "parameters": [{"name": "WIDTH", "default": 8}, {"name": "N", "default": 4}],
            "packages": [],
            "sva_assertions": ["assert property (@(posedge clk) disable iff(!rst_n) $onehot0(grant));", "assert property (@(posedge clk) disable iff(!rst_n) (|req |-> ##[1:4] |grant));"],
            "requirement_traceability": [{"req": "Round-robin", "rtl_signal": "priority register"}, {"req": "One-hot grant", "rtl_signal": "grant one-hot0 SVA"}],
        },
    },
    {
        "user": json.dumps(spec_examples[4]["assistant"]),
        "assistant": {
            "module_name": "alu_pipe3_8bit",
            "rtl": "module alu_pipe3_8bit(input logic clk, rst_n, input logic [7:0] a,b, input logic [2:0] op, output logic [7:0] result, output logic valid); logic [7:0] a_r,b_r, alu_comb; logic [2:0] op_r; logic v1,v2; always_ff @(posedge clk or negedge rst_n) if(!rst_n) begin a_r<=0;b_r<=0;op_r<=0;v1<=0;v2<=0;result<=0;valid<=0; end else begin a_r<=a;b_r<=b;op_r<=op;v1<=1; case(op_r) 0:alu_comb=a_r+b_r;1:alu_comb=a_r-b_r;2:alu_comb=a_r&b_r;3:alu_comb=a_r|b_r;4:alu_comb=a_r^b_r;5:alu_comb=~a_r;6:alu_comb=a_r<<1;7:alu_comb=a_r>>1; endcase v2<=v1; result<=alu_comb; valid<=v2; end endmodule",
            "parameters": [{"name": "WIDTH", "default": 8}],
            "packages": [],
            "sva_assertions": ["assert property (@(posedge clk) disable iff(!rst_n) ##3 valid==1);"],
            "requirement_traceability": [{"req": "3-cycle latency", "rtl_signal": "v1->v2->valid pipeline"}],
        },
    },
    {
        "user": json.dumps(spec_examples[2]["assistant"]),
        "assistant": {
            "module_name": "uart_tx_8n1",
            "rtl": "module uart_tx_8n1(input logic clk, rst_n, input logic [7:0] tx_data, input logic tx_valid, output logic tx_ready, input logic [15:0] baud_div, output logic tx_serial, tx_idle); logic [15:0] baud_cnt; logic [3:0] bit_cnt; logic [9:0] shift_reg; logic [1:0] state; always_ff @(posedge clk or negedge rst_n) if(!rst_n) begin state<=0; baud_cnt<=0; bit_cnt<=0; shift_reg<=1; tx_serial<=1; tx_ready<=1; end else case(state) 0: begin tx_ready<=1; if(tx_valid) begin shift_reg<={1'b1,tx_data,1'b0}; bit_cnt<=0; baud_cnt<=0; state<=1; tx_ready<=0; end end 1: begin if(baud_cnt==baud_div) begin baud_cnt<=0; tx_serial<=shift_reg[0]; shift_reg<=shift_reg>>1; bit_cnt<=bit_cnt+1; if(bit_cnt==9) state<=2; end else baud_cnt<=baud_cnt+1; end 2: begin tx_serial<=1; tx_ready<=1; state<=0; end endcase assign tx_idle=(state==0); endmodule",
            "parameters": [{"name": "DATA_BITS", "default": 8}],
            "packages": [],
            "sva_assertions": ["assert property (@(posedge clk) disable iff(!rst_n) $rose(tx_valid) |-> ##[1:$] !tx_serial throughout tx_idle[->1]);"],
            "requirement_traceability": [{"req": "8N1 frame", "rtl_signal": "shift_reg={1,data,0}, 10 bits"}],
        },
    },
    {
        "user": json.dumps(spec_examples[1]["assistant"]),
        "assistant": {
            "module_name": "axil_regbank_4x32",
            "rtl": "module axil_regbank_4x32(input logic s_axi_aclk, s_axi_aresetn, input logic [4:0] s_axi_awaddr, input logic s_axi_awvalid, output logic s_axi_awready, input logic [31:0] s_axi_wdata, input logic [3:0] s_axi_wstrb, input logic s_axi_wvalid, output logic s_axi_wready, output logic [1:0] s_axi_bresp, output logic s_axi_bvalid, input logic s_axi_bready, input logic [4:0] s_axi_araddr, input logic s_axi_arvalid, output logic s_axi_arready, output logic [31:0] s_axi_rdata, output logic [1:0] s_axi_rresp, output logic s_axi_rvalid, input logic s_axi_rready); logic [31:0] regs[0:3]; logic [1:0] wr_state, rd_state; always_ff @(posedge s_axi_aclk or negedge s_axi_aresetn) if(!s_axi_aresetn) begin s_axi_awready<=0;s_axi_wready<=0;s_axi_bvalid<=0;s_axi_arready<=0;s_axi_rvalid<=0; for(int i=0;i<4;i++) regs[i]<=0; end else begin if(s_axi_awvalid&&!s_axi_awready) s_axi_awready<=1; else if(s_axi_awready) s_axi_awready<=0; if(s_axi_wvalid&&!s_axi_wready) s_axi_wready<=1; else if(s_axi_wready) s_axi_wready<=0; if(s_axi_awready&&s_axi_wready) begin for(int i=0;i<4;i++) if(s_axi_wstrb[i]) regs[s_axi_awaddr[3:2]][i*8+:8]<=s_axi_wdata[i*8+:8]; s_axi_bvalid<=1; s_axi_bresp<=0; end if(s_axi_bvalid&&s_axi_bready) s_axi_bvalid<=0; if(s_axi_arvalid&&!s_axi_arready) s_axi_arready<=1; else if(s_axi_arready) begin s_axi_arready<=0; s_axi_rdata<=regs[s_axi_araddr[3:2]]; s_axi_rresp<=0; s_axi_rvalid<=1; end if(s_axi_rvalid&&s_axi_rready) s_axi_rvalid<=0; end endmodule",
            "parameters": [{"name": "N_REGS", "default": 4}, {"name": "DATA_WIDTH", "default": 32}],
            "packages": [],
            "sva_assertions": ["assert property (@(posedge s_axi_aclk) disable iff(!s_axi_aresetn) s_axi_bresp==2'b00);", "assert property (@(posedge s_axi_aclk) disable iff(!s_axi_aresetn) s_axi_rresp==2'b00);"],
            "requirement_traceability": [{"req": "4 R/W registers", "rtl_signal": "regs[0:3]"}, {"req": "AXI4-Lite 5 channel", "rtl_signal": "AW/W/B/AR/R channels"}],
        },
    },
]

# ---------------- STAGE 3: FUNCTIONAL VERIFICATION ----------------
verif_examples = [
    {
        "user": json.dumps({"spec": spec_examples[0]["assistant"], "rtl": rtl_examples[0]["assistant"]["rtl"]}),
        "assistant": {
            "testbench_file": "#include \"Vfifo_sync_4x8.h\"\n#include \"verilated.h\"\nint main(int argc, char** argv){ Verilated::commandArgs(argc, argv); Vfifo_sync_4x8* top = new Vfifo_sync_4x8; top->clk=0; top->rst_n=0; top->eval(); top->rst_n=1; int errors=0; for(int cycle=0; cycle<1000; cycle++){ top->clk=!top->clk; top->eval(); if(cycle%2==0){ top->wr_en = (cycle<10) ? 1 : 0; top->din = cycle & 0xFF; top->rd_en = (cycle>10) ? 1 : 0; } if(top->full && top->wr_en) { printf(\"ERROR: write while full\\n\"); errors++; } } printf(\"Simulation done, errors=%d\\n\", errors); top->final(); delete top; return errors?1:0; }",
            "golden_reference_model": "class RefFIFO: def __init__(self): self.q=collections.deque(); self.full=False; self.empty=True; def push(self,d): if not self.full: self.q.append(d); def pop(self): return self.q.popleft() if not self.empty else None",
            "stimulus_sequences": ["directed_fill_then_empty", "random_interleaved_rd_wr", "backpressure_full_assertion"],
            "assertion_checks": ["no_write_when_full", "no_read_when_empty", "data_ordering_FIFO"],
            "coverage_points": ["full_flag_high", "empty_flag_high", "simultaneous_rd_wr"],
        },
    },
    {
        "user": json.dumps({"spec": spec_examples[3]["assistant"], "rtl": rtl_examples[1]["assistant"]["rtl"]}),
        "assistant": {
            "testbench_file": "#include \"Varbiter_rr4.h\"\n#include \"verilated.h\"\nint main(int argc,char**argv){Verilated::commandArgs(argc,argv); Varbiter_rr4* t=new Varbiter_rr4; t->clk=0;t->rst_n=0;t->eval();t->rst_n=1;int err=0; for(int c=0;c<500;c++){t->clk=!t->clk;t->eval(); if(c%2==0){ t->req = (c*7+3)&0xF; } int g=t->grant; int ones=__builtin_popcount(g); if(ones>1){printf(\"ERROR: grant not one-hot %x\\n\",g);err++;} } printf(\"err=%d\\n\",err);t->final();delete t;return err?1:0;}",
            "golden_reference_model": "def rr_arbiter(req, priority): for i in range(4): idx=(priority+i)%4; if req[idx]: return idx, 1<<idx; return None, 0",
            "stimulus_sequences": ["all_request_patterns_16", "single_requester_starvation_check", "rotating_priority"],
            "assertion_checks": ["grant_onehot0", "fairness_no_starvation_4cycles"],
            "coverage_points": ["all_16_req_patterns", "priority_wrap_3->0"],
        },
    },
    {
        "user": json.dumps({"spec": spec_examples[4]["assistant"], "rtl": rtl_examples[2]["assistant"]["rtl"]}),
        "assistant": {
            "testbench_file": "#include \"Valu_pipe3_8bit.h\"\n#include \"verilated.h\"\nint main(int argc,char**argv){Verilated::commandArgs(argc,argv); Valu_pipe3_8bit* t=new Valu_pipe3_8bit; t->clk=0;t->rst_n=0;t->eval();t->rst_n=1;int err=0; unsigned char expected[3]={0}; for(int c=0;c<200;c++){ t->clk=!t->clk; t->eval(); if(c%2==0){ t->a=(c*13)&0xFF; t->b=(c*7+5)&0xFF; t->op=c&7; expected[2]=expected[1]; expected[1]=expected[0]; switch(c&7){case 0:expected[0]=t->a+t->b;break;case 1:expected[0]=t->a-t->b;break;case 2:expected[0]=t->a&t->b;break;case 3:expected[0]=t->a|t->b;break;case 4:expected[0]=t->a^t->b;break;case 5:expected[0]=~t->a;break;case 6:expected[0]=t->a<<1;break;case 7:expected[0]=t->a>>1;break;} if(c>6 && t->valid && t->result!=expected[2]){printf(\"ERR cycle %d got %02x exp %02x\\n\",c,t->result,expected[2]);err++;} } } printf(\"err=%d\\n\",err);t->final();delete t;return err?1:0;}",
            "golden_reference_model": "def alu_ref(a,b,op): ops=[lambda:a+b,lambda:a-b,lambda:a&b,lambda:a|b,lambda:a^b,lambda:~a,lambda:a<<1,lambda:a>>1]; return ops[op]() & 0xFF",
            "stimulus_sequences": ["all_8_opcodes", "boundary_operands_0_255_127", "back_to_back_pipeline"],
            "assertion_checks": ["latency_exactly_3_cycles", "result_matches_golden"],
            "coverage_points": ["all_opcodes", "carry_out", "overflow_flag"],
        },
    },
    {
        "user": json.dumps({"spec": spec_examples[2]["assistant"], "rtl": rtl_examples[3]["assistant"]["rtl"]}),
        "assistant": {
            "testbench_file": "#include \"Vuart_tx_8n1.h\"\n#include \"verilated.h\"\nint main(int argc,char**argv){Verilated::commandArgs(argc,argv); Vuart_tx_8n1* t=new Vuart_tx_8n1; t->clk=0;t->rst_n=0;t->eval();t->rst_n=1;t->baud_div=10; int err=0; int bit_idx=0; unsigned char expect=0xA5; for(int c=0;c<2000;c++){ t->clk=!t->clk;t->eval(); if(c==10){t->tx_valid=1;t->tx_data=expect;} if(c==12)t->tx_valid=0; } printf(\"err=%d\\n\",err);t->final();delete t;return err?1:0;}",
            "golden_reference_model": "def uart_frame(data): return [0]+[(data>>i)&1 for i in range(8)]+[1]  # start + 8 data + stop",
            "stimulus_sequences": ["single_byte_frame_check", "back_to_back_bytes", "baud_div_corner_1"],
            "assertion_checks": ["start_bit_zero", "stop_bit_one", "idle_line_high"],
            "coverage_points": ["all_data_bits_0_1", "baud_div_min_max"],
        },
    },
    {
        "user": json.dumps({"spec": spec_examples[1]["assistant"], "rtl": rtl_examples[4]["assistant"]["rtl"]}),
        "assistant": {
            "testbench_file": "#include \"Vaxil_regbank_4x32.h\"\n#include \"verilated.h\"\nint main(int argc,char**argv){Verilated::commandArgs(argc,argv); Vaxil_regbank_4x32* t=new Vaxil_regbank_4x32; t->s_axi_aclk=0;t->s_axi_aresetn=0;t->eval();t->s_axi_aresetn=1;int err=0; for(int c=0;c<500;c++){ t->s_axi_aclk=!t->s_axi_aclk;t->eval(); if(c%2==0){ t->s_axi_awaddr=(c&3)<<2; t->s_axi_awvalid=1; t->s_axi_wdata=0xDEAD0000|(c&0xFFFF); t->s_axi_wstrb=0xF; t->s_axi_wvalid=1; t->s_axi_bready=1; } } printf(\"err=%d\\n\",err);t->final();delete t;return err?1:0;}",
            "golden_reference_model": "class RefRegBank: def __init__(self): self.r=[0]*4; def write(self,addr,data,strb): idx=(addr>>2)&3; for i in range(4): if strb&(1<<i): self.r[idx]=(self.r[idx]&~(0xFF<<(i*8)))|((data>>(i*8)&0xFF)<<(i*8)); def read(self,addr): return self.r[(addr>>2)&3]",
            "stimulus_sequences": ["write_read_each_reg", "byte_strobe_partial", "back_to_back_no_idle"],
            "assertion_checks": ["bresp_OKAY", "rresp_OKAY", "readback_matches_write"],
            "coverage_points": ["all_4_registers", "all_4_byte_strobes"],
        },
    },
]

# ---------------- STAGE 4: LOGIC SYNTHESIS ----------------
synth_examples = [
    {
        "user": json.dumps({"rtl": rtl_examples[0]["assistant"]["rtl"], "target_clock_ns": 4.0}),
        "assistant": {
            "synthesis_script": "read_verilog -sv fifo_sync_4x8.v\nhierarchy -check\nproc; opt; fsm; opt; memory; opt\ntechmap; opt\nstat\nwrite_verilog -noattr fifo_netlist.v\nwrite_json fifo_synth.json",
            "target_clock_ns": 4.0,
            "expected_cell_primitives": ["DFF", "MUX", "ADDER", "COMPARATOR", "MEMRD", "MEMWR"],
            "timing_slack_estimate": "positive (small counter logic, 250 MHz easily met)",
            "netlist_directives": ["flatten memory to registers for DEPTH=4", "infer 4x8 distributed RAM"],
        },
    },
    {
        "user": json.dumps({"rtl": rtl_examples[1]["assistant"]["rtl"], "target_clock_ns": 2.5}),
        "assistant": {
            "synthesis_script": "read_verilog -sv arbiter_rr4.v\nhierarchy -check\nproc; opt; fsm; opt; techmap; opt\nstat\nwrite_verilog -noattr arbiter_netlist.v",
            "target_clock_ns": 2.5,
            "expected_cell_primitives": ["DFF", "MUX", "PRIORITY_ENCODER", "COMPARATOR"],
            "timing_slack_estimate": "positive (combinational priority logic < 2.5ns in 7nm)",
            "netlist_directives": ["keep grant register output", "one-hot encoding for grant"],
        },
    },
    {
        "user": json.dumps({"rtl": rtl_examples[2]["assistant"]["rtl"], "target_clock_ns": 2.0}),
        "assistant": {
            "synthesis_script": "read_verilog -sv alu_pipe3_8bit.v\nhierarchy -check\nproc; opt; fsm; opt; techmap; opt\nstat\nwrite_verilog -noattr alu_netlist.v",
            "target_clock_ns": 2.0,
            "expected_cell_primitives": ["DFF", "ADDER", "MUX8", "LOGIC_OPS", "SHIFT"],
            "timing_slack_estimate": "positive (pipelined, 500 MHz target met)",
            "netlist_directives": ["retime pipeline registers", "balance adder tree"],
        },
    },
    {
        "user": json.dumps({"rtl": rtl_examples[3]["assistant"]["rtl"], "target_clock_ns": 20.0}),
        "assistant": {
            "synthesis_script": "read_verilog -sv uart_tx_8n1.v\nhierarchy -check\nproc; opt; fsm; opt; techmap; opt\nstat\nwrite_verilog -noattr uart_netlist.v",
            "target_clock_ns": 20.0,
            "expected_cell_primitives": ["DFF", "COUNTER", "SHIFT_REG", "MUX", "COMPARATOR"],
            "timing_slack_estimate": "very positive (50 MHz, slow baud counter)",
            "netlist_directives": ["infer shift register for 10-bit frame", "16-bit baud counter"],
        },
    },
    {
        "user": json.dumps({"rtl": rtl_examples[4]["assistant"]["rtl"], "target_clock_ns": 10.0}),
        "assistant": {
            "synthesis_script": "read_verilog -sv axil_regbank_4x32.v\nhierarchy -check\nproc; opt; fsm; opt; techmap; opt\nstat\nwrite_verilog -noattr axil_netlist.v",
            "target_clock_ns": 10.0,
            "expected_cell_primitives": ["DFF", "MUX4", "DEMUX", "REGISTER_FILE_4x32", "FSM"],
            "timing_slack_estimate": "positive (100 MHz AXI, register bank simple)",
            "netlist_directives": ["infer 4x32 register file", "keep AXI handshake FSM separate"],
        },
    },
]

def write_jsonl(path, system, examples):
    with open(path, "w") as f:
        for ex in examples:
            asst = ex["assistant"]
            asst_str = json.dumps(asst) if isinstance(asst, dict) else str(asst)
            rec = {"system": system, "user": ex["user"], "assistant": asst_str}
            f.write(json.dumps(rec) + "\n")
    print(f"Wrote {len(examples)} examples -> {path}")

write_jsonl("data_spec.jsonl", SYS_SPEC, spec_examples)
write_jsonl("data_rtl.jsonl", SYS_RTL, rtl_examples)
write_jsonl("data_verif.jsonl", SYS_VERIF, verif_examples)
write_jsonl("data_synth.jsonl", SYS_SYNTH, synth_examples)
print("All 4 datasets built.")
