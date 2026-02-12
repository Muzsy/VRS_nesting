# DXF import konvencios layer-feldolgozas implementacio

## 🎯 Funkcio
Ez a task a P1-DXF-01 es P1-DXF-02 kovetelmenyeket zarja: bevezeti a konvencios DXF import layer-feldolgozast (`CUT_OUTER`, `CUT_INNER`) egy dedikalt importer modulban, determinisztikus hibakodokkal.
A cel, hogy a repo-ban valos kod legyen a hianyzott `vrs_nesting/dxf/importer.py` helyen, es legyen ra futtathato smoke ellenorzes a standard gate-ben.

## 🧠 Fejlesztesi reszletek
### Scope
- Benne van:
  - `vrs_nesting/dxf/importer.py` letrehozasa DXF layer-konvencio feldolgozassal.
  - Determinisztikus hibakodok bevezetese import-hibakra (`DXF_NO_OUTER_LAYER`, `DXF_MULTIPLE_OUTERS`, `DXF_OPEN_OUTER_PATH`, `DXF_OPEN_INNER_PATH`, `DXF_UNSUPPORTED_ENTITY_TYPE`).
  - Konnyu smoke script + fixture mintak a gate-be kotheto ellenorzeshez.
- Nincs benne:
  - Geometriai offset/polygonize pipeline (`vrs_nesting/geometry/*`).
  - Teljes CLI projekt-schema atallitas DXF-only part workflowra.

### Erintett fajlok
- `vrs_nesting/dxf/importer.py`
- `scripts/smoke_dxf_import_convention.py`
- `samples/dxf_import/part_contract_ok.json`
- `samples/dxf_import/part_missing_outer.json`
- `samples/dxf_import/part_open_outer.json`
- `scripts/check.sh`
- `codex/codex_checklist/egyedi_solver/dxf_import_convention_layers_impl.md`
- `codex/reports/egyedi_solver/dxf_import_convention_layers_impl.md`

### DoD
- [ ] Letrejon a `vrs_nesting/dxf/importer.py`, ami konvencio szerint kezeli a `CUT_OUTER` es `CUT_INNER` retegeket.
- [ ] Az importer determinisztikus hibat ad hianyzo/tobb outer, nyitott kontur es nem tamogatott layer-entitas esetben.
- [ ] Van futtathato smoke script, ami sikeres es hibas fixture eseteket is ellenoriz.
- [ ] A standard gate (`scripts/check.sh`) lefuttatja a DXF import smoke ellenorzest.
- [ ] A reportban DoD -> Evidence matrix ki van toltve valos kodhivatkozasokkal.

### Kockazat + mitigacio + rollback
- Kockazat: a check gate uj lepes miatt tobb helyen bukhat, ha importer API valtozik.
- Mitigacio: smoke script minimalis, determinisztikus fixturekkel fut, kulso csomag nelkul.
- Rollback: a `scripts/check.sh` DXF import smoke szakasza egyben visszavonhato, az importer modul izolan marad.

## 🧪 Tesztallapot
- Kotelezo gate: `./scripts/verify.sh --report codex/reports/egyedi_solver/dxf_import_convention_layers_impl.md`
- Relevans futasok:
  - `./scripts/check.sh`
  - `python3 scripts/smoke_dxf_import_convention.py`

## 🌍 Lokalizacio
N/A

## 📎 Kapcsolodasok
- `tmp/egyedi_solver/mvp_terv_tablas_nesting_fix_w_h_alakos_tabla_alap_a_meglevo_vrs_nesting_repora_epitve.md` (4.2 DXF import)
- `docs/dxf_nesting_app_2_dxf_import_konturok_kinyerese_konvencioval_reszletes.md`
- `codex/reports/egyedi_solver_p1_audit.md` (P1-DXF-01, P1-DXF-02 finding)
- `canvases/egyedi_solver/dxf_import_convention_layers.md`
