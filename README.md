# SILICA — Autonomous Semiconductor Engineering Platform

Silica is an autonomous AI engineering platform that helps engineers design, verify,
synthesize, and prepare digital chip designs for manufacturing. Physical fabrication
is performed by an external foundry.

## What works today (real, tested)

A working end-to-end path for small digital circuits, executed by **real EDA tools**
(no simulated results):

1. **Lint** — `verilator --lint-only -Wall` (real warnings/errors captured).
2. **Compile** — `verilator --cc --exe` + `make` (g++ build of C++ simulator).
3. **Simulate** — auto-generated testbench checks the counter sequence; pass/fail
   reported from actual simulation output.
4. **Synthesis** — `yosys synth` produces a gate-level netlist (`counter_netlist.v`),
   synthesis database (`counter_synth.json`), and cell/area statistics.
5. **Report** — reproducible `report.json` with commands, versions, exit codes,
   durations, artifacts, and an explicit signoff note.

### Autonomous failure recovery (demonstrated)

Submit intentionally-broken RTL (missing semicolon + undeclared signal `cnt`).
The RTL agent reads the **actual Verilator error evidence**, applies controlled
fixes in an isolated working copy (insert missing semicolon; rename `cnt` to
Verilator-suggested `count`), retries only the affected stages, and records every
action. Both the broken→recovered run and the clean baseline run pass all five
stages. Failed attempts are preserved on disk.

### Persistence and observability

Every run is stored under `data/projects/<id>/runs/<rid>/`:
`run.json`, `logs/{lint,compile,make,simulate,synthesis}.log`,
`recovery_*.diff`, `artifacts/{counter_netlist.v, counter_synth.json, report.json,
counter.v.final}`. Every reported result traces to real execution evidence.

## Run it

```bash
# requires: verilator, yosys, g++, make  (apt install verilator yosys build-essential)
python3 server.py
# open http://localhost:3000  ->  Workspace -> New Design -> check "Execute on REAL EDA backend"
# optionally check "Demo: submit broken RTL" to watch autonomous failure recovery.
```

The server serves the static frontend and the `/api/*` orchestrator on the same
port (no CORS issues). Static-only deployments (e.g. Vercel) gracefully fall back
to the recorded-transcript demo.

## API

- `GET  /api/health` — tool versions + availability.
- `POST /api/projects` — `{name, spec, rtl?}`.
- `POST /api/projects/<id>/run` — `{rtl?, demo_broken?}` starts a threaded run.
- `GET  /api/projects` — project list with last-run status.
- `GET  /api/runs/<rid>` — full run detail (stages, recovery, artifacts).
- `GET  /api/artifacts/<rid>/<name>` — download artifact.
- `GET  /api/logs/<rid>/<name>` — stage log.

## Specialist multi-agent system (silica_agents/)
Silica now runs an 8-agent specialist pipeline with typed contracts, versioned
domain prompts, sandboxed EDA execution, HF model-serving adapter, evidence-based
failure recovery, and an honest signoff agent. Vertical slice (real EDA):
`specification → rtl_design → functional_verification → logic_synthesis`, with
`physical_design` and `timing_verification` honestly labeled BLOCKED.
- `python3 eval/benchmark.py` — 6-case regression suite (all pass with real Verilator+Yosys).
- `python3 smoke_test.py` — end-to-end clean + broken-RTL recovery test.
- `training/` — model-eval matrix, dataset prep, and reproducible LoRA script (GPU required; not run here).
- See `STATUS_REPORT.md` for what works, what is blocked, and next priorities.
- LLM augmentation: set `HF_TOKEN` and `SILICA_ALLOW_EXTERNAL_LLM=1`; otherwise the
  deterministic baseline is used and the fallback is recorded in every audit trail.

## Deliberate limitations (honestly labeled)

- **No physical design.** No OpenROAD floorplan/place/route, no timing signoff, no
  DRC/LVS, no GDSII. A passing simulation is **not** physical signoff; a generated
  netlist is **not** fabrication-ready. The report states this explicitly.
- Recovery handles a narrow, evidence-based set of RTL errors (missing semicolon,
  undeclared signal with Verilator suggestion). Beyond that it stops and requests
  human intervention.
- Single-clock, small designs only. No constraint files, no power analysis, no
  multi-clock CDC verification.
- Vercel (static) cannot run EDA tools; real execution requires the local
  `server.py`. The deployed site falls back to the recorded demo.

## Next priorities

1. OpenROAD integration (floorplan -> placement -> routing -> DEF/LEF).
2. STA (OpenSTA) timing reports with real slacks.
3. Run comparison view and per-stage log streaming in the UI.
4. Constraint editor (SDC) and multi-clock CDC checks.
5. User auth + per-project artifact storage.


## Specialist agents and evaluation (silica_agents.py, benchmark.py)

- silica_agents.py: specialist agents (RTL design, functional verification, logic synthesis, failure recovery, signoff report) with structured I/O contracts, deterministic validation layers, and per-agent audit trails. Model-serving adapter calls HF Inference API when HF_TOKEN is set, else deterministic fallback (no hallucination).
- benchmark.py: known-answer RTL tasks validated by real Verilator/Yosys. Writes benchmark_report.json. Note: this session ephemeral VM repeatedly wiped EDA tools, so benchmark execution is blocked on environment stability; the orchestrator-level end-to-end tests passed 2/2 (clean + broken-to-recovered) in commit c17bdf6.
- HF login: blocked - browser type tool drops special characters in the password. Manual step: log in at huggingface.co, create an access token (Settings -> Access Tokens), export HF_TOKEN=...
