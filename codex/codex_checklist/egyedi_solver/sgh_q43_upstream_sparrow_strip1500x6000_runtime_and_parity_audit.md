# SGH-Q43 Codex Checklist

Task: `sgh_q43_upstream_sparrow_strip1500x6000_runtime_and_parity_audit`
Canvas: `canvases/egyedi_solver/sgh_q43_upstream_sparrow_strip1500x6000_runtime_and_parity_audit.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q43_upstream_sparrow_strip1500x6000_runtime_and_parity_audit.yaml`

## Pre-immutability

- [x] `artifacts/benchmarks/sgh_q43/pre_own_source_status.log` (git status --short)
- [x] `artifacts/benchmarks/sgh_q43/pre_own_source_diff.log` (0 byte)

## Upstream source

- [x] `.cache/sparrow` clone identified: `c95454e390276231b278c879d25b39708398b7d3`
- [x] `artifacts/benchmarks/sgh_q43/upstream_clone_info.json`
- [x] `artifacts/benchmarks/sgh_q43/upstream_build.log`

## Q43 scripts

- [x] `scripts/run_sgh_q43_upstream_sparrow_strip1500x6000.py` (runner)
- [x] `scripts/smoke_sgh_q43_upstream_sparrow_strip_audit.py` (smoke)
- [x] `scripts/build_sgh_q43_comparison_artifacts.py` (comparison + parity)

## Upstream runs

- [x] Run A 1200 sec lefutott: `artifacts/benchmarks/sgh_q43/upstream_run_1200.log` + output JSON + SVG
- [x] Run A summary: 276/276 placement, strip_width=1496.15, density=0.743, wall=1208.18s
- [ ] Run B 2400 sec (a háttérben fut a checklist készítésekor)

## Artifacts

- [x] `artifacts/benchmarks/sgh_q43/upstream/inputs/sgh_q43_upstream_full276_1500x6000_continuous_1200.json`
- [x] `artifacts/benchmarks/sgh_q43/upstream/inputs/sgh_q43_upstream_full276_1500x6000_continuous_2400.json`
- [x] `artifacts/benchmarks/sgh_q43/upstream_summary.json`
- [x] `artifacts/benchmarks/sgh_q43/comparison_summary.json`
- [x] `artifacts/benchmarks/sgh_q43/semantic_parity_matrix.json` (9 topics, 5 verdict type)

## Post-immutability

- [x] `artifacts/benchmarks/sgh_q43/post_own_source_status.log`
- [x] `artifacts/benchmarks/sgh_q43/post_own_source_diff.log` (0 byte — own solver source unchanged)

## Report

- [x] `codex/reports/egyedi_solver/sgh_q43_upstream_sparrow_strip1500x6000_runtime_and_parity_audit.md`
- [x] All 9 audit topics covered with verdicts
- [x] `NOT DIRECTLY COMPARABLE` verdict explicit
- [x] Final verdict szekció (4 független ítélet)

## Verifications

- [x] `python3 scripts/smoke_sgh_q43_upstream_sparrow_strip_audit.py` → PASS
- [ ] `./scripts/verify.sh --report ...` → fut a háttérben; a Q43 spec elfogadja a környezeti FAIL-t is

## Acceptance

A Q43 akkor tekinthető késznek, ha minden fenti doboz ki van pipálva (a Run B opcionális ha Run A interpretálható).
