# Codex Checklist — nesting_engine_rotation_fixedpoint_lut

**Task slug:** `nesting_engine_rotation_fixedpoint_lut`  
**Canvas:** `canvases/nesting_engine/nesting_engine_rotation_fixedpoint_lut.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_rotation_fixedpoint_lut.yaml`

---

## DoD

- [x] A `rotate_point()` nem-ortogonális ága nem használ `f64 sin/cos` számolást.
- [x] Új fixed-point LUT modul készült (`TRIG_SCALE`, `SIN_Q`, `COS_Q`, `normalize_deg`, determinisztikus `round_div_i128`).
- [x] A LUT modul be van kötve a `geometry` modulba.
- [x] Van Rust unit teszt nem-ortogonális (17°) fix i64 kimenetre.
- [x] Frissítve lett az architektúra doksi a rotation determinism policy-val.
- [x] Létrejött a platform determinism smoke script rögzített `EXPECTED_OUTPUT_SHA256` értékkel.
- [x] Létrejött a kétplatformos CI workflow (`x86_64` + `arm64`).
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_rotation_fixedpoint_lut.md` PASS.
- [x] Report AUTO_VERIFY blokk és `.verify.log` elkészült.

## Lokális ellenőrzések

- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml` PASS.
- [x] `bash -n scripts/smoke_platform_determinism_rotation.sh` PASS.
- [x] `./scripts/smoke_platform_determinism_rotation.sh` PASS.
