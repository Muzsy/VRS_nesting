# SGH-Q52 Codex Checklist

Task: `sgh_q52_density_biased_admission`
Canvas: `canvases/egyedi_solver/sgh_q52_density_biased_admission.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q52_density_biased_admission.yaml`
Branch: `sgh-q52-density-biased-admission` (stacked on `sgh-q51-...`)

## T1 — density_biased_separate

- [x] focused iterative separator: **lexicographic** clear-first (interlock-ranked) / collision-proxy fallback
      (the combined `collision + w·density` form was tried first and dropped — it broke feasibility)
- [x] uniform + contour-near candidates, continuous rotation, spacing-collision shape (gap-preserving)
- [x] CDE-valid feasibility check; budgeted (SWEEPS=12)
- [x] unit test: synthetic overlapping concave pair (U + square) resolves into interlock (not apart)
- [x] `cargo build` + `cargo test` green

## T2 — wire into try_admit_critical + measure-gate

- [x] density_biased_separate used in the co-movable admission step (gated `VRS_ADMISSION_DENSITY_BIAS`)
- [x] **measure-gate:** 6×`Lv8_11612` at spacing 5 — **NEGATIVE**: 2 big/sheet across w=0.5/2/6/15 (300 samples)
      ⇒ bottleneck is the sequential single-part search structure, not the objective

## T3 — tuning

- [x] `w_density`, sweeps, per-part budget; `VRS_ADMISSION_DENSITY_BIAS` knob (default `0.0` = off)
- [x] confirmed tuning does not move tight-spacing big/sheet (negative finding documented)

## T4 — tests

- [x] separator interlock unit test; builder+bias integration valid; default-off unchanged
- [x] existing suites green (486 unit + integration)

## T5 — A/B benchmark

- [x] `scripts/bench_sgh_q52_density_biased_admission.py`
- [x] `artifacts/benchmarks/sgh_q52/` (6-big spacing 5/8 + spacing-0 proof + full276; bias ON vs builder-only vs OFF)

## T6 — verify + report

- [x] `codex/reports/egyedi_solver/sgh_q52_density_biased_admission.md` (honest NEGATIVE verdict + Q53 lever)
- [ ] `./scripts/verify.sh --report ...`
