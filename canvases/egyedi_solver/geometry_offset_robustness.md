# Polygonize + offset robusztussag

## 🎯 Funkcio
Ez a P1 task a geometriai preprocess (polygonize/clean/offset) robustusitasi keretet adja meg, hogy shape-es DXF bemenetnel is stabilan keszuljon solver-kompatibilis geometria. P1, mert P0-ban a futasi pipeline mar megvan, de a teljes gyartasi geometriaeloszites meg hianyos.

## 🧠 Fejlesztesi reszletek
### Scope
- Benne van:
  - Ivek/spline-ok polygonize tolerancia strategiajanak rogzitese.
  - Part outset + stock inset offset szabalyok keretezese.
  - Degeneracio detektalas es figyelmeztetes terv.
- Nincs benne:
  - DXF import layer parser implementacio.
  - Solver heurisztika atirasa.
  - Export formatum bovites.

### Erintett modulok/fajlok
- `NINCS: vrs_nesting/geometry/polygonize.py`
- `NINCS: vrs_nesting/geometry/offset.py`
- `NINCS: vrs_nesting/geometry/clean.py`
- `vrs_nesting/nesting/instances.py`
- `rust/vrs_solver/src/main.rs`
- `codex/reports/egyedi_solver/geometry_offset_robustness.md`
- `codex/codex_checklist/egyedi_solver/geometry_offset_robustness.md`

### DoD
- [ ] A canvas konkret offset/polygonize scope-ot es nem-cel listat tartalmaz.
- [ ] A report vaz tartalmaz regresszio-guard tervet a P0 shape+holes validatorhoz.
- [ ] A checklist tartalmazza a P0 gate visszaellenorzes pontjat.
- [ ] A scaffold report/checklist kitoltve.

### Kockazat + mitigacio + rollback
- Kockazat: offset degeneracio (vekony fal, self-intersection) hibas placementhez vezethet.
- Mitigacio: tolerancia policy + regresszios fixture lista + explicit fail-fast.
- Rollback: geometry modulok izolaltak, P0 runner/validator utvonal visszafordithato.

### Regresszio-orseg (P0 nem romolhat)
- Kotelezo ellenorzes: `./scripts/verify.sh --report codex/reports/egyedi_solver/geometry_offset_robustness.md`.
- Ellenorizni kell, hogy a P0 smoke gate (`scripts/check.sh`) valtozatlanul zold.

## 🧪 Tesztallapot
- Kotelezo gate: `./scripts/verify.sh --report codex/reports/egyedi_solver/geometry_offset_robustness.md`
- Relevans letezo szkriptek:
  - `./scripts/check.sh`
  - `python3 scripts/validate_nesting_solution.py --help`

## 🌍 Lokalizacio
N/A

## 📎 Kapcsolodasok
- `tmp/egyedi_solver/mvp_terv_tablas_nesting_fix_w_h_alakos_tabla_alap_a_meglevo_vrs_nesting_repora_epitve.md`
- `tmp/egyedi_solver/uj_tablas_solver_fix_w_h_alakos_stock_komplett_dokumentacio.md`
- `tmp/egyedi_solver/tablas_optimalizacios_algoritmus_jagua_rs_integracio_reszletes_rendszerleiras.md`
- `canvases/egyedi_solver/stock_holes_native_support.md`
- `canvases/egyedi_solver/jagua_rs_feasibility_integration.md`
