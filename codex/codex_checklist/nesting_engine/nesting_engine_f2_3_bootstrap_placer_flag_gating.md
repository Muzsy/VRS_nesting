# Codex Checklist — nesting_engine_f2_3_bootstrap_placer_flag_gating

**Task slug:** `nesting_engine_f2_3_bootstrap_placer_flag_gating`  
**Canvas:** `canvases/nesting_engine/nesting_engine_f2_3_bootstrap_placer_flag_gating.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_f2_3_bootstrap_placer_flag_gating.yaml`

---

## DoD

- [x] `nesting_engine nest --placer blf|nfp` működik (default: blf).
- [x] Hybrid gating megvan: holes vagy hole_collapsed esetén `--placer nfp` → BLF fallback (determinism hash egyezik baseline-nal).
- [x] Új hole-mentes fixture valid JSON és lefut rajta a `nest --placer nfp`.
- [x] Gate smoke bővítve a két új ellenőrzéssel.
- [x] Gate PASS: `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_f2_3_bootstrap_placer_flag_gating.md`.
