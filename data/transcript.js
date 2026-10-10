/* ============================================================
   SILICA — Recorded reference run transcript (demo data)
   This is a static, recorded event sequence used to illustrate the
   live run view. It is NOT live EDA execution. In production these
   events arrive over WebSocket from the Workflow Orchestrator.
   Project: AES-128 encryption core, illustrative TSMC 16nm flow.
   ============================================================ */
window.SILICA_TRANSCRIPT = {
  project: "AES-128 Encryption Core",
  brief: "Compact AES-128 ECB encrypt core, 128-bit data path, 10 rounds, single-clock synchronous design, target 400 MHz.",
  node: "TSMC 16nm FinFET (illustrative)",
  events: [
    // ---- 1. Specification ----
    {t:0, type:"stage", stage:0, status:"running", name:"Specification", sub:"Parsing design brief"},
    {t:1, type:"task", text:"Parsing natural-language design brief into architectural specification"},
    {t:2, type:"op", text:"silica.spec.parse --brief \"AES-128 ECB, 128-bit, 10 rounds, 400 MHz\" --format json"},
    {t:3, type:"log", level:"info", text:"Extracted: data_width=128, key_width=128, rounds=10, mode=ECB, target_freq=400MHz"},
    {t:4, type:"agent", role:"Supervisor Agent", text:"Specification resolved. 128-bit datapath, iterative 10-round architecture selected for area efficiency. Dispatching RTL Design Agent."},
    {t:5, type:"artifact", name:"spec.json", desc:"Architectural specification", status:"generated", size:"4.2 KB", check:"pass"},
    {t:6, type:"stage", stage:0, status:"passed"},

    // ---- 2. RTL Design ----
    {t:7, type:"stage", stage:1, status:"running", name:"RTL Design", sub:"Generating SystemVerilog"},
    {t:8, type:"task", text:"RTL Design Agent generating synthesizable SystemVerilog modules"},
    {t:9, type:"op", text:"rtl-agent generate --target aes128 --lang systemverilog --style iterative"},
    {t:11, type:"log", level:"info", text:"Wrote 6 modules: aes_core, key_expand, sub_bytes, shift_rows, mix_columns, add_round_key"},
    {t:12, type:"log", level:"ok", text:"Tree-sitter parse: 0 syntax errors. Lint clean (no latches, no implicit wires)."},
    {t:13, type:"artifact", name:"rtl/aes_core.sv", desc:"Top-level RTL", status:"generated", size:"8.1 KB", check:"pass"},
    {t:14, type:"artifact", name:"rtl/key_expand.sv", desc:"Key expansion", status:"generated", size:"6.4 KB", check:"pass"},
    {t:15, type:"stage", stage:1, status:"passed"},

    // ---- 3. Functional Verification (with recovery) ----
    {t:16, type:"stage", stage:2, status:"running", name:"Functional Verification", sub:"UVM-style testbench + simulation"},
    {t:17, type:"task", text:"Functional Verification Agent building directed + random testbench"},
    {t:18, type:"op", text:"verilator --cc rtl/aes_core.sv --top-module aes_core --exe tb_aes.cpp"},
    {t:20, type:"log", level:"err", text:"%Error: tb_aes.cpp:42: Cannot find field 'force_error' in class 'Vtb_aes'"},
    {t:21, type:"diag", kind:"fail", text:"Testbench referenced a debug signal that does not exist in the generated RTL. Simulation compile failed."},
    {t:22, type:"agent", role:"Functional Verification Agent", text:"Diagnosed stale testbench reference. Removed invalid probe, regenerated harness against actual RTL port list."},
    {t:23, type:"diag", kind:"recover", text:"Recovery: regenerated tb_aes.cpp from current RTL port list (action bounded to testbench only). Retrying compile."},
    {t:25, type:"op", text:"verilator --cc rtl/aes_core.sv --top-module aes_core --exe tb_aes.cpp && obj_dir/Vaes_core +cycles=20000"},
    {t:28, type:"log", level:"ok", text:"20,000 vectors passed (1,024 directed NIST FIPS-197 vectors + 18,976 random). Coverage: line 96.4%, toggle 91.2%."},
    {t:29, type:"artifact", name:"sim/report.txt", desc:"Functional simulation report", status:"generated", size:"12 KB", check:"pass"},
    {t:30, type:"stage", stage:2, status:"recovered", name:"Functional Verification", sub:"1 recovery — passed"},

    // ---- 4. Synthesis (failure + recovery, the key demo) ----
    {t:31, type:"stage", stage:3, status:"running", name:"Synthesis", sub:"Yosys technology mapping"},
    {t:32, type:"task", text:"Synthesizing RTL to gate-level netlist with 16nm standard-cell library"},
    {t:33, type:"op", text:"yosys -q -p \"read_verilog rtl/*.sv; synth -top aes_core; dfflibmap -lib nangate16.db; abc -lib nangate16.db -D 2500; write_verilog netlist/aes_core.v\""},
    {t:37, type:"log", level:"info", text:"Mapped to 12,482 standard cells. Combinational area: 48,210 µm². Critical path estimate: 3.1 ns."},
    {t:38, type:"log", level:"err", text:"STA: WNS = -0.60 ns at 400 MHz (2.5 ns target). Timing NOT met. 14 endpoints violating."},
    {t:39, type:"diag", kind:"fail", text:"Critical path through MixColumns→SubBytes pipeline stage exceeds 2.5 ns target. First synthesis attempt failed timing closure."},
    {t:40, type:"agent", role:"Physical Implementation Agent", text:"Identified long combinational path in round logic. Retrying with register retiming enabled and ABC effort 'ultra'. Bounded change: synthesis script only; RTL untouched."},
    {t:41, type:"diag", kind:"recover", text:"Recovery: added 'retime -map -latch' and '-effort ultra' to synthesis. Re-running (attempt 2 of 3)."},
    {t:43, type:"op", text:"yosys -q -p \"...; retime -map -latch; abc -lib nangate16.db -D 2500 -effort ultra; ...\""},
    {t:47, type:"log", level:"ok", text:"Retiming moved 3 registers into MixColumns stage. WNS = +0.12 ns. All 14 violating endpoints resolved. Timing met."},
    {t:48, type:"metric", label:"Cell count", value:"11,904", unit:"cells", qualifier:"tool-reported"},
    {t:49, type:"metric", label:"Combinational area", value:"46.3", unit:"k µm²", qualifier:"tool-reported"},
    {t:50, type:"metric", label:"WNS @ 400MHz", value:"+0.12", unit:"ns", qualifier:"tool-reported"},
    {t:51, type:"artifact", name:"netlist/aes_core.v", desc:"Gate-level netlist", status:"generated", size:"214 KB", check:"pass"},
    {t:52, type:"artifact", name:"synth/report_synth.txt", desc:"Synthesis report", status:"generated", size:"88 KB", check:"pass"},
    {t:53, type:"stage", stage:3, status:"recovered", name:"Synthesis", sub:"1 recovery — timing closed"},

    // ---- 5. Floorplanning ----
    {t:54, type:"stage", stage:4, status:"running", name:"Floorplanning", sub:"Die size, macro placement"},
    {t:55, type:"task", text:"Floorplanning die area and placing hard macros"},
    {t:56, type:"op", text:"openroad -exit -no_init -scripts scripts/floorplan.tcl"},
    {t:59, type:"log", level:"info", text:"Die: 320 × 320 µm. Utilization target 55%. Core ring + power grid (M5/M6) constructed."},
    {t:60, type:"artifact", name:"floorplan.def", desc:"Floorplan DEF", status:"generated", size:"31 KB", check:"pass"},
    {t:61, type:"stage", stage:4, status:"passed"},

    // ---- 6. Placement ----
    {t:62, type:"stage", stage:5, status:"running", name:"Placement", sub:"Global + detailed placement"},
    {t:63, type:"task", text:"Global placement, legalization, and placement optimization"},
    {t:64, type:"op", text:"openroad -exit -no_init -scripts scripts/place.tcl"},
    {t:68, type:"log", level:"ok", text:"Placement legalized. HPWL 1.84e6 µm. 0 overlaps. Post-place WNS +0.08 ns."},
    {t:69, type:"artifact", name:"placed.def", desc:"Placed DEF", status:"generated", size:"1.2 MB", check:"pass"},
    {t:70, type:"stage", stage:5, status:"passed"},

    // ---- 7. Routing ----
    {t:71, type:"stage", stage:6, status:"running", name:"Routing", sub:"Global + detailed routing"},
    {t:72, type:"task", text:"Global routing followed by detailed routing (DRV repair loop)"},
    {t:73, type:"op", text:"openroad -exit -no_init -scripts scripts/route.tcl"},
    {t:78, type:"log", level:"info", text:"Global route: 100% nets. Detailed route: 3 iterations."},
    {t:79, type:"log", level:"ok", text:"DRC violations: 0. Shorts: 0. Routed 100% of 13,204 nets."},
    {t:80, type:"artifact", name:"routed.def", desc:"Routed DEF", status:"generated", size:"6.8 MB", check:"pass"},
    {t:81, type:"stage", stage:6, status:"passed"},

    // ---- 8. Timing Analysis ----
    {t:82, type:"stage", stage:7, status:"running", name:"Timing Analysis", sub:"Static timing, all corners"},
    {t:83, type:"task", text:"Signoff static timing analysis across process corners"},
    {t:84, type:"op", text:"opensta -exit scripts/timing_signoff.tcl (corners: ss_125c, ff_-40c, tt_25c)"},
    {t:88, type:"log", level:"ok", text:"WNS (ss,125°C): +0.06 ns. TNS: 0.00 ns. Setup violations: 0. Hold violations: 0."},
    {t:89, type:"metric", label:"Power (typ)", value:"18.4", unit:"mW", qualifier:"estimated"},
    {t:90, type:"metric", label:"Core area", value:"102.4", unit:"k µm²", qualifier:"tool-reported"},
    {t:91, type:"artifact", name:"sta/report_timing.rpt", desc:"Signoff timing report", status:"generated", size:"42 KB", check:"pass"},
    {t:92, type:"stage", stage:7, status:"passed"},

    // ---- 9. Physical Verification ----
    {t:93, type:"stage", stage:8, status:"running", name:"Physical Verification", sub:"DRC / LVS / antenna"},
    {t:94, type:"task", text:"Design-rule check, layout-vs-schematic, antenna check"},
    {t:95, type:"op", text:"magic -noconsole -rcfile nangate16.techrc scripts/drc.tcl && netgen lvs netlist/aes_core.v routed.spice"},
    {t:100, type:"log", level:"ok", text:"DRC: 0 violations. LVS: netlists match (12,482 cells). Antenna: 0 violations."},
    {t:101, type:"artifact", name:"pv/drc.rpt", desc:"DRC report", status:"generated", size:"6 KB", check:"pass"},
    {t:102, type:"artifact", name:"pv/lvs.rpt", desc:"LVS report", status:"generated", size:"4 KB", check:"pass"},
    {t:103, type:"stage", stage:8, status:"passed"},

    // ---- 10. Tapeout Preparation ----
    {t:104, type:"stage", stage:9, status:"running", name:"Tapeout Preparation", sub:"GDSII stream-out"},
    {t:105, type:"task", text:"Streaming out GDSII/OASIS and assembling foundry handoff package"},
    {t:106, type:"op", text:"klayout -b -r scripts/streamout.lym -rd input=routed.oasis output=gds/aes_core.gds"},
    {t:110, type:"log", level:"ok", text:"GDSII streamed: 8 metal layers + 2 BEOL. OASIS compressed. Foundry deck validated."},
    {t:111, type:"artifact", name:"gds/aes_core.gds", desc:"Final layout (GDSII)", status:"generated", size:"4.1 MB", check:"pass"},
    {t:112, type:"artifact", name:"gds/aes_core.oas", desc:"Final layout (OASIS)", status:"generated", size:"1.8 MB", check:"pass"},
    {t:113, type:"artifact", name:"tapeout/handover.pdf", desc:"Foundry handover package", status:"generated", size:"212 KB", check:"pending"},
    {t:114, type:"stage", stage:9, status:"passed"},

    // ---- Outcome ----
    {t:116, type:"outcome", kind:"pass", title:"Run completed — design ready for foundry handoff",
      text:"All 10 stages passed. 2 recoveries (testbench compile, synthesis timing). 14 artifacts generated. Physical fabrication performed externally by foundry partner."}
  ]
};
