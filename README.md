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
