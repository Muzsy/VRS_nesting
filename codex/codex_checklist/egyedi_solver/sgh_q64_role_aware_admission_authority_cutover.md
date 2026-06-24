# Q64 Codex Checklist

Task: `sgh_q64_role_aware_admission_authority_cutover`
Canvas: `canvases/egyedi_solver/sgh_q64_role_aware_admission_authority_cutover.md`
Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q64_role_aware_admission_authority_cutover.yaml`
Report: `codex/reports/egyedi_solver/sgh_q64_role_aware_admission_authority_cutover.md`

## DoD

- [x] A generic direct short-circuit és az Anchor catalog fallback-only szabály ellenőrizve, reportban rögzítve.
- [x] Minden létrehozott/módosított fájl szerepel a YAML outputs listájában.
- [x] A known skeleton role productionben nem short-circuitolódik a generic direct ágra.
- [x] A generic direct ág csak másodvonalbeli fallbackként marad meg a role-aware próbálkozás után.
- [x] Az existing Anchor feature-vs-catalog commit sorrend stabil marad.
- [x] A módosításra van célzott automatizált teszt.
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q64_role_aware_admission_authority_cutover.md` lefutott.
- [x] Report Standard v2 DoD->Evidence Matrix kitöltve path+line bizonyítékkal.

## Task-specific gates

- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::sparrow::bpp_reduction`
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q64_role_aware_admission_authority_cutover.md`
