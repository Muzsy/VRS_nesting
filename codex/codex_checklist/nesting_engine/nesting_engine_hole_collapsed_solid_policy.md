# Codex Checklist — nesting_engine_hole_collapsed_solid_policy

**Task slug:** `nesting_engine_hole_collapsed_solid_policy`  
**Canvas:** `canvases/nesting_engine/nesting_engine_hole_collapsed_solid_policy.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_hole_collapsed_solid_policy.yaml`

---

## DoD

- [x] `pipeline.rs`: HOLE_COLLAPSED esetén mindig `inflated_holes_points_mm == []` (hard + detect ág).
- [x] `pipeline.rs`: HOLE_COLLAPSED esetén outer-only envelope nem üres marad.
- [x] `pipeline.rs`: HOLE_COLLAPSED diagnosztika `preserve_for_export=true`, `usable_for_nesting=false`.
- [x] `main.rs`: HOLE_COLLAPSED státusznál a placer felé átadott polygon `holes == []`.
- [x] Új unit teszt lefedi a detect-path HOLE_COLLAPSED esetet.
- [x] `docs/nesting_engine/tolerance_policy.md` szinkronizálva a valós policy-vel.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_hole_collapsed_solid_policy.md` futtatva.
- [x] Checklist + report létrehozva.

## Lokális ellenőrzések

- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml hole_collapsed_detect_path_forces_outer_only_nesting_geometry` PASS.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_hole_collapsed_solid_policy.md` PASS.
