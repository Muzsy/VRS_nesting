# Codex checklist - engine_v2_nfp_rc_t02_geometry_profile_contract

- [x] AGENTS.md + T02 master runner/canvas/YAML/runner prompt beolvasva
- [x] T02 altal eloirt valos Rust fajlok beolvasva (`types.rs`, `scale.rs`, `float_policy.rs`, `pipeline.rs`, `nfp/mod.rs`, `boundary_clean.rs`)
- [x] SCALE es GEOM_EPS_MM tenyleges kodbeli erteke rogzitve (`SCALE=1_000_000`, `GEOM_EPS_MM=1e-9`)
- [x] `docs/nesting_engine/geometry_preparation_contract_v1.md` letrehozva
- [x] Mind a 7 kotelezo szekcio szerepel a dokumentumban
- [x] Explicit szerepel: `solver geometry != gyártási geometry`
- [x] Explicit szerepel: `Point64` az integer robust layer implementacioja
- [x] `ls docs/nesting_engine/geometry_preparation_contract_v1.md` PASS
- [x] Kotelezo kulcsszo/szekcio ellenorzes PASS
- [x] `git diff --name-only HEAD -- '*.rs' '*.py' '*.ts' '*.tsx'` -> ures (nincs production kod modositas)
- [x] Report DoD -> Evidence matrix kitoltve
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/engine_v2_nfp_rc_t02_geometry_profile_contract.md` PASS
