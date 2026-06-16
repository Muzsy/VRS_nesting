# SGH-Q50 Codex Checklist

Task: `sgh_q50_density_lns_sheet_drop`
Canvas: `canvases/egyedi_solver/sgh_q50_density_lns_sheet_drop.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q50_density_lns_sheet_drop.yaml`
Branch: `sgh-q50-density-lns-sheet-drop` (stacked on `sgh-q49-...` / main)

## T1 — density_insert_part

- [x] `density_insert_part(part, target_sheet)`: density-guided insertion of a not-yet-placed part
- [x] reuses contour sampling + density score; continuous rotation preserved; CDE clear-check
- [x] unit test: inserts a part into a target neighbour's concavity as an interlock placement
- [x] `cargo build` + `cargo test` green

## T2 — lns_sheet_drop ruin-recreate pass

- [x] `lns_sheet_drop` (gated `VRS_BPP_LNS`, default off), runs after density compaction
- [x] ruin least-utilized sheet → recreate into the rest via T1 `density_insert_part` (receiving-sheet compaction deferred; Q49 already compacts before the LNS)
- [x] perturbed restarts (`VRS_BPP_LNS_RESTARTS`, default 4); full revert on failure
- [x] accept only when all ruined parts placed feasibly on fewer sheets

## T3 — LNS diagnostics

- [x] `io.rs` `bpp_lns_applied` / `attempts` / `sheets_dropped` / `parts_reinserted` / `restarts`
- [x] result/adapter wiring

## T4 — Tests

- [x] positive: constructed fixture where a sheet is droppable ⇒ LNS drops it
- [x] negative: safe revert (unchanged, valid) when not droppable
- [x] `VRS_BPP_LNS=0` unchanged; deterministic; existing suites green

## T5 — A/B benchmark (full276)

- [x] `scripts/bench_sgh_q50_lns_sheet_drop.py`
- [x] `artifacts/benchmarks/sgh_q50/` (A/B + `q50_summary.json`)
- [x] used_sheets / sheets_dropped / attempts / restarts / utilization / validity

## T6 — Verify + report

- [x] `codex/reports/egyedi_solver/sgh_q50_density_lns_sheet_drop.md`
- [ ] `./scripts/verify.sh --report ...`
