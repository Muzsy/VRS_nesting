# Codex Checklist — nesting_engine_baseline_placer_i_overlay_feasibility_fixes

**Task slug:** `nesting_engine_baseline_placer_i_overlay_feasibility_fixes`  
**Canvas:** `canvases/nesting_engine/nesting_engine_baseline_placer_i_overlay_feasibility_fixes.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_baseline_placer_i_overlay_feasibility_fixes.yaml`

---

## DoD

- [x] A feasibility narrow-phase ténylegesen i_overlay predikátumokra épül (containment + no-overlap).
- [x] A korábbi custom segment/PIP narrow-phase már nem az aktív implementáció.
- [x] A `scripts/check.sh` baseline bin smoke blokk megmaradt.
- [x] A `scripts/check.sh` új CLI-smoke blokkot tartalmaz (`nest-v2`).
- [x] A baseline dokumentációk (`nesting_engine_baseline_placer.md`, `nesting_engine_backlog.md`) a valós működéshez igazítva.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_baseline_placer_i_overlay_feasibility_fixes.md` PASS.
- [x] Report és checklist teljesen kitöltve (DoD -> Evidence + AUTO_VERIFY).

## Lokális ellenőrzések

- [x] `CARGO_HOME=/tmp/vrs_cargo_home cargo test --manifest-path rust/nesting_engine/Cargo.toml` PASS.
- [x] `bash -n scripts/check.sh` PASS.
- [x] Gyors CLI-smoke hash egyezés (`nesting_engine nest` vs `python3 -m vrs_nesting.cli nest-v2`) PASS.
