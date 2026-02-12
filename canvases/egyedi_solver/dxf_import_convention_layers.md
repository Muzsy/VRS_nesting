# DXF import konvenciok + clean pipeline

## 🎯 Funkcio
Ez a P1 task a DXF import reteg stabilizalasat kesziti elo, hogy a tablas solver valodi DXF forrasokkal tudjon dolgozni konzisztens layer-konvenciok mellett. A P1 besorolas oka, hogy a P0 solver/validator/export gate mar mukodik, de teljes DXF import pipeline nelkul a production-adatok kezelese korlatozott.

## 🧠 Fejlesztesi reszletek
### Scope
- Benne van:
  - DXF import konvencio (`CUT_OUTER`, `CUT_INNER`) formalizalasa.
  - Nyitott kontur es hibas layer esetek deterministicus hibakezelese.
  - Part + holes normalizalt kimeneti szerzodes rogzitese.
- Nincs benne:
  - Teljes geometriai offset algoritmus implementacio.
  - Solver heurisztika tuning.
  - DXF exporter uj feature.

### Erintett modulok/fajlok
- `NINCS: vrs_nesting/dxf/importer.py`
- `NINCS: vrs_nesting/geometry/clean.py`
- `docs/mvp_project_schema.md`
- `docs/solver_io_contract.md`
- `scripts/check.sh`
- `codex/reports/egyedi_solver/dxf_import_convention_layers.md`
- `codex/codex_checklist/egyedi_solver/dxf_import_convention_layers.md`

### DoD
- [ ] DXF import layer-konvencio explicit dokumentalva van (`CUT_OUTER`, `CUT_INNER`, hibatipusok).
- [ ] A task report tartalmaz regresszio-guard tervet a P0 validator/smoke gate megtartasara.
- [ ] A task checklistben szerepel a P0 nem romolhat ellenorzes.
- [ ] A task report es checklist scaffold kitoltott.

### Kockazat + mitigacio + rollback
- Kockazat: piszkos DXF inputokra tobb hard-fail ag jelenhet meg.
- Mitigacio: hibatipusonkent determinisztikus hibakod + minta-fixture terv.
- Rollback: import pipeline valtozasok kulon modulban maradnak; P0 futasi utvonal visszaallithato.

### Regresszio-orseg (P0 nem romolhat)
- Kotelezo ellenorzes: `./scripts/verify.sh --report codex/reports/egyedi_solver/dxf_import_convention_layers.md`.
- P0 gate referencia: `scripts/check.sh`, `.github/workflows/nesttool-smoketest.yml`.

## 🧪 Tesztallapot
- Kotelezo gate: `./scripts/verify.sh --report codex/reports/egyedi_solver/dxf_import_convention_layers.md`
- Relevans letezo szkriptek:
  - `./scripts/check.sh`
  - `python3 scripts/validate_nesting_solution.py --help`

## 🌍 Lokalizacio
N/A

## 📎 Kapcsolodasok
- `tmp/egyedi_solver/mvp_terv_tablas_nesting_fix_w_h_alakos_tabla_alap_a_meglevo_vrs_nesting_repora_epitve.md`
- `tmp/egyedi_solver/uj_tablas_solver_fix_w_h_alakos_stock_komplett_dokumentacio.md`
- `docs/dxf_nesting_app_4_spacing_margin_implementacio_offsettel_reszletes.md`
- `canvases/egyedi_solver/project_schema_and_cli_skeleton.md`
- `canvases/egyedi_solver/solver_io_contract_and_runner.md`
- `canvases/egyedi_solver/table_solver_mvp_multisheet.md`
