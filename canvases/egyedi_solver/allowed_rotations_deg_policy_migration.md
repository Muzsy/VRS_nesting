# Rotacios policy atallitas listaalapu allowed_rotations_deg modellre

## 🎯 Funkcio
A task celja a P0 audit harmadik javitando pontjanak megoldasa: a bool alapu `allow_rotation` policy helyett listaalapu `allowed_rotations_deg` modell bevezetese a projekt schemaban, solver IO contractban, Rust solverben es Python validator/exporter utilokban.

## 🧠 Fejlesztesi reszletek
### Scope
- Benne van:
  - `allowed_rotations_deg` lista bevezetese (`project model`, `solver_input` contract).
  - Rust solver atallitasa listaalapu rotacios policyra.
  - Python validacio/export atallitasa listaalapu policy checkre.
  - Smoke inputok frissitese (`scripts/check.sh`, CI workflow).
  - Sample input frissitese az uj policy modellre.
- Nincs benne:
  - Folyamatos (nem 90-fokos) rotacio tamogatas.
  - Heurisztika redesign.
  - Teljes backward kompatibilitasi matrix fenntartasa legacy fielddel minden doksiban.

### Erintett fajlok
- `canvases/egyedi_solver/allowed_rotations_deg_policy_migration.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_allowed_rotations_deg_policy_migration.yaml`
- `docs/mvp_project_schema.md`
- `docs/solver_io_contract.md`
- `vrs_nesting/project/model.py`
- `rust/vrs_solver/src/main.rs`
- `vrs_nesting/nesting/instances.py`
- `vrs_nesting/dxf/exporter.py`
- `scripts/check.sh`
- `.github/workflows/nesttool-smoketest.yml`
- `samples/project_rect_1000x2000.json`
- `codex/codex_checklist/egyedi_solver/allowed_rotations_deg_policy_migration.md`
- `codex/reports/egyedi_solver/allowed_rotations_deg_policy_migration.md`

### DoD
- [ ] A project schema `parts[].allowed_rotations_deg` listat var, es validalja az engedett fokokat.
- [ ] A solver IO contract dokumentacio listaalapu rotacios policyt ir le.
- [ ] A Rust solver listaalapu rotaciokat hasznal placementnel es fit-checknel.
- [ ] A Python validator es DXF exporter a placement `rotation_deg` mezot a listahoz ellenorzi.
- [ ] A smoke inputok az uj mezot hasznaljak.
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/allowed_rotations_deg_policy_migration.md` PASS.

### Kockazat + mitigacio + rollback
- Kockazat: regresszio legacy fixture-okon, ha `allow_rotation`-ra epultek.
- Mitigacio: explicit listaalapu parse + deterministic hiba uzenetek + smoke input frissites.
- Rollback: policy parse logika visszaallithato bool modellre, az erintett fajlok izolaltak.

## 🧪 Tesztallapot
- Kotelezo gate: `./scripts/verify.sh --report codex/reports/egyedi_solver/allowed_rotations_deg_policy_migration.md`
- Task-specifikus ellenorzesek:
  - `cargo build --release --manifest-path rust/vrs_solver/Cargo.toml`
  - `python3 scripts/validate_nesting_solution.py --help`
  - `python3 vrs_nesting/dxf/exporter.py --help`

## 🌍 Lokalizacio
Nem relevans.

## 📎 Kapcsolodasok
- `codex/reports/egyedi_solver_p0_audit.md`
- `tmp/egyedi_solver/mvp_terv_tablas_nesting_fix_w_h_alakos_tabla_alap_a_meglevo_vrs_nesting_repora_epitve.md`
- `tmp/egyedi_solver/uj_tablas_solver_fix_w_h_alakos_stock_komplett_dokumentacio.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
