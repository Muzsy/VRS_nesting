# DXF exporter fejlesztése BLOCK+INSERT, eredeti geometria-alapú export irányba

## 🎯 Funkcio
A task celja a P0 audit negyedik javitando pontjanak teljesitese: a sheet-enkenti DXF export javitasa ugy, hogy part-geometriat BLOCK definiciokban taroljon, es elhelyezeseket INSERT transformokkal irja ki.

## 🧠 Fejlesztesi reszletek
### Scope
- Benne van:
  - `vrs_nesting/dxf/exporter.py` atallitasa BLOCK+INSERT strategyra.
  - Export source geometriak tamogatasa `parts[].outer_points` + `parts[].holes_points` mezokkel.
  - Rectangle fallback megtartasa, ha geometriapontok nincsenek.
  - Solver IO contract dokumentacio frissitese a part geometriamezokkel.
  - Checklist + report artefaktok letrehozasa es verify futtatasa.
- Nincs benne:
  - DXF importer implementacio.
  - Full CAD entitas tamogatas (ARC/SPLINE), MVP-ben poligon konturok LINE-kent.
  - End-to-end pipeline bekotes project szintrol eredeti DXF visszaemelessel.

### Erintett fajlok
- `canvases/egyedi_solver/dxf_export_block_insert_geometry.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_dxf_export_block_insert_geometry.yaml`
- `vrs_nesting/dxf/exporter.py`
- `docs/solver_io_contract.md`
- `codex/codex_checklist/egyedi_solver/dxf_export_block_insert_geometry.md`
- `codex/reports/egyedi_solver/dxf_export_block_insert_geometry.md`

### DoD
- [ ] Exporter BLOCKS szekcioban partonkenti blokkot general (`PART_<id>` naming).
- [ ] Exporter ENTITIES szekcioban INSERT entitasokkal helyezi el a blokkokat (`x`,`y`,`rotation_deg`).
- [ ] Ha `parts[].outer_points`/`holes_points` adott, a block geometriat ez alapjan generalja; egyebkent rectangle fallback marad.
- [ ] A solver IO contract dokumentacio leirja az opcionális part geometriamezoket.
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/dxf_export_block_insert_geometry.md` PASS.

### Kockazat + mitigacio + rollback
- Kockazat: egyes CAD nezetek eltérően kezelik az INSERT rotation orientaciot.
- Mitigacio: standard DXF group code-ok (BLOCK/ENDBLK/INSERT, group 50 rotacio) hasznalata, plusz rectangle fallback.
- Rollback: exporter visszaallithato a korabbi direkt LINE exportra egy fajl revert-tel.

## 🧪 Tesztallapot
- Kotelezo gate: `./scripts/verify.sh --report codex/reports/egyedi_solver/dxf_export_block_insert_geometry.md`
- Task-specifikus ellenorzesek:
  - `python3 vrs_nesting/dxf/exporter.py --help`
  - geometria alapu export smoke futas ideiglenes input/output jsonnal

## 🌍 Lokalizacio
Nem relevans.

## 📎 Kapcsolodasok
- `codex/reports/egyedi_solver_p0_audit.md`
- `tmp/egyedi_solver/mvp_terv_tablas_nesting_fix_w_h_alakos_tabla_alap_a_meglevo_vrs_nesting_repora_epitve.md`
- `tmp/egyedi_solver/uj_tablas_solver_fix_w_h_alakos_stock_komplett_dokumentacio.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
