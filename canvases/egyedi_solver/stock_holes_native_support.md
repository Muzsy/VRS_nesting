# Alakos stock + holes natív támogatás (IO contract + solver + validator)

## 🎯 Funkcio
A task celja a P0 auditban jelzett blocker megszuntetese: az alakos stock es holes natív támogatás bevezetése a belső solver IO contractban, a Rust solverben és a Python validátorban.

## 🧠 Fejlesztesi reszletek
### Scope
- Benne van:
  - `docs/solver_io_contract.md` bővítése shape + holes mezőkkel.
  - `rust/vrs_solver/src/main.rs` bővítése alakos stock + holes containment checkkel.
  - `vrs_nesting/nesting/instances.py` validátor bővítése alakos stock + holes kezelésre.
  - `scripts/validate_nesting_solution.py` hole-tiltás eltávolítása, natív shape validáció megtartása.
  - smoke inputok frissítése (`scripts/check.sh`, `.github/workflows/nesttool-smoketest.yml`) hogy a gate ténylegesen lefedje a shape+holes ágat.
- Nincs benne:
  - jagua-rs integráció.
  - DXF importer implementáció.
  - haladó heurisztikai optimalizáció.

### Erintett fajlok
- `canvases/egyedi_solver/stock_holes_native_support.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_stock_holes_native_support.yaml`
- `docs/solver_io_contract.md`
- `rust/vrs_solver/src/main.rs`
- `vrs_nesting/nesting/instances.py`
- `scripts/validate_nesting_solution.py`
- `scripts/check.sh`
- `.github/workflows/nesttool-smoketest.yml`
- `codex/codex_checklist/egyedi_solver/stock_holes_native_support.md`
- `codex/reports/egyedi_solver/stock_holes_native_support.md`

### DoD
- [ ] Solver IO contract leírja a `stocks[].outer_points` + `stocks[].holes_points[]` mezőket.
- [ ] Rust solver shape+holes stockon nem helyez lyukba és nem lóg túl a stock outeren.
- [ ] Python validátor shape+holes inputon ellenőrzi az in-bounds + hole-exclusion + no-overlap szabályokat.
- [ ] `scripts/check.sh` table-solver smoke shape+holes inputon fut, és PASS.
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/stock_holes_native_support.md` PASS.

### Kockazat + mitigacio + rollback
- Kockazat: geometriai edge-case-ek (boundary-touch, lebegopont).
- Mitigacio: egyszerű, determinisztikus polygon és szegmens metszés szabályok, explicit hibauzenetekkel.
- Rollback: a task izolált fájlokat érint; szükség esetén a korábbi rectangle-only viselkedés visszaállítható.

## 🧪 Tesztallapot
- Kotelezo gate: `./scripts/verify.sh --report codex/reports/egyedi_solver/stock_holes_native_support.md`
- Task-specifikus ellenorzesek:
  - `python3 scripts/validate_nesting_solution.py --help`
  - `python3 -m vrs_nesting.runner.vrs_solver_runner --help`
  - smoke futas shape+holes stock bemenettel (`scripts/check.sh`)

## 🌍 Lokalizacio
Nem relevans.

## 📎 Kapcsolodasok
- `codex/reports/egyedi_solver_p0_audit.md`
- `tmp/egyedi_solver/dxf_nesting_app_7_multi_sheet_wrapper_reszletes.md`
- `tmp/egyedi_solver/mvp_terv_tablas_nesting_fix_w_h_alakos_tabla_alap_a_meglevo_vrs_nesting_repora_epitve.md`
- `tmp/egyedi_solver/tablas_optimalizacios_algoritmus_jagua_rs_integracio_reszletes_rendszerleiras.md`
- `tmp/egyedi_solver/uj_tablas_solver_fix_w_h_alakos_stock_komplett_dokumentacio.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
