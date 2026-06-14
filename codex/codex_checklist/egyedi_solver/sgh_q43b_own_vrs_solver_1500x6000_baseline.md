# SGH-Q43b Codex Checklist

Task: `sgh_q43b_own_vrs_solver_1500x6000_baseline`
Canvas: `canvases/egyedi_solver/sgh_q43b_own_vrs_solver_1500x6000_baseline.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q43b_own_vrs_solver_1500x6000_baseline.yaml`

## Pre-immutability

- [x] `artifacts/benchmarks/sgh_q43b/pre_own_source_status.log` (git status --short)
- [x] `artifacts/benchmarks/sgh_q43b/pre_own_source_diff.log` (0 byte)

## Own solver source

- [x] `rust/vrs_solver` repo identified: main@1295e99
- [x] `artifacts/benchmarks/sgh_q43b/upstream_clone_info.json`
- [x] `artifacts/benchmarks/sgh_q43b/upstream_build.log`

## Q43b scripts

- [x] `scripts/bench_sgh_q43b_own_full276_1500x6000.py` (runner)
- [x] `scripts/smoke_sgh_q43b_own_solver_audit.py` (smoke)
- [x] `scripts/build_sgh_q43b_comparison_artifacts.py` (3-way comparison + parity)

## Own solver run

- [x] Run A 1200 sec lefutott: `artifacts/benchmarks/sgh_q43b/upstream_run_1200.log` + output JSON
- [x] Run A summary: 218/276 placement (partial), wall=1138.96s, 0 collision, 184 unique rotations
- [x] Run B: skipped (single-run spec)
- [x] Render evidence: `artifacts/benchmarks/sgh_q43b/renders/.../sheet_00.svg` + `overview.svg` + `sheet_00.png` + `overview.png` + `render_manifest.json`

## Artifacts

- [x] `artifacts/benchmarks/sgh_q43b/inputs/q43b_full276_1x1500x6000_margin5_spacing8_continuous_1200.json`
- [x] `artifacts/benchmarks/sgh_q43b/outputs/q43b_full276_1x1500x6000_margin5_spacing8_continuous_1200_output.json`
- [x] `artifacts/benchmarks/sgh_q43b/logs/q43b_full276_1x1500x6000_margin5_spacing8_continuous_1200.log`
- [x] `artifacts/benchmarks/sgh_q43b/q43b_summary.json`
- [x] `artifacts/benchmarks/sgh_q43b/upstream_summary.json` (Q43-sema)
- [x] `artifacts/benchmarks/sgh_q43b/comparison_summary.json` (3-way: Q43 + Q43b + Q42)
- [x] `artifacts/benchmarks/sgh_q43b/semantic_parity_matrix.json` (9 topics)

## Post-immutability

- [x] `artifacts/benchmarks/sgh_q43b/post_own_source_status.log`
- [x] `artifacts/benchmarks/sgh_q43b/post_own_source_diff.log` (0 byte — own solver source unchanged)

## Report

- [x] `codex/reports/egyedi_solver/sgh_q43b_own_vrs_solver_1500x6000_baseline.md`
- [x] Q43-mal azonos szerkezet (Scope, Strict rule, Imm. proof, Why, Source, Build, Input, Run A, Run B, Runtime, Optimization, Upstream result, Own Q42 source, Comparison, Direct comparability, Audit methodology, 9 parity sections, Parity matrix, Risky, Intentional, Unknown, Recommendations, Final verdict)
- [x] 3-way comparison szekció (Q43 upstream + Q43b own + Q42 own)
- [x] Final verdict szekció (4 független ítélet)

## Verifications

- [x] `python3 scripts/smoke_sgh_q43b_own_solver_audit.py` → PASS

## Acceptance

A Q43b akkor tekinthető késznek, ha minden fenti doboz ki van pipálva.
